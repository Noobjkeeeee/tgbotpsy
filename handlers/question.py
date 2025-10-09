import json
import logging

from aiogram import F, Router, types
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from sqlalchemy import select

from config import ADMIN_CHAT_IDS, GROUP_ID
from database import (
    AsyncSessionLocal,
    Question,
    create_question,
    update_question_answer,
)
from states import Form
from storage import bot
from utils import is_non_empty

logging.basicConfig(level=logging.INFO)
router = Router()

yes_no_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

MAX_TELEGRAM_MSG_LENGTH = 4096

admin_actions_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Ответить еще раз"), KeyboardButton(text="✏️ Редактировать ответ")],
        [KeyboardButton(text="✅ Завершить вопрос"), KeyboardButton(text="🚫 Отменить")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


def split_text(text: str):
    return [text[i:i + MAX_TELEGRAM_MSG_LENGTH] for i in range(0, len(text), MAX_TELEGRAM_MSG_LENGTH)]


async def send_answer_to_group(question_text: str, answer_text: str):
    group_message_prefix = (
        "Рубрика #анонимные_вопросы_психологу.\n\n"
        "Сегодня публикуем новый вопрос и ответ в нашей рубрике.\n\n"
        f"🟢 <b>Вопрос, анонимно:</b> {question_text}\n\n"
        f"🟢 <b>Ответ психолога:</b>\n\n"
    )

    full_message = group_message_prefix + answer_text
    message_parts = split_text(full_message)

    for part in message_parts:
        await bot.send_message(chat_id=GROUP_ID, text=part, parse_mode="HTML")


@router.message(lambda m: m.text == "Задать вопрос психологу")
async def start_question(message: types.Message, state: FSMContext):
    await state.update_data(request_type="Задать вопрос психологу")
    await message.answer("❓ Пожалуйста, введите ваш вопрос (обязательно):")
    await state.set_state(Form.waiting_for_question)


@router.message(StateFilter(Form.waiting_for_question))
async def process_question(message: types.Message, state: FSMContext):
    question = message.text.strip()
    if not is_non_empty(question):
        await message.answer(
            "⚠️ Вопрос не может быть пустым. Пожалуйста, введите ваш вопрос:"
        )
        return
    await state.update_data(question=question)
    preview_text = (
        "📋 <b>ПРЕДВАРИТЕЛЬНЫЙ ПРОСМОТР</b>\n\n"
        "▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️\n"
        "💭 <b>Ваш вопрос:</b>\n"
        f"<i>«{question}»</i>\n"
        "▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️\n\n"
        "✅ Подтвердите отправление заявки, пожалуйста:"
    )
    await message.answer(preview_text, parse_mode="HTML", reply_markup=yes_no_kb)
    await state.set_state(Form.waiting_for_personal_data_agreement_question)


@router.message(StateFilter(Form.waiting_for_personal_data_agreement_question))
async def personal_data_agreement(message: types.Message, state: FSMContext):
    answer = message.text.lower()
    if answer == "/cancel":
        await state.clear()
        await message.answer("❌ Заявка отменена.", reply_markup=ReplyKeyboardRemove())
        return
    if answer not in ["да", "нет"]:
        await message.answer(
            "Пожалуйста, выберите «Да» или «Нет» кнопкой ниже.", reply_markup=yes_no_kb
        )
        return
    if answer == "нет":
        await message.answer(
            "⚠️ Без согласия заявка не может быть отправлена. Ваша заявка отменена.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()
        return

    data = await state.get_data()
    question_text = data.get("question")
    user_id = message.from_user.id

    notification_text = (
        f"🆕 Новый анонимный вопрос\n\n"
        f"<b>❓ ВОПРОС:</b>\n"
        f"<i>«{question_text}»</i>\n\n"
        "💬 Просто ответьте на это сообщение, чтобы отправить ответ в группу."
    )

    admin_messages = []
    for admin_id in ADMIN_CHAT_IDS:
        sent_message = await bot.send_message(
            admin_id, notification_text, parse_mode="HTML"
        )
        admin_messages.append(
            {"admin_id": admin_id, "message_id": sent_message.message_id}
        )

    question_id = await create_question(
        user_id=user_id, question_text=question_text, admin_message_id=None
    )

    async with AsyncSessionLocal() as session:
        question = await session.get(Question, question_id)
        question.admin_messages = json.dumps(admin_messages)
        await session.commit()

    first_admin_msg = admin_messages[0]
    notification_text_with_id = (
        f"🆕 Новый анонимный вопрос №{question_id}\n\n"
        f"<b>❓ ВОПРОС:</b>\n"
        f"<i>«{question_text}»</i>\n\n"
        "💬 Просто ответьте на это сообщение, чтобы отправить ответ в группу."
    )

    await bot.edit_message_text(
        chat_id=first_admin_msg["admin_id"],
        message_id=first_admin_msg["message_id"],
        text=notification_text_with_id,
        parse_mode="HTML",
    )

    await message.answer(
        "Спасибо! Ваш вопрос успешно отправлен. Наши волонтеры-психологи обязательно его рассмотрят и как только ответ будет опубликован - мы Вас сразу же уведомим.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.clear()


@router.message(F.reply_to_message)
async def handle_admin_reply(message: types.Message, state: FSMContext):
    replied_message = message.reply_to_message
    if replied_message.from_user.id != (await bot.get_me()).id:
        return

    admin_id = message.from_user.id
    admin_message_id = replied_message.message_id

    question = await get_question_by_admin_and_message(admin_id, admin_message_id)
    if not question:
        await message.answer("❌ Вопрос не найден.")
        return

    if question.status == "завершен":
        await message.answer(
            "❌ Этот вопрос уже завершен. Ответить больше нельзя.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    await state.update_data(
        question_id=question.id,
        user_id=question.user_id,
        question_text=question.question_text,
        current_answer=message.text,
        admin_message_id=admin_message_id
    )

    await message.answer(
        f"📝 <b>Ответ на вопрос №{question.id}</b>\n\n"
        f"❓ Вопрос: {question.question_text}\n\n"
        f"💬 Ваш ответ ({len(message.text)} символов) готов.\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=admin_actions_kb
    )

    await state.set_state(Form.waiting_for_admin_action)


@router.message(StateFilter(Form.waiting_for_admin_action))
async def handle_admin_action(message: types.Message, state: FSMContext):
    action = message.text
    data = await state.get_data()

    question_id = data.get("question_id")
    user_id = data.get("user_id")
    question_text = data.get("question_text")
    current_answer = data.get("current_answer")

    if action == "📝 Ответить еще раз":
        await message.answer(
            "📝 Отправьте дополнительный ответ к этому вопросу:",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(Form.waiting_for_additional_answer)

    elif action == "✏️ Редактировать ответ":
        preview_answer = current_answer[:1000] + "..." if len(current_answer) > 1000 else current_answer

        await message.answer(
            f"✏️ <b>Текущий ответ</b> ({len(current_answer)} символов):\n\n"
            f"{preview_answer}\n\n"
            "Отправьте исправленную версию ответа:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(Form.waiting_for_edited_answer)

    elif action == "✅ Завершить вопрос":
        await send_answer_to_group(question_text, current_answer)

        await bot.send_message(
            chat_id=user_id,
            text="✅ Ваш вопрос опубликован в группе. Спасибо за доверие!"
        )

        await update_question_answer(question_id, current_answer, status="завершен")

        await message.answer(
            f"✅ Вопрос №{question_id} завершен. Ответ отправлен в группу и пользователь уведомлен.",
            reply_markup=ReplyKeyboardRemove()
        )

        await state.clear()

    elif action == "🚫 Отменить":
        await message.answer(
            "❌ Действие отменено. Вы можете ответить на вопрос позже.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()

    else:
        await message.answer(
            "Пожалуйста, выберите действие с помощью кнопок ниже:",
            reply_markup=admin_actions_kb
        )


@router.message(StateFilter(Form.waiting_for_additional_answer))
async def handle_additional_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_answer = data.get("current_answer", "")
    new_answer = message.text

    combined_answer = current_answer + "\n\n" + new_answer

    await state.update_data(current_answer=combined_answer)

    await message.answer(
        f"📝 <b>Ответ обновлен</b>\n\n"
        f"Теперь ответ состоит из {len(combined_answer)} символов.\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=admin_actions_kb
    )

    await state.set_state(Form.waiting_for_admin_action)


@router.message(StateFilter(Form.waiting_for_edited_answer))
async def handle_edited_answer(message: types.Message, state: FSMContext):
    await state.update_data(current_answer=message.text)

    preview_answer = message.text[:500] + "..." if len(message.text) > 500 else message.text

    await message.answer(
        f"✏️ <b>Ответ отредактирован</b>\n\n"
        f"Теперь ответ состоит из {len(message.text)} символов.\n\n"
        f"<b>Предпросмотр:</b>\n{preview_answer}\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=admin_actions_kb
    )

    await state.set_state(Form.waiting_for_admin_action)


async def get_question_by_admin_and_message(admin_id: int, message_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Question))
        questions = result.scalars().all()
        for q in questions:
            if q.admin_messages:
                admin_msgs = json.loads(q.admin_messages)
                for admin_msg in admin_msgs:
                    if (
                            admin_msg["admin_id"] == admin_id
                            and admin_msg["message_id"] == message_id
                    ):
                        return q
    return None
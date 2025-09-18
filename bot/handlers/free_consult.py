import re

from aiogram import Router, types
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from bot.config import ADMIN_CHAT_IDS
from bot.database import Application, AsyncSessionLocal
from bot.logger import error_logger, logger
from bot.states import Form
from bot.utils import is_non_empty, validate_email, validate_tg_account

router = Router()

yes_no_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]],
    resize_keyboard=True,
    one_time_keyboard=True,
)


async def save_application(data: dict, user: types.User):
    async with AsyncSessionLocal() as session:
        app = Application(
            user_id=user.id,
            username=user.username or "",
            request_type=data.get("request_type", ""),
            name=data.get("name", ""),
            phone=data.get("phone", ""),
            description=data.get("description", ""),
            email=data.get("email", ""),
            tg_account=data.get("tg_account", ""),
            status="новая",
        )
        session.add(app)
        await session.commit()
        await session.refresh(app)
        return app


async def notify_admin_about_application(bot, application: Application):
    status_emoji = {
        "новая": "🆕",
        "принята": "✅",
        "отклонена": "❌",
        "на_доработке": "✏️",
    }

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Принять", callback_data=f"accept_{application.id}"
                ),
                InlineKeyboardButton(
                    text="Отклонить", callback_data=f"reject_{application.id}"
                ),
            ]
        ]
    )

    text = (
        f"{status_emoji.get(application.status, '📩')} Заявка №{application.id}\n"
        f"<b>Тип</b>: {application.request_type}\n"
        f"<b>Имя</b>: {application.name}\n"
        f"<b>Телефон</b>: {application.phone or 'не указан'}\n"
        f"<b>Описание</b>: {application.description}\n"
        f"<b>E-mail</b>: {application.email}\n"
        f"<b>Telegram</b>: {application.tg_account or 'не указан'}\n"
        f"<b>Статус</b>: {application.status}\n"
    )

    if application.admin_comment:
        text += f"\n📋 Комментарий админа: {application.admin_comment}"

    for admin_id in ADMIN_CHAT_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id, text=text, parse_mode="HTML", reply_markup=markup
            )
        except Exception as e:
            error_logger.error(
                f"Не удалось отправить уведомление администратору {admin_id}: {e}"
            )


@router.message(lambda m: m.text == "Запросить бесплатную видеоконсультацию")
async def start_free_consult(message: types.Message, state: FSMContext):
    try:
        await state.update_data(request_type="Запросить бесплатную видеоконсультацию")
        await message.answer("👤 Введите ваше имя (обязательно):")
        await state.set_state(Form.waiting_for_name_free)
    except Exception as e:
        error_logger.error(
            f"Ошибка в start_free_consult для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(Form.waiting_for_name_free))
async def process_name(message: types.Message, state: FSMContext):
    try:
        name = message.text.strip()
        if not is_non_empty(name):
            await message.answer("⚠️ Имя обязательно. Пожалуйста, введите ваше имя:")
            return
        await state.update_data(name=name)
        await message.answer(
            '📞 Введите ваш контактный номер телефона (не обязательно) в формате: +79XXXXXXXXX).\n\nЕсли не хотите указывать телефон, напишите "пропустить":'
        )
        await state.set_state(Form.waiting_for_phone_free)
    except Exception as e:
        error_logger.error(
            f"Ошибка в process_name для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(Form.waiting_for_phone_free))
async def process_phone(message: types.Message, state: FSMContext):
    try:
        phone = message.text.strip()

        if phone.lower() in ["пропустить", "skip", "нет", "не хочу"]:
            await state.update_data(phone="")
            await message.answer(
                "💬 Опишите кратко вашу проблему/вопрос (обязательно):"
            )
            await state.set_state(Form.waiting_for_description_free)
            return

        if phone and not re.fullmatch(r"\+79\d{9}", phone):
            await message.answer(
                '⚠️ Телефон должен быть в формате +79XXXXXXXXX и содержать ровно 11 цифр. Введите номер ещё раз или напишите "пропустить":'
            )
            return

        await state.update_data(phone=phone)
        await message.answer("💬 Опишите кратко вашу проблему/вопрос (обязательно):")
        await state.set_state(Form.waiting_for_description_free)
    except Exception as e:
        error_logger.error(
            f"Ошибка в process_phone для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(Form.waiting_for_description_free))
async def process_description(message: types.Message, state: FSMContext):
    try:
        description = message.text.strip()
        if not is_non_empty(description):
            await message.answer(
                "⚠️ Описание обязательно. Пожалуйста, опишите проблему или вопрос:"
            )
            return
        await state.update_data(description=description)
        await message.answer("✉️ Введите ваш e-mail (обязательно):")
        await state.set_state(Form.waiting_for_email_free)
    except Exception as e:
        error_logger.error(
            f"Ошибка в process_description для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(Form.waiting_for_email_free))
async def process_email(message: types.Message, state: FSMContext):
    try:
        email = message.text.strip()
        if not validate_email(email):
            await message.answer(
                "⚠️ Пожалуйста, введите корректный e-mail, например: example@domain.com"
            )
            return
        await state.update_data(email=email)
        await message.answer(
            '📱 Введите ваш аккаунт в Телеграме (не обязательно) должен начинаться с @).\n\nЕсли не хотите указывать Telegram, напишите "пропустить":'
        )
        await state.set_state(Form.waiting_for_tg_account_free)
    except Exception as e:
        error_logger.error(
            f"Ошибка в process_email для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(Form.waiting_for_tg_account_free))
async def process_tg_account(message: types.Message, state: FSMContext):
    try:
        tg_account = message.text.strip()

        if tg_account.lower() in ["пропустить", "skip", "нет", "не хочу"]:
            await state.update_data(tg_account="")
            await confirm_data(message, state)
            return

        if tg_account and not validate_tg_account(tg_account):
            await message.answer(
                "⚠️ Telegram аккаунт должен начинаться с '@' и содержать только латинские буквы, цифры или '_'. Введите ещё раз или напишите \"пропустить\":"
            )
            return

        await state.update_data(tg_account=tg_account)
        await confirm_data(message, state)
    except Exception as e:
        error_logger.error(
            f"Ошибка в process_tg_account для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


async def confirm_data(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()

        phone_text = data.get("phone", "не указан")
        tg_text = data.get("tg_account", "не указан")

        text = (
            "Пожалуйста, подтвердите согласие на обработку персональных данных и отправку заявки.\n\n"
            "<b>Введённые данные:</b>\n\n"
            f"👤 <b>Имя:</b> {data.get('name')}\n"
            f"📞 <b>Телефон:</b> {phone_text}\n"
            f"💬 <b>Описание:</b> {data.get('description')}\n"
            f"✉️ <b>E-mail:</b> {data.get('email')}\n"
            f"📱 <b>Telegram:</b> {tg_text}\n\n"
            "📄 Пожалуйста, ознакомьтесь с нашей "
            "<a href='https://p-d.tel/person_data/'>Политикой обработки персональных данных</a>.\n\n"
            "✅ Напишите «согласен» для подтверждения или «не согласен» для отмены заявки."
        )
        await message.answer(text, parse_mode="HTML")
        logger.info(
            f"Пользователю {message.from_user.id} показана ссылка на политику персональных данных перед соглашением"
        )
        await state.set_state(Form.waiting_for_personal_data_agreement_free)
    except Exception as e:
        error_logger.error(
            f"Ошибка в confirm_data для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(Form.waiting_for_personal_data_agreement_free))
async def personal_data_agreement(message: types.Message, state: FSMContext):
    try:
        answer = message.text.lower()
        logger.info(
            f"Пользователь {message.from_user.id} ответил '{answer}' на соглашение о политике использования персональных данных"
        )

        if answer not in ["согласен", "не согласен"]:
            await message.answer("Пожалуйста, напишите «согласен» или «не согласен».")
            return
        if answer == "не согласен":
            await message.answer(
                "⚠️ Без согласия на обработку персональных данных заявка не может быть отправлена. Ваша заявка отменена.",
                reply_markup=ReplyKeyboardRemove(),
            )
            await state.clear()
            return

        data = await state.get_data()
        app = await save_application(data, message.from_user)
        await notify_admin_about_application(message.bot, app)

        await message.answer(
            f"✅ <b>Спасибо! Ваша заявка №{app.id} на бесплатную видеоконсультацию создана и будет рассмотрена.</b>\n\n"
            "Мы ценим ваше доверие и свяжемся с вами в ближайшее время.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()
    except Exception as e:
        error_logger.error(
            f"Ошибка в personal_data_agreement для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")

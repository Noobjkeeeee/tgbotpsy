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

from config import ADMIN_CHAT_IDS
from database import Application, AsyncSessionLocal
from logger import error_logger, logger
from states import Form
from utils import is_non_empty, validate_email, validate_tg_account

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
        f"📩 Заявка №{application.id}\n"
        f"<b>Тип</b>: {application.request_type}\n"
        f"<b>Имя</b>: {application.name}\n"
        f"<b>Телефон</b>: {application.phone}\n"
        f"<b>Описание</b>: {application.description}\n"
        f"<b>E-mail</b>: {application.email}\n"
        f"<b>Telegram</b>: {application.tg_account}\n"
        f"<b>Статус</b>: {application.status}\n"
    )
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id, text=text, parse_mode="HTML", reply_markup=markup
            )
        except Exception as e:
            error_logger.error(
                f"Не удалось отправить уведомление администратору {admin_id}: {e}"
            )


@router.message(lambda m: m.text == "Запросить платную видеоконсультацию")
async def start_paid_consult(message: types.Message, state: FSMContext):
    try:
        await state.update_data(request_type="Запросить платную видеоконсультацию")
        await message.answer("👤 Введите ваше имя (обязательно):")
        await state.set_state(Form.waiting_for_name_paid)
    except Exception as e:
        error_logger.error(
            f"Ошибка в start_paid_consult для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(Form.waiting_for_name_paid))
async def process_name(message: types.Message, state: FSMContext):
    try:
        name = message.text.strip()
        if not is_non_empty(name):
            await message.answer("⚠️ Имя обязательно. Пожалуйста, введите ваше имя:")
            return
        await state.update_data(name=name)
        await message.answer(
            "📞 Введите контактный номер телефона (обязательно, формат: +79XXXXXXXXX):"
        )
        await state.set_state(Form.waiting_for_phone_paid)
    except Exception as e:
        error_logger.error(
            f"Ошибка в process_name для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(Form.waiting_for_phone_paid))
async def process_phone(message: types.Message, state: FSMContext):
    try:
        phone = message.text.strip()
        if not re.fullmatch(r"\+79\d{9}", phone):
            await message.answer(
                "⚠️ Телефон должен быть в формате +79XXXXXXXXX и содержать ровно 11 цифр. Введите номер ещё раз:"
            )
            return
        await state.update_data(phone=phone)
        await message.answer("💬 Опишите кратко вашу проблему/вопрос (обязательно):")
        await state.set_state(Form.waiting_for_description_paid)
    except Exception as e:
        error_logger.error(
            f"Ошибка в process_phone для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(Form.waiting_for_description_paid))
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
        await state.set_state(Form.waiting_for_email_paid)
    except Exception as e:
        error_logger.error(
            f"Ошибка в process_description для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(Form.waiting_for_email_paid))
async def process_email(message: types.Message, state: FSMContext):
    try:
        email = message.text.strip()
        if not validate_email(email):
            await message.answer(
                "⚠️ Пожалуйста, введите корректный e-mail, например: example@mail.ru"
            )
            return
        await state.update_data(email=email)
        await message.answer(
            "📱 Введите ваш аккаунт в Телеграме (обязательно, должно начинаться с @):"
        )
        await state.set_state(Form.waiting_for_tg_account_paid)
    except Exception as e:
        error_logger.error(
            f"Ошибка в process_email для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(Form.waiting_for_tg_account_paid))
async def process_tg_account(message: types.Message, state: FSMContext):
    try:
        tg_account = message.text.strip()
        if not validate_tg_account(tg_account):
            await message.answer(
                "⚠️ Telegram аккаунт должен начинаться с '@' и содержать только латинские буквы, цифры или '_'. Введите ещё раз:"
            )
            return
        await state.update_data(tg_account=tg_account)
        await message.answer(
            "📋 Пожалуйста, подтвердите согласие на оказание платных услуг:\nНапишите «согласен» или «не согласен»."
        )
        await state.set_state(Form.waiting_for_paid_agreement)
    except Exception as e:
        error_logger.error(
            f"Ошибка в process_tg_account для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(Form.waiting_for_paid_agreement))
async def process_paid_agreement(message: types.Message, state: FSMContext):
    try:
        answer = message.text.lower()
        if answer not in ["согласен", "не согласен"]:
            await message.answer("Пожалуйста, напишите «согласен» или «не согласен».")
            return
        if answer == "не согласен":
            await message.answer(
                "⚠️ Для платной видеоконсультации необходимо согласие на оказание платных услуг. Заявка отменена.",
                reply_markup=ReplyKeyboardRemove(),
            )
            await state.clear()
            return
        logger.info(
            f"Пользователю {message.from_user.id} отправлено подтверждение согласия на платные услуги"
        )

        data = await state.get_data()
        confirm_text = (
            "Пожалуйста, подтвердите согласие на обработку персональных данных и отправку заявки.\n\n"
            "<b>Введённые данные:</b>\n\n"
            f"👤 <b>Имя:</b> {data.get('name')}\n"
            f"📞 <b>Телефон:</b> {data.get('phone')}\n"
            f"💬 <b>Описание:</b> {data.get('description')}\n"
            f"✉️ <b>E-mail:</b> {data.get('email')}\n"
            f"📱 <b>Telegram:</b> {data.get('tg_account')}\n\n"
            "📄 Пожалуйста, ознакомьтесь с нашей "
            "<a href='https://p-d.tel/person_data/'>Политикой обработки персональных данных</a>.\n\n"
            "✅ Напишите «согласен» для подтверждения или «не согласен» для отмены заявки."
        )
        await message.answer(confirm_text, parse_mode="HTML")
        logger.info(
            f"Пользователю {message.from_user.id} показана ссылка на политику персональных данных перед соглашением"
        )
        await state.set_state(Form.waiting_for_personal_data_agreement_paid)
    except Exception as e:
        error_logger.error(
            f"Ошибка в process_paid_agreement для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(Form.waiting_for_personal_data_agreement_paid))
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
                "⚠️ Без согласия на обработку персональных данных заявка не может быть отправлена. Заявка отменена.",
                reply_markup=ReplyKeyboardRemove(),
            )
            await state.clear()
            return

        data = await state.get_data()
        app = await save_application(data, message.from_user)
        await notify_admin_about_application(message.bot, app)

        await message.answer(
            f"✅ <b>Заявка №{app.id} создана и будет рассмотрена!</b>\n\n"
            "Мы ценим ваше доверие и свяжемся с вами в ближайшее время для согласования времени и оплаты консультации.",
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

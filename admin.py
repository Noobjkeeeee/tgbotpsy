from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from database import Application, AsyncSessionLocal
from logger import error_logger

admin_router = Router()


class RejectReason(StatesGroup):
    waiting_for_reason = State()
    application_id = State()


@admin_router.callback_query(F.data.startswith("accept_"))
async def accept_application(callback: CallbackQuery):
    app_id = int(callback.data.split("_")[1])

    async with AsyncSessionLocal() as session:
        application = await session.get(Application, app_id)
        if not application:
            return await callback.answer("Заявка не найдена или уже обработана.")

        if application.status != "новая":
            return await callback.answer(
                "Эта заявка уже была обработана.", show_alert=True
            )

        application.status = "принята"
        await session.commit()

    try:
        await callback.bot.send_message(
            application.user_id,
            f"Ваша заявка №{application.id} подтверждена. Скоро с вами свяжутся.",
        )
    except Exception as e:
        error_logger.error(
            f"Не удалось отправить уведомление пользователю {application.user_id} по заявке №{application.id}: {e}"
        )

    await callback.answer("Заявка принята")
    await callback.message.edit_reply_markup(reply_markup=None)


@admin_router.callback_query(F.data.startswith("reject_"))
async def reject_application(callback: CallbackQuery, state: FSMContext):
    app_id = int(callback.data.split("_")[1])

    async with AsyncSessionLocal() as session:
        application = await session.get(Application, app_id)
        if not application:
            return await callback.answer("Заявка не найдена или уже обработана.")

        if application.status != "новая":
            return await callback.answer(
                "Эта заявка уже была обработана.", show_alert=True
            )

    await state.update_data(application_id=app_id)
    await state.set_state(RejectReason.waiting_for_reason)

    await callback.message.answer(f"Введите причину отклонения заявки №{app_id}:")
    await callback.answer()


@admin_router.message(RejectReason.waiting_for_reason)
async def process_reject_reason(message: Message, state: FSMContext):
    reason = message.text
    data = await state.get_data()
    app_id = data.get("application_id")

    async with AsyncSessionLocal() as session:
        application = await session.get(Application, app_id)
        if not application:
            await message.answer("Заявка не найдена или уже обработана.")
            await state.clear()
            return

        application.status = "отклонена"
        application.admin_comment = reason
        await session.commit()

    try:
        await message.bot.send_message(
            application.user_id,
            f"❌ <b>Ваша заявка №{application.id} отклонена.</b>\n"
            f"📋 <i>Причина:</i> {reason}",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
    except Exception as e:
        error_logger.error(
            f"Не удалось отправить уведомление пользователю {application.user_id} по заявке №{application.id}: {e}"
        )

    await message.answer(f"Заявка №{application.id} отклонена с причиной: {reason}")
    await state.clear()

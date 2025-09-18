import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from aiogram.filters.command import CommandStart
from aiogram.fsm.context import FSMContext

from bot.admin import admin_router
from bot.handlers import free_consult, paid_consult, question
from bot.keyboards import menu_kb
from bot.logger import error_logger
from bot.states import Form
from bot.storage import bot, dp

import uvicorn

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запускаем бот как задачу в фоне
    bot_task = asyncio.create_task(dp.start_polling(bot))
    logging.info("Bot polling запущен")
    try:
        yield
    finally:
        # При завершении — останавливаем задачу
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            logging.info("Bot polling остановлен")
        # Закрываем сессию бота
        await bot.session.close()
        logging.info("Сессия бота закрыта")

app = FastAPI(lifespan=lifespan)

dp.include_router(question.router)
dp.include_router(free_consult.router)
dp.include_router(paid_consult.router)
dp.include_router(admin_router)

@app.get("/", response_class=PlainTextResponse)
async def root():
    return "Telegram bot is running"

@dp.message(CommandStart())
async def cmd_start(message, state: FSMContext):
    try:
        await message.answer(
            "Здравствуйте! Я помогу вам отправить заявку. Выберите тип заявки:",
            reply_markup=menu_kb,
        )
        await state.set_state(Form.waiting_for_type)
    except Exception as e:
        error_logger.error(
            f"Ошибка в обработчике команд /start для пользователя {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer(
            "Произошла ошибка при обработке команды /start. Попробуйте позднее."
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
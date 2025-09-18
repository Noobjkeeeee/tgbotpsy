import os
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from aiogram.filters.command import CommandStart
from aiogram.fsm.context import FSMContext

from admin import admin_router
from handlers import free_consult, paid_consult, question
from keyboards import menu_kb
from logger import error_logger
from states import Form
from storage import bot, dp

import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot_task = None

async def run_bot():
    try:
        dp.include_router(question.router)
        dp.include_router(free_consult.router)
        dp.include_router(paid_consult.router)
        dp.include_router(admin_router)

        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook удален, начинается polling")

        await cmd_start(bot)

        await dp.start_polling(bot)
    except Exception as exc:
        logger.error(f"Ошибка в основном цикле бота: {exc}", exc_info=True)
        raise


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

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_task
    try:
        bot_task = asyncio.create_task(run_bot())
        logger.info("Бот запущен через FastAPI lifespan")
        yield
    finally:
        if bot_task:
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                logger.info("Бот корректно остановлен")

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "running", "service": "MyDialogue Telegram Bot"}

def start_fastapi():
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting FastAPI server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    start_fastapi()

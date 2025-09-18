import os
import logging
import multiprocessing
import asyncio

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
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

app = FastAPI()

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

def start_bot():
    logging.info("Starting Telegram bot polling")
    asyncio.run(dp.start_polling(bot))
    asyncio.run(bot.session.close())
    logging.info("Telegram bot session closed")


def start_fastapi():
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting FastAPI server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    bot_process = multiprocessing.Process(target=start_bot)
    bot_process.start()

    start_fastapi()

    bot_process.join()
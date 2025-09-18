import asyncio
import logging
import os

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

async def main():
    logging.basicConfig(level=logging.INFO)

    port = int(os.getenv("PORT", 8000))

    config = uvicorn.Config(app=app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)

    polling_task = asyncio.create_task(dp.start_polling(bot))
    server_task = asyncio.create_task(server.serve())

    await asyncio.gather(polling_task, server_task)

if __name__ == "__main__":
    asyncio.run(main())
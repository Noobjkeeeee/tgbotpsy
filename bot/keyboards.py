from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Задать вопрос психологу")],
        [KeyboardButton(text="Запросить бесплатную видеоконсультацию")],
        [KeyboardButton(text="Запросить платную видеоконсультацию")],
    ],
    resize_keyboard=True,
)

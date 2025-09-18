import re
from typing import Dict


def validate_tg_account(tg_account: str) -> bool:
    """
    Проверяет, что telegram аккаунт начинается с '@' и содержит валидные символы.
    """
    pattern = r"^@[a-zA-Z0-9_]{5,32}$"
    return re.match(pattern, tg_account) is not None


def validate_email(email: str) -> bool:
    """
    Проверяет корректность e-mail с помощью регулярного выражения.
    Возвращает True, если email валиден, иначе False.
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_phone(phone: str) -> bool:
    """
    Проверка телефонного номера:
    номер должен начинаться с +79 и далее строго 9 цифр.
    """
    pattern = r"^\+79\d{9}$"
    return re.match(pattern, phone) is not None


def format_notification(data: Dict) -> str:
    """
    Форматирует текст уведомления для администратора на основе данных заявки.
    Ожидается, что data содержит:
    - request_type, question или name, phone, description, email, tg_account, и др.
    """
    rt = data.get("request_type", "Неизвестный тип заявки")

    if rt == "Задать вопрос психологу":
        text = (
            "Новая заявка: Анонимный вопрос\n"
            f"Вопрос: {data.get('question', 'не указано')}\n"
        )
    else:
        text = (
            f"Новая заявка: {rt}\n"
            f"Имя: {data.get('name', 'не указано')}\n"
            f"Телефон: {data.get('phone', 'не указан')}\n"
            f"Описание: {data.get('description', 'не указано')}\n"
            f"E-mail: {data.get('email', 'не указано')}\n"
            f"Telegram: {data.get('tg_account', 'не указан')}\n"
        )
    return text


def check_personal_data_consent(answer: str) -> bool:
    """
    Проверяет ответ пользователя по согласию на обработку персональных данных.
    Ожидается ответ 'да' или 'нет' (регистр не важен).
    Возвращает True, если ответ положительный.
    """
    return answer.strip().lower() == "да"


def validate_paid_agreement(answer: str) -> bool:
    """
    Проверяет согласие пользователя с условиями платных услуг.
    Ожидается ответ 'да' или 'нет' (регистр не важен).
    Возвращает True, если согласие есть.
    """
    return answer.strip().lower() == "да"


def is_non_empty(text: str) -> bool:
    """
    Проверка, что строка не пустая и содержит непустые символы.
    """
    return bool(text and text.strip())

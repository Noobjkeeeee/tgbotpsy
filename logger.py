import logging

logger = logging.getLogger("bot_logger")
logger.setLevel(logging.INFO)

if logger.handlers:
    logger.handlers.clear()

file_handler = logging.FileHandler("bot/bot_log.log", encoding="utf-8", mode="a")
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

error_logger = logging.getLogger("error_logger")
error_logger.setLevel(logging.ERROR)

if error_logger.handlers:
    error_logger.handlers.clear()

error_handler = logging.FileHandler("bot/bot_error.log", encoding="utf-8", mode="a")
error_handler.setLevel(logging.ERROR)

error_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
error_handler.setFormatter(error_formatter)

error_logger.addHandler(error_handler)

payment_logger = logging.getLogger("payment_logger")
payment_logger.setLevel(logging.INFO)

if payment_logger.handlers:
    payment_logger.handlers.clear()

payment_handler = logging.FileHandler("bot/payments.log", encoding="utf-8", mode="a")
payment_handler.setLevel(logging.INFO)

payment_formatter = logging.Formatter("%(asctime)s - PAYMENT - %(message)s")
payment_handler.setFormatter(payment_formatter)

payment_logger.addHandler(payment_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

error_console_handler = logging.StreamHandler()
error_console_handler.setLevel(logging.ERROR)
error_console_handler.setFormatter(error_formatter)

payment_console_handler = logging.StreamHandler()
payment_console_handler.setLevel(logging.INFO)
payment_console_handler.setFormatter(payment_formatter)

logger.addHandler(console_handler)
error_logger.addHandler(error_console_handler)
payment_logger.addHandler(payment_console_handler)

logger.propagate = False
error_logger.propagate = False
payment_logger.propagate = False

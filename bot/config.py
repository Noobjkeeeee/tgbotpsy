import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
admin_ids_str = os.getenv("ADMIN_CHAT_IDS", "")
ADMIN_CHAT_IDS = [int(x) for x in admin_ids_str.split(",") if x.strip().isdigit()]
GROUP_ID = int(os.getenv("GROUP_ID", 0))

if not all([BOT_TOKEN, ADMIN_CHAT_IDS, GROUP_ID]):
    raise ValueError("Не все обязательные переменные окружения установлены")

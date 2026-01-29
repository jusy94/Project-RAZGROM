# config_agent4.py
import os
from dotenv import load_dotenv

load_dotenv()

# Используем общий токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
YANDEX_API_KEY_4 = os.getenv("YANDEX_API_KEY_4")
FOLDER_ID_4 = os.getenv("FOLDER_ID_4")
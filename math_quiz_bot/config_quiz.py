# config.py
from dotenv import load_dotenv
load_dotenv()
import os

BOT_TOKEN = "8245328893:AAE-F1JiA7vUIGDqOaT6QCeaWpxGwGuVnys"
YANDEX_API_KEY = "AQVNwJ4heGJ-cqvyM8enCxqkQEwahHLln7Jt-vWc"
FOLDER_ID = "b1g56mq62a5qdqshrhoe"


if not all([BOT_TOKEN, YANDEX_API_KEY, FOLDER_ID]):
    raise ValueError("Не заданы необходимые переменные окружения: BOT_TOKEN, YANDEX_API_KEY, FOLDER_ID")

YANDEX_MODEL_URI = f"gpt://{FOLDER_ID}/yandexgpt/latest"
YANDEX_COMPLETION_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

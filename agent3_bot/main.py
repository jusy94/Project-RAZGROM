# main.py (обновлённая версия)
import asyncio
import logging
import os  # ← добавлено
from dotenv import load_dotenv  # ← добавлено

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from handlers.explanation import router as explanation_router

# ДОБАВЬТЕ ЭТУ СТРОКУ — загружает .env в переменные окружения
load_dotenv()


async def main():
    logging.basicConfig(level=logging.INFO)

    bot_token = os.getenv("BOT_TOKEN")  # теперь будет брать из .env
    if not bot_token:
        raise ValueError("BOT_TOKEN environment variable is required (check .env file!)")

    storage = MemoryStorage()
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)

    dp.include_router(explanation_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
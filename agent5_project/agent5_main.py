# agent5_main.py

from dotenv import load_dotenv
load_dotenv(".env5")  # ← загружаем переменные из .env5
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from handlers5 import setup_handlers
from utils5 import initialize_storage

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Setup handlers
setup_handlers(dp)

# Initialize storage directory
initialize_storage()

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))

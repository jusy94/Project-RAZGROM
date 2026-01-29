# main4.py (обновленный для обработки завершения состояния)
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config4 import BOT_TOKEN
from handler4 import setup_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()  # Хранилище состояний
    dp = Dispatcher(storage=storage)
    setup_handlers(dp)
    logger.info("Бот (агент 4) запускается...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
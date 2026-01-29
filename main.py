import asyncio
import logging
import os
import sys
import traceback  # ← ОБЯЗАТЕЛЬНО ДОБАВЬТЕ!
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart

# Добавляем пути для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Загружаем переменные окружения
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN environment variable is required")

    storage = MemoryStorage()
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)

    # Импортируем роутеры из всех агентов
    try:
        from agent3_bot.handlers.explanation import router as explanation_router
        dp.include_router(explanation_router)
        logger.info("Агент 3 загружен")
    except Exception as e:
        logger.error(f"Ошибка загрузки агента 3: {e}")
        logger.error(traceback.format_exc())  # ← Теперь работает!

    try:
        from agent4.handler4 import router4 as problems_router
        dp.include_router(problems_router)
        logger.info("Агент 4 загружен")
    except Exception as e:
        logger.error(f"Ошибка загрузки агента 4: {e}")
        logger.error(traceback.format_exc())

    try:
        from agent5_project.handlers5 import router as plans_router
        dp.include_router(plans_router)
        logger.info("Агент 5 загружен")
    except Exception as e:
        logger.error(f"Ошибка загрузки агента 5: {e}")
        logger.error(traceback.format_exc())

    try:
        from math_quiz_bot.router import router as quiz_router
        dp.include_router(quiz_router)
        logger.info("Агент Quiz загружен")
    except Exception as e:
        logger.error(f"Ошибка загрузки агента Quiz: {e}")
        logger.error(traceback.format_exc())

    # Импорт нового OCR агента
    try:
        from agent_ocr.handlers.ocr_handler import router as ocr_router
        dp.include_router(ocr_router)
        logger.info("Агент OCR загружен")
    except Exception as e:
        logger.error(f"Ошибка загрузки агента OCR: {e}")
        logger.error(traceback.format_exc())

    # Команда старта
    @dp.message(CommandStart())
    async def cmd_start(message: types.Message):
        text = """Добро пожаловать в объединённого бота для студентов МИФИ!

Доступные команды:
 /explanation - Теоретические объяснения (Агент 3)
 /problems - Решение задач (Агент 4)
 /plans - Планирование и заметки (Агент 5)
 /quiz - Математическая викторина (Агент Quiz)
 /abstract - Конспекты по фотографиям (Агент OCR)

Каждый агент работает независимо. Выберите нужную команду!"""
        await message.answer(text)

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        text = """Список доступных команд:
/start - Начало работы
/explanation - Теоретические объяснения
/problems - Решение задач
/plans - Планирование и заметки
/quiz - Математическая викторина
/abstract - Конспекты по фотографиям
/help - Помощь"""
        await message.answer(text)

    logger.info("Бот запущен со всеми агентами")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
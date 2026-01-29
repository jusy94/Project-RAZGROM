# shared/router_config.py
from aiogram import Router
from aiogram.filters import Command

def setup_main_router(dp, bot_router):
    """Настраивает основной роутер с приоритетом команд"""
    main_router = Router()
    
    @main_router.message(Command("start"))
    async def cmd_start(message):
        text = """
🤖 Добро пожаловать в объединённого бота для студентов МИФИ!

Доступные команды:
📚 /explanation - Теоретические объяснения (Агент 3)
🧮 /problems - Решение задач (Агент 4)
📅 /plans - Планирование и заметки (Агент 5)
🎯 /quiz - Математическая викторина (Агент Quiz)

Каждый агент работает независимо. Выберите нужную команду!
        """
        await message.answer(text)

    @main_router.message(Command("help"))
    async def cmd_help(message):
        text = """
Список доступных команд:
/start - Начало работы
/explanation - Теоретические объяснения
/problems - Решение задач
/plans - Планирование и заметки
/quiz - Математическая викторина
/help - Помощь
        """
        await message.answer(text)

    # Регистрируем основной роутер первым (высший приоритет)
    dp.include_router(main_router)
    dp.include_router(bot_router)
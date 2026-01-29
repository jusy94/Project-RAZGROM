from aiogram import Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage

def setup_dispatcher():
    """Настройка общего диспетчера"""
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    return dp

def register_all_routers(dp):
    """Регистрация всех роутеров"""
    # Импорты внутри функции для избежания циклических зависимостей
    from agent3_bot.handlers.explanation import router as explanation_router
    from agent4.handler4 import router4 as problems_router
    from agent5_project.handlers5 import router as plans_router
    from math_quiz_bot.bot import dp as quiz_dp
    
    dp.include_router(explanation_router)
    dp.include_router(problems_router)
    dp.include_router(plans_router)
    
    # Копируем хендлеры из quiz бота
    for event_type, handlers in quiz_dp.observers.items():
        for handler in handlers.handlers:
            dp.observers[event_type].register(handler)
    
    return dp
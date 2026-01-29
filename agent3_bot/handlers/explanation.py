import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

try:
    from shared.services.yandex_gpt_agent3 import get_yandex_gpt_response
except ImportError:
    # Альтернативный импорт
    import importlib.util
    import sys
    
    # Пытаемся импортировать напрямую
    spec = importlib.util.spec_from_file_location(
        "yandex_gpt_agent3", 
        os.path.join(os.path.dirname(__file__), "..", "..", "shared", "services", "yandex_gpt_agent3.py")
    )
    yandex_gpt_module = importlib.util.module_from_spec(spec)
    sys.modules["yandex_gpt_agent3"] = yandex_gpt_module
    spec.loader.exec_module(yandex_gpt_module)
    from yandex_gpt_agent3 import get_yandex_gpt_response

router = Router()


class ExplanationStates(StatesGroup):
    waiting_for_topic = State()
    waiting_for_problem = State()


@router.message(Command("explanation"))
async def cmd_explanation(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Объяснить тему")],
            [KeyboardButton(text="Помощь с задачей")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Выберите, что хотите объяснить:",
        reply_markup=keyboard
    )
    await state.set_state(ExplanationStates.waiting_for_topic)


@router.message(ExplanationStates.waiting_for_topic, F.text == "Объяснить тему")
async def ask_for_topic(message: Message, state: FSMContext):
    await message.answer("Введите название темы (например: производная сложной функции):")
    await state.set_state(ExplanationStates.waiting_for_topic)


@router.message(ExplanationStates.waiting_for_topic, F.text == "Помощь с задачей")
async def ask_for_problem(message: Message, state: FSMContext):
    await message.answer("Введите формулировку задачи (например: найти предел (sin x)/x при x→0):")
    await state.set_state(ExplanationStates.waiting_for_problem)


@router.message(ExplanationStates.waiting_for_topic)
async def process_topic(message: Message, state: FSMContext):
    user_input = message.text
    instruction = """Ты — агент «АГЕНТ 3» в Telegram-боте для студентов 1-го курса НИЯУ МИФИ. Твоя задача — давать строго теоретические объяснения по математическому анализу: либо по названию темы, либо по формулировке задачи (без решения задачи!).

Правила:
1. Никогда не решай задачу. При запросе вида «Решите...», «Найдите...», «Вычислите...» — определи, какие теоретические приёмы, определения, теоремы нужны для решения, и дай краткую справку по ним.
2. Максимальная длина ответа — 4096 символов. Укладывайся строго.
3. Используй только достоверную, академически верную информацию. Галлюцинации категорически запрещены.
4. Экранируй математические формулы и символы с помощью **звёздочек**, как в Telegram: **x²**, **sin(x)**, **limₓ→₀**, **∫₀¹ f(x) dx**, **ε-δ**. НИКОГДА не используй `$...$`, `$$...$$` или LaTeX-режим.
5. Ответ должен быть структурирован и понятен студенту-первокурснику: без излишней формальности, но без упрощений в ущерб точности.

Формат:
— Если запрос — тема: используй структуру:  Определение,  Формулы/теоремы,  Интуиция,  Ошибки.
— Если запрос — задача: используй структуру:  Что нужно?,  Теоретический минимум,  На что обратить внимание.
— Всегда начинаешь с: «Это АГЕНТ 3 — теоретическая справка по математическому анализу. Ниже — разбор по запросу: [запрос кратко].»
— Если запрос вне темы — ответь: «Запрос выходит за рамки теоретического курса математического анализа 1-го курса МИФИ. Пожалуйста, уточните тему или задачу.»"""

    try:
        response_text = await get_yandex_gpt_response(instruction, user_input)
    except Exception as e:
        response_text = f"Ошибка при обращении к Yandex GPT: {str(e)}"

    await message.answer(response_text)
    await state.clear()


@router.message(ExplanationStates.waiting_for_problem)
async def process_problem(message: Message, state: FSMContext):
    user_input = message.text
    instruction = """Ты — агент «АГЕНТ 3» в Telegram-боте для студентов 1-го курса НИЯУ МИФИ. Твоя задача — давать строго теоретические объяснения по математическому анализу: либо по названию темы, либо по формулировке задачи (без решения задачи!).

Правила:
1. Никогда не решай задачу. При запросе вида «Решите...», «Найдите...», «Вычислите...» — определи, какие теоретические приёмы, определения, теоремы нужны для решения, и дай краткую справку по ним.
2. Максимальная длина ответа — 4096 символов. Укладывайся строго.
3. Используй только достоверную, академически верную информацию. Галлюцинации категорически запрещены.
4. Экранируй математические формулы и символы с помощью **звёздочек**, как в Telegram: **x²**, **sin(x)**, **limₓ→₀**, **∫₀¹ f(x) dx**, **ε-δ**. НИКОГДА не используй `$...$`, `$$...$$` или LaTeX-режим.
5. Ответ должен быть структурирован и понятен студенту-первокурснику: без излишней формальности, но без упрощений в ущерб точности.

Формат:
— Если запрос — тема: используй структуру:  Определение,  Формулы/теоремы,  Интуиция,  Ошибки.
— Если запрос — задача: используй структуру:  Что нужно?,  Теоретический минимум,  На что обратить внимание.
— Всегда начинаешь с: «Это АГЕНТ 3 — теоретическая справка по математическому анализу. Ниже — разбор по запросу: [запрос кратко].»
— Если запрос вне темы — ответь: «Запрос выходит за рамки теоретического курса математического анализа 1-го курса МИФИ. Пожалуйста, уточните тему или задачу.»"""

    try:
        response_text = await get_yandex_gpt_response(instruction, user_input)
    except Exception as e:
        response_text = f"Ошибка при обращении к Yandex GPT: {str(e)}"

    await message.answer(response_text)
    await state.clear()
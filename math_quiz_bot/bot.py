# bot.py

import random
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from math_quiz_bot.config_quiz import BOT_TOKEN
from math_quiz_bot.yandex_gpt_quiz import ask_yandex_gpt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class QuizState(StatesGroup):
    waiting_for_topic = State()
    waiting_for_mode = State()
    answering = State()

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я бот-викторина по математике для студентов 1 курса.\n\n"
        "Напишите тему, например:\n"
        "• Пределы\n• Производные\n• Интегралы\n• Матрицы\n• Векторы\n• ДУ\n\n"
        "Введите тему:"
    )
    await state.set_state(QuizState.waiting_for_topic)

@dp.message(lambda message: message.text and message.text.lower() == "стоп")
async def handle_stop(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Сценарий остановлен.\n"
        "Напишите /start, чтобы начать новую викторину"
    )

@dp.message(QuizState.waiting_for_topic)
async def get_topic(message: Message, state: FSMContext):
    topic = message.text.strip()
    if len(topic) < 2:
        await message.answer("Тема слишком короткая. Попробуйте ещё раз:")
        return
    await state.update_data(topic=topic)
    mode_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Тест (4 варианта)"), KeyboardButton(text="Ввод числа")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(f"Тема: *{topic}*\nВыберите режим:", reply_markup=mode_kb)
    await state.set_state(QuizState.waiting_for_mode)

@dp.message(QuizState.waiting_for_mode)
async def choose_mode(message: Message, state: FSMContext):
    mode_map = {
        "Тест (4 варианта)": "test",
        "Ввод числа": "input"
    }
    if message.text not in mode_map:
        await message.answer("Пожалуйста, выберите режим с помощью кнопок.")
        return

    mode = mode_map[message.text]
    data = await state.get_data()
    topic = data["topic"]

    # Случайные модификаторы для разнообразия
    difficulty = random.choice(["лёгкую", "средней сложности", "нестандартную"])
    task_types_test = [
        "теоретический вопрос и практическую задачу",
        "задачу на вычисление",
        "вопрос на понимание определения",
        "задачу с выбором правильного утверждения"
    ]
    task_types_input = [
        "вычислительную задачу",
        "задачу на нахождение предела/интеграла/производной",
        "уравнение или систему",
        "геометрическую задачу"
    ]

    if mode == "test":
        task_desc = random.choice(task_types_test)
        user_prompt = (
            f"Сгенерируй ОДНУ {difficulty} задачу по теме «{topic}» для студента 1 курса. "
            f"Это должна быть {task_desc}. "
            "Дай ровно 4 варианта ответа в формате: [\"A) ...\", \"B) ...\", \"C) ...\", \"D) ...\"]. "
            "Правильный ответ должен точно совпадать с одним из вариантов. "
            "Не повторяй предыдущие вопросы."
        )
    else:
        task_desc = random.choice(task_types_input)
        user_prompt = (
            f"Сгенерируй ОДНУ {difficulty} {task_desc} по теме «{topic}» для студента 1 курса, "
            "у которой есть **однозначный числовой ответ** (например: целое число, дробь, десятичная дробь, корень и т.д.). "
            "Не используй буквы или слова в ответе. "
            "Не повторяй предыдущие вопросы."
        )

    await message.answer("Генерирую задачу... ")
    quiz_data = await ask_yandex_gpt(user_prompt, mode=mode)

    if not quiz_data:
        await message.answer(
            " Не удалось создать корректную задачу. Это может происходить из-за сложности темы.\n"
            "Попробуйте выбрать другую тему или режим."
        )
        return

    await state.update_data(quiz_data=quiz_data, mode=mode)

    if mode == "test":
        options = quiz_data["options"]
        # Сохраняем options в состоянии для восстановления по индексу
        await state.update_data(options=options)

        # Создаём кнопки с короткими callback_data: ans_0, ans_1, ...
        buttons = []
        for i, opt in enumerate(options):
            buttons.append(InlineKeyboardButton(text=opt, callback_data=f"ans_{i}"))
        # Разбиваем на строки по 2 кнопки
        kb = InlineKeyboardMarkup(inline_keyboard=[
            buttons[:2],
            buttons[2:]
        ])
        await message.answer(f"Вопрос:\n\n{quiz_data['question']}", reply_markup=kb)
    else:
        await message.answer(f"Вопрос:\n\n{quiz_data['question']}\n\nВведите ваш ответ (число):")

    await state.set_state(QuizState.answering)

@dp.callback_query(lambda c: c.data.startswith("ans_"))
async def handle_test_answer(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        index = int(callback.data[4:])  # "ans_2" → 2
    except (ValueError, IndexError):
        await callback.message.answer(" Некорректный выбор.")
        return

    data = await state.get_data()
    options = data.get("options")
    correct = data["quiz_data"]["correct"]

    if options is None or index < 0 or index >= len(options):
        await callback.message.answer(" Ошибка: недопустимый вариант.")
        return

    user_answer = options[index]

    if user_answer == correct:
        result = "Верно!"
    else:
        result = f"Неверно. Правильный ответ: {correct}"

    await callback.message.edit_text(f"{callback.message.text}\n\n{result}")
    await state.set_state(QuizState.waiting_for_topic)
    await callback.message.answer("Готов к новому вопросу! Напишите тему:")

@dp.message(QuizState.answering)
async def handle_input_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    correct_raw = data["quiz_data"]["correct"]

    try:
        correct = float(correct_raw)
    except (ValueError, TypeError):
        await message.answer("Ошибка: правильный ответ не является числом. Начните заново — напишите тему.")
        await state.clear()
        return

    try:
        user_num = float(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите число (например: 3.14 или -5).")
        return

    if abs(user_num - correct) < 1e-6:
        result = "Верно!"
    else:
        result = f"Неверно. Правильный ответ: {correct}"

    await message.answer(result)
    await state.set_state(QuizState.waiting_for_topic) 
    await message.answer("Готов к новому вопросу! Напишите тему:")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
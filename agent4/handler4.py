# handler4.py (полностью переработанный)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re

from .yandex4 import get_gpt_response

router4 = Router(name="problems_router4")

class ProblemsState(StatesGroup):
    waiting_for_task = State()
    waiting_for_confirmation = State()

# Храним контекст для каждого пользователя
user_contexts = {}

def remove_latex(text: str) -> str:
    """Очищает текст от LaTeX-синтаксиса"""
    if not text:
        return text
    
    # Удаляем $...$ и \[...\]
    text = re.sub(r'\$(.*?)\$', r'\1', text)
    text = re.sub(r'\\\[(.*?)\\\]', r'\1', text)
    
    # Заменяем LaTeX-команды
    replacements = {
        '\\int': '∫',
        '\\ln': 'ln',
        '\\frac': '',
        '\\,': ' ',
        '\\ ': ' ',
        '\\cdot': '·',
        '\\times': '×',
        '\\rightarrow': '→',
        '\\to': '→',
        '\\infty': '∞',
        '\\le': '≤',
        '\\ge': '≥',
        '\\neq': '≠',
        '\\in': '∈',
        '\\subset': '⊂'
    }
    
    for latex, normal in replacements.items():
        text = text.replace(latex, normal)
    
    # Удаляем оставшиеся обратные слэши
    text = text.replace('\\', '')
    
    # Удаляем фигурные скобки
    text = text.replace('{', '').replace('}', '')
    
    # Заменяем ^ на степени
    text = re.sub(r'\^(\d)', lambda m: ['', '¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹'][int(m.group(1))], text)
    
    # Удаляем двойные пробелы
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

@router4.message(Command("problems"))
async def cmd_problems(message: Message, state: FSMContext):
    """Начало решения задачи"""
    await state.set_state(ProblemsState.waiting_for_task)
    user_id = message.from_user.id
    
    # Очищаем старый контекст
    if user_id in user_contexts:
        del user_contexts[user_id]
    
    await message.answer(
        "Пришлите задание, с которым необходимо помочь.\n"
        "Я буду объяснять решение по шагам. После каждого шага скажите 'Да' (если понятно) "
        "или 'Нет' (если нужно пояснение)."
    )

@router4.message(ProblemsState.waiting_for_task)
async def handle_task(message: Message, state: FSMContext):
    """Обработка новой задачи"""
    user_id = message.from_user.id
    task_text = message.text.strip()
    
    if task_text.startswith('/'):
        return
    
    # Инициализируем контекст пользователя
    user_contexts[user_id] = {
        "task": task_text,
        "history": [
            {"role": "user", "text": f"Задача: {task_text}. Пожалуйста, начни решение по шагам."}
        ],
        "current_step": 1,
        "last_gpt_response": None
    }
    
    # Получаем первый шаг решения
    response = await get_gpt_response(
        user_contexts[user_id]["history"],
        expecting_next_step=True
    )
    
    response = remove_latex(response)
    
    if response and not response.startswith("Ошибка"):
        # Сохраняем ответ GPT
        user_contexts[user_id]["history"].append({
            "role": "assistant",
            "text": response
        })
        user_contexts[user_id]["last_gpt_response"] = response
        
        # Отправляем пользователю
        await message.answer(response, parse_mode=None)
        await state.set_state(ProblemsState.waiting_for_confirmation)
    else:
        await message.answer("Не удалось начать решение. Попробуйте переформулировать задачу.")
        await state.clear()
        if user_id in user_contexts:
            del user_contexts[user_id]

@router4.message(ProblemsState.waiting_for_confirmation)
async def handle_confirmation(message: Message, state: FSMContext):
    """Обработка ответов пользователя на шаги"""
    user_id = message.from_user.id
    
    if user_id not in user_contexts:
        await message.answer("Сессия завершена. Используйте /problems для новой задачи.")
        await state.clear()
        return
    
    user_input = message.text.strip().lower()
    
    # Проверяем команды завершения
    if user_input in ['/stop', '/стоп', 'завершить', 'выход', 'отмена']:
        await message.answer("Решение прервано. Для новой задачи используйте /problems")
        del user_contexts[user_id]
        await state.clear()
        return
    
    # Получаем контекст
    context = user_contexts[user_id]
    
    # Добавляем ответ пользователя в историю
    context["history"].append({
        "role": "user",
        "text": user_input
    })
    
    # Определяем, что делать
    if user_input in ['да', 'yes', 'понятно', 'ясно', 'согласен', 'дальше']:
        # Пользователь понял шаг - запрашиваем следующий
        response = await get_gpt_response(
            context["history"],
            expecting_next_step=True
        )
        
        response = remove_latex(response)
        
        if response and not response.startswith("Ошибка"):
            # Проверяем, не завершено ли решение
            if "Решение завершено" in response:
                await message.answer(response, parse_mode=None)
                await message.answer(
                    "Решение завершено! Для новой задачи используйте /problems\n"
                    "Если хотите повторить решение этой задачи, также используйте /problems"
                )
                del user_contexts[user_id]
                await state.clear()
                return
            
            # Сохраняем и отправляем следующий шаг
            context["history"].append({
                "role": "assistant",
                "text": response
            })
            context["last_gpt_response"] = response
            context["current_step"] += 1
            
            await message.answer(response, parse_mode=None)
            # Остаемся в состоянии ожидания подтверждения
        else:
            await message.answer("Произошла ошибка. Попробуйте начать заново с /problems")
            del user_contexts[user_id]
            await state.clear()
    
    elif user_input in ['нет', 'no', 'непонятно', 'не понял', 'объясни', 'повтори']:
        # Пользователь не понял - запрашиваем пояснение
        response = await get_gpt_response(
            context["history"],
            expecting_next_step=False  # Не следующий шаг, а пояснение
        )
        
        response = remove_latex(response)
        
        if response and not response.startswith("Ошибка"):
            # Сохраняем и отправляем пояснение
            context["history"].append({
                "role": "assistant",
                "text": response
            })
            context["last_gpt_response"] = response
            
            await message.answer(response, parse_mode=None)
        else:
            await message.answer("Произошла ошибка при объяснении. Попробуйте еще раз.")
    
    else:
        # Некорректный ответ
        await message.answer(
            "Пожалуйста, ответьте:\n"
            "• 'Да' - если шаг понятен и можно перейти к следующему\n"
            "• 'Нет' - если нужно пояснение\n"
            "• '/stop' - чтобы завершить решение"
        )

def setup_handlers(dp):
    dp.include_router(router4)
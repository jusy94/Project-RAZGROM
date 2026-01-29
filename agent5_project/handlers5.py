# handlers5.py - исправленная версия
import json
import os
import re
from datetime import datetime
from typing import Optional, Dict
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from agent5_project.utils_agent5 import (
    call_yandex_gpt, 
    load_user_notes, 
    save_user_note, 
    format_notes_for_display,
    delete_user_note,
    get_note_by_index
)

router = Router()

# States for the bot
class AddNoteStates(StatesGroup):
    waiting_for_note_text = State()
    waiting_for_note_date = State()

class AskAIStates(StatesGroup):
    waiting_for_question = State()

class DeleteNoteStates(StatesGroup):
    waiting_for_note_to_delete = State()
    confirming_deletion = State()

# Temporary cache for pagination
pagination_cache = {}

def setup_handlers(dp):
    dp.include_router(router)

# Главное меню с 4 кнопками
@router.message(Command("plans"))
async def cmd_plans(message: types.Message, state: FSMContext):
    """Обработчик команды /plans"""
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Добавить заметку", callback_data="add_note")],
        [types.InlineKeyboardButton(text="Спросить совет у ИИ", callback_data="ask_ai")],
        [types.InlineKeyboardButton(text="Посмотреть заметки", callback_data="view_notes")],
        [types.InlineKeyboardButton(text="Удалить заметку", callback_data="delete_note")]
    ])
    await message.answer("Выберите действие:", reply_markup=keyboard)
    await state.clear()

# Обработчик для всех callback-кнопок
@router.callback_query()
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик всех callback-запросов"""
    data = callback_query.data
    
    if data == "add_note":
        await state.set_state(AddNoteStates.waiting_for_note_text)
        await callback_query.message.answer("Напишите содержание заметки.")
        await callback_query.answer()
        
    elif data == "ask_ai":
        await state.set_state(AskAIStates.waiting_for_question)
        await callback_query.message.answer("Пришлите задание, с которым необходимо помочь.")
        await callback_query.answer()
        
    elif data == "view_notes":
        user_id = callback_query.from_user.id
        notes = load_user_notes(user_id)
        
        if not notes:
            await callback_query.message.answer("У вас пока нет заметок.")
        else:
            formatted_notes, next_start = format_notes_for_display(notes, 0)
            if next_start is not None:
                pagination_cache[user_id] = next_start
                formatted_notes += "\n… Чтобы посмотреть дальше, напишите 'ещё'."
            
            await callback_query.message.answer(formatted_notes)
        await callback_query.answer()
        
    elif data == "delete_note":
        await delete_note_start(callback_query, state)
        
    elif data and data.startswith("delete_select_"):
        await select_note_for_deletion(callback_query, state)
        
    elif data == "confirm_delete":
        await confirm_deletion(callback_query, state)
        
    elif data == "cancel_delete":
        await cancel_deletion(callback_query, state)
        
    elif data == "back_to_menu":
        await back_to_main_menu(callback_query, state)

# НАЧАЛО УДАЛЕНИЯ ЗАМЕТКИ
async def delete_note_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало процесса удаления заметки"""
    user_id = callback_query.from_user.id
    notes = load_user_notes(user_id)
    
    if not notes:
        await callback_query.message.answer("У вас пока нет заметок для удаления.")
        await callback_query.answer()
        return
    
    # Создаем клавиатуру с заметками
    keyboard_buttons = []
    
    for i, note in enumerate(notes):
        note_preview = note['text'][:30] + "..." if len(note['text']) > 30 else note['text']
        timestamp = note['timestamp']
        button_text = f"{i+1}. {timestamp}: {note_preview}"
        
        keyboard_buttons.append(
            types.InlineKeyboardButton(
                text=button_text,
                callback_data=f"delete_select_{i}"
            )
        )
    
    # Создаем ряды по 2 кнопки в каждом
    rows = []
    for i in range(0, len(keyboard_buttons), 2):
        row = []
        row.append(keyboard_buttons[i])
        if i + 1 < len(keyboard_buttons):
            row.append(keyboard_buttons[i + 1])
        rows.append(row)
    
    # Добавляем кнопку отмены
    rows.append([types.InlineKeyboardButton(text="Отмена", callback_data="cancel_delete")])
    
    # Создаем клавиатуру
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=rows)
    
    await callback_query.message.edit_text(
        "*Выберите заметку для удаления:*\n\n" +
        "\n".join([f"{i+1}. **{note['timestamp']}**: {note['text'][:50]}..." for i, note in enumerate(notes)]),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback_query.answer()

# ВЫБОР ЗАМЕТКИ ДЛЯ УДАЛЕНИЯ
async def select_note_for_deletion(callback_query: types.CallbackQuery, state: FSMContext):
    """Выбор конкретной заметки для удаления"""
    try:
        note_index = int(callback_query.data.split("_")[2])
    except (IndexError, ValueError):
        await callback_query.answer("Ошибка: неверный формат данных")
        return
    
    user_id = callback_query.from_user.id
    note = get_note_by_index(user_id, note_index)
    
    if not note:
        await callback_query.answer("Заметка не найдена")
        return
    
    await state.update_data(
        note_index=note_index,
        note_text=note['text'],
        note_timestamp=note['timestamp']
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="Да, удалить", callback_data="confirm_delete"),
            types.InlineKeyboardButton(text="Нет, отмена", callback_data="cancel_delete")
        ]
    ])
    
    await callback_query.message.edit_text(
        f"*Вы действительно хотите удалить эту заметку?*\n\n"
        f"**Дата:** {note['timestamp']}\n"
        f"**Текст:** {note['text'][:100]}...\n\n"
        f"*Это действие нельзя отменить!*",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback_query.answer()

# ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ
async def confirm_deletion(callback_query: types.CallbackQuery, state: FSMContext):
    """Подтверждение и выполнение удаления"""
    user_id = callback_query.from_user.id
    data = await state.get_data()
    
    note_index = data.get('note_index')
    note_text = data.get('note_text', '')
    note_timestamp = data.get('note_timestamp', '')
    
    if note_index is None:
        await callback_query.answer("Ошибка: не найден индекс заметки")
        return
    
    success = delete_user_note(user_id, note_index)
    
    if success:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Вернуться в меню", callback_data="back_to_menu")]
        ])
        
        await callback_query.message.edit_text(
            f"*Заметка успешно удалена!*\n\n"
            f"Удалено: **{note_timestamp}**\n"
            f"Текст: {note_text[:100]}...",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await callback_query.message.edit_text(
            "*Не удалось удалить заметку.*\n"
            "Попробуйте еще раз или обратитесь к администратору.",
            parse_mode="Markdown"
        )
    
    await state.clear()
    await callback_query.answer()

# ОТМЕНА УДАЛЕНИЯ
async def cancel_deletion(callback_query: types.CallbackQuery, state: FSMContext):
    """Отмена процесса удаления"""
    await state.clear()
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Добавить заметку", callback_data="add_note")],
        [types.InlineKeyboardButton(text="Спросить совет у ИИ", callback_data="ask_ai")],
        [types.InlineKeyboardButton(text="Посмотреть заметки", callback_data="view_notes")],
        [types.InlineKeyboardButton(text="Удалить заметку", callback_data="delete_note")]
    ])
    
    await callback_query.message.edit_text(
        "*Удаление отменено.*\n\n"
        "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback_query.answer()

# ВОЗВРАТ В ГЛАВНОЕ МЕНЮ
async def back_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Добавить заметку", callback_data="add_note")],
        [types.InlineKeyboardButton(text="Спросить совет у ИИ", callback_data="ask_ai")],
        [types.InlineKeyboardButton(text="Посмотреть заметки", callback_data="view_notes")],
        [types.InlineKeyboardButton(text="Удалить заметку", callback_data="delete_note")]
    ])
    
    await callback_query.message.edit_text(
        "Выберите действие:",
        reply_markup=keyboard
    )
    await callback_query.answer()

# --- СУЩЕСТВУЮЩИЙ КОД ---

@router.message(AddNoteStates.waiting_for_note_text, ~F.text.startswith('/'))
async def process_note_text(message: types.Message, state: FSMContext):
    await state.update_data(note_text=message.text)
    await state.set_state(AddNoteStates.waiting_for_note_date)
    await message.answer("Укажите дату и время (как удобно – словами или цифрами).")

@router.message(AddNoteStates.waiting_for_note_date, ~F.text.startswith('/'))
async def process_note_date(message: types.Message, state: FSMContext):
    raw_date = message.text
    prompt = (
        "Ты – конвертер дат. Преобразуй входную дату/время в строгий формат MM-DD HH:MM (24-часовой). "
        "Если не указан год – используй текущий. В ответе дай ТОЛЬКО строку вида: 12-07 15:00. Ничего больше."
    )
    user_input = f"Вход: {raw_date}"
    normalized_date_raw = await call_yandex_gpt(prompt, user_input)

    # Извлекаем дату из ответа
    if normalized_date_raw:
        match = re.search(r"\b(\d{2})[-./](\d{2})\s+(\d{2})[:.](\d{2})\b", normalized_date_raw)
        if match:
            mm, dd, hh, mn = match.groups()
            normalized_date = f"{mm}-{dd} {hh}:{mn}"
        else:
            match = re.search(r"\b(\d{8})\b", normalized_date_raw)
            if match:
                s = match.group(1)
                normalized_date = f"{s[0:2]}-{s[2:4]} {s[4:6]}:{s[6:8]}"
            else:
                normalized_date = None
    else:
        normalized_date = None

    if not normalized_date:
        await message.answer(
            "Не удалось распознать дату. Попробуйте ввести её проще: например, "
            "'15 декабря 14:30' или '12-15 14:30'."
        )
        return

    data = await state.get_data()
    note_text = data.get("note_text", "")
    user_id = message.from_user.id

    save_user_note(user_id, note_text, normalized_date)
    await message.answer(f"Заметка сохранена на {normalized_date}.")
    await state.clear()

@router.message(AskAIStates.waiting_for_question, ~F.text.startswith('/'))
async def process_ai_question(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_question = message.text
    user_notes = load_user_notes(user_id)

    # Prepare context
    context_str = "[Контекст заметок пользователя]\n"
    if user_notes:
        sorted_notes = sorted(user_notes, key=lambda x: x['timestamp'])
        context_str += "\n".join([f"{n['timestamp']}: {n['text']}" for n in sorted_notes])
    else:
        context_str += "Пользователь не имеет заметок."

    system_prompt = """Ты – помощник по тайм-менеджменту для студента 1-го курса МИФИ. Ответь кратко и по делу. Не объясняй, не извиняйся, не добавляй преамбул. Только решение. Макс. 4096 символов."""

    try:
        ai_response = await call_yandex_gpt(system_prompt, user_question, context_str)
        if ai_response:
            full_response = f"Совет от ИИ:\n{ai_response[:4096]}"
        else:
            full_response = "Не удалось обработать запрос. Попробуйте позже."
    except Exception:
        full_response = "Не удалось обработать запрос. Попробуйте позже."

    await message.answer(full_response)
    await state.clear()

@router.message(lambda m: m.text and m.text.strip().lower() == "ещё")
async def handle_more_notes(message: types.Message):
    user_id = message.from_user.id
    start_index = pagination_cache.get(user_id)
    if start_index is None:
        await message.answer("Для продолжения сначала запросите список заметок.")
        return

    notes = load_user_notes(user_id)
    if not notes or start_index >= len(notes):
        await message.answer("Больше заметок нет.")
        if user_id in pagination_cache:
            del pagination_cache[user_id]
        return

    formatted_notes, next_start = format_notes_for_display(notes, start_index)
    if next_start is not None:
        pagination_cache[user_id] = next_start
        formatted_notes += "\n… Чтобы посмотреть дальше, напишите 'ещё'."
    else:
        if user_id in pagination_cache:
            del pagination_cache[user_id]

    await message.answer(formatted_notes)
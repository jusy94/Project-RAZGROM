# utils_agent5.py

import json
import logging
import re
import os
import aiohttp
from datetime import datetime
from typing import Optional, Dict

STORAGE_DIR = "agent5_storage"

def initialize_storage():
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)
        logging.info(f" Создана папка для хранения: {STORAGE_DIR}")

def get_user_file_path(user_id):
    return os.path.join(STORAGE_DIR, f"user_{user_id}_notes.json")

def load_user_notes(user_id):
    file_path = get_user_file_path(user_id)
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_user_note(user_id, text, timestamp):
    # Убедимся, что папка существует
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)
    
    file_path = get_user_file_path(user_id)
    notes = load_user_notes(user_id)
    notes.append({"text": text, "timestamp": timestamp})
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
    
    logging.info(f" Заметка сохранена для пользователя {user_id}")

def format_notes_for_display(notes, start_index):
    if not notes:
        return "Нет заметок", None
    
    sorted_notes = sorted(notes, key=lambda x: x['timestamp'])
    current_msg = ""
    i = start_index
    while i < len(sorted_notes):
        note = sorted_notes[i]
        note_str = f"{note['timestamp']} — {note['text']}\n"
        if len(current_msg) + len(note_str) > 4096:
            if not current_msg:
                # Если одна заметка слишком длинная, обрезаем её
                note_str = note_str[:4096]
                return note_str, None
            return current_msg.rstrip(), i
        current_msg += note_str
        i += 1
    return current_msg.rstrip(), None

async def call_yandex_gpt(system_prompt, user_prompt="", context=""):
    api_key = os.getenv("YANDEX_API_KEY_5")
    folder_id = os.getenv("YANDEX_FOLDER_ID_5")
    
    if not api_key or not folder_id:
        logging.error(" YANDEX_API_KEY_5 или YANDEX_FOLDER_ID_5 не заданы")
        return None

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json"
    }

    messages = [
        {"role": "system", "text": system_prompt},
        {"role": "user", "text": user_prompt}
    ]
    if context:
        messages.insert(1, {"role": "user", "text": f"[Контекст]\n{context}"})

    data = {
        "modelUri": f"gpt://{folder_id}/yandexgpt-lite/latest",
        "completionOptions": {"temperature": 0.1, "maxTokens": "500"},
        "messages": messages
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data, timeout=10) as resp:
                if resp.status == 200:
                    r = await resp.json()
                    text = r["result"]["alternatives"][0]["message"]["text"].strip()
                    logging.info(f" GPT response: {repr(text)}")
                    return text
                else:
                    error_text = await resp.text()
                    logging.error(f" GPT error {resp.status}: {error_text}")
                    return None
        except Exception as e:
            logging.exception(" Exception in call_yandex_gpt")
            return None

def delete_user_note(user_id: int, note_index: int) -> bool:
    """
    Удаляет заметку пользователя по индексу
    Возвращает True если успешно, False если ошибка
    """
    file_path = get_user_file_path(user_id)
    
    if not os.path.exists(file_path):
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            notes = json.load(f)
        
        # Проверяем индекс
        if 0 <= note_index < len(notes):
            # Удаляем заметку
            deleted_note = notes.pop(note_index)
            
            # Сохраняем обновленный список
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(notes, f, ensure_ascii=False, indent=2)
            
            return True
        else:
            return False
            
    except Exception as e:
        logging.error(f"Ошибка при удалении заметки: {e}")
        return False

def get_note_by_index(user_id: int, note_index: int) -> Optional[Dict]:
    """
    Получает заметку по индексу
    """
    notes = load_user_notes(user_id)
    
    if 0 <= note_index < len(notes):
        return notes[note_index]
    return None
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

STORAGE_DIR = "ocr_summaries"

def ensure_storage():
    """Создает директорию для хранения если ее нет"""
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)

def get_user_file_path(user_id: int) -> str:
    """Возвращает путь к файлу конспектов пользователя"""
    return os.path.join(STORAGE_DIR, f"user_{user_id}_summaries.json")

def save_summary(user_id: int, topic: str, content: str, timestamp: str = None) -> bool:
    """Сохраняет конспект пользователя"""
    ensure_storage()
    file_path = get_user_file_path(user_id)
    
    # Загружаем существующие конспекты
    summaries = load_summaries(user_id)
    
    # Используем переданный timestamp или текущее время
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # Проверяем, есть ли уже такая тема (важно для страниц)
    topic_exists = False
    for summary in summaries:
        if summary['topic'] == topic:
            summary['content'] = content
            summary['timestamp'] = timestamp
            topic_exists = True
            break
    
    if not topic_exists:
        summaries.append({
            "topic": topic,
            "content": content,
            "timestamp": timestamp
        })
    
    # Сохраняем обратно
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(summaries, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def load_summaries(user_id: int) -> List[Dict]:
    """Загружает все конспекты пользователя"""
    file_path = get_user_file_path(user_id)
    
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def delete_summary(user_id: int, topic: str) -> bool:
    """Удаляет конспект по теме"""
    summaries = load_summaries(user_id)
    
    # Фильтруем, оставляя все кроме указанной темы
    filtered = [s for s in summaries if s['topic'] != topic]
    
    if len(filtered) == len(summaries):
        return False  # Тема не найдена
    
    # Сохраняем обновленный список
    file_path = get_user_file_path(user_id)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(filtered, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def get_summary_topics(user_id: int) -> List[str]:
    """Возвращает список тем пользователя"""
    summaries = load_summaries(user_id)
    return [s['topic'] for s in summaries]
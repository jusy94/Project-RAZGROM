# yandex4.py (обновленный)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp
import logging

# Используем относительный импорт
from .config_agent4 import YANDEX_API_KEY_4, FOLDER_ID_4

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — решатель задач по математическому анализу для студентов 1 курса НИЯУ МИФИ.\n"
    "ТВОИ СТРОГИЕ ПРАВИЛА ДЛЯ ПОШАГОВОГО РЕШЕНИЯ:\n"
    "\n"
    "1. ВСЕГДА решай задачу ПО ОДНОМУ ШАГУ за раз.\n"
    "2. НИКОГДА не давай следующий шаг, пока пользователь явно не скажет 'Да' на текущий шаг.\n"
    "3. НИКОГДА не отвечай на свой собственный вопрос 'Понятен ли этот шаг?'.\n"
    "4. Формат для КАЖДОГО шага:\n"
    "   **Шаг N: [Короткое название шага]**\n"
    "   [Решение только этого шага]\n"
    "   Понятен ли этот шаг? (Да/Нет)\n"
    "\n"
    "5. Когда пользователь говорит 'Нет' на шаг N:\n"
    "   • В ответе должен быть ТОТ ЖЕ САМЫЙ ШАГ N\n"
    "   • Добавь только ОДНО простое предложение с пояснением в конце шага\n"
    "   • Не переходи к следующему шагу\n"
    "   • Снова спроси 'Понятен ли этот шаг?'\n"
    "\n"
    "6. Когда пользователь говорит 'Да' на шаг N:\n"
    "   • Ты должен замолчать и ждать следующего запроса от системы\n"
    "   • НЕ ГЕНЕРИРУЙ следующий шаг автоматически\n"
    "   • Следующий шаг будет запрошен отдельно\n"
    "\n"
    "7. Когда задача полностью решена:\n"
    "   • Напиши 'Решение завершено. Все шаги понятны?'\n"
    "   • НЕ пиши итоговую формулу еще раз\n"
    "\n"
    "8. АБСОЛЮТНЫЙ ЗАПРЕТ:\n"
    "   • LaTeX: $, \\, \\int, \\ln, \\frac, ^, _, {, }, =, любые обратные слэши\n"
    "   • Самостоятельные переходы между шагами без явного согласия пользователя\n"
    "\n"
    "9. Используй только обычный текст и разрешенные символы:\n"
    "   ∫, ·, ², ³, −, →, ∞, ≤, ≥, ≠\n"
    "   Формулы в **двойных звёздочках**, например: **∫ x·ln x dx**\n"
    "\n"
    "10. Сейчас я дам тебе историю диалога. ОТВЕТЬ ТОЛЬКО НА ПОСЛЕДНЕЕ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ.\n"
    "    Если пользователь сказал 'Да' на шаг — ничего не отвечай (система сама запросит следующий шаг).\n"
    "    Если пользователь сказал 'Нет' — дай пояснение к текущему шагу.\n"
    "    Если пользователь прислал новую задачу — начни с шага 1.\n"
    "\n"
    "Запомни: ты отвечаешь ТОЛЬКО когда пользователь что-то сказал. Если в истории видишь,\n"
    "что пользователь сказал 'Да', то ты должен МОЛЧАТЬ — система сама тебя вызовет для следующего шага.\n"
)

async def get_gpt_response(conversation_history: list, expecting_next_step: bool = False) -> str:
    """
    Получить ответ от GPT на основе истории диалога
    expecting_next_step: True - система запрашивает следующий шаг после 'Да'
                        False - пользователь ответил на вопрос
    """
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY_4}",
        "Content-Type": "application/json"
    }

    model_uri = f"gpt://{FOLDER_ID_4}/yandexgpt-lite"
    
    # Создаем динамический промпт в зависимости от ситуации
    dynamic_prompt = SYSTEM_PROMPT
    
    if expecting_next_step:
        dynamic_prompt += "\n\nСИСТЕМА: Пользователь сказал 'Да' на предыдущий шаг. " \
                         "Пожалуйста, предоставь СЛЕДУЮЩИЙ ШАГ решения. " \
                         "Если задача решена, напиши 'Решение завершено. Все шаги понятны?'"
    
    messages = [{"role": "system", "text": dynamic_prompt}]
    messages.extend(conversation_history)

    payload = {
        "modelUri": model_uri,
        "completionOptions": {
            "maxTokens": "800",
            "temperature": 0.1,
            "stream": False
        },
        "messages": messages
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Ошибка API ({resp.status}): {error_text}")
                    return "Ошибка при обращении к API."
                data = await resp.json()
                # Извлекаем текст
                try:
                    solution = data["result"]["alternatives"][0]["message"]["text"].strip()
                    return solution
                except KeyError as e:
                    logger.error(f"Ответ не содержит ожидаемой структуры: {e}. Ответ: {data}")
                    return "Ошибка: некорректный формат ответа."
    except Exception as e:
        logger.error(f"Исключение при запросе к Yandex GPT: {e}")
        return "Ошибка: невозможно получить ответ от GPT."
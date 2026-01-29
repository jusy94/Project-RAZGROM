# yandex_gpt.py

import json
import re
import logging
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from math_quiz_bot.config_quiz import YANDEX_API_KEY, YANDEX_MODEL_URI, YANDEX_COMPLETION_URL

logger = logging.getLogger(__name__)

def clean_json_response(text: str) -> str:
    match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text.strip()

async def ask_yandex_gpt(prompt: str, mode: str = "test", max_retries: int = 3) -> Optional[Dict[str, Any]]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
    }

    # Уточняем формат в зависимости от режима
    if mode == "test":
        format_example = (
            '{"question": "Чему равен определитель матрицы A?", '
            '"options": ["A) 0", "B) 1", "C) -1", "D) 2"], '
            '"correct": "A) 0", "mode": "test"}'
        )
        instruction = (
            "Ты должен сгенерировать РОВНО ОДНУ задачу в режиме теста. "
            "Массив options должен содержать ровно 4 строки вида 'A) ...', 'B) ...' и т.д. "
            "Поле correct — это одна из этих строк целиком."
        )
    else:
        format_example = '{"question": "Найдите предел при x→0", "correct": 1.0, "mode": "input"}'
        instruction = (
            "Ты должен сгенерировать РОВНО ОДНУ задачу с числовым ответом. "
            "Поле correct должно быть числом (без кавычек)."
        )

    system_prompt = (
        "Ты — генератор математических задач для студентов 1 курса. "
        "Отвечай ТОЛЬКО валидным JSON, без какого-либо текста до или после. "
        f"{instruction}\n\nПример ответа:\n{format_example}"
    )

    for attempt in range(max_retries):
        logger.info(f"Попытка {attempt + 1} для режима '{mode}'")
        payload = {
            "modelUri": YANDEX_MODEL_URI,
            "completionOptions": {"stream": False, "temperature": 0.5, "maxTokens": 1000},
            "messages": [
                {"role": "system", "text": system_prompt},
                {"role": "user", "text": prompt}
            ]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(YANDEX_COMPLETION_URL, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"HTTP {resp.status}: {error_text}")
                        await asyncio.sleep(1.5)
                        continue

                    data = await resp.json()
                    if "result" not in data or "alternatives" not in data["result"]:
                        logger.error(f"Некорректный ответ API: {data}")
                        await asyncio.sleep(1.5)
                        continue

                    raw_text = data["result"]["alternatives"][0]["message"]["text"]
                    logger.debug(f"Raw: {raw_text}")

                    cleaned = clean_json_response(raw_text)
                    logger.debug(f"Cleaned: {cleaned}")

                    try:
                        parsed = json.loads(cleaned)
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON decode error: {e}")
                        await asyncio.sleep(1.5)
                        continue

                    # Валидация
                    if parsed.get("mode") != mode:
                        logger.warning(f"Несоответствие режима: ожидалось {mode}, получено {parsed.get('mode')}")
                        continue

                    if mode == "test":
                        required = {"question", "options", "correct"}
                        if not required.issubset(parsed.keys()):
                            logger.warning("Не хватает полей в test-режиме")
                            continue
                        opts = parsed["options"]
                        if not isinstance(opts, list) or len(opts) != 4:
                            logger.warning("options должен быть списком из 4 элементов")
                            continue
                        if parsed["correct"] not in opts:
                            logger.warning(f"correct не в options: {parsed['correct']} ∉ {opts}")
                            continue
                        return parsed

                    elif mode == "input":
                        if not {"question", "correct"}.issubset(parsed.keys()):
                            logger.warning("Не хватает полей в input-режиме")
                            continue
                        try:
                            parsed["correct"] = float(parsed["correct"])
                        except (TypeError, ValueError):
                            logger.warning("correct не преобразуется в число")
                            continue
                        return parsed

        except Exception as e:
            logger.exception(f"Исключение в ask_yandex_gpt: {e}")
            await asyncio.sleep(1.5)
            continue

    logger.error("Все попытки исчерпаны")
    return None
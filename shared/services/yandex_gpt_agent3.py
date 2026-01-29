# Копия оригинального yandex_gpt.py из agent3_bot
import aiohttp
import os
from typing import Optional


async def get_yandex_gpt_response(instruction: str, input_text: str) -> str:
    api_key = os.getenv("YC_API_KEY")
    folder_id = os.getenv("YC_FOLDER_ID")

    if not api_key or not folder_id:
        raise ValueError("YC_API_KEY and YC_FOLDER_ID environment variables are required")

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.1,
            "maxTokens": "3000"
        },
        "messages": [
            {
                "role": "system",
                "text": instruction
            },
            {
                "role": "user",
                "text": input_text
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status != 200:
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=f"Yandex GPT API error: {response.status}"
                )

            result = await response.json()
            # Extract the text from the first candidate
            if 'result' in result and 'alternatives' in result['result'] and len(result['result']['alternatives']) > 0:
                return result['result']['alternatives'][0]['message']['text']
            else:
                raise ValueError("Unexpected response format from Yandex GPT API")
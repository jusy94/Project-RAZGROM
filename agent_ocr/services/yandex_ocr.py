import aiohttp
import os
import logging
import base64
import json
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

async def extract_text_from_image(image_bytes: bytes) -> Optional[str]:
    """
    Извлекает текст из изображения через Yandex Vision OCR
    """
    api_key = os.getenv("YANDEX_OCR_API_KEY")
    folder_id = os.getenv("YANDEX_OCR_FOLDER_ID")
    
    if not api_key or not folder_id:
        logger.error("❌ YANDEX_OCR_API_KEY или YANDEX_OCR_FOLDER_ID не заданы")
        return None
    
    url = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json"
    }
    
    content = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "folderId": folder_id,
        "analyze_specs": [{
            "content": content,
            "features": [{
                "type": "TEXT_DETECTION",
                "text_detection_config": {
                    "language_codes": ["*"]
                }
            }]
        }]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    
                    try:
                        if ('results' in result and 
                            len(result['results']) > 0 and 
                            'results' in result['results'][0] and 
                            len(result['results'][0]['results']) > 0):
                            
                            first_result = result['results'][0]['results'][0]
                            
                            if 'error' in first_result:
                                error_msg = first_result['error'].get('message', 'Unknown error')
                                logger.error(f"❌ Vision API вернул ошибку: {error_msg}")
                                return None
                            
                            if 'textDetection' not in first_result:
                                logger.error(f"❌ В ответе нет textDetection")
                                return None
                            
                            text_detection = first_result['textDetection']
                            
                            # Вариант 1: Ищем полный текст в fullTextAnnotation
                            if 'fullTextAnnotation' in text_detection:
                                full_text = text_detection['fullTextAnnotation'].get('text', '')
                                if full_text:
                                    logger.info(f"✅ Извлечен текст ({len(full_text)} символов)")
                                    return full_text
                            
                            # Вариант 2: Собираем текст из blocks/lines/words
                            if 'pages' in text_detection:
                                full_text = ""
                                for page in text_detection['pages']:
                                    if 'blocks' in page:
                                        for block in page['blocks']:
                                            if 'lines' in block:
                                                for line in block['lines']:
                                                    if 'words' in line:
                                                        for word in line['words']:
                                                            if 'text' in word:
                                                                full_text += word['text'] + " "
                                                    full_text += "\n"
                                full_text = full_text.strip()
                                
                                if full_text:
                                    logger.info(f"✅ Извлечен текст ({len(full_text)} символов)")
                                    return full_text
                            
                            logger.error(f"❌ Не удалось извлечь текст из структуры textDetection")
                            
                        else:
                            logger.error(f"❌ Неожиданная структура ответа Vision API")
                            
                    except Exception as e:
                        logger.error(f"❌ Ошибка при парсинге ответа Vision API: {e}")
                    
                    return None
                else:
                    error_text = await resp.text()
                    logger.error(f"❌ Vision API error {resp.status}: {error_text}")
                    return None
                    
    except Exception as e:
        logger.error(f"❌ Исключение при запросе к Vision API: {str(e)}")
        return None
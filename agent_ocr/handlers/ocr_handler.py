import tempfile
import os
import logging
from datetime import datetime
from typing import List, Dict
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from agent_ocr.services.yandex_ocr import extract_text_from_image
from agent_ocr.storage.local_storage import save_summary, load_summaries, delete_summary, get_summary_topics

logger = logging.getLogger(__name__)

router = Router()

class OcrStates(StatesGroup):
    collecting_photos = State()
    waiting_for_topic_to_delete = State()

# Меню бота
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить новый конспект")],
            [KeyboardButton(text="Прислать конспект в TXT")],
            [KeyboardButton(text="Удалить тему конспекта")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

@router.message(Command("abstract"))
async def cmd_abstract(message: Message, state: FSMContext):
    """Команда /abstract - главное меню"""
    await state.clear()
    await message.answer(
        "*Режим конспектирования*\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@router.message(F.text == "Добавить новый конспект")
async def add_summary_start(message: Message, state: FSMContext):
    """Начало добавления конспекта"""
    await message.answer(
        "*Создание конспекта*\n\n"
        "**Как это работает:**\n"
        "1. Введите название конспекта\n"
        "2. Отправляйте фотографии по одной\n"
        "3. Текст из каждой фото добавляется в ОДИН конспект\n"
        "4. Необработанные фото пропускаются\n"
        "5. Когда закончите - напишите **/stop**\n\n"
        "*Введите название конспекта:*",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    await state.update_data(
        topic="",
        pages_content=[],  # Список текстов всех страниц
        processed_pages=0,
        failed_pages=0
    )
    await state.set_state(OcrStates.collecting_photos)

# 1. Обработчик для /stop
@router.message(OcrStates.collecting_photos, F.text == "/stop")
async def finish_summary_creation(message: Message, state: FSMContext):
    """Завершение создания конспекта"""
    data = await state.get_data()
    topic = data.get('topic', 'Конспект')
    pages_content = data.get('pages_content', [])
    processed_pages = data.get('processed_pages', 0)
    failed_pages = data.get('failed_pages', 0)
    
    if not pages_content:
        await message.answer(
            "*Конспект пуст.*\n"
            "Все отправленные фотографии не были обработаны.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        await state.clear()
        return
    
    # Создаем единый конспект из всех страниц
    full_content = f"# {topic}\n\n"
    full_content += f"*Создан: {datetime.now().strftime('%d.%m.%Y %H:%M')}*\n"
    full_content += f"*Страниц: {len(pages_content)}*\n\n"
    full_content += "=" * 50 + "\n\n"
    
    for i, page_text in enumerate(pages_content, 1):
        full_content += f"## Страница {i}\n\n"
        full_content += page_text + "\n\n"
        full_content += "-" * 40 + "\n\n"
    
    full_content += "=" * 50 + "\n"
    full_content += f"*Конец конспекта*\n"
    full_content += f"*Всего символов: {len(full_content)}*\n"
    
    # Сохраняем ЕДИНЫЙ конспект
    user_id = message.from_user.id
    success = save_summary(
        user_id,
        topic,
        full_content,
        datetime.now().strftime('%Y-%m-%d %H:%M')
    )
    
    if success:
        response = f"*Конспект создан!*\n\n"
        response += f"**Название:** {topic}\n"
        response += f"**Страниц в конспекте:** {len(pages_content)}\n"
        response += f"**Всего символов:** {len(full_content)}\n"
        
        if failed_pages > 0:
            response += f"**Не обработано:** {failed_pages} фото\n"
        
        response += f"\n**Содержание конспекта:**\n"
        
        # Показываем первые 2 страницы для предпросмотра
        for i, page_text in enumerate(pages_content[:2], 1):
            preview = page_text[:100].replace('\n', ' ') + "..."
            response += f"{i}. {preview}\n"
        
        if len(pages_content) > 2:
            response += f"... и еще {len(pages_content) - 2} страниц\n"
        
        response += f"\n*Конспект сохранен и доступен в вашем списке.*"
        
        await message.answer(response, parse_mode="Markdown")
    else:
        await message.answer("*Ошибка при сохранении конспекта*", parse_mode="Markdown")
    
    await message.answer("Что дальше?", reply_markup=get_main_keyboard())
    await state.clear()

# 2. Обработчик для /cancel
@router.message(OcrStates.collecting_photos, F.text == "/cancel")
async def cancel_in_collection(message: Message, state: FSMContext):
    """Отмена во время сбора страниц"""
    await state.clear()
    await message.answer(
        "*Создание конспекта отменено.*\n\n"
        "Возвращаюсь в главное меню:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# 3. Обработчик для фото
@router.message(OcrStates.collecting_photos, F.photo)
async def add_page_to_summary(message: Message, state: FSMContext):
    """Добавление страницы в единый конспект"""
    data = await state.get_data()
    topic = data.get('topic', '')
    pages_content = data.get('pages_content', [])
    processed_pages = data.get('processed_pages', 0)
    failed_pages = data.get('failed_pages', 0)
    
    # Проверяем, установлена ли тема
    if not topic:
        await message.answer(
            "*Сначала укажите название конспекта!*\n\n"
            "Напишите название конспекта:",
            parse_mode="Markdown"
        )
        return
    
    # Скачиваем фото
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    image_bytes = file_bytes.read()
    
    await message.answer(f"*Обрабатываю страницу...*", parse_mode="Markdown")
    
    # Извлекаем текст
    text = await extract_text_from_image(image_bytes)
    
    if not text:
        # Страница НЕ обработалась
        failed_pages += 1
        await state.update_data(failed_pages=failed_pages)
        
        await message.answer(
            f"*Страница не обработана.*\n"
            f"Текст не извлечен. Эта страница не будет добавлена в конспект.\n\n"
            f"Попробуйте отправить другую фотографию.",
            parse_mode="Markdown"
        )
        return
    
    # Страница обработалась успешно - добавляем в конспект
    pages_content.append(text)
    processed_pages += 1
    current_page_number = len(pages_content)
    
    await state.update_data(
        pages_content=pages_content,
        processed_pages=processed_pages
    )
    
    # Показываем статус
    await message.answer(
        f"*Страница {current_page_number} добавлена в конспект!*\n\n"
        f"**Конспект:** {topic}\n"
        f"**Страниц в конспекте:** {current_page_number}\n"
        f"**Символов на странице:** {len(text)}\n\n"
        f"**Содержание страницы:**\n{text[:150]}...\n\n"
        f"*Отправьте следующую фотографию или напишите /stop для завершения*",
        parse_mode="Markdown"
    )

# 4. Обработчик для текста (установка темы) - должен быть ПОСЛЕДНИМ!
@router.message(OcrStates.collecting_photos, F.text)
async def set_topic(message: Message, state: FSMContext):
    """Установка названия конспекта"""
    text = message.text.strip()
    
    # Пропускаем команды, они уже обработаны
    if text in ["/stop", "/cancel"]:
        return
    
    topic = text
    
    if not topic or len(topic) < 2:
        await message.answer("Пожалуйста, введите название конспекта (минимум 2 символа):")
        return
    
    await state.update_data(topic=topic)
    
    await message.answer(
        f"*Название установлено:* {topic}\n\n"
        f"Теперь отправляйте фотографии с текстом.\n"
        f"Текст из каждой УСПЕШНО обработанной фотографии будет добавлен в конспект '{topic}'.\n\n"
        f"*Отправьте первую фотографию:*",
        parse_mode="Markdown"
    )

@router.message(F.text == "/cancel")
async def cancel_operation(message: Message, state: FSMContext):
    """Отмена текущей операции из любого состояния"""
    await state.clear()
    await message.answer(
        "*Операция отменена.*\n\n"
        "Возвращаюсь в главное меню:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@router.message(F.text == "Прислать конспект в TXT")
async def send_summaries_as_txt(message: Message):
    """Отправляет все конспекты пользователя в виде текстового файла"""
    user_id = message.from_user.id
    summaries = load_summaries(user_id)
    
    if not summaries:
        await message.answer(
            "У вас пока нет сохраненных конспектов.\n"
            "Начните с добавления нового конспекта.",
            reply_markup=get_main_keyboard()
        )
        return
    
    await message.answer("Создаю файл с вашими конспектами...")
    
    try:
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', 
                                         suffix='.txt', delete=False) as tmp:
            tmp_path = tmp.name
            
            # Записываем заголовок
            tmp.write("=" * 60 + "\n")
            tmp.write(" " * 20 + "МОИ КОНСПЕКТЫ\n")
            tmp.write("=" * 60 + "\n\n")
            tmp.write(f"Создано: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
            tmp.write(f"Всего конспектов: {len(summaries)}\n")
            tmp.write("=" * 60 + "\n\n")
            
            # Сортируем конспекты по времени создания (новые сначала)
            sorted_summaries = sorted(summaries, key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Записываем каждый конспект
            for summary in sorted_summaries:
                tmp.write(f"\n{'═' * 50}\n")
                tmp.write(f"КОНСПЕКТ: {summary.get('topic', 'Без названия')}\n")
                tmp.write(f"{'═' * 50}\n")
                tmp.write(f"Создан: {summary.get('timestamp', 'Неизвестно')}\n")
                tmp.write(f"{'─' * 50}\n\n")
                
                content = summary.get('content', '')
                # Форматируем контент
                lines = content.split('\n')
                for line in lines:
                    if line.strip():
                        tmp.write(f"  {line.strip()}\n")
                    else:
                        tmp.write("\n")
                
                tmp.write(f"\n{'─' * 30}\n")
            
            tmp.write(f"\n{'=' * 60}\n")
            tmp.write("Конец файла\n")
        
        # Отправляем файл пользователю
        with open(tmp_path, 'rb') as file_to_send:
            await message.answer_document(
                FSInputFile(tmp_path, filename=f"конспекты_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"),
                caption=f"Ваши конспекты ({len(summaries)} шт.)\n"
                       f"Создано: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
        
        # Удаляем временный файл
        os.unlink(tmp_path)
        
        await message.answer("Файл отправлен! Что дальше?", reply_markup=get_main_keyboard())
        
    except Exception as e:
        logger.error(f"Ошибка при создании файла: {e}")
        await message.answer(
            "Произошла ошибка при создании файла.\n"
            "Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=get_main_keyboard()
        )

@router.message(F.text == "Удалить тему конспекта")
async def delete_summary_start(message: Message, state: FSMContext):
    """Начало удаления конспекта"""
    user_id = message.from_user.id
    topics = get_summary_topics(user_id)
    
    if not topics:
        await message.answer(
            "Нет конспектов для удаления.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Создаем клавиатуру с темами
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=topic)] for topic in topics] + 
                 [[KeyboardButton(text="Назад")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    topics_list = "\n".join([f"• {topic}" for topic in topics])
    await message.answer(
        f"*Выберите тему для удаления:*\n\n{topics_list}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(OcrStates.waiting_for_topic_to_delete)

@router.message(OcrStates.waiting_for_topic_to_delete, F.text == "Назад")
async def back_to_main(message: Message, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await message.answer(
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )

@router.message(OcrStates.waiting_for_topic_to_delete)
async def process_deletion(message: Message, state: FSMContext):
    """Обработка удаления темы"""
    topic = message.text
    user_id = message.from_user.id
    
    success = delete_summary(user_id, topic)
    
    if success:
        await message.answer(f"Конспект '{topic}' удален.")
    else:
        await message.answer(f"Конспект '{topic}' не найден.")
    
    await state.clear()
    await message.answer("Что дальше?", reply_markup=get_main_keyboard())

# Общий обработчик для непонятных сообщений в состоянии сбора
@router.message(OcrStates.collecting_photos)
async def handle_other_messages_collecting(message: Message):
    """Обработка других сообщений во время сбора"""
    await message.answer(
        "*Отправляйте фотографии с текстом.*\n"
        "Текст из каждой УСПЕШНО обработанной фотографии будет добавлен в конспект.\n\n"
        "Когда закончите - напишите **/stop**\n"
        "Чтобы отменить - напишите **/cancel**",
        parse_mode="Markdown"
    )
import asyncio
from datetime import datetime, timedelta, time
import logging
import sqlite3
from uuid import uuid4
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove,
    KeyboardButton,
    WebAppInfo  # Добавлен импорт WebAppInfo
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram.helpers import escape_markdown

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "8465822681:AAGKGiqX5VgOzmV64yMOV5vMt4tFId6izkY"
DB_FILE = "support_bot.db"
ADMIN_CHAT_ID = "6749042856"  # Ваш chat_id

# Рабочее время (10:00-18:00)
WORK_START = time(10, 0)
WORK_END = time(18, 0)

# Состояния ConversationHandler
(
    SELECT_PROBLEM, GET_SCREENSHOT, GET_SERIAL, 
    GET_PHONE_MODEL, RETURN_REQUEST, CASHBACK_REQUEST
) = range(6)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS tickets
                     (id TEXT PRIMARY KEY,
                      user_id INTEGER,
                      username TEXT,
                      request_type TEXT,
                      status TEXT DEFAULT 'pending',
                      screenshot_id TEXT,
                      serial_photo_id TEXT,
                      phone_model TEXT,
                      created_at TEXT,
                      reviewed_at TEXT,
                      admin_comment TEXT,
                      admin_message_id INTEGER)''')
    
    # Проверяем существование столбца и добавляем, если его нет
    cursor.execute("PRAGMA table_info(tickets)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'admin_message_id' not in columns:
        cursor.execute('''ALTER TABLE tickets ADD COLUMN admin_message_id INTEGER''')
    
    conn.commit()
    conn.close()

def main_menu():
    return ReplyKeyboardMarkup([
        ["🔹 Активировать гарантию", "🔹 Проблема с зарядкой"],
        ["🔹 Не работают наушники", "🔹 Возврат товара"],
        ["🔹 Инструкция", "🔹 Связаться с поддержкой"]
    ], resize_keyboard=True)

def is_working_hours():
    """Проверяет, находится ли текущее время в рабочем интервале"""
    now = datetime.now().time()
    return WORK_START <= now <= WORK_END

async def check_working_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет рабочее время и отправляет сообщение, если время нерабочее"""
    if not is_working_hours():
        await update.message.reply_text(
            "⏳ В настоящее время поддержка не работает.\n"
            "Рабочее время: с 10:00 до 18:00.\n"
            "Ваш запрос будет обработан в рабочее время.",
            reply_markup=main_menu()
        )
        return False
    return True

async def check_user_can_request(user_id: int, request_type: str) -> bool:
    """Проверяет, может ли пользователь отправить новую заявку"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''SELECT created_at, status 
                          FROM tickets 
                          WHERE user_id = ? AND request_type = ?
                          ORDER BY created_at DESC 
                          LIMIT 1''', (user_id, request_type))
        last_request = cursor.fetchone()
        
        if not last_request:
            return True
            
        created_at_str, status = last_request
        created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
        
        if status == 'pending':
            return False
            
        if datetime.now() - created_at < timedelta(hours=24):
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при проверке возможности запроса: {e}")
        return False
    finally:
        conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Добро пожаловать в поддержку Технол!\nВыберите нужный вариант:",
        reply_markup=main_menu()
    )

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data.clear()
    user = update.effective_user
    
    if text == "🔹 Активировать гарантию":
        if not await check_working_hours(update, context):
            return ConversationHandler.END
            
        request_type = "warranty_activation"
        can_request = await check_user_can_request(user.id, request_type)
        if not can_request:
            await update.message.reply_text(
                "❌ Вы уже отправили заявку на активацию гарантии. "
                "Пожалуйста, дождитесь ответа или попробуйте через 24 часа.",
                reply_markup=main_menu()
            )
            return ConversationHandler.END
            
        context.user_data['request_type'] = request_type
        await update.message.reply_text(
            "Для активации гарантии пришлите:\n1. Скриншот покупки\n2. Фото серийного номера\n3. Модель телефона\n\nОтправьте скриншот:",
            reply_markup=ReplyKeyboardRemove()
        )
        return GET_SCREENSHOT
        
    elif text == "🔹 Проблема с зарядкой":
        await update.message.reply_text(
            "🔋 Проблемы с зарядкой:\n1. Используйте оригинальный кабель\n2. Заряжайте 2-3 часа\n3. Избегайте кабелей от iPhone\n4. Перезагрузите наушники",
            reply_markup=main_menu()
        )
        
    elif text == "🔹 Не работают наушники":
        await update.message.reply_text(
            "🔄 Инструкция по перезагрузке:\n1. Зарядите 4-5 часов\n2. Удерживайте кнопку 50 сек\n3. Для одного наушника - удерживайте углубление",
            reply_markup=main_menu()
        )
        
    elif text == "🔹 Возврат товара":
        if not await check_working_hours(update, context):
            return ConversationHandler.END
            
        request_type = "return_request"
        can_request = await check_user_can_request(user.id, request_type)
        if not can_request:
            await update.message.reply_text(
                "❌ Вы уже отправили заявку на возврат товара. "
                "Пожалуйста, дождитесь ответа или попробуйте через 24 часа.",
                reply_markup=main_menu()
            )
            return ConversationHandler.END
            
        context.user_data['request_type'] = request_type
        await update.message.reply_text(
            "Для оформления возврата пришлите:\n1. Скриншот покупки\n2. Фото товара\n3. Причину возврата\n\nОтправьте скриншот:",
            reply_markup=ReplyKeyboardRemove()
        )
        return GET_SCREENSHOT
        
    elif text == "🔹 Инструкция":
        # Создаем кнопку с WebApp
        web_app_button = KeyboardButton(
            text="📖 Открыть инструкцию",
            web_app=WebAppInfo(url="https://your-mini-app-url.com")  # Замените на ваш URL
        )
        back_button = KeyboardButton("🔙 Назад")
        
        keyboard = ReplyKeyboardMarkup([[web_app_button], [back_button]], resize_keyboard=True)
        
        await update.message.reply_text(
            "📚 Инструкции по использованию наших продуктов:",
            reply_markup=keyboard
        )
        
    elif text == "🔹 Связаться с поддержкой":
        if not await check_working_hours(update, context):
            return ConversationHandler.END
            
        request_type = "support_request"
        can_request = await check_user_can_request(user.id, request_type)
        if not can_request:
            await update.message.reply_text(
                "❌ Вы уже отправили вопрос в поддержку. "
                "Пожалуйста, дождитесь ответа или попробуйте через 24 часа.",
                reply_markup=main_menu()
            )
            return ConversationHandler.END
            
        context.user_data['request_type'] = request_type
        await update.message.reply_text(
            "✍️ Напишите ваш вопрос, и мы ответим в рабочее время (10:00-18:00):",
            reply_markup=ReplyKeyboardRemove()
        )
        return SELECT_PROBLEM

    elif text == "🔙 Назад":
        await update.message.reply_text(
            "👋 Добро пожаловать в поддержку Технол!\nВыберите нужный вариант:",
            reply_markup=main_menu()
        )

async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_working_hours(update, context):
        return ConversationHandler.END
    
    if not update.message.text:
        await update.message.reply_text("Пожалуйста, напишите ваш вопрос текстом")
        return SELECT_PROBLEM
    
    user_question = update.message.text
    user = update.effective_user
    ticket_id = str(uuid4())[:6].upper()
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''INSERT INTO tickets 
                         (id, user_id, username, request_type, status,
                          admin_comment, created_at)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (ticket_id, user.id, 
                          user.username,
                          "support_request",
                          "pending",
                          user_question,
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при сохранении вопроса: {e}")
    finally:
        conn.close()
    
    try:
        admin_message = (f"🆕 Новый вопрос в поддержку #{ticket_id}\n"
                       f"👤 Пользователь: @{user.username or 'нет'} (ID: {user.id})\n"
                       f"❓ Вопрос:\n{user_question}\n\n"
                       f"Ответьте на это сообщение, чтобы отправить ответ пользователю.")
        
        sent_msg = await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
        
        # Сохраняем message_id в базе данных
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''UPDATE tickets SET admin_message_id = ? WHERE id = ?''',
                     (sent_msg.message_id, ticket_id))
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления админу: {e}")
    
    await update.message.reply_text(
        "✅ Ваш вопрос отправлен в поддержку! Мы ответим в рабочее время (10:00-18:00).",
        reply_markup=main_menu()
    )
    return ConversationHandler.END

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_working_hours(update, context):
        return ConversationHandler.END
    
    if update.message.photo:
        context.user_data['screenshot_id'] = update.message.photo[-1].file_id
        request_type = context.user_data.get('request_type')
        
        if request_type == "warranty_activation":
            await update.message.reply_text("📸 Скриншот получен. Теперь отправьте фото серийного номера:")
            return GET_SERIAL
        elif request_type == "return_request":
            await update.message.reply_text("📸 Скриншот получен. Теперь отправьте фото товара:")
            return GET_SERIAL
        elif request_type == "cashback_request":
            await update.message.reply_text("📸 Скриншот отзыва получен. Теперь укажите номер карты для перевода:")
            return CASHBACK_REQUEST
    else:
        await update.message.reply_text("Пожалуйста, отправьте скриншот как фото")
        return GET_SCREENSHOT

async def handle_serial_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_working_hours(update, context):
        return ConversationHandler.END
    
    if update.message.photo:
        context.user_data['serial_photo_id'] = update.message.photo[-1].file_id
        request_type = context.user_data.get('request_type')
        
        if request_type == "warranty_activation":
            await update.message.reply_text("🔢 Серийный номер получен. Укажите модель телефона:")
            return GET_PHONE_MODEL
        elif request_type == "return_request":
            await update.message.reply_text("📦 Фото товара получено. Укажите причину возврата:")
            return RETURN_REQUEST
    else:
        await update.message.reply_text("Пожалуйста, отправьте фото")
        return GET_SERIAL

async def handle_phone_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_working_hours(update, context):
        return ConversationHandler.END
    
    if not update.message.text:
        await update.message.reply_text("Пожалуйста, введите модель телефона текстом")
        return GET_PHONE_MODEL
    
    context.user_data['phone_model'] = update.message.text
    await complete_request(update, context)
    return ConversationHandler.END

async def handle_return_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_working_hours(update, context):
        return ConversationHandler.END
    
    if not update.message.text:
        await update.message.reply_text("Пожалуйста, укажите причину возврата")
        return RETURN_REQUEST
    
    context.user_data['return_reason'] = update.message.text
    await complete_request(update, context)
    return ConversationHandler.END

async def handle_cashback_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_working_hours(update, context):
        return ConversationHandler.END
    
    if not update.message.text:
        await update.message.reply_text("Пожалуйста, укажите номер карты для перевода")
        return CASHBACK_REQUEST
    
    context.user_data['card_number'] = update.message.text
    await complete_request(update, context)
    return ConversationHandler.END

async def complete_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request_type = context.user_data.get('request_type')
    ticket_id = str(uuid4())[:6].upper()
    user = update.effective_user
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        if request_type == "warranty_activation":
            cursor.execute('''INSERT INTO tickets 
                             (id, user_id, username, request_type, status,
                              screenshot_id, serial_photo_id, phone_model, created_at)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                             (ticket_id, user.id, 
                              user.username,
                              request_type,
                              "pending",
                              context.user_data['screenshot_id'],
                              context.user_data['serial_photo_id'],
                              context.user_data['phone_model'],
                              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            response_text = "✅ Ваш запрос на активацию гарантии получен!"
            
        elif request_type == "return_request":
            cursor.execute('''INSERT INTO tickets 
                             (id, user_id, username, request_type, status,
                              screenshot_id, serial_photo_id, admin_comment, created_at)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                             (ticket_id, user.id, 
                              user.username,
                              request_type,
                              "pending",
                              context.user_data['screenshot_id'],
                              context.user_data['serial_photo_id'],
                              context.user_data['return_reason'],
                              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            response_text = "✅ Ваш запрос на возврат товара получен!"
            
        elif request_type == "cashback_request":
            cursor.execute('''INSERT INTO tickets 
                             (id, user_id, username, request_type, status,
                              screenshot_id, admin_comment, created_at)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                             (ticket_id, user.id, 
                              user.username,
                              request_type,
                              "pending",
                              context.user_data['screenshot_id'],
                              context.user_data['card_number'],
                              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            response_text = "✅ Ваш запрос на кэшбэк получен!"
        elif request_type == "support_request":
            cursor.execute('''INSERT INTO tickets 
                             (id, user_id, username, request_type, status,
                              admin_comment, created_at)
                             VALUES (?, ?, ?, ?, ?, ?, ?)''',
                             (ticket_id, user.id, 
                              user.username,
                              request_type,
                              "pending",
                              context.user_data.get('question', update.message.text),
                              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            response_text = "✅ Ваш вопрос отправлен в поддержку!"
        
        conn.commit()
        
        response_text += "\nНаш специалист обрабатывает его в ближайшее время."
        await update.message.reply_text(response_text, reply_markup=main_menu())
        
        await notify_admin(context, ticket_id, request_type, user)
        
    except Exception as e:
        logger.error(f"Ошибка при создании тикета: {e}")
        await update.message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже.",
            reply_markup=main_menu()
        )
    finally:
        conn.close()
        context.user_data.clear()
    return ConversationHandler.END

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, ticket_id: str, request_type: str, user):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        if request_type == "warranty_activation":
            cursor.execute('''SELECT phone_model, screenshot_id, serial_photo_id 
                            FROM tickets WHERE id = ?''', (ticket_id,))
            phone_model, screenshot_id, serial_photo_id = cursor.fetchone()
            
            message_text = (f"🆕 Новая заявка на гарантию #{ticket_id}\n"
                         f"👤 Пользователь: @{user.username or 'нет'} (ID: {user.id})\n"
                         f"📱 Телефон: {phone_model}\n\n"
                         f"Ответьте на это сообщение, чтобы отправить ответ пользователю.")
            
            sent_msg = await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message_text)
            await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=screenshot_id)
            await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=serial_photo_id)
            
        elif request_type == "return_request":
            cursor.execute('''SELECT admin_comment, screenshot_id, serial_photo_id 
                            FROM tickets WHERE id = ?''', (ticket_id,))
            return_reason, screenshot_id, product_photo = cursor.fetchone()
            
            message_text = (f"🆕 Запрос на возврат #{ticket_id}\n"
                         f"👤 Пользователь: @{user.username or 'нет'}\n"
                         f"📦 Причина: {return_reason}\n\n"
                         f"Ответьте на это сообщение, чтобы отправить ответ пользователю.")
            
            sent_msg = await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message_text)
            await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=screenshot_id)
            await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=product_photo)
            
        elif request_type == "cashback_request":
            cursor.execute('''SELECT admin_comment, screenshot_id 
                            FROM tickets WHERE id = ?''', (ticket_id,))
            card_number, screenshot_id = cursor.fetchone()
            
            message_text = (f"🆕 Запрос на кэшбэк #{ticket_id}\n"
                         f"👤 Пользователь: @{user.username or 'нет'}\n"
                         f"💳 Карта: {card_number}\n\n"
                         f"Ответьте на это сообщение, чтобы отправить ответ пользователю.")
            
            sent_msg = await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message_text)
            await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=screenshot_id)
            
        elif request_type == "support_request":
            cursor.execute('''SELECT admin_comment 
                            FROM tickets WHERE id = ?''', (ticket_id,))
            question = cursor.fetchone()[0]
            
            message_text = (f"🆕 Новый вопрос в поддержку #{ticket_id}\n"
                         f"👤 Пользователь: @{user.username or 'нет'}\n"
                         f"❓ Вопрос:\n{question}\n\n"
                         f"Ответьте на это сообщение, чтобы отправить ответ пользователю.")
            
            sent_msg = await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message_text)
            
        # Сохраняем message_id в базе данных для связи
        cursor.execute('''UPDATE tickets SET admin_message_id = ? WHERE id = ?''',
                     (sent_msg.message_id, ticket_id))
        conn.commit()
            
    except Exception as e:
        logger.error(f"Ошибка уведомления админа: {e}")
    finally:
        conn.close()

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа администратора на заявку"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Доступ запрещен")
        return

    # Проверяем, является ли сообщение ответом на другое сообщение
    if not update.message.reply_to_message:
        await update.message.reply_text("ℹ️ Ответьте на сообщение с заявкой, чтобы отправить ответ пользователю")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Получаем ID оригинального сообщения
        replied_message_id = update.message.reply_to_message.message_id
        
        # Ищем заявку по ID сообщения
        cursor.execute('''SELECT id, user_id, request_type, status 
                         FROM tickets 
                         WHERE admin_message_id = ?''', (replied_message_id,))
        result = cursor.fetchone()
        
        if not result:
            await update.message.reply_text("❌ Не найдена заявка, связанная с этим сообщением")
            return
            
        ticket_id, user_id, request_type, status = result
        
        # Проверяем статус заявки
        if status in ['answered', 'approved', 'rejected']:
            await update.message.reply_text("⚠️ Эта заявка уже закрыта")
            return
        
        # Формируем текст ответа с экранированием всех специальных символов
        response_text = (
            f"📨 Ответ от поддержки по заявке \\#{escape_markdown(ticket_id, version=2)}\n"
            f"Тип запроса: {escape_markdown(request_type, version=2)}\n\n"
            f"{escape_markdown(update.message.text, version=2)}"
        )
        
        try:
            # Отправляем ответ пользователю с MarkdownV2
            await context.bot.send_message(
                chat_id=user_id, 
                text=response_text,
                parse_mode="MarkdownV2"
            )
            
            # Обновляем статус заявки
            cursor.execute('''UPDATE tickets 
                            SET status = 'answered',
                                reviewed_at = ?,
                                admin_comment = ?
                            WHERE id = ?''',
                            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                             update.message.text, 
                             ticket_id))
            conn.commit()
            
            await update.message.reply_text(
                f"✅ Ответ отправлен пользователю (ID: {user_id})\n"
                f"Тип запроса: {request_type}\n"
                f"ID заявки: #{ticket_id}"
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Не удалось отправить сообщение пользователю: {e}")
            logger.error(f"Ошибка отправки ответа пользователю: {e}")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}\n\n"
                                      "Правильный формат ответа:\n"
                                      "1. Ответьте на сообщение с заявкой\n"
                                      "2. Напишите ваш ответ")
        logger.error(f"Ошибка обработки ответа администратора: {e}")
    finally:
        conn.close()

async def approve_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /approve_TICKETID"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    try:
        ticket_id = update.message.text.split('_')[1]
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''SELECT request_type, user_id, username FROM tickets WHERE id = ?''', (ticket_id,))
        result = cursor.fetchone()
        
        if not result:
            await update.message.reply_text("❌ Заявка не найдена")
            return
            
        request_type, user_id, username = result
        
        # Проверяем статус заявки
        cursor.execute('''SELECT status FROM tickets WHERE id = ?''', (ticket_id,))
        status = cursor.fetchone()[0]
        
        if status in ['answered', 'approved', 'rejected']:
            await update.message.reply_text("⚠️ Эта заявка уже обработана")
            return
        
        # Обновляем статус
        cursor.execute('''UPDATE tickets 
                         SET status = 'approved',
                             reviewed_at = ?
                         WHERE id = ?''',
                         (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ticket_id))
        
        conn.commit()
        
        # Формируем сообщение в зависимости от типа запроса
        if request_type == "warranty_activation":
            message = (f"🎉 Ваша гарантия #{ticket_id} активирована!\n"
                     f"Срок гарантии: 3 месяца\n"
                     f"Дата активации: {datetime.now().strftime('%d.%m.%Y')}")
        elif request_type == "return_request":
            message = (f"✅ Ваш возврат #{ticket_id} одобрен!\n"
                     f"Мы свяжемся с вами для уточнения деталей.")
        elif request_type == "cashback_request":
            message = (f"💰 Ваш кэшбэк по заявке #{ticket_id} одобрен!\n"
                     f"Средства поступят в течение 3 рабочих дней.")
        elif request_type == "support_request":
            message = (f"✅ По вашему вопросу #{ticket_id} дан ответ:\n"
                     f"Если вам нужна дополнительная помощь, свяжитесь с нами снова.")
        
        # Уведомляем пользователя
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя: {e}")
        
        # Подтверждение администратору
        await update.message.reply_text(
            f"✅ Заявка #{ticket_id} одобрена\n"
            f"Пользователь @{username} уведомлен"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при одобрении заявки: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке")
    finally:
        conn.close()

async def reject_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /reject_TICKETID Причина"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    try:
        parts = update.message.text.split(maxsplit=2)
        ticket_id = parts[0].split('_')[1]
        reason = parts[1] if len(parts) >= 2 else "Причина не указана"
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''SELECT request_type, user_id, username, status 
                         FROM tickets WHERE id = ?''', (ticket_id,))
        result = cursor.fetchone()
        
        if not result:
            await update.message.reply_text("❌ Заявка не найдена")
            return
            
        request_type, user_id, username, status = result
        
        # Проверяем статус заявки
        if status in ['answered', 'approved', 'rejected']:
            await update.message.reply_text("⚠️ Эта заявка уже обработана")
            return
        
        # Обновляем статус
        cursor.execute('''UPDATE tickets 
                         SET status = 'rejected',
                             reviewed_at = ?,
                             admin_comment = ?
                         WHERE id = ?''',
                         (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                          reason, ticket_id))
        
        conn.commit()
        
        # Формируем сообщение в зависимости от типа запроса
        if request_type == "warranty_activation":
            message = (f"❌ В активации гарантии #{ticket_id} отказано.\n"
                     f"Причина: {reason}\n\n"
                     f"Для уточнения свяжитесь с поддержкой.")
        elif request_type == "return_request":
            message = (f"❌ Ваш запрос на возврат #{ticket_id} отклонен.\n"
                     f"Причина: {reason}\n\n"
                     f"Для уточнения свяжитесь с поддержкой.")
        elif request_type == "cashback_request":
            message = (f"❌ Ваш запрос на кэшбэк #{ticket_id} отклонен.\n"
                     f"Причина: {reason}\n\n"
                     f"Для уточнения свяжитесь с поддержкой.")
        elif request_type == "support_request":
            message = (f"❌ По вашему вопросу #{ticket_id} принято решение:\n"
                     f"Причина: {reason}\n\n"
                     f"Для уточнения свяжитесь с нами снова.")
        
        # Уведомляем пользователя
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя: {e}")
        
        # Подтверждение администратору
        await update.message.reply_text(
            f"✅ Заявка #{ticket_id} отклонена\n"
            f"Причина: {reason}\n"
            f"Пользователь @{username} уведомлен"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при отклонении заявки: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке")
    finally:
        conn.close()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменяет текущий диалог и возвращает в главное меню"""
    await update.message.reply_text(
        "Действие отменено",
        reply_markup=main_menu()
    )
    context.user_data.clear()
    return ConversationHandler.END

def main():
    init_db()
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    app = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('cancel', cancel))
    
    # Обработчики команд администратора
    app.add_handler(MessageHandler(
        filters.Regex(r'^/approve_') & filters.Chat(chat_id=int(ADMIN_CHAT_ID)),
        approve_request
    ))
    app.add_handler(MessageHandler(
        filters.Regex(r'^/reject_') & filters.Chat(chat_id=int(ADMIN_CHAT_ID)),
        reject_request
    ))
    
    # Обработчик ответов администратора
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(chat_id=int(ADMIN_CHAT_ID)) & filters.REPLY,
        admin_reply
    ))
    
    # ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r'^(🔹 Активировать гарантию|🔹 Возврат товара|🔹 Получить кэшбэк|🔹 Связаться с поддержкой)$'), 
                          handle_main_menu)
        ],
        states={
            SELECT_PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support_message)],
            GET_SCREENSHOT: [MessageHandler(filters.PHOTO, handle_screenshot)],
            GET_SERIAL: [MessageHandler(filters.PHOTO, handle_serial_photo)],
            GET_PHONE_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone_model)],
            RETURN_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_return_reason)],
            CASHBACK_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_cashback_request)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    app.add_handler(conv_handler)
    
    # Обработка главного меню
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu))
    
    logger.info("Бот запущен и готов к работе!")
    app.run_polling()

if __name__ == '__main__':
    main()
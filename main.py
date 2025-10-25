import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    InlineQueryHandler
)
from telegram.error import BadRequest, TelegramError
import sqlite3
import asyncio
import itertools
import random
import uuid
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
DATABASE_NAME = "love_bot.db"
HEART_ANIMATION_FRAMES = [
    "❤️", "🧡", "💛", "💚", "💙", "💜", "🤎", "🖤", "🤍", "💖",
    "💗", "💓", "💞", "💕", "💘", "💝", "💟"
]

# Действия для инлайн-режима
INLINE_ACTIONS = {
    "поцеловать": {"emoji": "💋", "description": "Послать нежный поцелуй", "action": "kiss"},
    "обнять": {"emoji": "🤗", "description": "Отправить теплые объятия", "action": "hug"}, 
    "погладить": {"emoji": "🖐️", "description": "Погладить по головке", "action": "pat"},
    "прижаться": {"emoji": "🫂", "description": "Прижаться и обниматься", "action": "cuddle"},
    "люблю": {"emoji": "💌", "description": "Признаться в любви", "action": "love"},
    "улыбнуться": {"emoji": "😄", "description": "Подарить улыбку", "action": "smile"},
    "подмигнуть": {"emoji": "😉", "description": "Подмигнуть игриво", "action": "wink"},
    "сердце": {"emoji": "❤️", "description": "Анимация сердца", "action": "heart"},
    "совместимость": {"emoji": "💑", "description": "Проверить совместимость", "action": "compatibility"},
    "анонимка": {"emoji": "📝", "description": "Отправить анонимную записку", "action": "anonymous_note"}
}

ACTION_TEXTS = {
    "kiss": "💋 поцеловал(а)",
    "hug": "🤗 обнял(а)",
    "pat": "🖐️ погладил(а)",
    "cuddle": "🫂 прижался(ась) к",
    "love": "💌 признался(ась) в любви",
    "smile": "😄 улыбнулся(ась)",
    "wink": "😉 подмигнул(а)"
}

# Глобальные переменные
animation_jobs = {}

# ========================
#  БАЗА ДАННЫХ
# ========================
def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        full_name TEXT,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS anonymous_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        recipient_id INTEGER NOT NULL,
        message_text TEXT NOT NULL,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def register_user(user):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user.id,))
    existing_user = cursor.fetchone()
    
    if not existing_user:
        cursor.execute('''
        INSERT INTO users (user_id, username, first_name, full_name)
        VALUES (?, ?, ?, ?)
        ''', (user.id, user.username, user.first_name, user.full_name))
        conn.commit()
    
    conn.close()

def find_user_id(username):
    username = username.lower().strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE LOWER(username) = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user['user_id'] if user else None

def get_user_info(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            'user_id': user['user_id'],
            'username': user['username'],
            'first_name': user['first_name'],
            'full_name': user['full_name']
        }
    return None

def add_anonymous_note(sender_id, recipient_id, message_text):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT INTO anonymous_notes (sender_id, recipient_id, message_text)
        VALUES (?, ?, ?)
        ''', (sender_id, recipient_id, message_text))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления анонимной записки: {str(e)}")
        return False
    finally:
        conn.close()

# ========================
#  АНИМАЦИЯ СЕРДЦА
# ========================
async def safe_edit_message(context, chat_id, message_id, text, reply_markup=None):
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup
        )
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.error(f"Ошибка редактирования: {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка редактирования: {str(e)}")

async def animate_hearts(context: ContextTypes.DEFAULT_TYPE):
    try:
        job = context.job
        frame = next(job.data['frame_iterator'])
        await safe_edit_message(
            context,
            job.data['chat_id'],
            job.data['message_id'],
            f"{frame}\nЯ тебя люблю <3",
            job.data['reply_markup']
        )
    except Exception as e:
        logger.error(f"Ошибка анимации: {str(e)}")
        job.schedule_removal()
        chat_id = job.data['chat_id']
        if chat_id in animation_jobs:
            animation_jobs.pop(chat_id, None)

async def send_heart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    register_user(user)
    
    # Останавливаем предыдущую анимацию
    if chat_id in animation_jobs:
        old_job = animation_jobs[chat_id]
        old_job.schedule_removal()
        animation_jobs.pop(chat_id, None)
        await asyncio.sleep(0.5)
    
    # Создаем клавиатуру с 2 кнопками
    keyboard = [
        [InlineKeyboardButton("💖 Ответить взаимностью", callback_data="heart_respond")],
        [InlineKeyboardButton("❌ Отказаться", callback_data="heart_reject")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем начальное сообщение
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="❤️\nЯ тебя люблю <3",
        reply_markup=reply_markup
    )
    
    # Создаем итератор кадров
    frame_iterator = itertools.cycle(HEART_ANIMATION_FRAMES)
    
    # Запускаем анимацию
    job = context.job_queue.run_repeating(
        animate_hearts,
        interval=0.8,
        first=0,
        data={
            'frame_iterator': frame_iterator,
            'chat_id': chat_id,
            'message_id': msg.message_id,
            'reply_markup': reply_markup
        },
        name=f"heart_anim_{chat_id}"
    )
    
    # Сохраняем ссылку на задание
    animation_jobs[chat_id] = job

async def handle_heart_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    chat_id = query.message.chat_id
    
    # Останавливаем анимацию
    if chat_id in animation_jobs:
        job = animation_jobs[chat_id]
        job.schedule_removal()
        animation_jobs.pop(chat_id, None)
    
    if query.data == "heart_respond":
        await query.edit_message_text(
            f"💖 {user.first_name} ответил(а) взаимностью на признание в любви! 💕"
        )
    elif query.data == "heart_reject":
        await query.edit_message_text(
            f"💔 {user.first_name} вежливо отказался(ась) от признания в любви..."
        )

# ========================
#  АНОНИМНЫЕ ЗАПИСКИ
# ========================
async def start_anonymous_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)
    
    if not context.args:
        await update.message.reply_text(
            "📝 *Анонимные записки*\n\n"
            "Отправьте анонимное сообщение пользователю:\n"
            "`/note @username Ваше сообщение`\n\n"
            "Пример: `/note @username Ты самая красивая! 💖`\n\n"
            "Получатель не узнает, кто отправил записку!",
            parse_mode="Markdown"
        )
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Укажите username и сообщение!")
        return
    
    username = context.args[0].lstrip('@').strip().lower()
    message_text = ' '.join(context.args[1:])
    
    if len(message_text) > 500:
        await update.message.reply_text("❌ Сообщение слишком длинное (макс. 500 символов)")
        return
    
    target_id = find_user_id(username)
    
    if not target_id:
        await update.message.reply_text(f"❌ Пользователь @{username} не найден.")
        return
    
    if user.id == target_id:
        await update.message.reply_text("❌ Нельзя отправить записку самому себе!")
        return
    
    # Сохраняем записку в базу
    success = add_anonymous_note(user.id, target_id, message_text)
    
    if success:
        # Отправляем уведомление получателю
        try:
            target_info = get_user_info(target_id)
            target_name = target_info['first_name'] if target_info else f"@{username}"
            
            await context.bot.send_message(
                chat_id=target_id,
                text=f"💌 *Вам анонимная записка!*\n\n"
                     f"_{message_text}_\n\n"
                     f"💝 Кто-то думает о тебе, {target_name}!",
                parse_mode="Markdown"
            )
            
            await update.message.reply_text(
                "✅ Записка успешно отправлена анонимно! 💝"
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки записки: {str(e)}")
            await update.message.reply_text("❌ Не удалось отправить записку. Пользователь, возможно, не запускал бота.")
    else:
        await update.message.reply_text("❌ Ошибка при отправке записки.")

# ========================
#  СОВМЕСТИМОСТЬ
# ========================
async def start_compatibility(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)
    
    args = context.args
    if not args:
        await update.message.reply_text(
            "💑 *Проверьте вашу совместимость с партнером!*\n\n"
            "Используйте: /compatibility @username\n"
            "Пример: /compatibility @username_любимого",
            parse_mode="Markdown"
        )
        return
        
    username = args[0].lstrip('@').strip().lower()
    partner_id = find_user_id(username)
    
    if not partner_id:
        await update.message.reply_text(f"Пользователь @{username} не найден.")
        return
    
    if user.id == partner_id:
        await update.message.reply_text("Нельзя проверить совместимость с самим собой! 😉")
        return
        
    user1_info = get_user_info(user.id)
    user2_info = get_user_info(partner_id)
    
    user1_name = user1_info['first_name'] if user1_info else user.first_name
    user2_name = user2_info['first_name'] if user2_info else f"Пользователь {partner_id}"
    
    message = await update.message.reply_text(
        f"🔮 *Расчет совместимости*\n\n"
        f"{user1_name} ❤️ {user2_name}\n\n"
        "▰▰▰▰▰▰▰▰▰ 0%",
        parse_mode="Markdown"
    )
    
    context.job_queue.run_once(
        calculate_compatibility, 
        3, 
        data={
            'chat_id': update.effective_chat.id,
            'message_id': message.message_id,
            'user1_id': user.id,
            'user2_id': partner_id,
            'user1_name': user1_name,
            'user2_name': user2_name
        }
    )

async def calculate_compatibility(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    data = job.data
    
    compatibility = random.randint(70, 99)
    progress = "🟥" * 10
    progress_bar = progress[:compatibility//10].replace("🟥", "🟩") + progress[compatibility//10:]
    
    descriptions = [
        "Ваши сердца бьются в унисон!",
        "Идеальное сочетание душ!",
        "Небеса предназначили вас друг для друга!",
        "Ваша связь особенная и уникальная!",
        "Настоящая любовь, которая преодолеет все преграды!"
    ]
    
    await context.bot.edit_message_text(
        chat_id=data['chat_id'],
        message_id=data['message_id'],
        text=(
            f"💖 *Результат совместимости!*\n\n"
            f"{data['user1_name']} ❤️ {data['user2_name']}\n\n"
            f"▰{progress_bar}▰ {compatibility}%\n\n"
            f"_{random.choice(descriptions)}_"
        ),
        parse_mode="Markdown"
    )

# ========================
#  ИНЛАЙН-РЕЖИМ
# ========================
async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.lower().strip()
    user = update.inline_query.from_user
    
    register_user(user)
    results = []
    
    if not query:
        for action_name, info in INLINE_ACTIONS.items():
            message_text = f"{info['emoji']} {user.first_name} {action_name}!"
            
            keyboard = [
                [InlineKeyboardButton("💖 Ответить взаимностью", callback_data=f"inline_respond_{info['action']}_{user.id}")],
                [InlineKeyboardButton("❌ Отказаться", callback_data=f"inline_reject_{user.id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=f"{info['emoji']} {action_name.capitalize()}",
                    description=info['description'],
                    input_message_content=InputTextMessageContent(
                        message_text=message_text,
                        parse_mode=None
                    ),
                    reply_markup=reply_markup
                )
            )
    else:
        for action_name, info in INLINE_ACTIONS.items():
            if query in action_name:
                message_text = f"{info['emoji']} {user.first_name} {action_name}!"
                
                keyboard = [
                    [InlineKeyboardButton("💖 Ответить взаимностью", callback_data=f"inline_respond_{info['action']}_{user.id}")],
                    [InlineKeyboardButton("❌ Отказаться", callback_data=f"inline_reject_{user.id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                results.append(
                    InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title=f"{info['emoji']} {action_name.capitalize()}",
                        description=info['description'],
                        input_message_content=InputTextMessageContent(
                            message_text=message_text,
                            parse_mode=None
                        ),
                        reply_markup=reply_markup
                    )
                )
    
    if not results:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="❌ Действие не найдено",
                description="Попробуйте: поцеловать, обнять, погладить...",
                input_message_content=InputTextMessageContent(
                    message_text="💖 Выберите романтическое действие!",
                    parse_mode=None
                )
            )
        )
    
    try:
        await update.inline_query.answer(results, cache_time=0, is_personal=True)
    except Exception as e:
        logger.error(f"Ошибка инлайн-запроса: {str(e)}")

# ========================
#  КОМАНДЫ С ЮЗЕРНЕЙМОМ
# ========================
async def send_cute_action_with_username(update: Update, context: ContextTypes.DEFAULT_TYPE, action_type: str, action_text: str):
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text(
            f"❌ Используйте: /{action_type} @username\n"
            f"Пример: /{action_type} @имя_пользователя"
        )
        return
    
    username = context.args[0].lstrip('@').strip().lower()
    target_id = find_user_id(username)
    
    if not target_id:
        await update.message.reply_text(f"❌ Пользователь @{username} не найден.")
        return
    
    if user.id == target_id:
        await update.message.reply_text(f"😊 Нельзя {action_text.split()[0]} самого себя!")
        return
    
    sender_info = get_user_info(user.id)
    target_info = get_user_info(target_id)
    
    sender_name = sender_info['first_name'] if sender_info else user.first_name
    target_name = target_info['first_name'] if target_info else f"@{username}"
    
    keyboard = [
        [InlineKeyboardButton("💖 Ответить взаимностью", callback_data=f"respond_{action_type}_{user.id}")],
        [InlineKeyboardButton("❌ Отказаться", callback_data=f"reject_{user.id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await update.message.reply_text(
            f"💞 {sender_name} {action_text} {target_name}!",
            reply_markup=reply_markup
        )
        
        # Отправляем уведомление целевому пользователю
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"💌 {sender_name} {action_text} вам!"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление: {str(e)}")
            
    except Exception as e:
        logger.error(f"Ошибка отправки действия: {str(e)}")

# Обработчики команд
async def send_kiss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "kiss", "💋 поцеловал(а)")

async def send_hug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "hug", "🤗 обнял(а)")

async def send_pat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "pat", "🖐️ погладил(а)")

async def send_cuddle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "cuddle", "🫂 прижался(ась) к")

async def send_love(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "love", "💌 признался(ась) в любви")

async def send_smile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "smile", "😄 улыбнулся(ась)")

async def send_wink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "wink", "😉 подмигнул(а)")

# ========================
#  ОБРАБОТЧИКИ КНОПОК
# ========================
async def handle_inline_button_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data_parts = query.data.split('_')
    
    if len(data_parts) >= 3 and data_parts[0] == "inline":
        action_type = data_parts[2]
        sender_id = int(data_parts[3])
        
        if user.id == sender_id:
            await query.edit_message_text("😊 Нельзя отвечать самому себе!")
            return
            
        if data_parts[1] == "respond":
            sender_info = get_user_info(sender_id)
            sender_name = sender_info['first_name'] if sender_info else f"Пользователь {sender_id}"
            
            action_text = ACTION_TEXTS.get(action_type, "сделал(а) что-то милое")
            
            await query.edit_message_text(
                f"💖 {user.first_name} ответил(а) взаимностью на {action_text} от {sender_name}! 💕"
            )
            
        elif data_parts[1] == "reject":
            await query.edit_message_text(
                f"💔 {user.first_name} вежливо отказался(ась)..."
            )

async def handle_regular_button_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data_parts = query.data.split('_')
    
    if len(data_parts) >= 3 and data_parts[0] == "respond":
        action_type = data_parts[1]
        sender_id = int(data_parts[2])
        
        if user.id == sender_id:
            await query.edit_message_text("😊 Нельзя отвечать самому себе!")
            return
            
        sender_info = get_user_info(sender_id)
        sender_name = sender_info['first_name'] if sender_info else f"Пользователь {sender_id}"
        
        action_text = ACTION_TEXTS.get(action_type, "сделал(а) что-то милое")
        
        await query.edit_message_text(
            f"💖 {user.first_name} ответил(а) взаимностью на {action_text} от {sender_name}! 💕"
        )
            
    elif len(data_parts) >= 2 and data_parts[0] == "reject":
        await query.edit_message_text(
            f"💔 {user.first_name} вежливо отказался(ась)..."
        )

# ========================
#  ОСНОВНЫЕ КОМАНДЫ
# ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)
    
    welcome_text = (
        f"💖 Привет, {user.first_name}!\n\n"
        "Я бот для романтики и нежных чувств! 💕\n\n"
        "✨ *Что я умею:*\n"
        "• Анимированные признания в любви ❤️\n"
        "• Отправка милых действий с кнопками\n"
        "• Анонимные записки 💌\n"
        "• Проверка совместимости 💑\n\n"
        "💝 *Основные команды:*\n"
        "`/heart` - Анимация сердца\n"
        "`/note @username текст` - Анонимная записка\n"
        "`/compatibility @username` - Совместимость\n\n"
        "🎮 *Действия:*\n"
        "`/kiss @username` - Поцеловать\n"
        "`/hug @username` - Обнять\n"
        "`/pat @username` - Погладить\n"
        "`/love @username` - Признаться в любви\n\n"
        "💬 *Инлайн-режим:*\n"
        "Напишите `@{context.bot.username}` в любом чате!"
    )
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "💖 *Помощь по командам*\n\n"
        "💝 *Основные:*\n"
        "`/start` - Начать работу\n"
        "`/heart` - Анимация сердца\n"
        "`/note @username текст` - Анонимная записка\n"
        "`/compatibility @username` - Совместимость\n\n"
        "🎮 *Романтические действия:*\n"
        "`/kiss @username` - Поцеловать 💋\n"
        "`/hug @username` - Обнять 🤗\n"
        "`/pat @username` - Погладить 🖐️\n"
        "`/cuddle @username` - Прижаться 🫂\n"
        "`/love @username` - Признаться в любви 💌\n"
        "`/smile @username` - Улыбнуться 😄\n"
        "`/wink @username` - Подмигнуть 😉\n\n"
        "💬 *Инлайн-режим:*\n"
        "Напишите `@{context.bot.username}` в любом чате!"
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

# ========================
#  HTTP СЕРВЕР ДЛЯ UPTIMEROBOT
# ========================
from aiohttp import web
import threading

async def handle_health_check(request):
    return web.Response(text="Bot is running!")

def run_http_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    app.router.add_get('/health', handle_health_check)
    
    port = int(os.environ.get('PORT', 8080))
    web.run_app(app, host='0.0.0.0', port=port)

# ========================
#  ЗАПУСК БОТА
# ========================
def main():
    # Инициализация базы данных
    init_db()
    
    # Запуск HTTP сервера в отдельном потоке
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Создание приложения бота
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("heart", send_heart))
    application.add_handler(CommandHandler("note", start_anonymous_note))
    application.add_handler(CommandHandler("compatibility", start_compatibility))
    
    # Обработчики действий
    application.add_handler(CommandHandler("kiss", send_kiss))
    application.add_handler(CommandHandler("hug", send_hug))
    application.add_handler(CommandHandler("pat", send_pat))
    application.add_handler(CommandHandler("cuddle", send_cuddle))
    application.add_handler(CommandHandler("love", send_love))
    application.add_handler(CommandHandler("smile", send_smile))
    application.add_handler(CommandHandler("wink", send_wink))
    
    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(handle_heart_response, pattern="^heart_"))
    application.add_handler(CallbackQueryHandler(handle_inline_button_response, pattern="^inline_"))
    application.add_handler(CallbackQueryHandler(handle_regular_button_response, pattern="^(respond|reject)_"))
    
    # Инлайн-режим
    application.add_handler(InlineQueryHandler(handle_inline_query))
    
    logger.info("Бот запущен с HTTP сервером для UptimeRobot!")
    application.run_polling()

if __name__ == '__main__':
    main()

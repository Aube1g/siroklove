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

# Все взаимодействия с иконками
INLINE_ACTIONS = {
    "поцеловать": {"emoji": "💋", "description": "Послать нежный поцелуй", "action": "kiss"},
    "обнять": {"emoji": "🤗", "description": "Отправить теплые объятия", "action": "hug"},
    "погладить": {"emoji": "🖐️", "description": "Погладить по головке", "action": "pat"},
    "прижаться": {"emoji": "🫂", "description": "Прижаться и обниматься", "action": "cuddle"},
    "люблю": {"emoji": "💌", "description": "Признаться в любви", "action": "love"},
    "смутить": {"emoji": "😊", "description": "Вызвать милое смущение", "action": "blush"},
    "улыбнуться": {"emoji": "😄", "description": "Подарить улыбку", "action": "smile"},
    "почесать": {"emoji": "🐾", "description": "Почесать за ушком", "action": "scratch"},
    "взять на руки": {"emoji": "👑", "description": "Взять на ручки", "action": "carry"},
    "крепко обнять": {"emoji": "🫂", "description": "Крепкие объятия", "action": "superhug"},
    "похвалить": {"emoji": "🌟", "description": "Похвалить", "action": "praise"},
    "подмигнуть": {"emoji": "😉", "description": "Подмигнуть игриво", "action": "wink"},
    "пощекотать": {"emoji": "😂", "description": "Пощекотать до смеха", "action": "tickle"},
    "поцеловать в щечку": {"emoji": "😚", "description": "Нежный поцелуй в щечку", "action": "cheek_kiss"},
    "шепнуть": {"emoji": "🔇", "description": "Шепнуть что-то на ушко", "action": "whisper"},
    "танцевать": {"emoji": "💃", "description": "Пригласить на танец", "action": "dance"},
    "спеть": {"emoji": "🎵", "description": "Спеть серенаду", "action": "sing"},
    "сделать массаж": {"emoji": "💆", "description": "Сделать расслабляющий массаж", "action": "massage"},
    "укрыть": {"emoji": "🛏️", "description": "Укрыть одеялом", "action": "cover"},
    "накормить": {"emoji": "🍓", "description": "Накормить чем-то вкусным", "action": "feed"},
    "ревновать": {"emoji": "💔", "description": "Показать ревность", "action": "jealous"},
    "флиртовать": {"emoji": "😘", "description": "Начать флиртовать", "action": "flirt"},
    "заботиться": {"emoji": "🥰", "description": "Показать заботу", "action": "care"},
    "защищать": {"emoji": "🛡️", "description": "Встать на защиту", "action": "protect"},
    "восхищаться": {"emoji": "🤩", "description": "Выразить восхищение", "action": "admire"},
    "благодарить": {"emoji": "🙏", "description": "Поблагодарить", "action": "thank"},
    "целовать в лоб": {"emoji": "😘", "description": "Нежно поцеловать в лобик", "action": "forehead_kiss"},
    "держать за руку": {"emoji": "🤝", "description": "Взять за ручку", "action": "hold_hand"},
    "смотреть в глаза": {"emoji": "👀", "description": "Глубоко смотреть в глаза", "action": "gaze"},
    "сделать сюрприз": {"emoji": "🎁", "description": "Сделать приятный сюрприз", "action": "surprise"},
    # 18+ взаимодействия
    "ласкать": {"emoji": "✨", "description": "Нежно ласкать", "action": "caress"},
    "прижать": {"emoji": "🔥", "description": "Страстно прижать", "action": "press"},
    "привязать": {"emoji": "🎀", "description": "Нежно привязать", "action": "tie"},
    "прилечь на ножки": {"emoji": "🦵", "description": "Прилечь на ножки", "action": "lay_on_legs"},
    "раздеть": {"emoji": "👗", "description": "Нежно раздеть", "action": "undress"},
    "переодеть": {"emoji": "🎭", "description": "Переодеть в костюм", "action": "redress"},
    "удовлетворить": {"emoji": "💫", "description": "Удовлетворить", "action": "satisfy"},
    "лапать": {"emoji": "✋", "description": "Нежно лапать", "action": "grope"},
    "кусать": {"emoji": "🦷", "description": "Нежно кусать", "action": "bite"},
    "лизать": {"emoji": "👅", "description": "Нежно лизать", "action": "lick"},
    "дразнить": {"emoji": "😈", "description": "Игриво дразнить", "action": "tease"},
    "возбуждать": {"emoji": "💦", "description": "Страстно возбуждать", "action": "arouse"},
    "трахнуть": {"emoji": "🍆", "description": "Страстно трахнуть", "action": "fuck"},
    "отсосать": {"emoji": "💦", "description": "Нежно отсосать", "action": "suck"},
    "кончить": {"emoji": "💧", "description": "Кончить на/в", "action": "cum"},
    "секс": {"emoji": "🛏️", "description": "Заняться сексом", "action": "sex"},
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
    "blush": "😊 смутил(а)",
    "smile": "😄 улыбнулся(ась)",
    "scratch": "🐾 почесал(а)",
    "carry": "👑 взял(а) на ручки",
    "superhug": "🫂 крепко обнял(а)",
    "praise": "🌟 похвалил(а)",
    "wink": "😉 подмигнул(а)",
    "tickle": "😂 пощекотал(а)",
    "cheek_kiss": "😚 поцеловал(а) в щечку",
    "whisper": "🔇 прошептал(а) на ушко",
    "dance": "💃 пригласил(а) на танец",
    "sing": "🎵 спел(а) серенаду для",
    "massage": "💆 сделал(а) массаж",
    "cover": "🛏️ укрыл(а) одеялом",
    "feed": "🍓 накормил(а)",
    "jealous": "💔 показал(а) ревность к",
    "flirt": "😘 начал(а) флиртовать с",
    "care": "🥰 позаботился(ась) о",
    "protect": "🛡️ встал(а) на защиту",
    "admire": "🤩 восхищается",
    "thank": "🙏 поблагодарил(а)",
    "forehead_kiss": "😘 поцеловал(а) в лобик",
    "hold_hand": "🤝 взял(а) за ручку",
    "gaze": "👀 глубоко смотрит в глаза",
    "surprise": "🎁 сделал(а) сюрприз для",
    # 18+ тексты
    "caress": "✨ нежно ласкает",
    "press": "🔥 страстно прижал(а)",
    "tie": "🎀 нежно привязал(а)",
    "lay_on_legs": "🦵 прилёг(ла) на ножки",
    "undress": "👗 нежно раздел(а)",
    "redress": "🎭 переодел(а) в костюм",
    "satisfy": "💫 удовлетворил(а)",
    "grope": "✋ нежно лапает",
    "bite": "🦷 нежно кусает",
    "lick": "👅 нежно лижет",
    "tease": "😈 игриво дразнит",
    "arouse": "💦 страстно возбуждает",
    "fuck": "🍆 страстно трахает",
    "suck": "💦 нежно сосет",
    "cum": "💧 кончил(а) на",
    "sex": "🛏️ занялся(ась) сексом с"
}

# Глобальные переменные
animation_jobs = {}

# ========================
# БАЗА ДАННЫХ
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
# АНИМАЦИЯ СЕРДЦА
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
# АНОНИМНЫЕ ЗАПИСКИ
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
# СОВМЕСТИМОСТЬ
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
# ИНЛАЙН-РЕЖИМ
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
# КОМАНДЫ С ЮЗЕРНЕЙМОМ
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

# Обработчики для всех действий
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

async def send_blush(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "blush", "😊 смутил(а)")

async def send_smile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "smile", "😄 улыбнулся(ась)")

async def send_scratch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "scratch", "🐾 почесал(а)")

async def send_carry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "carry", "👑 взял(а) на ручки")

async def send_superhug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "superhug", "🫂 крепко обнял(а)")

async def send_praise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "praise", "🌟 похвалил(а)")

async def send_wink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "wink", "😉 подмигнул(а)")

async def send_tickle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "tickle", "😂 пощекотал(а)")

async def send_cheek_kiss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "cheek_kiss", "😚 поцеловал(а) в щечку")

async def send_whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "whisper", "🔇 прошептал(а) на ушко")

async def send_dance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "dance", "💃 пригласил(а) на танец")

async def send_sing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "sing", "🎵 спел(а) серенаду для")

async def send_massage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "massage", "💆 сделал(а) массаж")

async def send_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "cover", "🛏️ укрыл(а) одеялом")

async def send_feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "feed", "🍓 накормил(а)")

async def send_jealous(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "jealous", "💔 показал(а) ревность к")

async def send_flirt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "flirt", "😘 начал(а) флиртовать с")

async def send_care(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "care", "🥰 позаботился(ась) о")

async def send_protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "protect", "🛡️ встал(а) на защиту")

async def send_admire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "admire", "🤩 восхищается")

async def send_thank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "thank", "🙏 поблагодарил(а)")

async def send_forehead_kiss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "forehead_kiss", "😘 поцеловал(а) в лобик")

async def send_hold_hand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "hold_hand", "🤝 взял(а) за ручку")

async def send_gaze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "gaze", "👀 глубоко смотрит в глаза")

async def send_surprise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "surprise", "🎁 сделал(а) сюрприз для")

# 18+ команды
async def send_caress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "caress", "✨ нежно ласкает")

async def send_press(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "press", "🔥 страстно прижал(а)")

async def send_tie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "tie", "🎀 нежно привязал(а)")

async def send_lay_on_legs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "lay_on_legs", "🦵 прилёг(ла) на ножки")

async def send_undress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "undress", "👗 нежно раздел(а)")

async def send_redress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "redress", "🎭 переодел(а) в костюм")

async def send_satisfy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "satisfy", "💫 удовлетворил(а)")

async def send_grope(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "grope", "✋ нежно лапает")

async def send_bite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "bite", "🦷 нежно кусает")

async def send_lick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "lick", "👅 нежно лижет")

async def send_tease(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "tease", "😈 игриво дразнит")

async def send_arouse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "arouse", "💦 страстно возбуждает")

async def send_fuck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "fuck", "🍆 страстно трахает")

async def send_suck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "suck", "💦 нежно сосет")

async def send_cum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "cum", "💧 кончил(а) на")

async def send_sex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_cute_action_with_username(update, context, "sex", "🛏️ занялся(ась) сексом с")

# ========================
# ОБРАБОТЧИКИ КНОПОК
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
# ОСНОВНЫЕ КОМАНДЫ
# ========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    welcome_text = (
        f"💖 Привет, {user.first_name}!\n\n"
        "Я бот для романтики и нежных чувств! 💕\n\n"
        "✨ *Что я умею:*\n"
        "• Анимированные признания в любви ❤️\n"
        "• 40+ романтических действий\n"
        "• Анонимные записки 💌\n"
        "• Проверка совместимости 💑\n"
        "• Интерактивные кнопки ответа\n\n"
        "💝 *Основные команды:*\n"
        "`/heart` - Анимация сердца\n"
        "`/note @username текст` - Анонимная записка\n"
        "`/compatibility @username` - Совместимость\n"
        "`/help` - Все команды\n\n"
        "💬 *Инлайн-режим:*\n"
        f"Напишите `@{context.bot.username}` в любом чате!"
    )

    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "💖 Все команды бота\n\n"
        "💝 Основные:\n"
        "/start - Начать работу\n"
        "/heart - Анимация сердца\n"
        "/note @username текст - Анонимная записка\n"
        "/compatibility @username - Совместимость\n\n"
        "🎮 Романтические действия:\n"
        "/kiss @username - Поцеловать 💋\n"
        "/hug @username - Обнять 🤗\n"
        "/pat @username - Погладить 🖐️\n"
        "/cuddle @username - Прижаться 🫂\n"
        "/love @username - Признаться в любви 💌\n"
        "/blush @username - Смутить 😊\n"
        "/smile @username - Улыбнуться 😄\n"
        "/scratch @username - Почесать 🐾\n"
        "/carry @username - Взять на ручки 👑\n"
        "/superhug @username - Крепко обнять 🫂\n"
        "/praise @username - Похвалить 🌟\n"
        "/wink @username - Подмигнуть 😉\n"
        "/tickle @username - Пощекотать 😂\n"
        "/cheek_kiss @username - Поцеловать в щечку 😚\n"
        "/whisper @username - Шепнуть 🔇\n"
        "/dance @username - Пригласить на танец 💃\n"
        "/sing @username - Спеть серенаду 🎵\n"
        "/massage @username - Сделать массаж 💆\n"
        "/cover @username - Укрыть одеялом 🛏️\n"
        "/feed @username - Накормить 🍓\n"
        "/jealous @username - Показать ревность 💔\n"
        "/flirt @username - Флиртовать 😘\n"
        "/care @username - Позаботиться 🥰\n"
        "/protect @username - Защитить 🛡️\n"
        "/admire @username - Восхищаться 🤩\n"
        "/thank @username - Поблагодарить 🙏\n"
        "/forehead_kiss @username - Поцеловать в лобик 😘\n"
        "/hold_hand @username - Взять за ручку 🤝\n"
        "/gaze @username - Смотреть в глаза 👀\n"
        "/surprise @username - Сделать сюрприз 🎁\n\n"
        "🔥 Для взрослых (18+):\n"
        "/caress @username - Нежно ласкать ✨\n"
        "/press @username - Страстно прижать 🔥\n"
        "/tie @username - Нежно привязать 🎀\n"
        "/lay_on_legs @username - Прилечь на ножки 🦵\n"
        "/undress @username - Нежно раздеть 👗\n"
        "/redress @username - Переодеть в костюм 🎭\n"
        "/satisfy @username - Удовлетворить 💫\n"
        "/grope @username - Нежно лапать ✋\n"
        "/bite @username - Нежно кусать 🦷\n"
        "/lick @username - Нежно лизать 👅\n"
        "/tease @username - Игриво дразнить 😈\n"
        "/arouse @username - Страстно возбуждать 💦\n"
        "/fuck @username - Страстно трахать 🍆\n"
        "/suck @username - Нежно сосать 💦\n"
        "/cum @username - Кончить на 💧\n"
        "/sex @username - Заняться сексом 🛏️\n\n"
        "💬 Инлайн-режим:\n"
        f"Напишите @{context.bot.username} в любом чате!"
    )

    await update.message.reply_text(help_text, parse_mode="Markdown")

# ========================
# ЗАПУСК БОТА
# ========================

def main():
    # Инициализация базы данных
    init_db()

    # Создание приложения бота
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()

    # Обработчики основных команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("heart", send_heart))
    application.add_handler(CommandHandler("note", start_anonymous_note))
    application.add_handler(CommandHandler("compatibility", start_compatibility))

    # Обработчики романтических действий
    application.add_handler(CommandHandler("kiss", send_kiss))
    application.add_handler(CommandHandler("hug", send_hug))
    application.add_handler(CommandHandler("pat", send_pat))
    application.add_handler(CommandHandler("cuddle", send_cuddle))
    application.add_handler(CommandHandler("love", send_love))
    application.add_handler(CommandHandler("blush", send_blush))
    application.add_handler(CommandHandler("smile", send_smile))
    application.add_handler(CommandHandler("scratch", send_scratch))
    application.add_handler(CommandHandler("carry", send_carry))
    application.add_handler(CommandHandler("superhug", send_superhug))
    application.add_handler(CommandHandler("praise", send_praise))
    application.add_handler(CommandHandler("wink", send_wink))
    application.add_handler(CommandHandler("tickle", send_tickle))
    application.add_handler(CommandHandler("cheek_kiss", send_cheek_kiss))
    application.add_handler(CommandHandler("whisper", send_whisper))
    application.add_handler(CommandHandler("dance", send_dance))
    application.add_handler(CommandHandler("sing", send_sing))
    application.add_handler(CommandHandler("massage", send_massage))
    application.add_handler(CommandHandler("cover", send_cover))
    application.add_handler(CommandHandler("feed", send_feed))
    application.add_handler(CommandHandler("jealous", send_jealous))
    application.add_handler(CommandHandler("flirt", send_flirt))
    application.add_handler(CommandHandler("care", send_care))
    application.add_handler(CommandHandler("protect", send_protect))
    application.add_handler(CommandHandler("admire", send_admire))
    application.add_handler(CommandHandler("thank", send_thank))
    application.add_handler(CommandHandler("forehead_kiss", send_forehead_kiss))
    application.add_handler(CommandHandler("hold_hand", send_hold_hand))
    application.add_handler(CommandHandler("gaze", send_gaze))
    application.add_handler(CommandHandler("surprise", send_surprise))

    # Обработчики 18+ действий
    application.add_handler(CommandHandler("caress", send_caress))
    application.add_handler(CommandHandler("press", send_press))
    application.add_handler(CommandHandler("tie", send_tie))
    application.add_handler(CommandHandler("lay_on_legs", send_lay_on_legs))
    application.add_handler(CommandHandler("undress", send_undress))
    application.add_handler(CommandHandler("redress", send_redress))
    application.add_handler(CommandHandler("satisfy", send_satisfy))
    application.add_handler(CommandHandler("grope", send_grope))
    application.add_handler(CommandHandler("bite", send_bite))
    application.add_handler(CommandHandler("lick", send_lick))
    application.add_handler(CommandHandler("tease", send_tease))
    application.add_handler(CommandHandler("arouse", send_arouse))
    application.add_handler(CommandHandler("fuck", send_fuck))
    application.add_handler(CommandHandler("suck", send_suck))
    application.add_handler(CommandHandler("cum", send_cum))
    application.add_handler(CommandHandler("sex", send_sex))

    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(handle_heart_response, pattern="^heart_"))
    application.add_handler(CallbackQueryHandler(handle_inline_button_response, pattern="^inline_"))
    application.add_handler(CallbackQueryHandler(handle_regular_button_response, pattern="^(respond|reject)_"))

    # Инлайн-режим
    application.add_handler(InlineQueryHandler(handle_inline_query))

    logger.info("Бот запущен со всеми взаимодействиями!")
    application.run_polling()

if __name__ == '__main__':
    main()

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, InlineQueryHandler
import os
import itertools
import uuid

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')

# Все взаимодействия 18+ включительно
INLINE_ACTIONS = {
    "поцеловать": {"emoji": "💋", "description": "Послать нежный поцелуй", "action": "kiss"},
    "обнять": {"emoji": "🤗", "description": "Отправить теплые объятия", "action": "hug"}, 
    "погладить": {"emoji": "🖐️", "description": "Погладить по головке", "action": "pat"},
    "прижаться": {"emoji": "🫂", "description": "Прижаться и обниматься", "action": "cuddle"},
    "люблю": {"emoji": "💌", "description": "Признаться в любви", "action": "love"},
    "улыбнуться": {"emoji": "😄", "description": "Подарить улыбку", "action": "smile"},
    "подмигнуть": {"emoji": "😉", "description": "Подмигнуть игриво", "action": "wink"},
    "пощекотать": {"emoji": "😂", "description": "Пощекотать до смеха", "action": "tickle"},
    "поцеловать в щечку": {"emoji": "😚", "description": "Нежный поцелуй в щечку", "action": "cheek_kiss"},
    "шепнуть": {"emoji": "🔇", "description": "Шепнуть что-то на ушко", "action": "whisper"},
    # 18+ взаимодействия
    "ласкать": {"emoji": "✨", "description": "Нежно ласкать", "action": "caress"},
    "прижать": {"emoji": "🔥", "description": "Страстно прижать", "action": "press"},
    "привязать": {"emoji": "🎀", "description": "Нежно привязать", "action": "tie"},
    "раздеть": {"emoji": "👗", "description": "Нежно раздеть", "action": "undress"},
    "удовлетворить": {"emoji": "💫", "description": "Удовлетворить", "action": "satisfy"},
    "лапать": {"emoji": "✋", "description": "Нежно лапать", "action": "grope"},
    "кусать": {"emoji": "🦷", "description": "Нежно кусать", "action": "bite"},
    "лизать": {"emoji": "👅", "description": "Нежно лизать", "action": "lick"},
    "дразнить": {"emoji": "😈", "description": "Игриво дразнить", "action": "tease"},
    "возбуждать": {"emoji": "💦", "description": "Страстно возбуждать", "action": "arouse"},
    "трахнуть": {"emoji": "🍆", "description": "Страстно трахнуть", "action": "fuck"},
    "отсосать": {"emoji": "💦", "description": "Нежно отсосать", "action": "suck"},
    "кончить": {"emoji": "💧", "description": "Кончить на/в", "action": "cum"},
    "секс": {"emoji": "🛏️", "description": "Заняться сексом", "action": "sex"}
}

ACTION_TEXTS = {
    "kiss": "💋 поцеловал(а)",
    "hug": "🤗 обнял(а)",
    "pat": "🖐️ погладил(а)",
    "cuddle": "🫂 прижался(ась) к",
    "love": "💌 признался(ась) в любви",
    "smile": "😄 улыбнулся(ась)",
    "wink": "😉 подмигнул(а)",
    "tickle": "😂 пощекотал(а)",
    "cheek_kiss": "😚 поцеловал(а) в щечку",
    "whisper": "🔇 прошептал(а) на ушко",
    # 18+ тексты
    "caress": "✨ нежно ласкает",
    "press": "🔥 страстно прижал(а)",
    "tie": "🎀 нежно привязал(а)",
    "undress": "👗 нежно раздел(а)",
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

HEART_FRAMES = ["❤️", "💖", "💗", "💓", "💞", "💕", "💘", "💝"]

# Основные команды
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    await update.message.reply_text(
        f"💖 Привет, {user.first_name}!\n\n"
        "Я бот для романтики и страсти! 🔥\n\n"
        "✨ Используй команды:\n"
        "/help - Все команды\n"
        "/kiss @username - Поцеловать\n"
        "/hug @username - Обнять\n"
        "/sex @username - Заняться сексом\n"
        "и многое другое...\n\n"
        "💬 Или напиши @{context.bot.username} в любом чате!"
    )

async def help_command(update: Update, context: CallbackContext):
    help_text = """
💖 *Все команды:*

*Романтические:*
/kiss @username - Поцеловать 💋
/hug @username - Обнять 🤗  
/pat @username - Погладить 🖐️
/love @username - Признаться в любви 💌
/cuddle @username - Прижаться 🫂
/smile @username - Улыбнуться 😄

*Страстные (18+):*
/caress @username - Ласкать ✨
/press @username - Прижать 🔥
/undress @username - Раздеть 👗
/satisfy @username - Удовлетворить 💫
/grope @username - Лапать ✋
/bite @username - Кусать 🦷
/lick @username - Лизать 👅
/tease @username - Дразнить 😈
/arouse @username - Возбуждать 💦
/fuck @username - Трахнуть 🍆
/suck @username - Сосать 💦
/cum @username - Кончить 💧
/sex @username - Секс 🛏️

💬 *Инлайн-режим:*
Напиши @{context.bot.username} в любом чате!
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")

# Функция для отправки действий
async def send_action(update: Update, context: CallbackContext, action_type: str, action_text: str):
    if not context.args:
        await update.message.reply_text(f"❌ Используй: /{action_type} @username")
        return
    
    target = context.args[0]
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("💖 Ответить взаимностью", callback_data=f"respond_{action_type}")],
        [InlineKeyboardButton("❌ Отказаться", callback_data="reject_action")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(f"{ACTION_TEXTS[action_type]} {target}!", reply_markup=reply_markup)

# Романтические команды
async def send_kiss(update: Update, context: CallbackContext):
    await send_action(update, context, "kiss", "💋 поцеловал(а)")

async def send_hug(update: Update, context: CallbackContext):
    await send_action(update, context, "hug", "🤗 обнял(а)")

async def send_pat(update: Update, context: CallbackContext):
    await send_action(update, context, "pat", "🖐️ погладил(а)")

async def send_love(update: Update, context: CallbackContext):
    await send_action(update, context, "love", "💌 признался(ась) в любви")

async def send_cuddle(update: Update, context: CallbackContext):
    await send_action(update, context, "cuddle", "🫂 прижался(ась) к")

async def send_smile(update: Update, context: CallbackContext):
    await send_action(update, context, "smile", "😄 улыбнулся(ась)")

# 18+ команды
async def send_caress(update: Update, context: CallbackContext):
    await send_action(update, context, "caress", "✨ нежно ласкает")

async def send_press(update: Update, context: CallbackContext):
    await send_action(update, context, "press", "🔥 страстно прижал(а)")

async def send_undress(update: Update, context: CallbackContext):
    await send_action(update, context, "undress", "👗 нежно раздел(а)")

async def send_satisfy(update: Update, context: CallbackContext):
    await send_action(update, context, "satisfy", "💫 удовлетворил(а)")

async def send_grope(update: Update, context: CallbackContext):
    await send_action(update, context, "grope", "✋ нежно лапает")

async def send_bite(update: Update, context: CallbackContext):
    await send_action(update, context, "bite", "🦷 нежно кусает")

async def send_lick(update: Update, context: CallbackContext):
    await send_action(update, context, "lick", "👅 нежно лижет")

async def send_tease(update: Update, context: CallbackContext):
    await send_action(update, context, "tease", "😈 игриво дразнит")

async def send_arouse(update: Update, context: CallbackContext):
    await send_action(update, context, "arouse", "💦 страстно возбуждает")

async def send_fuck(update: Update, context: CallbackContext):
    await send_action(update, context, "fuck", "🍆 страстно трахает")

async def send_suck(update: Update, context: CallbackContext):
    await send_action(update, context, "suck", "💦 нежно сосет")

async def send_cum(update: Update, context: CallbackContext):
    await send_action(update, context, "cum", "💧 кончил(а) на")

async def send_sex(update: Update, context: CallbackContext):
    await send_action(update, context, "sex", "🛏️ занялся(ась) сексом с")

# Инлайн режим
async def handle_inline_query(update: Update, context: CallbackContext):
    query = update.inline_query.query.lower().strip()
    user = update.inline_query.from_user
    
    results = []
    
    for action_name, info in INLINE_ACTIONS.items():
        if not query or query in action_name:
            message_text = f"{info['emoji']} {user.first_name} {action_name}!"
            
            keyboard = [
                [InlineKeyboardButton("💖 Ответить взаимностью", callback_data=f"inline_{info['action']}")],
                [InlineKeyboardButton("❌ Отказаться", callback_data="inline_reject")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=f"{info['emoji']} {action_name.capitalize()}",
                    description=info['description'],
                    input_message_content=InputTextMessageContent(message_text),
                    reply_markup=reply_markup
                )
            )
    
    await update.inline_query.answer(results, cache_time=0)

# Обработка кнопок
async def handle_button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if "respond" in query.data:
        await query.edit_message_text(f"💖 {user.first_name} ответил(а) взаимностью! 💕")
    elif "reject" in query.data:
        await query.edit_message_text(f"💔 {user.first_name} отказался(ась)...")

# Запуск бота
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Основные команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Романтические команды
    application.add_handler(CommandHandler("kiss", send_kiss))
    application.add_handler(CommandHandler("hug", send_hug))
    application.add_handler(CommandHandler("pat", send_pat))
    application.add_handler(CommandHandler("love", send_love))
    application.add_handler(CommandHandler("cuddle", send_cuddle))
    application.add_handler(CommandHandler("smile", send_smile))
    
    # 18+ команды
    application.add_handler(CommandHandler("caress", send_caress))
    application.add_handler(CommandHandler("press", send_press))
    application.add_handler(CommandHandler("undress", send_undress))
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
    
    # Обработчики
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(InlineQueryHandler(handle_inline_query))
    
    # Запуск
    application.run_polling()

if __name__ == '__main__':
    main()

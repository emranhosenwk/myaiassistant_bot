import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8643482563:AAHBCVHeY4ufObZ-_cZarjBru2U9kNWPq0U")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Groq client
client = Groq(api_key=GROQ_API_KEY)

# Store conversation history per user
user_histories = {}

SYSTEM_PROMPT = """You are a helpful, friendly AI assistant. You can help with:
- Answering questions on any topic
- Writing and editing text
- Coding help
- Analysis and research
- General conversation

Be concise, helpful, and friendly. Respond in the same language the user writes in."""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        "I'm your AI Assistant powered by Groq ⚡\n\n"
        "You can ask me anything! I can help with:\n"
        "• 💬 General questions\n"
        "• ✍️ Writing & editing\n"
        "• 💻 Coding help\n"
        "• 🔍 Research & analysis\n\n"
        "Just send me a message to get started!\n\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/clear - Clear conversation history\n"
        "/help - Get help"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *AI Assistant Help*\n\n"
        "Just send me any message and I'll respond!\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/clear - Clear chat history\n"
        "/help - Show this help\n\n"
        "*Tips:*\n"
        "• I remember our conversation context\n"
        "• Use /clear to start a fresh conversation\n"
        "• I can respond in any language",
        parse_mode="Markdown"
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("🗑️ Conversation cleared! Let's start fresh.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    # Initialize history for new users
    if user_id not in user_histories:
        user_histories[user_id] = []

    # Add user message to history
    user_histories[user_id].append({
        "role": "user",
        "content": user_message
    })

    # Keep only last 10 messages to avoid token limits
    if len(user_histories[user_id]) > 10:
        user_histories[user_id] = user_histories[user_id][-10:]

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        # Call Groq API
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *user_histories[user_id]
            ],
            max_tokens=1024,
            temperature=0.7
        )

        assistant_message = response.choices[0].message.content

        # Add assistant response to history
        user_histories[user_id].append({
            "role": "assistant",
            "content": assistant_message
        })

        await update.message.reply_text(assistant_message)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            "❌ Sorry, something went wrong. Please try again!"
        )


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in groups - only respond when mentioned"""
    bot_username = context.bot.username
    message = update.message

    # Check if bot is mentioned or message is a reply to bot
    is_mentioned = f"@{bot_username}" in (message.text or "")
    is_reply_to_bot = (
        message.reply_to_message and
        message.reply_to_message.from_user.id == context.bot.id
    )

    if is_mentioned or is_reply_to_bot:
        # Remove bot mention from message
        clean_message = (message.text or "").replace(f"@{bot_username}", "").strip()
        update.message.text = clean_message
        await handle_message(update, context)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear))

    # Private chat messages
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_message
    ))

    # Group messages (only when mentioned)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
        handle_group_message
    ))

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

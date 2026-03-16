import os
import logging
import httpx
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from groq import Groq
from urllib.parse import quote

# ========== CONFIG ==========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")  # openweathermap.org - free
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")  # newsapi.org - free

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY)
user_histories = {}

SYSTEM_PROMPT = """You are a powerful AI assistant in Telegram. You can help with:
- Answering any questions
- Writing emails, CVs, cover letters, essays
- Writing and debugging code
- Translating text
- Summarizing content
- Analysis and research
- General conversation

Be helpful, concise, and friendly. Use the same language the user writes in.
Format responses nicely using Telegram markdown when appropriate."""

# ========== AI HELPER ==========
async def get_ai_response(user_id: int, message: str, system: str = None) -> str:
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    user_histories[user_id].append({"role": "user", "content": message})
    if len(user_histories[user_id]) > 12:
        user_histories[user_id] = user_histories[user_id][-12:]
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system or SYSTEM_PROMPT},
            *user_histories[user_id]
        ],
        max_tokens=1024,
        temperature=0.7,
    )
    
    reply = response.choices[0].message.content
    user_histories[user_id].append({"role": "assistant", "content": reply})
    return reply

# ========== COMMANDS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🌤️ Weather", callback_data="menu_weather"),
         InlineKeyboardButton("📰 News", callback_data="menu_news")],
        [InlineKeyboardButton("🔍 Web Search", callback_data="menu_search"),
         InlineKeyboardButton("🖼️ Image Gen", callback_data="menu_image")],
        [InlineKeyboardButton("✍️ Write For Me", callback_data="menu_write"),
         InlineKeyboardButton("💻 Code Help", callback_data="menu_code")],
        [InlineKeyboardButton("🌐 Summarize URL", callback_data="menu_url"),
         InlineKeyboardButton("💱 Currency", callback_data="menu_currency")],
        [InlineKeyboardButton("📋 All Commands", callback_data="menu_help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 *Welcome to SuperBot AI!*\n\n"
        f"I'm your all-in-one AI assistant. I can:\n\n"
        f"🤖 Answer any question\n"
        f"🌤️ Check weather anywhere\n"
        f"📰 Get latest news\n"
        f"🔍 Search the web\n"
        f"🖼️ Generate images\n"
        f"✍️ Write emails, CVs & more\n"
        f"💻 Help with coding\n"
        f"🌐 Summarize websites\n"
        f"💱 Convert currencies\n\n"
        f"_Just send me a message or pick an option below!_",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📋 *SuperBot AI — Commands*

🤖 *AI Chat:*
Just send any message!

🌤️ *Weather:*
`/weather London`
`/weather Dhaka`

📰 *News:*
`/news technology`
`/news bangladesh`

🔍 *Web Search:*
`/search python tutorial`

🖼️ *Image Generation:*
`/image a beautiful sunset`

✍️ *Writing:*
`/email [topic]` — Write email
`/cv [job title]` — Write CV tips
`/translate [text]` — Translate

💻 *Coding:*
`/code [your question]`

🌐 *Summarize Website:*
`/url https://example.com`

💱 *Currency:*
`/currency 100 USD to BDT`

🗑️ *Clear History:*
`/clear`

_Powered by Groq AI ⚡_
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("🗑️ Conversation history cleared!")

# ========== WEATHER ==========
async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Usage: `/weather London`", parse_mode="Markdown")
    
    city = " ".join(context.args)
    await update.message.reply_text(f"🌤️ Getting weather for *{city}*...", parse_mode="Markdown")
    
    try:
        if WEATHER_API_KEY:
            async with httpx.AsyncClient() as client_http:
                r = await client_http.get(
                    f"https://api.openweathermap.org/data/2.5/weather",
                    params={"q": city, "appid": WEATHER_API_KEY, "units": "metric"}
                )
                data = r.json()
                
                if data.get("cod") == 200:
                    temp = data["main"]["temp"]
                    feels = data["main"]["feels_like"]
                    humidity = data["main"]["humidity"]
                    desc = data["weather"][0]["description"].title()
                    wind = data["wind"]["speed"]
                    country = data["sys"]["country"]
                    
                    text = f"""🌍 *{city}, {country}*

🌡️ Temperature: *{temp}°C* (Feels like {feels}°C)
☁️ Condition: *{desc}*
💧 Humidity: *{humidity}%*
💨 Wind: *{wind} m/s*

_Powered by OpenWeatherMap_"""
                    await update.message.reply_text(text, parse_mode="Markdown")
                else:
                    await update.message.reply_text(f"❌ City '{city}' not found!")
        else:
            # Use AI if no API key
            reply = await get_ai_response(
                update.effective_user.id,
                f"Give me a general weather description for {city} based on its typical climate. Format nicely.",
                "You are a weather assistant. Provide helpful weather information."
            )
            await update.message.reply_text(f"🌤️ *{city} Weather Info:*\n\n{reply}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Weather error: {e}")
        await update.message.reply_text("❌ Could not fetch weather. Try again!")

# ========== NEWS ==========
async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args) if context.args else "world"
    await update.message.reply_text(f"📰 Getting latest news about *{topic}*...", parse_mode="Markdown")
    
    try:
        if NEWS_API_KEY:
            async with httpx.AsyncClient() as client_http:
                r = await client_http.get(
                    "https://newsapi.org/v2/everything",
                    params={"q": topic, "apiKey": NEWS_API_KEY, "pageSize": 5, "sortBy": "publishedAt"}
                )
                data = r.json()
                
                if data.get("articles"):
                    text = f"📰 *Latest News: {topic.title()}*\n\n"
                    for i, article in enumerate(data["articles"][:5], 1):
                        title = article.get("title", "No title")[:80]
                        url = article.get("url", "")
                        text += f"{i}. [{title}]({url})\n\n"
                    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)
                else:
                    await update.message.reply_text("❌ No news found for this topic.")
        else:
            # Use AI
            reply = await get_ai_response(
                update.effective_user.id,
                f"Give me 5 recent news headlines about {topic}. Format as a numbered list with brief descriptions.",
                "You are a news assistant. Provide recent, factual news summaries."
            )
            await update.message.reply_text(f"📰 *News: {topic.title()}*\n\n{reply}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"News error: {e}")
        await update.message.reply_text("❌ Could not fetch news. Try again!")

# ========== WEB SEARCH ==========
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Usage: `/search python tutorial`", parse_mode="Markdown")
    
    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 Searching for *{query}*...", parse_mode="Markdown")
    
    try:
        reply = await get_ai_response(
            update.effective_user.id,
            f"Search results for: {query}\n\nProvide comprehensive, accurate information about this topic. Include key facts, explanations, and if relevant, mention where to find more info.",
            "You are a web search assistant. Provide accurate, comprehensive search results."
        )
        
        search_url = f"https://www.google.com/search?q={quote(query)}"
        keyboard = [[InlineKeyboardButton("🔍 Open Google", url=search_url)]]
        
        await update.message.reply_text(
            f"🔍 *Search: {query}*\n\n{reply}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("❌ Search failed. Try again!")

# ========== IMAGE GENERATION ==========
async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Usage: `/image a beautiful sunset over mountains`", parse_mode="Markdown")
    
    prompt = " ".join(context.args)
    await update.message.reply_text(f"🖼️ Generating image: *{prompt}*\n\n⏳ Please wait...", parse_mode="Markdown")
    
    try:
        # Using Pollinations AI - completely free
        image_url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=800&height=600&nologo=true"
        
        async with httpx.AsyncClient(timeout=30) as client_http:
            r = await client_http.get(image_url)
            
            if r.status_code == 200:
                await update.message.reply_photo(
                    photo=r.content,
                    caption=f"🖼️ *Generated Image*\n\n_{prompt}_\n\n_Powered by Pollinations AI_",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Image generation failed. Try a different prompt!")
    except Exception as e:
        logger.error(f"Image error: {e}")
        await update.message.reply_text("❌ Image generation failed. Try again!")

# ========== EMAIL WRITING ==========
async def email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Usage: `/email job application for software developer`", parse_mode="Markdown")
    
    topic = " ".join(context.args)
    await update.message.reply_text(f"✍️ Writing email about: *{topic}*...", parse_mode="Markdown")
    
    try:
        reply = await get_ai_response(
            update.effective_user.id,
            f"Write a professional email about: {topic}",
            "You are a professional email writer. Write clear, professional, and effective emails."
        )
        await update.message.reply_text(f"✉️ *Email Draft:*\n\n{reply}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ Failed. Try again!")

# ========== TRANSLATE ==========
async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Usage: `/translate Hello, how are you?`", parse_mode="Markdown")
    
    text = " ".join(context.args)
    await update.message.reply_text("🌍 Translating...", parse_mode="Markdown")
    
    try:
        reply = await get_ai_response(
            update.effective_user.id,
            f"Detect the language of this text and translate it to English (if not English) or Bengali (if English): '{text}'\n\nProvide: 1) Detected language 2) Translation",
            "You are a professional translator. Provide accurate translations."
        )
        await update.message.reply_text(f"🌍 *Translation:*\n\n{reply}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ Translation failed. Try again!")

# ========== CODE HELP ==========
async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Usage: `/code how to make a for loop in python`", parse_mode="Markdown")
    
    question = " ".join(context.args)
    await update.message.reply_text("💻 Processing your code request...", parse_mode="Markdown")
    
    try:
        reply = await get_ai_response(
            update.effective_user.id,
            question,
            "You are an expert programmer. Provide clear, working code examples with explanations. Use proper code formatting."
        )
        await update.message.reply_text(f"💻 *Code Help:*\n\n{reply}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ Failed. Try again!")

# ========== URL SUMMARIZE ==========
async def url_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Usage: `/url https://example.com`", parse_mode="Markdown")
    
    url = context.args[0]
    await update.message.reply_text(f"🌐 Fetching and summarizing URL...", parse_mode="Markdown")
    
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client_http:
            r = await client_http.get(url, headers={"User-Agent": "Mozilla/5.0"})
            
            # Extract text (simple)
            text = r.text[:3000]
            
            reply = await get_ai_response(
                update.effective_user.id,
                f"Summarize the content of this webpage in 5 bullet points:\n\nURL: {url}\n\nContent snippet: {text}",
                "You are a web content summarizer. Provide clear, concise summaries."
            )
            await update.message.reply_text(f"🌐 *Website Summary:*\n_{url}_\n\n{reply}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"URL error: {e}")
        await update.message.reply_text("❌ Could not fetch URL. Make sure it's a valid, public URL.")

# ========== CURRENCY ==========
async def currency_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Usage: `/currency 100 USD to BDT`", parse_mode="Markdown")
    
    query = " ".join(context.args)
    await update.message.reply_text("💱 Converting currency...", parse_mode="Markdown")
    
    try:
        async with httpx.AsyncClient() as client_http:
            r = await client_http.get("https://api.exchangerate-api.com/v4/latest/USD")
            rates = r.json().get("rates", {})
        
        reply = await get_ai_response(
            update.effective_user.id,
            f"Convert: {query}\n\nCurrent exchange rates (based on USD): {json.dumps(dict(list(rates.items())[:20]))}",
            "You are a currency converter. Calculate accurate conversions using the provided rates."
        )
        await update.message.reply_text(f"💱 *Currency Conversion:*\n\n{reply}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Currency error: {e}")
        await update.message.reply_text("❌ Conversion failed. Try again!")

# ========== CALLBACK HANDLER ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    prompts = {
        "menu_weather": "🌤️ Send: `/weather [city name]`\n\nExample: `/weather Dhaka`",
        "menu_news": "📰 Send: `/news [topic]`\n\nExample: `/news technology` or `/news bangladesh`",
        "menu_search": "🔍 Send: `/search [query]`\n\nExample: `/search how to learn python`",
        "menu_image": "🖼️ Send: `/image [description]`\n\nExample: `/image beautiful mountain sunset`",
        "menu_write": "✍️ Commands:\n`/email [topic]` — Write email\n`/translate [text]` — Translate",
        "menu_code": "💻 Send: `/code [question]`\n\nExample: `/code how to read a file in python`",
        "menu_url": "🌐 Send: `/url [website link]`\n\nExample: `/url https://bbc.com`",
        "menu_currency": "💱 Send: `/currency [amount] [from] to [to]`\n\nExample: `/currency 100 USD to BDT`",
        "menu_help": None,
    }
    
    if data == "menu_help":
        await help_command(update, context)
    elif data in prompts:
        await query.message.reply_text(prompts[data], parse_mode="Markdown")

# ========== INTENT DETECTION ==========
async def detect_intent(message: str) -> dict:
    """Use AI to detect what the user wants to do"""
    system = """You are an intent detector. Analyze the user message and return ONLY a JSON object.
    
Detect these intents:
- image: user wants to generate/create/draw an image/picture/photo
- weather: user asks about weather/temperature/climate of a place  
- news: user wants news/updates about a topic
- search: user wants to search/find information
- translate: user wants to translate text
- currency: user wants to convert currency/money
- url: user shared a URL and wants it summarized
- chat: general conversation, questions, writing help, coding

Return JSON format:
{"intent": "image", "query": "extracted query for the action"}

Examples:
"ছবি বানাও একটা পাখির" -> {"intent": "image", "query": "a beautiful bird flying"}
"ঢাকার আবহাওয়া কেমন" -> {"intent": "weather", "query": "Dhaka"}
"আজকের খবর দেখাও" -> {"intent": "news", "query": "today world news"}
"100 ডলার বাংলাদেশি টাকায় কত" -> {"intent": "currency", "query": "100 USD to BDT"}
"এই লিংক summarize করো https://bbc.com" -> {"intent": "url", "query": "https://bbc.com"}
"how are you" -> {"intent": "chat", "query": "how are you"}

ONLY return the JSON, nothing else."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": message}
        ],
        max_tokens=100,
        temperature=0.1,
    )
    
    try:
        result = json.loads(response.choices[0].message.content.strip())
        return result
    except:
        return {"intent": "chat", "query": message}


# ========== MESSAGE HANDLER ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    
    if not user_message:
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Detect intent
        intent_data = await detect_intent(user_message)
        intent = intent_data.get("intent", "chat")
        query = intent_data.get("query", user_message)
        
        # Route to appropriate handler
        if intent == "image":
            await update.message.reply_text(f"🖼️ *ছবি তৈরি করছি:* _{query}_\n\n⏳ একটু অপেক্ষা করুন...", parse_mode="Markdown")
            try:
                encoded = quote(query)
                seed = abs(hash(query)) % 99999
                image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=800&height=600&nologo=true&seed={seed}"
                
                image_sent = False
                async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client_http:
                    try:
                        r = await client_http.get(image_url)
                        if r.status_code == 200 and len(r.content) > 5000:
                            await update.message.reply_photo(
                                photo=r.content,
                                caption=f"🖼️ *Generated Image*\n\n_{user_message}_\n\n_Powered by AI_",
                                parse_mode="Markdown"
                            )
                            image_sent = True
                    except:
                        pass
                
                if not image_sent:
                    keyboard = [[InlineKeyboardButton("🖼️ ছবি দেখুন", url=image_url)]]
                    await update.message.reply_text(
                        f"🖼️ *ছবি তৈরি হয়েছে!*\n\n_{query}_\n\nনিচের বাটনে click করে দেখুন 👇",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            except Exception as e:
                logger.error(f"Image error: {e}")
                await update.message.reply_text("❌ ছবি তৈরি করতে পারলাম না। আবার চেষ্টা করুন!")

        elif intent == "weather":
            context.args = query.split()
            await weather_command(update, context)

        elif intent == "news":
            context.args = query.split()
            await news_command(update, context)

        elif intent == "search":
            context.args = query.split()
            await search_command(update, context)

        elif intent == "translate":
            context.args = query.split()
            await translate_command(update, context)

        elif intent == "currency":
            context.args = query.split()
            await currency_command(update, context)

        elif intent == "url":
            # Extract URL from message
            words = user_message.split()
            url = next((w for w in words if w.startswith("http")), query)
            context.args = [url]
            await url_command(update, context)

        else:
            # General chat
            reply = await get_ai_response(update.effective_user.id, user_message)
            if len(reply) > 4096:
                for i in range(0, len(reply), 4096):
                    await update.message.reply_text(reply[i:i+4096])
            else:
                await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Message error: {e}")
        await update.message.reply_text("❌ Something went wrong. Please try again!")

# ========== MAIN ==========
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("weather", weather_command))
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(CommandHandler("email", email_command))
    app.add_handler(CommandHandler("translate", translate_command))
    app.add_handler(CommandHandler("code", code_command))
    app.add_handler(CommandHandler("url", url_command))
    app.add_handler(CommandHandler("currency", currency_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🚀 SuperBot AI is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

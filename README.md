# Telegram AI Chatbot 🤖

An AI-powered Telegram bot using Groq API (Free & Fast!)

## Features
- 💬 Smart AI conversations
- 🧠 Remembers conversation context
- 👥 Works in private chats & groups
- ⚡ Super fast responses (Groq)
- 🌍 Supports all languages

## Commands
- `/start` - Start the bot
- `/help` - Show help
- `/clear` - Clear conversation history

## Setup

### Local Run
```bash
pip install -r requirements.txt
python bot.py
```

### Railway Deploy
1. Upload files to GitHub
2. Connect Railway to GitHub repo
3. Add environment variables:
   - `TELEGRAM_TOKEN` = your telegram token
   - `GROQ_API_KEY` = your groq api key
4. Deploy!

## Environment Variables
| Variable | Description |
|----------|-------------|
| TELEGRAM_TOKEN | Your Telegram Bot Token from @BotFather |
| GROQ_API_KEY | Your Groq API Key from console.groq.com |

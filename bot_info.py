#!/usr/bin/env python3
"""
Helper script to get bot information and setup instructions
Usage: python bot_info.py
"""

import asyncio
from telegram import Bot
from config import Config
from dotenv import load_dotenv

load_dotenv()


async def get_bot_info():
    """Get bot information from Telegram"""
    bot_token = Config.TELEGRAM_BOT_TOKEN

    if not bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not set in .env file")
        print("\nPlease add your bot token to .env file:")
        print("TELEGRAM_BOT_TOKEN=your-bot-token-here")
        return

    try:
        bot = Bot(token=bot_token)
        me = await bot.get_me()

        print("\n" + "=" * 60)
        print("✅ Bot Connected Successfully!")
        print("=" * 60)
        print(f"\n📱 Bot Information:")
        print(f"   Name: {me.first_name}")
        print(f"   Username: @{me.username}")
        print(f"   ID: {me.id}")

        print("\n" + "=" * 60)
        print("📋 Setup Instructions:")
        print("=" * 60)

        print(f"\n1️⃣  Open Telegram and search for: @{me.username}")
        print(f"2️⃣  Click 'Start' or send any message to the bot")
        print(f"3️⃣  Get your Telegram ID from @userinfobot")
        print(f"4️⃣  Create a user with this command:")
        print(f"    python create_user.py create --phone YOUR_PHONE --telegram_id YOUR_ID")
        print(f"5️⃣  Run the app: python app.py")
        print(f"6️⃣  Login at: http://localhost:5000")

        print("\n" + "=" * 60)
        print("🔗 Bot Link: https://t.me/{0}".format(me.username))
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Error connecting to Telegram: {e}")
        print("\nPlease check:")
        print("1. Your TELEGRAM_BOT_TOKEN is correct in .env file")
        print("2. You have internet connection")
        print("3. The token format is correct (should be like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)")


if __name__ == '__main__':
    asyncio.run(get_bot_info())
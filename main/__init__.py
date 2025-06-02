#Github.com/Vasusen-code

from pyrogram import Client

from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from decouple import config
import logging, time, sys

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

# Variables with proper type conversion
API_ID = config("API_ID", "28614709")
API_HASH = config("API_HASH", "f36fd2ee6e3d3a17c4d244ff6dc1bac8")
BOT_TOKEN = config("BOT_TOKEN", "8049166513:AAFmB5M8Qz6uboPYXPiS9PBX3FrQAZbjHA4")
SESSION = config("SESSION", default=None)
FORCESUB = config("FORCESUB", default=None)

# Convert AUTH to integer to avoid phone number error
try:
    AUTH = int(config("AUTH", "7970350353"))
    print(f"✅ AUTH loaded as integer: {AUTH}")
except (ValueError, TypeError) as e:
    print(f"❌ Error converting AUTH to integer: {e}")
    AUTH = 7970350353  # Default fallback
    print(f"Using default AUTH: {AUTH}")

# Initialize bot first (this always works)
try:
    bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
    print("✅ Telethon bot client initialized successfully!")
except Exception as e:
    print(f"❌ Telethon Bot Error: {e}")
    sys.exit(1)

# Handle userbot with SESSION check
userbot = None
if SESSION:
    try:
        userbot = Client("saverestricted", session_string=SESSION, api_hash=API_HASH, api_id=API_ID)
        userbot.start()
        print("✅ Userbot started successfully!")
    except Exception as e:
        print(f"❌ Userbot Error: {e}")
        print("⚠️  Userbot functionality will be disabled. Only public channels will work.")
        userbot = None
else:
    print("⚠️  SESSION not provided. Userbot functionality disabled.")

# Initialize Pyrogram Bot client
try:
    Bot = Client(
        "SaveRestricted",
        bot_token=BOT_TOKEN,
        api_id=int(API_ID),
        api_hash=API_HASH
    )
    Bot.start()
    print("✅ Pyrogram bot client started successfully!")
except Exception as e:
    print(f"❌ Pyrogram Bot Error: {e}")
    sys.exit(1)

# Final status
print("🚀 Bot is ready!")
print(f"📋 Configuration Summary:")
print(f"   - API_ID: {API_ID}")
print(f"   - Bot Token: {BOT_TOKEN[:10]}...")
print(f"   - Owner ID: {AUTH}")
print(f"   - Force Sub: {FORCESUB if FORCESUB else 'Disabled'}")
print(f"   - Userbot: {'Enabled' if userbot else 'Disabled'}")

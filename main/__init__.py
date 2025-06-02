#Github.com/Vasusen-code

from pyrogram import Client

from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from decouple import config
import logging, time, sys

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

# variables
API_ID = config("API_ID", "28614709")
API_HASH = config("API_HASH", "f36fd2ee6e3d3a17c4d244ff6dc1bac8")
BOT_TOKEN = config("BOT_TOKEN", "8049166513:AAFmB5M8Qz6uboPYXPiS9PBX3FrQAZbjHA4")
SESSION = config("SESSION", default=None)
FORCESUB = config("FORCESUB", default=None)
AUTH = config("AUTH", "7970350353")

# Initialize bot first (this always works)
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN) 

# Handle userbot with SESSION check
if SESSION:
    userbot = Client("saverestricted", session_string=SESSION, api_hash=API_HASH, api_id=API_ID) 
    try:
        userbot.start()
        print("✅ Userbot started successfully!")
    except BaseException as e:
        print(f"❌ Userbot Error: {e}")
        print("Have you added SESSION while deploying?")
        sys.exit(1)
else:
    userbot = None

# Initialize Bot client
Bot = Client(
    "SaveRestricted",
    bot_token=BOT_TOKEN,
    api_id=int(API_ID),
    api_hash=API_HASH
)    

try:
    Bot.start()
    print("✅ Bot client started successfully!")
except Exception as e:
    print(f"❌ Bot Error: {e}")
    sys.exit(1)

print("🚀 Bot is ready!")

from decouple import config
import os

# Telegram API Configuration
API_ID = config("API_ID", "28614709")
API_HASH = config("API_HASH", "f36fd2ee6e3d3a17c4d244ff6dc1bac8")
BOT_TOKEN = config("BOT_TOKEN", "8049166513:AAFmB5M8Qz6uboPYXPiS9PBX3FrQAZbjHA4")

# Userbot Session Configuration
SESSION = config("SESSION", default=None)

# Bot Owner Configuration - Convert to integer
try:
    AUTH = int(config("AUTH", "7970350353"))
except (ValueError, TypeError):
    AUTH = 7970350353

# Force Subscribe Configuration
FORCESUB = config("FORCESUB", "-1002669902570")

# File Download Configuration
DOWNLOAD_LOCATION = config("DOWNLOAD_LOCATION", default="/app")

# Progress Bar Configuration
FINISHED_PROGRESS_STR = "█"
UN_FINISHED_PROGRESS_STR = ""

# Batch Processing Configuration
MAX_BATCH_SIZE = 100

# Time Delays (in seconds) to avoid FloodWait
BATCH_DELAY_SMALL = 5   # For first 25 files
BATCH_DELAY_MEDIUM = 10  # For files 26-50
BATCH_DELAY_LARGE = 15   # For files 51-100
BATCH_DELAY_PUBLIC = 2   # For public channels (first 25)
BATCH_DELAY_PUBLIC_LARGE = 3  # For public channels (after 25)

# Bot Messages
FORCE_SUB_MESSAGE = "To use this bot you've to join @{channel}."
START_MESSAGE = "Send me Link of any message to clone it here, For private channel message, send invite link first.\n\n**SUPPORT:** @TeamDrone"
BATCH_ACTIVE_MESSAGE = "You've already started one batch, wait for it to complete you dumbfuck owner!"
BATCH_COMPLETE_MESSAGE = "Batch completed."
PROCESSING_MESSAGE = "Processing!"

# File Extensions and MIME Types
SUPPORTED_VIDEO_FORMATS = ["video/mp4", "video/x-matroska"]

# Error Messages
CHANNEL_JOIN_ERROR = "Have you joined the channel?"
FLOODWAIT_ERROR = "Try again after {seconds} seconds due to floodwait from telegram."
CLONE_ERROR = "An error occurred during cloning of `{link}`\n\n**Error:** {error}"
BATCH_FLOODWAIT_CANCEL = "Cancelling batch since you have floodwait more than 5 minutes."

# Success Messages
JOIN_SUCCESS = "Successfully joined the Channel"
USER_ALREADY_PARTICIPANT = "User is already a participant."
THUMBNAIL_SAVED = "Temporary thumbnail saved!"
THUMBNAIL_REMOVED = "Removed!"

# Validation
def validate_config():
    """Validate essential configuration"""
    required_vars = ['API_ID', 'API_HASH', 'BOT_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not globals()[var] or globals()[var] == "":
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required configuration variables: {', '.join(missing_vars)}")
    
    if not SESSION:
        print("WARNING: SESSION not provided. Userbot functionality will not work.")
    
    # Validate AUTH is integer
    if not isinstance(AUTH, int):
        raise ValueError("AUTH must be an integer user ID")
    
    return True

# Initialize validation
try:
    validate_config()
    print("Configuration loaded successfully!")
    print(f"Bot Owner ID: {AUTH}")
except ValueError as e:
    print(f"Configuration Error: {e}")

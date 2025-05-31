from decouple import config

try:
    APP_ID = config("APP_ID", "28614709")
    API_HASH = config("API_HASH", "f36fd2ee6e3d3a17c4d244ff6dc1bac8")
    BOT_TOKEN = config("BOT_TOKEN", "8191627683:AAErornKfnEpvSlt-l8G0cyexYAR_GOSmeA")
    DEV = 7970350353
    OWNER = config("OWNER", "7970350353")
    FFMPEG = config("FFMPEG", 'ffmpeg -i "{}" -vf "scale=854:480" -preset ultrafast -c:v libx265 -crf 30 -map 0:v -c:a aac -map 0:a -c:s copy -map 0:s? "{}"')
    TELEGRAPH_API = config("TELEGRAPH_API", default="https://api.telegra.ph")
    THUMB = config("THUMBNAIL", default="https://graph.org/file/75ee20ec8d8c8bba84f02.jpg")
except Exception as e:
    print("Environment vars Missing")
    print("something went wrong")
    print(str(e))
    exit()

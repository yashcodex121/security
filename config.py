# config.py
import os

class Config:
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "security_bot")
    LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "")  # @username ya ID
    
    # Bot Owner
    OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
    
    # Anti-Link Settings
    LINK_DELETE = True
    BIO_LINK_DELETE = True
    
    # Sticker Timer (seconds)
    STICKER_DELETE_TIMER = int(os.environ.get("STICKER_DELETE_TIMER", "60"))
    
    # Warning Banner Auto Delete (seconds)
    WARNING_AUTO_DELETE = 30

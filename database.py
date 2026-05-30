# database.py
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.client[Config.DB_NAME]
        
        self.banned = self.db["banned"]
        self.muted = self.db["muted"]
        self.abuse_words = self.db["abuse_words"]
        self.logs = self.db["logs"]
        self.approved_users = self.db["approved_users"]
        self.chat_settings = self.db["chat_settings"]
        self.bot_users = self.db["bot_users"]  # Private log users
    
    async def add_banned(self, chat_id, user_id, username, by_user):
        await self.banned.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"username": username, "banned_by": by_user}},
            upsert=True
        )
    
    async def remove_banned(self, chat_id, user_id):
        await self.banned.delete_one({"chat_id": chat_id, "user_id": user_id})
    
    async def is_banned(self, chat_id, user_id):
        return bool(await self.banned.find_one({"chat_id": chat_id, "user_id": user_id}))
    
    async def add_muted(self, chat_id, user_id, username, muted_by, until=None):
        await self.muted.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"username": username, "muted_by": muted_by, "until": until}},
            upsert=True
        )
    
    async def remove_muted(self, chat_id, user_id):
        await self.muted.delete_one({"chat_id": chat_id, "user_id": user_id})
    
    async def is_muted(self, chat_id, user_id):
        data = await self.muted.find_one({"chat_id": chat_id, "user_id": user_id})
        if data:
            if data.get("until") and datetime.now() > data["until"]:
                await self.remove_muted(chat_id, user_id)
                return False
            return True
        return False
    
    async def get_abuse_words(self, chat_id):
        data = await self.abuse_words.find_one({"chat_id": chat_id})
        return data.get("words", []) if data else []
    
    async def add_abuse_word(self, chat_id, word):
        await self.abuse_words.update_one(
            {"chat_id": chat_id},
            {"$addToSet": {"words": word.lower()}},
            upsert=True
        )
    
    async def remove_abuse_word(self, chat_id, word):
        await self.abuse_words.update_one(
            {"chat_id": chat_id},
            {"$pull": {"words": word.lower()}}
        )
    
    async def add_log(self, chat_id, event_type, data):
        log_entry = {
            "chat_id": chat_id,
            "event_type": event_type,
            "data": data,
            "time": datetime.now()
        }
        await self.logs.insert_one(log_entry)
        
        # Also send to log channel if configured
        if Config.LOG_CHANNEL:
            # Will be handled by bot
            pass
        return log_entry
    
    async def is_approved(self, chat_id, user_id):
        return bool(await self.approved_users.find_one({"chat_id": chat_id, "user_id": user_id}))
    
    async def add_approved(self, chat_id, user_id):
        await self.approved_users.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"user_id": user_id}},
            upsert=True
        )
    
    async def remove_approved(self, chat_id, user_id):
        await self.approved_users.delete_one({"chat_id": chat_id, "user_id": user_id})
    
    async def add_bot_user(self, user_id, username, log_chat_id):
        await self.bot_users.update_one(
            {"user_id": user_id},
            {"$set": {"username": username, "log_chat_id": log_chat_id}},
            upsert=True
        )
    
    async def get_bot_user(self, user_id):
        return await self.bot_users.find_one({"user_id": user_id})

db = Database()

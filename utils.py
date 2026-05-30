# utils.py
import asyncio
from datetime import datetime, timedelta
from telethon import events
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChannelBannedRights, ChatBannedRights
from config import Config
from database import db

# Stylish font converter (Faux bold/italic using Unicode)
STYLISH_MAP = {
    'A': '𝐀', 'B': '𝐁', 'C': '𝐂', 'D': '𝐃', 'E': '𝐄', 'F': '𝐅', 'G': '𝐆',
    'H': '𝐇', 'I': '𝐈', 'J': '𝐉', 'K': '𝐊', 'L': '𝐋', 'M': '𝐌', 'N': '𝐍',
    'O': '𝐎', 'P': '𝐏', 'Q': '𝐐', 'R': '𝐑', 'S': '𝐒', 'T': '𝐓', 'U': '𝐔',
    'V': '𝐕', 'W': '𝐖', 'X': '𝐗', 'Y': '𝐘', 'Z': '𝐙',
    'a': '𝐚', 'b': '𝐛', 'c': '𝐜', 'd': '𝐝', 'e': '𝐞', 'f': '𝐟', 'g': '𝐠',
    'h': '𝐡', 'i': '𝐢', 'j': '𝐣', 'k': '𝐤', 'l': '𝐥', 'm': '𝐦', 'n': '𝐧',
    'o': '𝐨', 'p': '𝐩', 'q': '𝐪', 'r': '𝐫', 's': '𝐬', 't': '𝐭', 'u': '𝐮',
    'v': '𝐯', 'w': '𝐰', 'x': '𝐱', 'y': '𝐲', 'z': '𝐳',
    '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒', '5': '𝟓', '6': '𝟔',
    '7': '𝟕', '8': '𝟖', '9': '𝟗'
}

def to_stylish(text):
    """Convert text to stylish bold Unicode font"""
    result = ""
    for char in text:
        result += STYLISH_MAP.get(char, char)
    return result

def to_stylish_font2(text):
    """Convert to script/monospace style"""
    mono = {
        'A': '𝙰', 'B': '𝙱', 'C': '𝙲', 'D': '𝙳', 'E': '𝙴', 'F': '𝙵', 'G': '𝙶',
        'H': '𝙷', 'I': '𝙸', 'J': '𝙹', 'K': '𝙺', 'L': '𝙻', 'M': '𝙼', 'N': '𝙽',
        'O': '𝙾', 'P': '𝙿', 'Q': '𝚀', 'R': '𝚁', 'S': '𝚂', 'T': '𝚃', 'U': '𝚄',
        'V': '𝚅', 'W': '𝚆', 'X': '𝚇', 'Y': '𝚈', 'Z': '𝚉',
        'a': '𝚊', 'b': '𝚋', 'c': '𝚌', 'd': '𝚍', 'e': '𝚎', 'f': '𝚏', 'g': '𝚐',
        'h': '𝚑', 'i': '𝚒', 'j': '𝚓', 'k': '𝚔', 'l': '𝚕', 'm': '𝚖', 'n': '𝚗',
        'o': '𝚘', 'p': '𝚙', 'q': '𝚚', 'r': '𝚛', 's': '𝚜', 't': '𝚝', 'u': '𝚞',
        'v': '𝚟', 'w': '𝚠', 'x': '𝚡', 'y': '𝚢', 'z': '𝚣'
    }
    result = ""
    for char in text:
        result += mono.get(char, char)
    return result

# URL Patterns
URL_PATTERNS = [
    r'https?://[^\s]+',
    r't\.me/[^\s]+',
    r'@[a-zA-Z0-9_]+',
    r'[a-zA-Z0-9]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'
]

def contains_url(text):
    """Check if text contains any URL patterns"""
    import re
    for pattern in URL_PATTERNS:
        if re.search(pattern, text):
            return True
    return False

def extract_entities(message):
    """Extract URLs from message entities"""
    urls = []
    if message.entities:
        for entity in message.entities:
            if isinstance(entity, (MessageEntityUrl, MessageEntityTextUrl)):
                if isinstance(entity, MessageEntityTextUrl):
                    urls.append(entity.url)
                else:
                    start = entity.offset
                    end = entity.offset + entity.length
                    urls.append(message.text[start:end])
    return urls

async def is_admin(client, chat_id, user_id):
    """Check if user is admin in the chat"""
    try:
        participants = await client.get_permissions(chat_id, user_id)
        return participants.is_admin or participants.is_creator
    except:
        return False

async def can_delete_messages(client, chat_id):
    """Check if bot can delete messages"""
    try:
        me = await client.get_me()
        permissions = await client.get_permissions(chat_id, me.id)
        return permissions.delete_messages
    except:
        return False

async def send_warning(client, chat_id, text):
    """Send a warning banner with stylish font that auto-deletes after 30 sec"""
    styled_text = to_stylish(text)
    msg = await client.send_message(chat_id, styled_text)
    
    async def auto_delete():
        await asyncio.sleep(Config.WARNING_AUTO_DELETE)
        try:
            await msg.delete()
        except:
            pass
    
    asyncio.create_task(auto_delete())
    return msg

async def log_event(client, chat_id, event_type, data):
    """Log event to database and log channel"""
    log_entry = await db.add_log(chat_id, event_type, data)
    
    # Send to log channel if configured
    if Config.LOG_CHANNEL:
        log_text = f"📋 **{event_type}**\n"
        for key, value in data.items():
            log_text += f"• **{key}**: {value}\n"
        
        try:
            entity = await client.get_entity(Config.LOG_CHANNEL)
            await client.send_message(entity, log_text)
        except:
            pass
    
    return log_entry

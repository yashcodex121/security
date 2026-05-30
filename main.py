# main.py
import os
import re
import asyncio
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.tl.types import (
    MessageEntityTextUrl, MessageEntityUrl, 
    ChannelBannedRights, ChatBannedRights, 
    MessageEntityMention, MessageEntityHashtag,
    User, Chat, Channel
)
from telethon.tl.functions.channels import EditBannedRequest
from telethon.errors import UserNotParticipantError

from config import Config
from database import db
from utils import (
    to_stylish, to_stylish_font2, contains_url, extract_entities,
    is_admin, can_delete_messages, send_warning, log_event
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize bot
bot = TelegramClient(
    'security_bot',
    Config.API_ID,
    Config.API_HASH
).start(bot_token=Config.BOT_TOKEN)

# Store pending actions for private bot users
pending_actions = {}

# ==================== START / HELP ====================

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user = await event.get_sender()
    user_id = user.id
    username = user.username or user.first_name or "Unknown"
    
    # Log start event
    await log_event(bot, event.chat_id, "🟢 USER_STARTED", {
        "User": f"{username} (ID: {user_id})",
        "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Premium UI Start Message
    welcome_text = f"""
{to_stylish('⚜️ SECURITY BOT ⚜️')}

{to_stylish_font2('─' * 30)}

{to_stylish('🤖 About This Bot')}
{to_stylish_font2('A powerful security management bot')}
{to_stylish_font2('for your Telegram groups & channels')}
{to_stylish_font2('with advanced protection features.')}

{to_stylish_font2('─' * 30)}

{to_stylish('📊 Statistics')}
{to_stylish_font2(f'• Total Groups Protected: {len(await bot.get_dialogs())}')}
{to_stylish_font2(f'• User: @{username if username else "N/A"}')}

{to_stylish_font2('─' * 30)}

{to_stylish('👇 SELECT OPTION BELOW')}
    """
    
    buttons = [
        [Button.inline(to_stylish("➕ ADD TO GROUP"), data="add_group")],
        [Button.inline(to_stylish("⚙️ MANAGE SETTINGS"), data="manage_settings")],
        [Button.inline(to_stylish("👥 GROUP"), data="group_cmd"), 
         Button.inline(to_stylish("📢 CHANNEL"), data="channel_cmd")],
        [Button.inline(to_stylish("🆘 SUPPORT"), data="support"), 
         Button.inline(to_stylish("ℹ️ INFORMATION"), data="info")],
        [Button.inline(to_stylish("🌐 LANGUAGES"), data="languages")]
    ]
    
    await event.respond(welcome_text, buttons=buttons)
    raise events.StopPropagation

# ==================== CALLBACK HANDLERS ====================

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode()
    user_id = event.sender_id
    
    if data == "add_group":
        text = f"""
{to_stylish('➕ ADD TO GROUP')}

{to_stylish_font2('To add me to your group:')}
{to_stylish_font2('1. Open your group')}
{to_stylish_font2('2. Go to Group Info → Admins')}
{to_stylish_font2('3. Tap "Add Admin" → Search "@YourBotUsername"')}
{to_stylish_font2('4. Give admin permissions')}

{to_stylish_font2('Or simply use this link:')}
{to_stylish_font2('t.me/YourBotUsername?startgroup=true')}
        """
        await event.edit(text)
        
    elif data == "manage_settings":
        text = f"""
{to_stylish('⚙️ MANAGE SETTINGS')}

{to_stylish_font2('Select a category to configure:')}
        """
        buttons = [
            [Button.inline(to_stylish("🚫 Anti-Link"), data="antilink_set"),
             Button.inline(to_stylish("🔞 Anti-Abuse"), data="antiabuse_set")],
            [Button.inline(to_stylish("🎯 Sticker Control"), data="sticker_set"),
             Button.inline(to_stylish("👤 Approved Users"), data="approved_set")],
            [Button.inline(to_stylish("📋 Log Settings"), data="log_set"),
             Button.inline(to_stylish("🔙 BACK"), data="back_start")]
        ]
        await event.edit(text, buttons=buttons)
        
    elif data == "group_cmd":
        text = f"""
{to_stylish('👥 GROUP COMMANDS')}

{to_stylish_font2('Admin Commands (reply or user ID):')}
{to_stylish_font2('• /ban [user] - Ban user')}
{to_stylish_font2('• /unban [user] - Unban user')}
{to_stylish_font2('• /mute [user] - Mute user')}
{to_stylish_font2('• /tmute [user] [min] - Temp mute')}
{to_stylish_font2('• /unmute [user] - Unmute user')}

{to_stylish_font2('Abuse Management:')}
{to_stylish_font2('• /addabuse [word] - Add abuse word')}
{to_stylish_font2('• /delabuse [word] - Remove abuse word')}
{to_stylish_font2('• /abuselist - List abuse words')}

{to_stylish_font2('Sticker Control:')}
{to_stylish_font2('• /sticker [sec] - Set sticker delete timer')}
{to_stylish_font2('• /adduser [user] - Approve user for stickers')}
{to_stylish_font2('• /deluser [user] - Remove approved user')}

{to_stylish_font2('Utility:')}
{to_stylish_font2('• /settings - Show group settings')}
{to_stylish_font2('• /log - Get group activity log')}
        """
        await event.edit(text)
        
    elif data == "channel_cmd":
        text = f"""
{to_stylish('📢 CHANNEL MODE')}

{to_stylish_font2('Add bot as admin to your channel')}
{to_stylish_font2('for automatic link/abuse deletion.')}

{to_stylish_font2('Features in channels:')}
{to_stylish_font2('• Auto-delete links')}
{to_stylish_font2('• Auto-delete abuse')}
{to_stylish_font2('• Bio link detection')}
        """
        await event.edit(text)
        
    elif data == "support":
        text = f"""
{to_stylish('🆘 SUPPORT')}

{to_stylish_font2('Need help? Contact:')}
{to_stylish_font2('• @YourSupportUsername')}
{to_stylish_font2('• Support Group: @YourSupportGroup')}

{to_stylish_font2('Report bugs or request features')}
{to_stylish_font2('to improve the bot!')}
        """
        await event.edit(text)
        
    elif data == "info":
        text = f"""
{to_stylish('ℹ️ INFORMATION')}

{to_stylish_font2('Bot Version: 2.0.0')}
{to_stylish_font2('Framework: Telethon')}
{to_stylish_font2('Database: MongoDB')}

{to_stylish_font2('Features:')}
{to_stylish_font2('✓ Ban/Mute/Temp Mute')}
{to_stylish_font2('✓ Anti-Link Protection')}
{to_stylish_font2('✓ Anti-Abuse System')}
{to_stylish_font2('✓ Bio Link Detection')}
{to_stylish_font2('✓ Sticker Control')}
{to_stylish_font2('✓ Private Log System')}
{to_stylish_font2('✓ Premium UI')}
        """
        await event.edit(text)
        
    elif data == "languages":
        text = f"""
{to_stylish('🌐 LANGUAGES')}

{to_stylish_font2('Currently Supported:')}
{to_stylish_font2('• 🇬🇧 English')}
{to_stylish_font2('• 🇮🇳 Hindi')}

{to_stylish_font2('More languages coming soon!')}
        """
        await event.edit(text)
        
    elif data == "back_start":
        await start_handler(event)
        
    elif data.startswith("antilink_set"):
        await event.edit(f"{to_stylish('🚫 ANTI-LINK')}\n\n{to_stylish_font2('Anti-link is enabled by default.')}")
        
    elif data.startswith("antiabuse_set"):
        await event.edit(f"{to_stylish('🔞 ANTI-ABUSE')}\n\n{to_stylish_font2('Use /addabuse [word] to add words.')}")
        
    elif data.startswith("sticker_set"):
        await event.edit(f"{to_stylish('🎯 STICKER CONTROL')}\n\n{to_stylish_font2('Use /sticker [sec] to set timer. Use /adduser to approve users.')}")
        
    elif data.startswith("approved_set"):
        await event.edit(f"{to_stylish('👤 APPROVED USERS')}\n\n{to_stylish_font2('Use /adduser [user] to approve.')}")
        
    elif data.startswith("log_set"):
        await event.edit(f"{to_stylish('📋 LOG SETTINGS')}\n\n{to_stylish_font2('Configured via LOG_CHANNEL env.')}")

# ==================== BAN COMMAND ====================

@bot.on(events.NewMessage(pattern=r'^/ban(?:\s+(\S+))?'))
async def ban_handler(event):
    if not event.is_group:
        return
    
    sender = await event.get_sender()
    if not await is_admin(bot, event.chat_id, sender.id):
        await send_warning(bot, event.chat_id, f"{to_stylish('⛔ Only admins can use this command!')}")
        return
    
    target_user = None
    target_id = None
    
    if event.message.reply_to_msg_id:
        replied = await event.get_reply_message()
        target_user = replied.sender
        target_id = target_user.id
    elif event.pattern_match.group(1):
        identifier = event.pattern_match.group(1)
        try:
            if identifier.isdigit() or (identifier.startswith('-') and identifier[1:].isdigit()):
                target_id = int(identifier)
            else:
                entity = await bot.get_entity(identifier)
                target_id = entity.id
                target_user = entity
        except:
            await send_warning(bot, event.chat_id, f"{to_stylish('❌ User not found!')}")
            return
    
    if not target_id:
        await send_warning(bot, event.chat_id, f"{to_stylish('❌ Reply to a user or provide user ID!')}")
        return
    
    if target_id == sender.id:
        await send_warning(bot, event.chat_id, f"{to_stylish('❌ You cannot ban yourself!')}")
        return
    
    try:
        # Ban user
        rights = ChannelBannedRights(
            until_date=None,
            view_messages=True,
            send_messages=True,
            send_media=True,
            send_stickers=True,
            send_gifs=True,
            send_games=True,
            send_inline=True,
            embed_links=True
        )
        
        await bot(EditBannedRequest(event.chat_id, target_id, rights))
        
        target_name = target_user.username if target_user and target_user.username else f"User {target_id}"
        sender_name = sender.username or sender.first_name or "Admin"
        
        # Database
        await db.add_banned(event.chat_id, target_id, target_name, sender.id)
        
        # Log
        await log_event(bot, event.chat_id, "🚫 BANNED", {
            "User": target_name,
            "ID": target_id,
            "Banned By": sender_name,
            "Group": event.chat.title
        })
        
        # Send warning banner
        await send_warning(bot, event.chat_id, 
            f"{to_stylish('🚫 USER BANNED')}\n{to_stylish_font2(f'• User: {target_name}')}\n{to_stylish_font2(f'• By: {sender_name}')}")
        
        await event.delete()
        
    except Exception as e:
        await send_warning(bot, event.chat_id, f"{to_stylish('❌ Error banning user')}\n{to_stylish_font2(str(e))}")

# ==================== UNBAN ====================

@bot.on(events.NewMessage(pattern=r'^/unban(?:\s+(\S+))?'))
async def unban_handler(event):
    if not event.is_group:
        return
    
    sender = await event.get_sender()
    if not await is_admin(bot, event.chat_id, sender.id):
        await send_warning(bot, event.chat_id, f"{to_stylish('⛔ Only admins can use this command!')}")
        return
    
    target_id = None
    
    if event.message.reply_to_msg_id:
        replied = await event.get_reply_message()
        target_id = replied.sender.id
    elif event.pattern_match.group(1):
        identifier = event.pattern_match.group(1)
        try:
            target_id = int(identifier) if identifier.isdigit() else (await bot.get_entity(identifier)).id
        except:
            await send_warning(bot, event.chat_id, f"{to_stylish('❌ User not found!')}")
            return
    
    if not target_id:
        return
    
    try:
        # Unban - restore all permissions
        rights = ChannelBannedRights(
            until_date=None,
            view_messages=False,
            send_messages=False,
            send_media=False,
            send_stickers=False,
            send_gifs=False,
            send_games=False,
            send_inline=False,
            embed_links=False
        )
        
        await bot(EditBannedRequest(event.chat_id, target_id, rights))
        await db.remove_banned(event.chat_id, target_id)
        
        await send_warning(bot, event.chat_id, 
            f"{to_stylish('✅ USER UNBANNED')}\n{to_stylish_font2(f'ID: {target_id}')}")
        
        await event.delete()
        
    except Exception as e:
        await send_warning(bot, event.chat_id, f"{to_stylish('❌ Error')}\n{to_stylish_font2(str(e))}")

# ==================== MUTE / TMUTE ====================

@bot.on(events.NewMessage(pattern=r'^/mute(?:\s+(\S+))?'))
async def mute_handler(event):
    if not event.is_group:
        return
    
    sender = await event.get_sender()
    if not await is_admin(bot, event.chat_id, sender.id):
        await send_warning(bot, event.chat_id, f"{to_stylish('⛔ Only admins can use this command!')}")
        return
    
    target_user = None
    target_id = None
    
    if event.message.reply_to_msg_id:
        replied = await event.get_reply_message()
        target_user = replied.sender
        target_id = target_user.id
    elif event.pattern_match.group(1):
        identifier = event.pattern_match.group(1)
        try:
            if identifier.isdigit() or (identifier.startswith('-') and identifier[1:].isdigit()):
                target_id = int(identifier)
            else:
                entity = await bot.get_entity(identifier)
                target_id = entity.id
                target_user = entity
        except:
            await send_warning(bot, event.chat_id, f"{to_stylish('❌ User not found!')}")
            return
    
    if not target_id or target_id == sender.id:
        return
    
    try:
        sender_name = sender.username or sender.first_name or "Admin"
        target_name = target_user.username if target_user and target_user.username else f"User {target_id}"
        
        # Mute - restrict sending messages
        rights = ChannelBannedRights(
            until_date=datetime.now() + timedelta(days=365),
            view_messages=False,
            send_messages=True,
            send_media=True,
            send_stickers=True,
            send_gifs=True,
            send_games=True,
            send_inline=True,
            embed_links=True
        )
        
        await bot(EditBannedRequest(event.chat_id, target_id, rights))
        await db.add_muted(event.chat_id, target_id, target_name, sender.id)
        
        await log_event(bot, event.chat_id, "🔇 MUTED", {
            "User": target_name,
            "ID": target_id,
            "Muted By": sender_name,
            "Duration": "Permanent"
        })
        
        await send_warning(bot, event.chat_id,
            f"{to_stylish('🔇 USER MUTED')}\n{to_stylish_font2(f'• User: {target_name}')}\n{to_stylish_font2(f'• By: {sender_name}')}")
        
        await event.delete()
        
    except Exception as e:
        await send_warning(bot, event.chat_id, f"{to_stylish('❌ Error')}\n{to_stylish_font2(str(e))}")

# ==================== TEMP MUTE ====================

@bot.on(events.NewMessage(pattern=r'^/tmute(?:\s+(\S+))?(?:\s+(\d+))?'))
async def tmute_handler(event):
    if not event.is_group:
        return
    
    sender = await event.get_sender()
    if not await is_admin(bot, event.chat_id, sender.id):
        await send_warning(bot, event.chat_id, f"{to_stylish('⛔ Only admins can use this command!')}")
        return
    
    target_user = None
    target_id = None
    minutes = 5  # default
    
    if event.message.reply_to_msg_id:
        replied = await event.get_reply_message()
        target_user = replied.sender
        target_id = target_user.id
        if event.pattern_match.group(2):
            minutes = int(event.pattern_match.group(2))
    elif event.pattern_match.group(1):
        identifier = event.pattern_match.group(1)
        # Check if second arg is minutes
        if event.pattern_match.group(2):
            minutes = int(event.pattern_match.group(2))
        try:
            if identifier.isdigit():
                target_id = int(identifier)
            else:
                entity = await bot.get_entity(identifier)
                target_id = entity.id
                target_user = entity
        except:
            pass
    
    if not target_id or target_id == sender.id:
        return
    
    # Parse minutes from message text for more complex patterns
    parts = event.message.text.split()
    if len(parts) >= 3 and parts[2].isdigit():
        minutes = int(parts[2])
    
    try:
        sender_name = sender.username or sender.first_name or "Admin"
        target_name = target_user.username if target_user and target_user.username else f"User {target_id}"
        
        until = datetime.now() + timedelta(minutes=minutes)
        
        rights = ChannelBannedRights(
            until_date=until,
            view_messages=False,
            send_messages=True,
            send_media=True,
            send_stickers=True,
            send_gifs=True,
            send_games=True,
            send_inline=True,
            embed_links=True
        )
        
        await bot(EditBannedRequest(event.chat_id, target_id, rights))
        await db.add_muted(event.chat_id, target_id, target_name, sender.id, until)
        
        await log_event(bot, event.chat_id, "🔇 TEMP MUTED", {
            "User": target_name,
            "ID": target_id,
            "Muted By": sender_name,
            "Duration": f"{minutes} minutes"
        })
        
        await send_warning(bot, event.chat_id,
            f"{to_stylish('🔇 USER TEMP MUTED')}\n{to_stylish_font2(f'• User: {target_name}')}\n{to_stylish_font2(f'• Duration: {minutes} min')}")
        
        await event.delete()
        
    except Exception as e:
        await send_warning(bot, event.chat_id, f"{to_stylish('❌ Error')}\n{to_stylish_font2(str(e))}")

# ==================== UNMUTE ====================

@bot.on(events.NewMessage(pattern=r'^/unmute(?:\s+(\S+))?'))
async def unmute_handler(event):
    if not event.is_group:
        return
    
    sender = await event.get_sender()
    if not await is_admin(bot, event.chat_id, sender.id):
        return
    
    target_id = None
    if event.message.reply_to_msg_id:
        replied = await event.get_reply_message()
        target_id = replied.sender.id
    elif event.pattern_match.group(1):
        identifier = event.pattern_match.group(1)
        try:
            target_id = int(identifier) if identifier.isdigit() else (await bot.get_entity(identifier)).id
        except:
            return
    
    if not target_id:
        return
    
    try:
        rights = ChannelBannedRights(
            until_date=None,
            view_messages=False,
            send_messages=False,
            send_media=False,
            send_stickers=False,
            send_gifs=False,
            send_games=False,
            send_inline=False,
            embed_links=False
        )
        
        await bot(EditBannedRequest(event.chat_id, target_id, rights))
        await db.remove_muted(event.chat_id, target_id)
        
        await send_warning(bot, event.chat_id,
            f"{to_stylish('✅ USER UNMUTED')}\n{to_stylish_font2(f'ID: {target_id}')}")
        
        await event.delete()
        
    except Exception as e:
        pass

# ==================== ANTI-LINK ====================

@bot.on(events.NewMessage)
async def anti_link_handler(event):
    if not event.is_group or not event.message.text:
        return
    
    # Skip commands
    if event.message.text.startswith('/'):
        return
    
    # Check if user is admin
    sender = await event.get_sender()
    if await is_admin(bot, event.chat_id, sender.id):
        return
    
    message_text = event.message.text
    
    # Check for URLs in text
    if contains_url(message_text):
        if not await can_delete_messages(bot, event.chat_id):
            return
        
        await event.delete()
        
        sender_name = sender.username or sender.first_name or "Unknown"
        await log_event(bot, event.chat_id, "🔗 LINK DELETED", {
            "User": sender_name,
            "ID": sender.id,
            "Message": message_text[:100]
        })
        
        await send_warning(bot, event.chat_id,
            f"{to_stylish('🔗 LINK DETECTED')}\n{to_stylish_font2(f'• User: {sender_name}')}\n{to_stylish_font2('• Message deleted automatically')}")

# ==================== BIO LINK DETECTION ====================

@bot.on(events.ChatAction)
async def bio_link_handler(event):
    if not event.is_group:
        return
    
    if event.user_joined or event.user_added:
        user = await event.get_user()
        if user:
            try:
                full_user = await bot.get_entity(user.id)
                if full_user.about and contains_url(full_user.about):
                    sender = await event.get_sender()
                    if sender and not await is_admin(bot, event.chat_id, sender.id):
                        # Kick user for having link in bio
                        try:
                            rights = ChannelBannedRights(
                                until_date=None,
                                view_messages=True,
                                send_messages=True,
                                send_media=True,
                                send_stickers=True,
                                send_gifs=True,
                                send_games=True,
                                send_inline=True,
                                embed_links=True
                            )
                            await bot(EditBannedRequest(event.chat_id, user.id, rights))
                            
                            await log_event(bot, event.chat_id, "🚫 BIO LINK BAN", {
                                "User": user.username or f"User {user.id}",
                                "ID": user.id,
                                "Bio": full_user.about[:100]
                            })
                            
                            await send_warning(bot, event.chat_id,
                                f"{to_stylish('🚫 BIO LINK DETECTED')}\n{to_stylish_font2(f'• User removed for having link in bio')}")
                        except:
                            pass
            except:
                pass

# ==================== ANTI-ABUSE ====================

@bot.on(events.NewMessage)
async def anti_abuse_handler(event):
    if not event.is_group or not event.message.text:
        return
    
    if event.message.text.startswith('/'):
        return
    
    sender = await event.get_sender()
    if await is_admin(bot, event.chat_id, sender.id):
        return
    
    # Get abuse words for this chat
    abuse_words = await db.get_abuse_words(event.chat_id)
    if not abuse_words:
        return
    
    message_lower = event.message.text.lower()
    
    for word in abuse_words:
        if word in message_lower:
            if not await can_delete_messages(bot, event.chat_id):
                return
            
            await event.delete()
            
            sender_name = sender.username or sender.first_name or "Unknown"
            await log_event(bot, event.chat_id, "🔞 ABUSE DELETED", {
                "User": sender_name,
                "ID": sender.id,
                "Word": word,
                "Message": event.message.text[:100]
            })
            
            await send_warning(bot, event.chat_id,
                f"{to_stylish('🔞 ABUSE DETECTED')}\n{to_stylish_font2(f'• User: {sender_name}')}\n{to_stylish_font2(f'• Word: {word}')}")
            break

# ==================== ADD/DELETE ABUSE WORDS ====================

@bot.on(events.NewMessage(pattern=r'^/addabuse\s+(.+)'))
async def add_abuse_handler(event):
    if not event.is_group:
        return
    
    sender = await event.get_sender()
    if not await is_admin(bot, event.chat_id, sender.id):
        return
    
    word = event.pattern_match.group(1).strip().lower()
    await db.add_abuse_word(event.chat_id, word)
    
    await event.delete()
    await send_warning(bot, event.chat_id,
        f"{to_stylish('✅ ABUSE WORD ADDED')}\n{to_stylish_font2(f'• Word: {word}')}")

@bot.on(events.NewMessage(pattern=r'^/delabuse\s+(.+)'))
async def del_abuse_handler(event):
    if not event.is_group:
        return
    
    sender = await event.get_sender()
    if not await is_admin(bot, event.chat_id, sender.id):
        return
    
    word = event.pattern_match.group(1).strip().lower()
    await db.remove_abuse_word(event.chat_id, word)
    
    await event.delete()
    await send_warning(bot, event.chat_id,
        f"{to_stylish('✅ ABUSE WORD REMOVED')}\n{to_stylish_font2(f'• Word: {word}')}")

@bot.on(events.NewMessage(pattern=r'^/abuselist'))
async def abuse_list_handler(event):
    if not event.is_group:
        return
    
    sender = await event.get_sender()
    if not await is_admin(bot, event.chat_id, sender.id):
        return
    
    words = await db.get_abuse_words(event.chat_id)
    if not words:
        await send_warning(bot, event.chat_id, f"{to_stylish('No abuse words configured.')}")
        return
    
    word_list = "\n".join([f"{to_stylish_font2(f'{i+1}. {w}')}" for i, w in enumerate(words)])
    await send_warning(bot, event.chat_id,
        f"{to_stylish('📋 ABUSE WORD LIST')}\n{word_list}")

# ==================== STICKER CONTROL ====================

@bot.on(events.NewMessage)
async def sticker_handler(event):
    if not event.is_group:
        return
    
    if event.message.sticker:
        sender = await event.get_sender()
        
        # Check if user is approved for stickers
        if await db.is_approved(event.chat_id, sender.id):
            return
        
        if await is_admin(bot, event.chat_id, sender.id):
            return
        
        if not await can_delete_messages(bot, event.chat_id):
            return
        
        # Get chat settings for sticker timer
        settings = await db.chat_settings.find_one({"chat_id": event.chat_id})
        timer = settings.get("sticker_timer", Config.STICKER_DELETE_TIMER) if settings else Config.STICKER_DELETE_TIMER
        
        if timer > 0:
            await asyncio.sleep(timer)
            try:
                await event.delete()
                
                sender_name = sender.username or sender.first_name or "Unknown"
                await log_event(bot, event.chat_id, "🎯 STICKER DELETED", {
                    "User": sender_name,
                    "ID": sender.id
                })
            except:
                pass

@bot.on(events.NewMessage(pattern=r'^/sticker\s+(\d+)'))
async def sticker_set_handler(event):
    if not event.is_group:
        return
    
    sender = await event.get_sender()
    if not await is_admin(bot, event.chat_id, sender.id):
        return
    
    timer = int(event.pattern_match.group(1))
    await db.chat_settings.update_one(
        {"chat_id": event.chat_id},
        {"$set": {"sticker_timer": timer}},
        upsert=True
    )
    
    await event.delete()
    await send_warning(bot, event.chat_id,
        f"{to_stylish('✅ STICKER TIMER SET')}\n{to_stylish_font2(f'• Timer: {timer} seconds')}")

# ==================== APPROVED USERS ====================

@bot.on(events.NewMessage(pattern=r'^/adduser(?:\s+(\S+))?'))
async def add_user_handler(event):
    if not event.is_group:
        return
    
    sender = await event.get_sender()
    if not await is_admin(bot, event.chat_id, sender.id):
        return
    
    target_id = None
    if event.message.reply_to_msg_id:
        replied = await event.get_reply_message()
        target_id = replied.sender.id
    elif event.pattern_match.group(1):
        identifier = event.pattern_match.group(1)
        try:
            target_id = int(identifier) if identifier.isdigit() else (await bot.get_entity(identifier)).id
        except:
            await send_warning(bot, event.chat_id, f"{to_stylish('❌ User not found!')}")
            return
    
    if not target_id:
        return
    
    await db.add_approved(event.chat_id, target_id)
    await send_warning(bot, event.chat_id,
        f"{to_stylish('✅ USER APPROVED')}\n{to_stylish_font2(f'• ID: {target_id}')}")

@bot.on(events.NewMessage(pattern=r'^/deluser(?:\s+(\S+))?'))
async def del_user_handler(event):
    if not event.is_group:
        return
    
    sender = await event.get_sender()
    if not await is_admin(bot, event.chat_id, sender.id):
        return
    
    target_id = None
    if event.message.reply_to_msg_id:
        replied = await event.get_reply_message()
        target_id = replied.sender.id
    elif event.pattern_match.group(1):
        identifier = event.pattern_match.group(1)
        try:
            target_id = int(identifier) if identifier.isdigit() else (await bot.get_entity(identifier)).id
        except:
            return
    
    if not target_id:
        return
    
    await db.remove_approved(event.chat_id, target_id)
    await send_warning(bot, event.chat_id,
        f"{to_stylish('✅ USER REMOVED FROM APPROVED')}\n{to_stylish_font2(f'• ID: {target_id}')}")

# ==================== SETTINGS ====================

@bot.on(events.NewMessage(pattern=r'^/settings'))
async def settings_handler(event):
    if not event.is_group:
        return
    
    sender = await event.get_sender()
    if not await is_admin(bot, event.chat_id, sender.id):
        return
    
    chat_title = event.chat.title or "Group"
    abuse_words = await db.get_abuse_words(event.chat_id)
    
    settings_text = f"""
{to_stylish('⚙️ GROUP SETTINGS')}
{to_stylish_font2('─' * 30)}

{to_stylish_font2(f'📌 Group: {chat_title}')}
{to_stylish_font2(f'🔗 Anti-Link: ✅ Enabled')}
{to_stylish_font2(f'🔞 Abuse Words: {len(abuse_words)}')}
{to_stylish_font2(f'🎯 Sticker Control: ✅ Active')}

{to_stylish_font2('─' * 30)}
{to_stylish('📋 Type /log for activity log')}
    """
    
    await event.reply(settings_text)

# ==================== PRIVATE LOG SYSTEM ====================

@bot.on(events.NewMessage(pattern=r'^/log$'))
async def log_handler(event):
    """Bot user ke private log ke liye"""
    user_id = event.sender_id
    
    if event.is_group:
        # Group log
        sender = await event.get_sender()
        if not await is_admin(bot, event.chat_id, sender.id):
            return
        
        # Get recent logs for this group
        logs_cursor = db.logs.find({"chat_id": event.chat_id}).sort("time", -1).limit(10)
        logs = []
        async for log in logs_cursor:
            logs.append(log)
        
        if not logs:
            await send_warning(bot, event.chat_id, f"{to_stylish('📋 No logs found.')}")
            return
        
        log_text = f"{to_stylish('📋 RECENT LOGS')}\n"
        for log in logs[:5]:  # Show last 5
            log_text += f"\n{to_stylish_font2(f'• {log["event_type"]}: {log["data"].get("User", "N/A")}')}"
        
        await event.reply(log_text)
    
    else:
        # Private chat - user wants to set up their own log
        bot_user = await db.get_bot_user(user_id)
        if bot_user:
            log_text = f"""
{to_stylish('📋 YOUR PRIVATE LOG')}

{to_stylish_font2('Your log chat is configured.')}
{to_stylish_font2(f'Log Chat ID: {bot_user["log_chat_id"]}')}

{to_stylish_font2('Use /setlog [chat_id] to change')}
{to_stylish_font2('or /removelog to remove.')}
            """
            await event.reply(log_text)
        else:
            await event.reply(
                f"{to_stylish('📋 PRIVATE LOG SETUP')}\n\n"
                f"{to_stylish_font2('Send /setlog [chat_id] to set up')}\n"
                f"{to_stylish_font2('your private log channel.')}\n\n"
                f"{to_stylish_font2('The log will show:')}\n"
                f"{to_stylish_font2('• Which link was used')}\n"
                f"{to_stylish_font2('• Who gave the command')}\n"
                f"{to_stylish_font2('• What action was taken')}"
            )

@bot.on(events.NewMessage(pattern=r'^/setlog\s+(-?\d+)'))
async def setlog_handler(event):
    """Bot user apna private log set kare"""
    if event.is_group:
        return
    
    user_id = event.sender_id
    log_chat_id = int(event.pattern_match.group(1))
    sender = await event.get_sender()
    username = sender.username or sender.first_name or "Unknown"
    
    await db.add_bot_user(user_id, username, log_chat_id)
    
    await event.reply(
        f"{to_stylish('✅ PRIVATE LOG SET')}\n\n"
        f"{to_stylish_font2(f'Log Chat ID: {log_chat_id}')}\n"
        f"{to_stylish_font2('All actions will be logged there.')}"
    )

@bot.on(events.NewMessage(pattern=r'^/removelog'))
async def removelog_handler(event):
    if event.is_group:
        return
    
    user_id = event.sender_id
    await db.bot_users.delete_one({"user_id": user_id})
    
    await event.reply(f"{to_stylish('✅ Private log removed.')}")

# ==================== JOIN/LEAVE/BOT ADDED LOGGING ====================

@bot.on(events.ChatAction)
async def chat_action_logger(event):
    if not event.is_group:
        return
    
    chat_title = event.chat.title or "Unknown Group"
    
    # User joined
    if event.user_joined:
        user = await event.get_user()
        if user:
            username = user.username or user.first_name or "Unknown"
            await log_event(bot, event.chat_id, "🟢 USER JOINED", {
                "User": username,
                "ID": user.id,
                "Group": chat_title
            })
    
    # User left
    if event.user_left:
        user = await event.get_user()
        if user:
            username = user.username or user.first_name or "Unknown"
            await log_event(bot, event.chat_id, "🔴 USER LEFT", {
                "User": username,
                "ID": user.id,
                "Group": chat_title
            })
    
    # Bot was added
    if event.user_added:
        user = await event.get_user()
        if user and user.id == (await bot.get_me()).id:
            # Bot was added to a group
            adder = await event.get_sender()
            adder_name = adder.username or adder.first_name or "Unknown"
            
            await log_event(bot, event.chat_id, "🤖 BOT ADDED", {
                "Group": chat_title,
                "Group ID": event.chat_id,
                "Added By": adder_name
            })
            
            # Send welcome message in the group
            welcome = f"""
{to_stylish('🎉 THANKS FOR ADDING ME!')}

{to_stylish_font2('I am your Security Bot.')}
{to_stylish_font2('Promote me to admin for full features.')}

{to_stylish_font2('Commands: /settings')}
{to_stylish_font2('Help: /start')}
            """
            await event.reply(welcome)
        
        elif user:
            # Another user was added
            adder = await event.get_sender()
            adder_name = adder.username or adder.first_name or "Unknown"
            username = user.username or user.first_name or "Unknown"
            
            await log_event(bot, event.chat_id, "➕ USER ADDED", {
                "User": username,
                "ID": user.id,
                "Added By": adder_name,
                "Group": chat_title
            })
    
    # Bot removed
    if event.user_kicked:
        user = await event.get_user()
        if user and user.id == (await bot.get_me()).id:
            await log_event(bot, event.chat_id, "🚫 BOT REMOVED", {
                "Group": chat_title,
                "Group ID": event.chat_id
            })

# ==================== PRIVATE BOT USER LOGS ====================

@bot.on(events.NewMessage)
async def private_log_for_users(event):
    """Jab bhi koi admin action use kare to bot users ke private log me bheje"""
    if not event.is_group or not event.message.text:
        return
    
    # Only track commands
    if not event.message.text.startswith('/'):
        return
    
    sender = await event.get_sender()
    
    # Check if sender has a private log configured
    bot_user = await db.get_bot_user(sender.id)
    if not bot_user:
        return
    
    log_chat_id = bot_user.get("log_chat_id")
    if not log_chat_id:
        return
    
    # Send command usage to their private log
    try:
        command_text = event.message.text.split('\n')[0][:100]
        log_msg = f"""
{to_stylish('📋 COMMAND LOG')}
{to_stylish_font2('─' * 20)}
{to_stylish_font2(f'• Group: {event.chat.title}')}
{to_stylish_font2(f'• User: @{sender.username or "N/A"}')}
{to_stylish_font2(f'• ID: {sender.id}')}
{to_stylish_font2(f'• Command: {command_text}')}
{to_stylish_font2(f'• Time: {datetime.now().strftime("%H:%M:%S")}')}
        """
        await bot.send_message(log_chat_id, log_msg)
    except:
        pass

# ==================== MAIN ====================

async def main():
    me = await bot.get_me()
    logger.info(f"Bot started: @{me.username}")
    
    # Start checking for expired mutes periodically
    async def check_expired_mutes():
        while True:
            await asyncio.sleep(60)
            # This is handled inline in is_muted() check
    
    asyncio.create_task(check_expired_mutes())
    
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        bot.loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        bot.disconnect()

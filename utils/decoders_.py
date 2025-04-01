from functools import wraps
from utils.log import logger
from assets.assets import load_asset
from config import ERROR429, LOGGER_CHATID, OWNER_ID
from utils.dataBase.FireDB import DB
from Modules.inline import ADMIN_ERROR, RATE_LIMITION
from utils.rate_limit import RateLimiter
from cachetools import TTLCache
from typing import Callable, Any, Optional
import asyncio

# Constants
LIST_OF_BAN_IDS = DB.blocked_users_cache
ADMIN_ID_LIST = DB.admins_users

# Cache settings
SPAM_CACHE_TTL = 60  # seconds
SPAM_CACHE_SIZE = 128

# Rate limiting
ratelimit = RateLimiter()
warned_users = TTLCache(maxsize=SPAM_CACHE_SIZE, ttl=SPAM_CACHE_TTL)
reported_users = set()
WARNING_MESSAGE = "Spam detected! Ignoring your requests for a few minutes."

def _get_user_id(update) -> str:
    """Extract user ID from update object as string."""
    return str(update.effective_user.id)

async def _report_spammer(context, update, user_id: str) -> None:
    """Report a spamming user to the log channel."""
    message = (
        f"First Name: {update.effective_user.first_name}, "
        f"User ID: <code>{user_id}</code>\n\n"
        f"Has been caught spamming even after warning message was sent."
    )
    await context.bot.send_message(
        chat_id=LOGGER_CHATID, 
        text=message, 
        parse_mode="HTML"
    )

def rate_limit(func: Callable) -> Callable:
    """
    Restricts users from spamming commands or pressing buttons multiple times
    using leaky bucket algorithm and pyrate_limiter.
    """
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user_id = _get_user_id(update)
        is_limited = await ratelimit.acquire(user_id)
        
        if is_limited:
            if user_id not in warned_users:
                # First time warning
                try:
                    await update.message.reply_photo(
                        photo=load_asset(ERROR429),
                        caption=WARNING_MESSAGE,
                        reply_markup=RATE_LIMITION
                    )
                    warned_users[user_id] = 1
                except Exception as e:
                    logger.error(f"Failed to send rate limit warning: {e}")
                return
            elif user_id not in reported_users:
                # Report user if they continue after warning
                await _report_spammer(context, update, user_id)
                reported_users.add(user_id)
                return
            # If already reported, silently ignore
            return
        
        # Clear user from reported set if they're behaving now
        reported_users.discard(user_id)
        
        # Execute the wrapped function
        return await func(update, context, *args, **kwargs)

    return wrapper

def restricted(func: Callable) -> Callable:
    """Restrict access to non-banned users only."""
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = _get_user_id(update)
        
        if user_id in LIST_OF_BAN_IDS:
            logger.info(f"Blocked user access denied: {user_id}")
            return None
            
        return await func(update, context, *args, **kwargs)
    
    return wrapped

def IsAdmin(func: Callable) -> Callable:
    """Allow access to admin users only."""
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = _get_user_id(update)
        
        if user_id in ADMIN_ID_LIST or user_id == str(OWNER_ID):
            return await func(update, context, *args, **kwargs)
        
        logger.info(f"Admin access denied for user: {user_id}")
        
        try:
            await update.message.reply_text(
                "Aᴄᴄᴇss ᴅᴇɴɪᴇᴅ. Oɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴅᴏ ᴛʜɪs.", 
                reply_markup=ADMIN_ERROR
            )
        except Exception as e:
            logger.error(f"Failed to send admin denial message: {e}")
            
        return None
    
    return wrapped

def IsOwner(func: Callable) -> Callable:
    """Allow access to owner only."""
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = _get_user_id(update)
        
        if user_id == str(OWNER_ID):
            return await func(update, context, *args, **kwargs)
        
        logger.info(f"Owner access denied for user: {user_id}")
        
        try:
            await update.message.reply_text(
                "Aᴄᴄᴇss ᴅᴇɴɪᴇᴅ. Oɴʟʏ Owner ᴄᴀɴ ᴅᴏ ᴛʜɪs."
            )
        except Exception as e:
            logger.error(f"Failed to send owner denial message: {e}")
            
        return None
    
    return wrapped
from functools import wraps
from utils.log import logger
from assets.assets import load_asset
from config import ERROR429, LOGGER_CHATID, OWNER_ID
from utils.dataBase.FireDB import DB
from Modules.inline import ADMIN_ERROR

from Modules.inline import RATE_LIMITION
from utils.rate_limit import RateLimiter
from cachetools import TTLCache
import asyncio
from datetime import datetime

LIST_OF_BAN_IDS = DB.blocked_users_cache
ADMIN_ID_LIST = DB.admins_users

# Improved rate limiter with more efficient bucket algorithm
ratelimit = RateLimiter()

# Storing spammy users in cache for 1 minute before allowing them to use commands again
warned_users = TTLCache(maxsize=256, ttl=60)
warning_message = "Spam detected! Ignoring your requests for a few minutes."

# Cache for users who have been reported to avoid repeated reports
reported_users = TTLCache(maxsize=128, ttl=300)  # 5 minutes cache for reported users

# Add a cooldown period for certain commands
command_cooldowns = TTLCache(maxsize=512, ttl=5)  # 5 seconds cooldown


def rate_limit(func):
    """
    Restricts users from spamming commands or pressing buttons multiple times
    using leaky bucket algorithm and pyrate_limiter with enhanced error handling
    and spam prevention.
    """
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        try:
            userid = update.effective_user.id
            command = update.message.text.split()[0] if update.message and update.message.text else "unknown"
            
            # Create a unique key for this user+command combination
            cooldown_key = f"{userid}:{command}"
            
            # Check if this user+command is in cooldown
            if cooldown_key in command_cooldowns:
                return
            
            # Check rate limit
            is_limited = await ratelimit.acquire(userid)
            
            if is_limited:
                if userid not in warned_users:
                    try:
                        # Send warning only once
                        await update.message.reply_photo(
                            photo=load_asset(ERROR429),
                            caption=warning_message,
                            reply_markup=RATE_LIMITION
                        )
                        warned_users[userid] = datetime.now()
                        
                        # Log the rate limit event
                        logger.warning(f"Rate limit applied for user {userid} ({update.effective_user.first_name})")
                    except Exception as e:
                        logger.error(f"Error sending rate limit message: {str(e)}")
                    return
                
                elif userid not in reported_users:
                    # Report user only once
                    message = (
                        f"⚠️ <b>Spam Alert</b> ⚠️\n\n"
                        f"First Name: {update.effective_user.first_name}\n"
                        f"Username: @{update.effective_user.username if update.effective_user.username else 'None'}\n"
                        f"User ID: <code>{userid}</code>\n\n"
                        f"Has been caught spamming even after warning."
                    )
                    try:
                        await context.bot.send_message(
                            chat_id=LOGGER_CHATID, text=message, parse_mode="HTML"
                        )
                        reported_users[userid] = True
                    except Exception as e:
                        logger.error(f"Error reporting spam user: {str(e)}")
                    return
                return  # Silently ignore further requests
            
            # User is not rate limited, add to command cooldown and execute function
            command_cooldowns[cooldown_key] = True
            return await func(update, context, *args, **kwargs)
        
        except Exception as e:
            logger.error(f"Error in rate_limit decorator: {str(e)}")
            try:
                await update.message.reply_text("An error occurred. Please try again later.")
            except:
                pass
            
    wrapper.__name__ = func.__name__
    return wrapper


def restricted (func):
    """
    Restricts access to commands for banned users with improved error handling.
    """
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        try:
            user_id = str(update.effective_user.id)
            
            # Check if user is banned
            if user_id in LIST_OF_BAN_IDS:
                logger.info(f"Blocked user {user_id} attempted to use {func.__name__}")
                return
            
            # Execute the function for non-banned users
            return await func(update, context, *args, **kwargs)
        
        except Exception as e:
            logger.error(f"Error in restricted decorator: {str(e)}")
            
    return wrapped


def IsAdmin(func):
    """
    Restricts access to admin-only commands with improved error handling
    and user feedback.
    """
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        try:
            user_id = str(update.effective_user.id)
            
            # Check if user is admin or owner
            if user_id in ADMIN_ID_LIST or user_id == str(OWNER_ID):
                return await func(update, context, *args, **kwargs)
            
            # Handle non-admin users
            logger.info(f"Non-admin user {user_id} attempted to use admin command {func.__name__}")
            
            try:
                await update.message.reply_text(
                    "Aᴄᴄᴇss ᴅᴇɴɪᴇᴅ. Oɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴅᴏ ᴛʜɪs.", 
                    reply_markup=ADMIN_ERROR
                )
            except Exception as reply_error:
                logger.error(f"Could not send admin denial message: {str(reply_error)}")
                
        except Exception as e:
            logger.error(f"Error in IsAdmin decorator: {str(e)}")
            
    return wrapped


def IsOwner(func):
    """
    Restricts access to owner-only commands with improved error handling
    and user feedback.
    """
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        try:
            user_id = str(update.effective_user.id)
            
            # Check if user is the owner
            if user_id == str(OWNER_ID):
                return await func(update, context, *args, **kwargs)
            
            # Handle non-owner users
            logger.info(f"Non-owner user {user_id} attempted to use owner command {func.__name__}")
            
            try:
                await update.message.reply_text("Aᴄᴄᴇss ᴅᴇɴɪᴇᴅ. Oɴʟʏ Owner ᴄᴀɴ ᴅᴏ ᴛʜɪs.")
            except Exception as reply_error:
                logger.error(f"Could not send owner denial message: {str(reply_error)}")
                
        except Exception as e:
            logger.error(f"Error in IsOwner decorator: {str(e)}")
            
    return wrapped


# Additional utility decorator for message throttling
def throttle(seconds=3):
    """
    Throttles how often a user can use a specific command.
    Different from rate_limit as it's per-command based.
    
    Args:
        seconds: The cooldown period in seconds
    """
    def decorator(func):
        # Store last usage timestamps
        last_used = TTLCache(maxsize=1024, ttl=seconds*2)
        
        @wraps(func)
        async def wrapped(update, context, *args, **kwargs):
            try:
                user_id = update.effective_user.id
                current_time = datetime.now().timestamp()
                
                # Check if user is in cooldown for this command
                if user_id in last_used:
                    time_diff = current_time - last_used[user_id]
                    if time_diff < seconds:
                        # Optional: silently ignore or inform about cooldown
                        return
                
                # Update the last usage time
                last_used[user_id] = current_time
                
                # Execute the function
                return await func(update, context, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in throttle decorator: {str(e)}")
                
        return wrapped
    return decorator
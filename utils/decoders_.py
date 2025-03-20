from functools import wraps
from utils.log import logger
from assets.assets import load_asset
from config import ERROR429, LOGGER_CHATID, OWNER_ID
from utils.dataBase.FireDB import DB
from Modules.inline import ADMIN_ERROR, RATE_LIMITION
from utils.rate_limit import RateLimiter
from cachetools import TTLCache
from typing import Callable, Any, Set, Dict, Optional
from telegram import Update
from telegram.ext import ContextTypes


# Cache for storing user-related data
class UserCache:
    """Centralized cache management for user-related data"""
    
    def __init__(self):
        # Initialize from database
        self.banned_users: Set[str] = set(DB.blocked_users_cache)
        self.admin_users: Set[str] = set(DB.admins_users)
        # Rate limiting components
        self.rate_limiter = RateLimiter()
        # Store warned users with TTL cache (auto-expiry after 60 seconds)
        self.warned_users: TTLCache = TTLCache(maxsize=128, ttl=60)
        # Track reported users to avoid duplicate reports
        self.reported_users: Set[str] = set()
    
    def is_banned(self, user_id: str) -> bool:
        """Check if a user is banned"""
        return user_id in self.banned_users
    
    def is_admin(self, user_id: str) -> bool:
        """Check if a user is an admin"""
        return user_id in self.admin_users
    
    def is_owner(self, user_id: str) -> bool:
        """Check if a user is the owner"""
        return user_id == str(OWNER_ID)
    
    def refresh_banned_users(self) -> None:
        """Refresh banned users list from database"""
        self.banned_users = set(DB.blocked_users_cache)
    
    def refresh_admin_users(self) -> None:
        """Refresh admin users list from database"""
        self.admin_users = set(DB.admins_users)


# Initialize the user cache
user_cache = UserCache()

# Warning message for rate-limited users
WARNING_MESSAGE = "Spam detected! Ignoring your requests for a few minutes."


async def handle_rate_limited_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str) -> None:
    """Handle rate-limited users consistently with proper logging"""
    if user_id not in user_cache.warned_users:
        # First warning - send message with photo
        try:
            await update.message.reply_photo(
                photo=load_asset(ERROR429),
                caption=WARNING_MESSAGE,
                reply_markup=RATE_LIMITION
            )
            user_cache.warned_users[user_id] = 1
            logger.info(f"Rate limit warning sent to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send rate limit warning: {e}")
    
    elif user_id not in user_cache.reported_users:
        # User continued spamming after warning - report to admin channel
        try:
            first_name = update.effective_user.first_name
            message = f"First Name: {first_name}, UserId: <code>{user_id}</code>\n\nHas been caught spamming even after warning message was sent."
            
            await context.bot.send_message(
                chat_id=LOGGER_CHATID, 
                text=message, 
                parse_mode="HTML"
            )
            user_cache.reported_users.add(user_id)
            logger.warning(f"User {user_id} reported for continued spamming")
        except Exception as e:
            logger.error(f"Failed to report spamming user: {e}")


def rate_limit(func: Callable) -> Callable:
    """
    Restricts users from spamming commands or pressing buttons multiple times
    using leaky bucket algorithm via pyrate_limiter.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
        if not update.effective_user:
            logger.warning("Rate limit check failed: No effective user found")
            return
            
        user_id = str(update.effective_user.id)
        
        try:
            is_limited = await user_cache.rate_limiter.acquire(user_id)
            
            if is_limited:
                await handle_rate_limited_user(update, context, user_id)
                return
            
            # User is not rate limited - remove from reported set if they were previously there
            user_cache.reported_users.discard(user_id)
            return await func(update, context, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in rate_limit decorator: {e}")
            # Fall through to original function to avoid blocking legitimate requests
            return await func(update, context, *args, **kwargs)

    return wrapper


def restricted(func: Callable) -> Callable:
    """
    Restricts command access to non-banned users only.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Optional[Any]:
        if not update.effective_user:
            logger.warning("Restricted check failed: No effective user found")
            return
            
        user_id = str(update.effective_user.id)
        
        # Periodically refresh the banned users list (e.g., every 100th check)
        if hash(user_id) % 100 == 0:
            user_cache.refresh_banned_users()
        
        if user_cache.is_banned(user_id):
            logger.info(f"Unauthorized access denied for banned user {user_id}")
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def is_admin(func: Callable) -> Callable:
    """
    Restricts command access to admin users only.
    Sends a notification if a non-admin user attempts to use an admin command.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Optional[Any]:
        if not update.effective_user:
            logger.warning("Admin check failed: No effective user found")
            return
            
        user_id = str(update.effective_user.id)
        
        # Periodically refresh the admin users list
        if hash(user_id) % 50 == 0:
            user_cache.refresh_admin_users()
        
        if user_cache.is_admin(user_id) or user_cache.is_owner(user_id):
            return await func(update, context, *args, **kwargs)
        
        logger.info(f"Admin access denied for user {user_id}")
        try:
            await update.message.reply_text(
                "Access denied. Only admins can do this.", 
                reply_markup=ADMIN_ERROR
            )
        except Exception as e:
            logger.error(f"Failed to send admin denial message: {e}")
        
        return None
    
    return wrapper


def is_owner(func: Callable) -> Callable:
    """
    Restricts command access to the owner only.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Optional[Any]:
        if not update.effective_user:
            logger.warning("Owner check failed: No effective user found")
            return
            
        user_id = str(update.effective_user.id)
        
        if user_cache.is_owner(user_id):
            return await func(update, context, *args, **kwargs)
        
        logger.info(f"Owner access denied for user {user_id}")
        try:
            await update.message.reply_text("Access denied. Only the owner can do this.")
        except Exception as e:
            logger.error(f"Failed to send owner denial message: {e}")
        
        return None
    
    return wrapper


# Aliases for backward compatibility
IsAdmin = is_admin
IsOwner = is_owner
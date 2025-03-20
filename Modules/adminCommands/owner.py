"""
Admin Management Module

This module provides commands for managing bot administrators through Telegram.
Features include adding/removing admins, listing admins, and refreshing user caches.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    filters
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden

import sys
import datetime
import asyncio
from typing import List, Optional

from utils.decoders_ import IsOwner
from utils.Group_log import LOG
from utils.dataBase.FireDB import DB
from config import OWNER_ID, SPECIAL_PASSWORD


# Constants for better code organization
ADMIN_PAGE_SIZE = 5  # Number of admins to show per page
CONFIRM_TIMEOUT = 60  # Seconds to wait for confirmation


async def get_user_info(bot, user_id: str) -> str:
    """
    Get user information (name + mention) from Telegram.
    
    Args:
        bot: Telegram bot instance
        user_id: User ID to look up
        
    Returns:
        str: Formatted user info with HTML link
    """
    try:
        user = await bot.get_chat(user_id)
        return f"➻ <a href='tg://user?id={user.id}'>{user.first_name}</a>"
    except (BadRequest, Forbidden) as e:
        return f"➻ User {user_id} (could not fetch info: {str(e)})"
    except Exception as e:
        return f"➻ User {user_id} (error: {str(e)})"


async def collect_user_info(bot, user_ids: List[str]) -> str:
    """
    Collect information for multiple users.
    
    Args:
        bot: Telegram bot instance
        user_ids: List of user IDs to look up
        
    Returns:
        str: Combined user information string
    """
    user_info_list = []
    
    # Use asyncio.gather to fetch user info concurrently
    async def fetch_single_user(uid):
        return await get_user_info(bot, uid)
    
    user_info_tasks = [fetch_single_user(uid) for uid in user_ids]
    user_info_list = await asyncio.gather(*user_info_tasks)
    
    return "\n".join(user_info_list)


@IsOwner
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Add one or more users as bot admins.
    
    Usage: /add_admin user_id1 [user_id2 ...]
    """
    user_ids = context.args
    
    if not user_ids:
        usage_msg = (
            "<b>Usage:</b> Add admin privileges to users\n\n"
            "<b>Format:</b> <code>/add_admin user_id1 [user_id2 ...]</code>\n\n"
            "<b>Example:</b> <code>/add_admin 123456789</code>"
        )
        await update.message.reply_text(usage_msg, parse_mode=ParseMode.HTML)
        return
    
    # Status message that will be updated
    status_msg = await update.message.reply_text(
        "⏳ Adding users to admin list...",
        parse_mode=ParseMode.HTML
    )
    
    success_count = 0
    already_admin_count = 0
    error_messages = []
    added_users = []
    
    # Process each user ID
    for user_id in user_ids:
        try:
            # Check if already admin
            if DB.is_admin(user_id):
                already_admin_count += 1
                continue
                
            # Add to admin list
            DB.add_admin(user_id)
            added_users.append(user_id)
            success_count += 1
        except Exception as e:
            error_messages.append(f"Error adding {user_id}: {str(e)}")
    
    # Create result message
    if not added_users and not already_admin_count:
        result_message = "❌ Failed to add any admins. See errors below:\n\n" + "\n".join(error_messages)
    else:
        result_parts = []
        
        if success_count > 0:
            result_parts.append(f"✅ Successfully added {success_count} admin{'s' if success_count != 1 else ''}.")
        
        if already_admin_count > 0:
            result_parts.append(f"ℹ️ {already_admin_count} user{'s' if already_admin_count != 1 else ''} already had admin privileges.")
            
        if error_messages:
            result_parts.append(f"⚠️ {len(error_messages)} error{'s' if len(error_messages) != 1 else ''}:\n" + "\n".join(error_messages))
            
        result_message = "\n\n".join(result_parts)
    
    # Update status message with result
    await status_msg.edit_text(result_message, parse_mode=ParseMode.HTML)
    
    # If users were added, get their info and log it
    if added_users:
        user_info = await collect_user_info(context.bot, added_users)
        log_message = f"<b>🔑 New Admin{'s' if len(added_users) > 1 else ''} Added:</b>\n{user_info}"
        await LOG(update, context, msg=log_message)


@IsOwner
async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Remove one or more users from bot admins.
    
    Usage: /rm_admin user_id1 [user_id2 ...]
    """
    user_ids = context.args
    
    if not user_ids:
        usage_msg = (
            "<b>Usage:</b> Remove admin privileges from users\n\n"
            "<b>Format:</b> <code>/rm_admin user_id1 [user_id2 ...]</code>\n\n"
            "<b>Example:</b> <code>/rm_admin 123456789</code>"
        )
        await update.message.reply_text(usage_msg, parse_mode=ParseMode.HTML)
        return
    
    # Check if trying to remove the owner
    if OWNER_ID in user_ids:
        await update.message.reply_text(
            "❌ Cannot remove the bot owner from admins!",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Status message that will be updated
    status_msg = await update.message.reply_text(
        "⏳ Removing users from admin list...",
        parse_mode=ParseMode.HTML
    )
    
    success_count = 0
    not_admin_count = 0
    error_messages = []
    removed_users = []
    
    # Process each user ID
    for user_id in user_ids:
        try:
            # Check if already an admin
            if not DB.is_admin(user_id):
                not_admin_count += 1
                continue
                
            # Remove from admin list
            DB.remove_admin(user_id)
            removed_users.append(user_id)
            success_count += 1
        except Exception as e:
            error_messages.append(f"Error removing {user_id}: {str(e)}")
    
    # Create result message
    if not removed_users and not not_admin_count:
        result_message = "❌ Failed to remove any admins. See errors below:\n\n" + "\n".join(error_messages)
    else:
        result_parts = []
        
        if success_count > 0:
            result_parts.append(f"✅ Successfully removed {success_count} admin{'s' if success_count != 1 else ''}.")
        
        if not_admin_count > 0:
            result_parts.append(f"ℹ️ {not_admin_count} user{'s' if not_admin_count != 1 else ''} were not admins.")
            
        if error_messages:
            result_parts.append(f"⚠️ {len(error_messages)} error{'s' if len(error_messages) != 1 else ''}:\n" + "\n".join(error_messages))
            
        result_message = "\n\n".join(result_parts)
    
    # Update status message with result
    await status_msg.edit_text(result_message, parse_mode=ParseMode.HTML)
    
    # If users were removed, get their info and log it
    if removed_users:
        user_info = await collect_user_info(context.bot, removed_users)
        log_message = f"<b>🔒 Admin{'s' if len(removed_users) > 1 else ''} Removed:</b>\n{user_info}"
        await LOG(update, context, msg=log_message)


@IsOwner
async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all admin users with pagination support."""
    
    # Get current page from context or default to 0
    page = context.user_data.get('admin_page', 0)
    
    # Status message
    status_msg = await update.message.reply_text(
        "⏳ Fetching admin list...",
        parse_mode=ParseMode.HTML
    )
    
    # Refresh admin list to ensure it's up to date
    DB._load_admin_users()
    admin_ids = list(DB.admin_users_cache)
    
    if not admin_ids:
        await status_msg.edit_text(
            "📝 Admin list is empty.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Calculate pagination
    total_pages = (len(admin_ids) - 1) // ADMIN_PAGE_SIZE + 1
    start_idx = page * ADMIN_PAGE_SIZE
    end_idx = min(start_idx + ADMIN_PAGE_SIZE, len(admin_ids))
    current_page_ids = admin_ids[start_idx:end_idx]
    
    # Get user info for current page
    admin_info = await collect_user_info(context.bot, current_page_ids)
    
    # Create message with pagination info
    message = (
        f"<b>🔑 Bot Administrators</b> (Page {page+1}/{total_pages}):\n\n"
        f"{admin_info}\n\n"
        f"Total Admins: {len(admin_ids)}"
    )
    
    # Create pagination keyboard
    keyboard = []
    
    # Add navigation buttons
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data="admin_prev"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data="admin_next"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    # Add refresh button
    keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    # Update message with admin list and navigation buttons
    await status_msg.edit_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def admin_pagination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin list pagination callbacks."""
    query = update.callback_query
    await query.answer()
    
    # Get current page or default to 0
    current_page = context.user_data.get('admin_page', 0)
    
    # Handle different actions
    if query.data == "admin_prev":
        context.user_data['admin_page'] = max(0, current_page - 1)
    elif query.data == "admin_next":
        context.user_data['admin_page'] = current_page + 1
    elif query.data == "admin_refresh":
        # Keep the same page, but refresh data
        pass
    
    # Call list_admins to refresh the list with the new page
    await list_admins(update, context)


@IsOwner
async def refresh_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Refresh admin and blocked user lists and display stats."""
    
    # Status message
    status_msg = await update.message.reply_text(
        "⏳ Refreshing user data from database...",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Refresh both caches
        DB.refresh_caches()
        
        # Get the counts for stats
        admin_count = len(DB.admin_users_cache)
        blocked_count = len(DB.blocked_users_cache)
        
        # Create options for which list to view
        keyboard = [
            [
                InlineKeyboardButton("👑 View Admins", callback_data="view_admins"),
                InlineKeyboardButton("🚫 View Blocked", callback_data="view_blocked")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update with counts and options
        await status_msg.edit_text(
            f"✅ Database refreshed successfully!\n\n"
            f"<b>Statistics:</b>\n"
            f"• Admin users: {admin_count}\n"
            f"• Blocked users: {blocked_count}\n\n"
            f"Select an option to view details:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    except Exception as e:
        await status_msg.edit_text(
            f"❌ Error refreshing database: {str(e)}",
            parse_mode=ParseMode.HTML
        )


async def view_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks for viewing admin or blocked users after refresh."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "view_admins":
        # Reset page counter and show admin list
        context.user_data['admin_page'] = 0
        await list_admins(update, context)
    elif query.data == "view_blocked":
        # Show blocked users list
        await list_blocked_users(update, context)


async def list_blocked_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all blocked users."""
    
    # Get current page from context or default to 0
    page = context.user_data.get('blocked_page', 0)
    
    # Status message (or use the existing message if from callback)
    if update.callback_query:
        status_msg = update.callback_query.message
        await status_msg.edit_text(
            "⏳ Fetching blocked users list...",
            parse_mode=ParseMode.HTML
        )
    else:
        status_msg = await update.message.reply_text(
            "⏳ Fetching blocked users list...",
            parse_mode=ParseMode.HTML
        )
    
    # Get blocked users
    blocked_ids = list(DB.blocked_users_cache)
    
    if not blocked_ids:
        await status_msg.edit_text(
            "📝 No users are currently blocked.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Calculate pagination
    total_pages = (len(blocked_ids) - 1) // ADMIN_PAGE_SIZE + 1
    start_idx = page * ADMIN_PAGE_SIZE
    end_idx = min(start_idx + ADMIN_PAGE_SIZE, len(blocked_ids))
    current_page_ids = blocked_ids[start_idx:end_idx]
    
    # Get user info for current page
    blocked_info = await collect_user_info(context.bot, current_page_ids)
    
    # Create message with pagination info
    message = (
        f"<b>🚫 Blocked Users</b> (Page {page+1}/{total_pages}):\n\n"
        f"{blocked_info}\n\n"
        f"Total Blocked: {len(blocked_ids)}"
    )
    
    # Create pagination keyboard
    keyboard = []
    
    # Add navigation buttons
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data="blocked_prev"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data="blocked_next"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    # Add refresh button
    keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="blocked_refresh")])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    # Update message with blocked list and navigation buttons
    await status_msg.edit_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def blocked_pagination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle blocked users list pagination callbacks."""
    query = update.callback_query
    await query.answer()
    
    # Get current page or default to 0
    current_page = context.user_data.get('blocked_page', 0)
    
    # Handle different actions
    if query.data == "blocked_prev":
        context.user_data['blocked_page'] = max(0, current_page - 1)
    elif query.data == "blocked_next":
        context.user_data['blocked_page'] = current_page + 1
    elif query.data == "blocked_refresh":
        # Keep the same page, but refresh data
        DB._load_blocked_users()
    
    # Call list_blocked_users to refresh the list with the new page
    await list_blocked_users(update, context)


@IsOwner
async def shutdown_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Shutdown the bot with password confirmation.
    
    Usage: /off [password]
    """
    # Check if password is provided
    if not context.args:
        await update.message.reply_text(
            "⚠️ Password required to shut down the bot.\n\n"
            "<b>Usage:</b> <code>/off [password]</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Check if password matches
    provided_password = context.args[0]
    
    if provided_password == SPECIAL_PASSWORD:
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, shut down", callback_data="shutdown_confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="shutdown_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Ask for confirmation
        message = await update.message.reply_text(
            "⚠️ <b>Are you sure you want to shut down the bot?</b>\n\n"
            "This will terminate the bot process. You will need to restart it manually.",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
        # Store message ID for later deletion on timeout
        context.user_data["shutdown_message_id"] = message.message_id
        
        # Set up job to clear shutdown request after timeout
        context.job_queue.run_once(
            clear_shutdown_request,
            CONFIRM_TIMEOUT,
            data={"chat_id": update.effective_chat.id, "message_id": message.message_id}
        )
    else:
        await update.message.reply_text(
            "❌ Incorrect password.",
            parse_mode=ParseMode.HTML
        )


async def shutdown_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle shutdown confirmation callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "shutdown_confirm":
        await query.edit_message_text(
            "🔄 Bot shutting down...\n\n"
            f"Shutdown initiated by: {query.from_user.first_name} (ID: {query.from_user.id})\n"
            f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode=ParseMode.HTML
        )
        
        # Log shutdown
        shutdown_log = (
            f"<b>⚠️ BOT SHUTDOWN</b>\n"
            f"Initiated by: {query.from_user.first_name} (ID: {query.from_user.id})\n"
            f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        try:
            await LOG(update, context, msg=shutdown_log)
        except Exception:
            pass  # Don't let logging failure prevent shutdown
        
        # Give a moment for messages to send
        await asyncio.sleep(2)
        
        # Exit
        sys.exit(0)
    
    elif query.data == "shutdown_cancel":
        await query.edit_message_text(
            "✅ Shutdown cancelled.",
            parse_mode=ParseMode.HTML
        )


async def clear_shutdown_request(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear shutdown request after timeout."""
    data = context.job.data
    chat_id = data["chat_id"]
    message_id = data["message_id"]
    
    try:
        await context.bot.edit_message_text(
            "⏱️ Shutdown request expired.",
            chat_id=chat_id,
            message_id=message_id
        )
    except Exception:
        # Message might have been deleted or edited already
        pass


async def bot_activation_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send activation message to owner when bot starts."""
    # Get the current time when the bot starts
    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create a keyboard with quick access buttons
    keyboard = [
        [
            InlineKeyboardButton("👑 Admin List", callback_data="admin_refresh"),
            InlineKeyboardButton("🚫 Blocked List", callback_data="blocked_refresh")
        ],
        [
            InlineKeyboardButton("🔄 Refresh Data", callback_data="refresh_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    start_message = (
        f"<b>🤖 Bot Started Successfully</b>\n\n"
        f"<b>Start Time:</b> <code>{start_time}</code>\n"
        f"<b>Shutdown Password:</b> <code>{SPECIAL_PASSWORD}</code>\n\n"
        f"<b>Quick Stats:</b>\n"
        f"• Admin Users: <code>{len(DB.admin_users_cache)}</code>\n"
        f"• Blocked Users: <code>{len(DB.blocked_users_cache)}</code>"
    )
    
    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=start_message,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Failed to send activation message: {e}")


# Register command handlers
def register_handlers(application):
    """Register all handlers for the admin management module."""
    
    # Admin management commands
    application.add_handler(CommandHandler("add_admin", add_admin))
    application.add_handler(CommandHandler(["rm_admin", "remove_admin"], remove_admin))
    application.add_handler(CommandHandler(["admins", "list_admin"], list_admins))
    application.add_handler(CommandHandler("refresh", refresh_users))
    application.add_handler(CommandHandler("blocked", list_blocked_users))
    application.add_handler(CommandHandler("off", shutdown_bot))
    
    # Callback handlers for interactive features
    application.add_handler(CallbackQueryHandler(admin_pagination_callback, pattern="^admin_(prev|next|refresh)$"))
    application.add_handler(CallbackQueryHandler(blocked_pagination_callback, pattern="^blocked_(prev|next|refresh)$"))
    application.add_handler(CallbackQueryHandler(view_users_callback, pattern="^view_(admins|blocked)$"))
    application.add_handler(CallbackQueryHandler(shutdown_callback, pattern="^shutdown_(confirm|cancel)$"))
    
    return application


# Standalone command handlers (for backward compatibility)
ADD_admin_CMD = CommandHandler("add_admin", add_admin)
RM_admin_CMD = CommandHandler(["rm_admin", "remove_admin"], remove_admin)
ADMINS_LIST_CMD = CommandHandler(["admins", "list_admin"], list_admins)
REFRESH_CMD = CommandHandler("refresh", refresh_users)
BLOCKED_CMD = CommandHandler("blocked", list_blocked_users)
OFF_COMMAND = CommandHandler("off", shutdown_bot)

# Export a function to send activation message
BOT_ACTIVATION_MESSAGE = bot_activation_message
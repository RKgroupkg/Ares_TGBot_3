from utils.decoders_ import IsOwner
from telegram import Update

from config import OWNER_ID
import datetime 

import sys

from utils.Group_log import LOG
from utils.dataBase.FireDB import DB
from telegram.ext import (
    ContextTypes,
    CommandHandler,
)




@IsOwner
async def ADD_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Add admins
    """
    UserIds = context.args
    if not UserIds:
        ADD_ADMIN_USAGE = f"<b>USAGE:</b> Add Admin via bot.\n\n<b>Example: </b><pre>/add_Admin 100021</pre>"
        await update.message.reply_text(ADD_ADMIN_USAGE,parse_mode="HTML")
    
    msg = await update.message.reply_text("Adding The User To Admin list...")
    user_info = ""
    added_users_info = ""

    for UserId in UserIds:
        DB.add_admin(UserId)
        try:
            user = await context.bot.get_chat(UserId)
            user_info = f"➻ <a href='tg://user?id={user.id}'>{user.first_name}</a>"
            added_users_info += f"\n{user_info}"
        except Exception as e:
            added_users_info += f"\nFailed to get user info for: {UserId}"


    log_message = (
        f"<b>New Admins Added:</b>{added_users_info}"
    )
    
            


    await LOG(update,context,msg=log_message)

    await msg.edit_text("The users have been added to the admin list.")


@IsOwner
async def Remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Remove admins
    """
    UserIds = context.args
    if not UserIds:
        ADD_ADMIN_USAGE = f"<b>USAGE:</b> Remove Admin via bot.\n\n<b>Example: </b><pre>/rm_Admin 100021</pre>"
        await update.message.reply_text(ADD_ADMIN_USAGE,parse_mode="HTML")
    
    msg = await update.message.reply_text("Removing The User From Admin list...")
    user_info = ""
    added_users_info = ""

    for UserId in UserIds:
        DB.remove_admin(UserId)
        try:
            user = await context.bot.get_chat(UserId)
            user_info = f"➻ <a href='tg://user?id={user.id}'>{user.first_name}</a>"
            added_users_info += f"\n{user_info}"
        except Exception as e:
            added_users_info += f"\nFailed to get user info for: {UserId}"


    log_message = (
        f"<b>Admins Removed:</b>{added_users_info}"
    )
    
            


    await LOG(update,context,msg=log_message)

    await msg.edit_text("The users have been removed from the admin list.")


@IsOwner
async def LIST_ADMIN(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Give Admin List
    """
    
    
    msg = await update.message.reply_text("Extracting The info...")
    user_info = ""
    added_users_info = ""

    DB._load_admin_users()
    Admins = DB.admins_users

    for UserId in Admins:
        try:
            user = await context.bot.get_chat(UserId)
            user_info = f"➻ <a href='tg://user?id={user.id}'>{user.first_name}</a>"
            added_users_info += f"\n{user_info}"
        except Exception as e:
            added_users_info += f"\nFailed to get user info for: {UserId}"


    message = (
        f"<b>Current Admins Are:</b>{added_users_info}"
    )

    await msg.edit_text(message,parse_mode="HTML")


@IsOwner
async def Refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Refresh Admin List and Blocked user List
    """
    
    
    msg = await update.message.reply_text("Refreshing the info The info...")
    user_info = ""
    Admin_info = ""
    bloacked_info =""

    DB._load_admin_users()
    DB._load_blocked_users()
    Admins = DB.admins_users
    Blocke_users = DB.blocked_users_cache

    for UserId in Admins:
        try:
            user = await context.bot.get_chat(UserId)
            user_info = f"➻ <a href='tg://user?id={user.id}'>{user.first_name}</a>"
            Admin_info += f"\n{user_info}"
        except Exception as e:
            Admin_info += f"\nFailed to get user info for: {UserId}"

    for UserId in Blocke_users:
        try:
            user = await context.bot.get_chat(UserId)
            user_info = f"➻ <a href='tg://user?id={user.id}'>{user.first_name}</a>"
            bloacked_info += f"\n{user_info}"
        except Exception as e:
            bloacked_info += f"\nFailed to get user info for: {UserId}"


    message = (
        f"<b>Current Admins Are:</b>{Admin_info}\n\n<b>Current Blocked Users Are:</b> {bloacked_info}"
    )

    await msg.edit_text(message,parse_mode="HTML")


@IsOwner
async def OFF(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the correct special password is provided as an argument
    await update.message.reply_text(f"Bot is shutting down...\n\n")
    # Perform any cleanup or final tasks here if needed  
    sys.exit(0)  # Exit the script with status code 0 (success)
   
async def BOT_ACTIVATION_MESSAGE(update):
        # Get the current time when the bot starts
        START_TIME = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        start_message = (
            f"<b>Bot Started</b>\n"
            f"Start Time: <code>{START_TIME}</code>\n"
        )
        await update.bot.send_message(chat_id=OWNER_ID, text=start_message, parse_mode="HTML")

    
ADD_admin_CMD = CommandHandler("add_admin",ADD_admin)
RM_admin_CMD = CommandHandler(("rm_admin","remove_admin"),Remove_admin)
ADMINS_LIST_CMD = CommandHandler(("admins","list_admin"),LIST_ADMIN)
REFRESH_CMD = CommandHandler("refresh",Refresh)
OFF_COMMAD = CommandHandler("off",OFF)
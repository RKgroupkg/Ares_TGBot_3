import aiofiles
import os
from time import time 
from httpx import AsyncClient
from datetime import datetime

from utils.helper.functions import get_readable_time
from config import BotStartTime

from utils.helper.pasting_servises import katbin_paste
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
)




async def paste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Paste the text in katb.in website.
    """
    
    paste_usage = f"♔ <b>Usage:</b> paste the text to katb.in website. Reply to a text file, text message or just type the text after command.\n\n<b>Example:</b> /paste type your text"
    paste_reply = await update.message.reply_text("♔ pasting...")
    replied_message = update.message.reply_to_message
    
    args = context.args
    if not args and not update.message.reply_to_message:
        await paste_reply.edit_text(paste_usage,parse_mode="HTML")
        
    
    if replied_message:
        if replied_message.text:
            content = replied_message.text
            
        elif replied_message.document and replied_message.document.mime_type in ['text/plain', 'application/json']:
            
            file = await replied_message.effective_attachment.get_file()
            file_path = await file.download_to_drive()
            async with aiofiles.open(file_path, "r+") as file:
                content = await file.read()
            os.remove(file_path)
            
        else:
            await paste_reply.edit_text(paste_usage)
            return
    elif args:
        content = ' '.join(args)
    else:
        await paste_reply.edit_text(paste_usage)
        return 


    
    output = await katbin_paste(content)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Open in Browser", url=output)]
    ])
    
    await paste_reply.edit_text(f"{output}", disable_web_page_preview=True,reply_markup=keyboard)


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):

    """
    Give ping speed of Telegram API along with Bot Uptime.
    """
    
    pong_reply = await update.message.reply_text("pong!")
    
    start = datetime.now()
    async with AsyncClient() as client:
        await client.get("http://api.telegram.org")
    end = datetime.now()
    
    botuptime = get_readable_time(time() - BotStartTime)
    pong = (end - start).microseconds / 1000
    await pong_reply.edit_text(
        f"♔ <b>Ping Time:</b><i>{pong}</i>ms |♔  <b>Bot is alive since:</b> <i>{botuptime}</i>",parse_mode="HTML")

async def ID(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /id gets the relavent ids realted to message
    """
    try:
        message = update.message
        if message.reply_to_message:
            replied_message_id = message.reply_to_message.message_id
            replied_user_id = message.reply_to_message.from_user.id
            text = (
                f"♔ <b>Message Id:</b> <code>{message.message_id}</code>\n"
                f"♕ <b>ʏᴏᴜʀ ɪᴅ:</b> <code>{message.from_user.id}</code>\n"
                f"♚ <b>ᴄʜᴀᴛ ɪᴅ:</b> <code>{message.chat_id}</code>\n\n"
                f"♛ <b>ʀᴇᴘʟɪᴇᴅ ᴍᴇssᴀɢᴇ ɪᴅ:</b> <code>{replied_message_id}</code>\n"
                f"♝ <b>ʀᴇᴘʟɪᴇᴅ ᴜsᴇʀ ɪᴅ:</b> <code>{replied_user_id}</code>"
            )
        else:
            text = (
                f"♞ <b>ᴍᴇssᴀɢᴇ ɪᴅ:</b> <code>{message.message_id}</code>\n"
                f"♜ <b>ʏᴏᴜʀ ɪᴅ:</b> <code>{message.from_user.id}</code>\n"
                f"♙ <b>ᴄʜᴀᴛ ɪᴅ:</b> <code>{message.chat_id}</code>\n\n"
                f"♚ <i>No message was replied to.</i>"
            )
         
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="HTML")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"♔ An error occurred: {e}")


PASTE_CMD = CommandHandler("paste",paste)
PING_CMD = CommandHandler("ping",ping)
ID_CMD = CommandHandler("id",ID)
from utils.log import logger
from utils.dataBase.FireDB import DB
from telegram.constants import ParseMode
from assets.assets import load_asset
from config import WARN_USERS, LOADING_BAR
from utils.decoders_ import IsAdmin
from Modules.inline import CLOSE_BUTTON
from utils.Group_log import LOG
from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
)
import asyncio
from typing import List, Union


async def send_message_with_retry(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: Union[str, int],
    original_message=None,
    warning_message=None,
    warning_photo=None,
    max_retries: int = 3,
    retry_delay: float = 1.0
):
    """Send a message with retry logic for better reliability"""
    for attempt in range(max_retries):
        try:
            if original_message:
                await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=original_message.chat_id,
                    message_id=original_message.message_id, 
                )
            elif warning_message and warning_photo:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=warning_photo,
                    caption=warning_message,
                    parse_mode=ParseMode.HTML
                )
            return True, None
        except Exception as e:
            if "bot was blocked by the user" in str(e):
                logger.info(f"User {user_id} has blocked the bot.")
                return False, f"User {user_id} has blocked the bot"
            elif attempt < max_retries - 1:
                logger.warning(f"Retrying message to {user_id}, attempt {attempt+1}/{max_retries}. Error: {e}")
                await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"Failed to send message to {user_id} after {max_retries} attempts: {e}")
                return False, str(e)
    
    return False, "Max retries exceeded"


async def update_progress_message(message, current, total, caption_prefix="Broadcasting"):
    """Update progress message with completion percentage"""
    if current % max(1, total // 10) == 0 or current == total:  # Update at 10% intervals or at completion
        progress_percentage = min(100, int((current / total) * 100))
        await message.edit_caption(
            caption=f"{caption_prefix}... {progress_percentage}% complete ({current}/{total})",
            parse_mode=ParseMode.HTML
        )


@IsAdmin
async def GB_broadCast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global broadcast to all users in database"""
    message = update.effective_message
    chat_id = message.chat_id
    
    if not message.reply_to_message:
        await context.bot.send_message(
            chat_id=chat_id, 
            text="Please reply to a message to broadcast it."
        )
        return
    
    original_message = message.reply_to_message
    
    msg = await update.message.reply_photo(
        photo=load_asset(LOADING_BAR),
        caption="Bʀᴏᴀᴅᴄᴀsᴛɪɴɢ ᴍᴇssᴀɢᴇ ᴛᴏ ᴀʟʟ ᴜsᴇʀs..."
    )
    
    logger.info(f"{update.effective_user.first_name} started a Global BroadCast")
    
    try:
        userIds = DB.get_usernames()
        if not userIds:
            await msg.edit_caption(caption="No users found in database for broadcast!")
            return
            
        successful = 0
        failed = 0
        blocked = 0
        errors = []
        
        for idx, user_id in enumerate(userIds):
            success, error = await send_message_with_retry(context, user_id, original_message=original_message)
            
            if success:
                successful += 1
            else:
                failed += 1
                if "blocked" in error.lower():
                    blocked += 1
                else:
                    errors.append(f"User {user_id}: {error}")
            
            # Update progress message periodically
            await update_progress_message(msg, idx + 1, len(userIds))
        
        # Log the broadcast action
        try:
            msg_Log = (
                f"<b>📢 Gʟᴏʙᴀʟ Bʀᴏᴀᴅᴄᴀsᴛ</b>\n"
                f"<b>ᴍsɢIᴅ:</b> <code>{message.id}</code>\n"
                f"<b>ChatID:</b> <code>{message.chat_id}</code>\n"
                f"<b>Stats:</b> ✅ {successful} sent, ❌ {failed} failed ({blocked} blocked)"
            )
            await LOG(update, context, msg_Log)
        except Exception as e:
            logger.error(f"Error logging global broadcast: {e}")
        
        # Final status message
        status_msg = (
            f"Bʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇ 🎉\n\n"
            f"📊 <b>Statistics:</b>\n"
            f"👥 <b>Total Users:</b> {len(userIds)}\n"
            f"✅ <b>Successful:</b> {successful}\n"
            f"❌ <b>Failed:</b> {failed}\n"
            f"🚫 <b>Blocked:</b> {blocked}"
        )
        
        await msg.edit_caption(
            caption=status_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=CLOSE_BUTTON
        )
        
        # If there are errors, send them in a separate message for admin review
        if errors and len(errors) <= 10:
            error_msg = "Detailed errors:\n" + "\n".join(errors[:10])
            await context.bot.send_message(
                chat_id=chat_id,
                text=error_msg,
                parse_mode=ParseMode.HTML
            )
    
    except Exception as e:
        logger.error(f"Critical error in global broadcast: {e}")
        await msg.edit_caption(
            caption=f"Broadcast error: {str(e)}",
            reply_markup=CLOSE_BUTTON
        )


@IsAdmin
async def SP_broadCast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Specific broadcast to selected users"""
    message = update.effective_message
    chat_id = message.chat_id

    args = context.args
    if not args:
        await update.message.reply_text("Usᴀɢᴇ: /sᴘ_ʙʀᴏᴀᴅᴄᴀsᴛ (ᴄʜᴀᴛ_ɪᴅ1) [ᴄʜᴀᴛ_ɪᴅ2] ...")
        return

    if not message.reply_to_message:
        await context.bot.send_message(
            chat_id=chat_id, 
            text="Please reply to a message to broadcast it."
        )
        return
    
    original_message = message.reply_to_message
    
    msg = await update.message.reply_photo(
        photo=load_asset(LOADING_BAR),
        caption=f"Bʀᴏᴀᴅᴄᴀsᴛɪɴɢ ᴍᴇssᴀɢᴇ ᴛᴏ {len(args)} users..."
    )
    
    logger.info(f"{update.effective_user.first_name} started a Specific BroadCast to: {args}")
    
    try:
        successful = 0
        failed = 0
        blocked = 0
        errors = []
        
        for idx, user_id in enumerate(args):
            success, error = await send_message_with_retry(context, user_id, original_message=original_message)
            
            if success:
                successful += 1
            else:
                failed += 1
                if "blocked" in error.lower():
                    blocked += 1
                else:
                    errors.append(f"User {user_id}: {error}")
            
            # Update progress message periodically
            await update_progress_message(msg, idx + 1, len(args))
        
        # Log the broadcast action
        try:
            msg_Log = (
                f"<b>📢 Sᴘᴇᴄɪғɪᴄ Bʀᴏᴀᴅᴄᴀsᴛ</b>\n"
                f"<b>ᴍsɢIᴅ:</b> <code>{message.id}</code>\n"
                f"<b>Fʀᴏᴍ ChatID:</b> <code>{message.chat_id}</code>\n"
                f"<b>Tᴏ CʜᴀᴛIᴅs:</b> {', '.join(args)}\n"
                f"<b>Stats:</b> ✅ {successful} sent, ❌ {failed} failed ({blocked} blocked)"
            )
            await LOG(update, context, msg_Log)
        except Exception as e:
            logger.error(f"Error logging specific broadcast: {e}")
        
        # Final status message
        status_msg = (
            f"Sᴘᴇᴄɪғɪᴄ Bʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇ 🎉\n\n"
            f"📊 <b>Statistics:</b>\n"
            f"👥 <b>Target Users:</b> {len(args)}\n"
            f"✅ <b>Successful:</b> {successful}\n"
            f"❌ <b>Failed:</b> {failed}\n"
            f"🚫 <b>Blocked:</b> {blocked}"
        )
        
        await msg.edit_caption(
            caption=status_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=CLOSE_BUTTON
        )
        
        # If there are errors, send them in a separate message for admin review
        if errors and len(errors) <= 10:
            error_msg = "Detailed errors:\n" + "\n".join(errors[:10])
            await context.bot.send_message(
                chat_id=chat_id,
                text=error_msg,
                parse_mode=ParseMode.HTML
            )
    
    except Exception as e:
        logger.error(f"Critical error in specific broadcast: {e}")
        await msg.edit_caption(
            caption=f"Broadcast error: {str(e)}",
            reply_markup=CLOSE_BUTTON
        )


@IsAdmin
async def Warn_Users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send warning messages to specific users"""
    chat_id = update.effective_message.chat_id

    args = context.args
    if not args:
        await update.message.reply_text("Usᴀɢᴇ: /warn (ᴄʜᴀᴛ_ɪᴅ1) [ᴄʜᴀᴛ_ɪᴅ2] ...")
        return
    
    msg = await update.message.reply_photo(
        photo=load_asset(LOADING_BAR),
        caption=f"Sending warning to {len(args)} users..."
    )
    
    logger.info(f"{update.effective_user.first_name} sent warning to: {args}")
    
    warning_message = """
<b>Official Warning Notice</b>

Dear User,

It has come to our attention that your recent behavior in our community has violated our community guidelines. We take such matters very seriously to ensure a positive and respectful environment for all members.

<i>This is an official warning issued by the administrators of the Ares community. Continued inappropriate behavior may result in further action, including but not limited to temporary or permanent suspension from the community.</i>

If you have any questions or believe this warning was issued in error, please reach out to our support team for assistance. You can contact us via our support chat by clicking <a href='https://t.me/AresChatBotAi'>ARES</a>.

Thank you for your attention to this matter and for your cooperation in maintaining a respectful community.

Sincerely,

The Ares Administration Team
"""

    try:
        successful = 0
        failed = 0
        blocked = 0
        errors = []
        
        for idx, user_id in enumerate(args):
            success, error = await send_message_with_retry(
                context, 
                user_id, 
                warning_message=warning_message,
                warning_photo=load_asset(WARN_USERS)
            )
            
            if success:
                successful += 1
            else:
                failed += 1
                if "blocked" in error.lower():
                    blocked += 1
                else:
                    errors.append(f"User {user_id}: {error}")
            
            # Update progress message periodically
            await update_progress_message(msg, idx + 1, len(args), caption_prefix="Sending warnings")
        
        # Log the warning broadcast
        try:
            msg_Log = (
                f"<b>📢 Wᴀʀɴɪɴɢ Bʀᴏᴀᴅᴄᴀsᴛ</b>\n"
                f"<b>ᴍsɢIᴅ:</b> <code>{update.message.id}</code>\n"
                f"<b>Fʀᴏᴍ ChatID:</b> <code>{update.message.chat_id}</code>\n"
                f"<b>Tᴏ CʜᴀᴛIᴅs:</b> {', '.join(args)}\n"
                f"<b>Stats:</b> ✅ {successful} sent, ❌ {failed} failed ({blocked} blocked)"
            )
            await LOG(update, context, msg_Log)
        except Exception as e:
            logger.error(f"Error logging warning broadcast: {e}")
        
        # Final status message
        status_msg = (
            f"Wᴀʀɴɪɴɢ Bʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇ 🎉\n\n"
            f"📊 <b>Statistics:</b>\n"
            f"👥 <b>Target Users:</b> {len(args)}\n"
            f"✅ <b>Successful:</b> {successful}\n"
            f"❌ <b>Failed:</b> {failed}\n"
            f"🚫 <b>Blocked:</b> {blocked}"
        )
        
        await msg.edit_caption(
            caption=status_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=CLOSE_BUTTON
        )
        
        # If there are errors, send them in a separate message for admin review
        if errors and len(errors) <= 10:
            error_msg = "Detailed errors:\n" + "\n".join(errors[:10])
            await context.bot.send_message(
                chat_id=chat_id,
                text=error_msg,
                parse_mode=ParseMode.HTML
            )
    
    except Exception as e:
        logger.error(f"Critical error in warning broadcast: {e}")
        await msg.edit_caption(
            caption=f"Warning broadcast error: {str(e)}",
            reply_markup=CLOSE_BUTTON
        )


# Command handlers remain the same to maintain compatibility
Global_BROADCAST = CommandHandler(("gb_broadcast", "global_broadcast", "GbBroadcast", "GlobalBroadCast"), GB_broadCast)
Specific_BROADCAST = CommandHandler(("sp_broadcast", "specific_broadcast", "sms"), SP_broadCast)
WARN_USER_BROADCAST = CommandHandler("warn", Warn_Users)
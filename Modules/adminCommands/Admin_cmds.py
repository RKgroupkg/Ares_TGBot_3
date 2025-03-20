import telegram 
from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
)
from utils.decoders_ import IsAdmin
from utils.dataBase.FireDB import DB
from utils.Group_log import LOG
import html


LIST_OF_BAN_IDS = DB.blocked_users_cache
LIST_ADMIN_USER_IDS = DB.admins_users


@IsAdmin
async def chat_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gives back chat information to the admin who requested it
    """
    chat_ids = context.args

    if not chat_ids:
        await update.message.reply_text("Usᴀɢᴇ: /chat_info (ᴄʜᴀᴛ_ɪᴅ)")
        return
    
    if len(chat_ids) > 30:
        await update.message.reply_text("Maximum of 30 chats can be shown at one time.\n\nUsᴀɢᴇ: /chat_info (ᴄʜᴀᴛ_ɪᴅ)")
        return
    
    msg = await update.message.reply_html("<b>Extracting info...</b>")

    for chat_id_str in chat_ids:
        try:
            chat_id = int(chat_id_str)

            try:
                chat = await context.bot.get_chat(chat_id)
                
                # Create dictionary of chat properties
                chat_data = {
                    "➻ cʜᴀᴛ ɪᴅ": f"<code>{chat.id}</code>",
                    "➻ cʜᴀᴛ ᴛʏᴘᴇ": chat.type,
                    "➻ ᴛɪᴛʟᴇ": chat.title,
                    "➻ ᴜsᴇʀɴᴀᴍᴇ": chat.username,
                    "➻ ғɪʀsᴛ ɴᴀᴍᴇ": chat.first_name,
                    "➻ ʟᴀsᴛ ɴᴀᴍᴇ": chat.last_name,
                    "➻ ᴘʜᴏᴛᴏ": chat.photo,
                    "➻ ᴅᴇsᴄʀɪᴘᴛɪᴏɴ": chat.description,
                    "➻ ɪɴᴠɪᴛᴇ ʟɪɴᴋ": chat.invite_link,
                    "➻ ᴘɪɴɴᴇᴅ ᴍᴇssᴀɢᴇ": chat.pinned_message.text if chat.pinned_message else None,
                    "➻ sᴛɪᴄᴋᴇʀ sᴇᴛ ɴᴀᴍᴇ": chat.sticker_set_name,
                    "➻ ᴄᴀɴ sᴇᴛ sᴛɪᴄᴋᴇʀ sᴇᴛ": chat.can_set_sticker_set,
                    "➻ ʟɪɴᴋᴇᴅ ᴄʜᴀᴛ ɪᴅ": chat.linked_chat_id,
                    "➻ ʟᴏᴄᴀᴛɪᴏɴ": chat.location,
                    "➻ ᴊᴏɪɴ ʙʏ ʀᴇǫᴜᴇsᴛ": chat.join_by_request,
                    "➻ ᴘᴇʀᴍɪssɪᴏɴs": chat.permissions,
                }
                
                # Filter out None values and format the output
                filtered_data = {k: v for k, v in chat_data.items() if v is not None}
                info_text = "\n".join([f"{key}: {value}" for key, value in filtered_data.items()])
                
                await msg.edit_text(f"Cʜᴀᴛ Iɴғᴏʀᴍᴀᴛɪᴏɴ:\n{info_text}", parse_mode='HTML')
            
            except telegram.error.Forbidden:
                await msg.edit_text(f"Cʜᴀᴛ ID {chat_id}: I ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀᴄᴄᴇss ᴛᴏ ᴛʜɪs ᴄʜᴀᴛ.")
            
            except telegram.error.BadRequest as e:
                await msg.edit_text(f"Cʜᴀᴛ ID {chat_id}: Bᴀᴅ ʀᴇǫᴜᴇsᴛ. Eʀʀᴏʀ: {e.message}")
            
            except Exception as e:
                await msg.edit_text(f"Cʜᴀᴛ ID {chat_id}: Fᴀɪʟᴇᴅ ᴛᴏ ɢᴇᴛ ᴄʜᴀᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ. Eʀʀᴏʀ: {str(e)}")
        
        except ValueError:
            await msg.edit_text(f"Iɴᴠᴀʟɪᴅ ᴄʜᴀᴛ ID: {chat_id_str}. Pʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ɴᴜᴍᴇʀɪᴄ ᴄʜᴀᴛ IDs.")


@IsAdmin
async def chat_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gives data about a user's bot usage
    """
    user_ids = context.args
    
    if not user_ids:
        await update.message.reply_text("Usᴀɢᴇ: /user_data (ᴜsᴇʀ_ɪᴅ)")
        return
    
    msg = await update.message.reply_html("<b>Extracting info...</b>")
    user_id = user_ids[0]
    
    try:
        chat = await context.bot.get_chat(user_id)
        
        # Determine name based on chat type
        if chat.type == "private":
            first_name = chat.first_name
        else:
            first_name = chat.title
        
        # Check if user is banned
        is_banned = "Yes" if user_id in LIST_OF_BAN_IDS else "No"
        
        # Get AI usage information
        ai_prompt = DB.extract_instruction(user_id)
        
        # Check if user exists in database
        user_data = DB.user_exists(user_id)
        used_ai = "Yes" if user_data else "No"
        
        # Check if user is admin
        user_admin = "Yes" if user_id in LIST_ADMIN_USER_IDS else "No"
        
        # Format and send the information
        info = f"""
<b>» Chat data:</b>

➻ ᴜsᴇʀɴᴀᴍᴇ: <a href='tg://user?id={chat.id}'>{first_name}</a>
➻ ɪs ʙᴀɴɴᴇᴅ: {is_banned}
➻ ɪs ᴀᴅᴍɪɴ: {user_admin}
➻ ᴀɪ ᴘʀᴏᴍᴘᴛ: {html.escape(ai_prompt)}
➻ ᴜsᴇᴅ ᴀɪ: {used_ai}
"""
        await msg.edit_text(info, parse_mode="HTML")
    
    except Exception as e:
        await msg.edit_text(f"Fᴀɪʟᴇᴅ ᴛᴏ ɢᴇᴛ ᴜsᴇʀ ᴅᴀᴛᴀ. Eʀʀᴏʀ: {str(e)}", parse_mode="HTML")


@IsAdmin
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Bans a user from using the bot
    """
    user_ids = context.args
    
    if not user_ids:
        await update.message.reply_text("Usᴀɢᴇ: /ban (ᴜsᴇʀ_ɪᴅ)")
        return
    
    msg = await update.message.reply_html("<b>Bᴀɴɴɪɴɢ ᴛʜᴇ ᴜsᴇʀ...</b>")
    
    for user_id in user_ids:
        try:
            # Ban the user in the database
            DB.block_user(user_id)
            
            try:
                # Get user information for logging
                user = await context.bot.get_chat(user_id)
                added_users_info = f"""
<b>User:</b> <a href='tg://user?id={user.id}'>{user.first_name}</a>
<b>User ID:</b> {user.id}
"""
                # Log the ban action
                log = f"""
<b>🔨» User Banned</b>
{added_users_info}
"""
                await LOG(update, context, log)
            
            except Exception as e:
                # Handle error when getting user info
                added_users_info = f"\nFᴀɪʟᴇᴅ ᴛᴏ ɢᴇᴛ ᴜsᴇʀ ɪɴғᴏ ғᴏʀ: {user_id}. Eʀʀᴏʀ: {str(e)}"
        
        except Exception as e:
            await msg.edit_text(f"Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ ᴡʜɪʟᴇ ʙᴀɴɴɪɴɢ ᴛʜᴇ ᴜsᴇʀ: {str(e)}")
            return
    
    await msg.edit_text("<b>🔨 User Banned Successfully</b>", parse_mode="HTML")


@IsAdmin
async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Unbans a user, allowing them to use the bot again
    """
    user_ids = context.args
    
    if not user_ids:
        await update.message.reply_text("Usᴀɢᴇ: /unban (ᴜsᴇʀ_ɪᴅ)")
        return
    
    msg = await update.message.reply_html("<b>Uɴʙᴀɴɴɪɴɢ ᴛʜᴇ ᴜsᴇʀ...</b>")
    
    for user_id in user_ids:
        try:
            # Unban the user in the database
            DB.unblock_user(user_id)
            
            try:
                # Get user information for logging
                user = await context.bot.get_chat(user_id)
                added_users_info = f"""
<b>User:</b> <a href='tg://user?id={user.id}'>{user.first_name}</a>
<b>User ID:</b> {user.id}
"""
                # Log the unban action
                log = f"""
<b>🔓» User Unbanned</b>
{added_users_info}
"""
                await LOG(update, context, log)
            
            except Exception as e:
                # Handle error when getting user info
                added_users_info = f"\nFᴀɪʟᴇᴅ ᴛᴏ ɢᴇᴛ ᴜsᴇʀ ɪɴғᴏ ғᴏʀ: {user_id}. Eʀʀᴏʀ: {str(e)}"
        
        except Exception as e:
            await msg.edit_text(f"Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ ᴡʜɪʟᴇ ᴜɴʙᴀɴɴɪɴɢ ᴛʜᴇ ᴜsᴇʀ: {str(e)}")
            return
    
    await msg.edit_text("<b>🔓 User Unbanned Successfully</b>", parse_mode="HTML")


# Command handler definitions
CHAT_INFO_CMD = CommandHandler(("cid_info", "chat_info"), chat_info)
CHAT_DATA_CMD = CommandHandler(("user_data", "chat_data"), chat_data)
BAN_CMD = CommandHandler(("ban", "block"), ban_user)
UN_BAN_CMD = CommandHandler(("unban", "un_ban", "unblock"), unban_user)
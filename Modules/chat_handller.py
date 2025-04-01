from telegram.constants import ParseMode, ChatAction
from utils.log import logger
from utils.escape import escape
from utils.dataBase.FireDB import DB
import threading
import asyncio
import textwrap
import jsonpickle
import google.generativeai as genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler
)
from utils.decoders_ import restricted, rate_limit
import os
import time
from config import (
    START_SWITCH,
    SYSTEM_INSTRUCTION,
    SAFETY_SETTINGS,
    GENERATION_CONFIG,
    GEMINE_API_KEY,
)

# Global variables
chat_histories = {}
model_lock = threading.Lock()
db_lock = threading.Lock()


google_search_tool = Tool(
    google_search = GoogleSearch()
)

# Configure Gemini AI
genai.configure(api_key=GEMINE_API_KEY)
model = genai.GenerativeModel(
    model_name="models/gemini-1.5-flash",
    safety_settings=SAFETY_SETTINGS,
    generation_config=GENERATION_CONFIG,
    system_instruction=SYSTEM_INSTRUCTION
)

async def send_message(update: Update, message: str, format=True, parse_mode=ParseMode.HTML) -> None:
    """Send a message to the user, handling large messages by splitting them."""
    try:
        async def send_wrap(message_: str):
            chunks = textwrap.wrap(message_, width=3500, break_long_words=False, replace_whitespace=False)
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode=parse_mode)

        if format:
            try:
                html_message = escape(message)
                await send_wrap(html_message)
            except Exception as e:
                logger.warning(f"Can't parse the response error: {e}")
                # Fallback to unformatted message if formatting fails
                await send_wrap(message)
        else:
            logger.warning("Sending unformatted message")
            await send_wrap(message)
    except Exception as e:
        await update.message.reply_text(
            f"♔ Whoops! An error occurred while sending the message: {e}", 
            parse_mode=ParseMode.HTML
        )
        logger.error(f"An error occurred while sending the message: {e}")

def get_chat_history(chat_id):
    """Retrieves chat history for the given chat ID with improved error handling and caching."""
    # Check if chat history exists locally
    if chat_id in chat_histories:
        return chat_histories[chat_id]  # Return existing history

    # If not found locally, try retrieving from cloud
    try:
        userData = DB.user_exists(chat_id)
        if userData:
            instruction = userData.get('system_instruction', SYSTEM_INSTRUCTION)
            
            # Use default instruction if set to 'default'
            if instruction == 'default':
                instruction = SYSTEM_INSTRUCTION
            
            model_temp = genai.GenerativeModel(
                model_name="models/gemini-1.5-flash",
                safety_settings=SAFETY_SETTINGS,
                generation_config=GENERATION_CONFIG,
                system_instruction=instruction
            )
            
            # Safely decode history
            try:
                history = jsonpickle.decode(userData['chat_session'])
                chat_histories[chat_id] = model_temp.start_chat(history=history)
                logger.info(f"Chat id:{chat_id} did not exist locally, got previous data from cloud")
                return chat_histories[chat_id]
            except (ValueError, TypeError, KeyError) as decode_error:
                logger.error(f"Error decoding chat history: {decode_error}. Creating new session.")
                chat_histories[chat_id] = model_temp.start_chat(history=[])
                return chat_histories[chat_id]
        else:
            # User doesn't exist in cloud, create a new one
            DB.create_user(chat_id)
            chat_histories[chat_id] = model.start_chat(history=[])
            logger.info(f"Chat id:{chat_id} did not exist, created one")
            return chat_histories[chat_id]

    except Exception as e:
        # Handle errors during cloud data retrieval
        logger.error(f"Error retrieving chat history for chat_id: {chat_id}, Error: {e}")
        # Return a fresh model as a fallback
        chat_histories[chat_id] = model.start_chat(history=[])
        return chat_histories[chat_id]

def generate_response(chat_id, input_text: str) -> str:
    """Generate a response using Gemini AI with improved error handling."""
    chat_history = get_chat_history(chat_id)
    logger.info(f"Generating response for chat_id: {chat_id}")
    
    try:
        # Try to generate a response
        try:
            with model_lock:  # Prevent concurrent model access issues
                response = chat_history.send_message(input_text)
        except Exception as e:
            logger.error(f"Error occurred while generating response: {e}")
            return f"♔ Error occurred while generating response: {e}"

        # Handle missing text attribute
        if not hasattr(response, "text"):
            return f"♔ *My apologies*, I've reached my usage limit for the moment. ⏳ Please try again in a few minutes.\n\n📡 Response: {response}"

        response_text = response.text
        
        # Update database in background
        def update_db():
            try:
                with db_lock:  # Use a thread-safe lock for Firebase access
                    DB.chat_history_add(chat_id, chat_history.history)
            except Exception as e:
                logger.error(f"Failed to update chat history in database: {e}")
        
        # Launch thread to update database
        thread = threading.Thread(target=update_db)
        thread.daemon = True  # Make thread a daemon so it doesn't block program exit
        thread.start()
        
        return response_text

    except Exception as e:
        logger.error(f"Critical error in generate_response: {e}")
        return f"♔ Sorry, I couldn't generate a response at the moment. Please try again later.\n\n🛑 Error: {e}"

@restricted
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process text messages from users."""
    if not update.message:
        return
        
    try:
        # Check if user is blocked
        user_id = str(update.message.from_user.id)
        if DB.is_user_blocked(user_id):
            logger.info(f"Ignoring command from blocked user {user_id}.")
            return

        chat_id = update.message.chat_id
        user_message = update.message.text.lower() if update.message.text else ""
        
        # Process message if it starts with the switch or is in private chat
        if user_message.startswith(START_SWITCH) or update.message.chat.type == 'private':
            first_name = update.effective_user.first_name
            
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            
            # Generate response
            response = generate_response(chat_id, user_message)
            
            # Send the response
            await send_message(update, message=response, format=True, parse_mode="MarkdownV2")
            
            # Log the interaction
            logger.info(f"Prompt({chat_id}): {user_message}\n\nResponse: {response[:100]}...")
            logger.info(f"{first_name if first_name else 'Someone'}: {user_message}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            await update.message.reply_text(
                f"♔ Sorry, I encountered an error while Processing your message.\n Error: {e}"
            )
        except Exception:
            logger.error("Failed to send error message to user")

async def Check_file_Size(message):
    """Check if a file is within size limits (20MB)."""
    try:
        if not message.photo:
            file_size = message.effective_attachment.file_size  # Size in bytes
            return file_size / (1024 * 1024)  # Convert to MB
        return 0
    except AttributeError:
        logger.warning("Could not determine file size")
        return 0

async def download_media_file(message, context):
    """Download media file with proper error handling."""
    try:
        if message.photo:
            file = await message.effective_attachment[-1].get_file()
        else:
            file = await message.effective_attachment.get_file()
            
        file_path = await file.download_to_drive()
        logger.debug(f"Downloaded file to {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
        raise

async def Genrate_text_via_Media(update, context, file_path, user_message=None):
    """Process media files and generate responses using Gemini AI."""
    if not user_message:
        user_message = "respond to what user send you."

    chat_id = update.message.chat_id
    cleanup_successful = False
    
    try:
        # Upload file to Gemini
        media_file = genai.upload_file(path=file_path)
        logger.debug(f"Uploaded file to Gemini: {media_file}")

        # Wait for Gemini to process the media
        wait_time = 0
        max_wait = 60  # Maximum wait time in seconds
        while media_file.state.name == "PROCESSING" and wait_time < max_wait:
            await asyncio.sleep(5)
            wait_time += 5
            media_file = genai.get_file(media_file.name)

        # Check processing state
        if media_file.state.name == "FAILED":
            await update.message.reply_text("♔ Gemini failed to process this media. Please try a different file.")
            return
        elif media_file.state.name == "PROCESSING":
            await update.message.reply_text("♔ Media is taking too long to process. Please try a smaller or different file.")
            return

        # Show typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        # Generate content using Gemini
        chat_session = get_chat_history(chat_id)
        with model_lock:
            response = chat_session.send_message([media_file, user_message])

        # Update database in background
        def update_db():
            try:
                with db_lock:
                    DB.chat_history_add(chat_id, chat_session.history)
            except Exception as e:
                logger.error(f"Failed to update chat history in database: {e}")
                
        thread = threading.Thread(target=update_db)
        thread.daemon = True
        thread.start()

        # Check and handle the response
        if hasattr(response, "text"):
            await send_message(update, message=response.text, format=True, parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(
                f"<b>My apologies</b>, I've reached my <i>usage limit</i> for the moment. ⏳ Please try again in a few minutes.",
                parse_mode='HTML'
            )
            
        # Try to clean up the file
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                cleanup_successful = True
        except Exception as cleanup_error:
            logger.error(f"Error during file cleanup: {cleanup_error}")
            
    except Exception as e:
        logger.error(f"Error in Genrate_text_via_Media: {e}")
        await update.message.reply_text(f"♔ An error occurred while processing your media: {e}")
        
    finally:
        # Final cleanup attempt if previous cleanup failed
        if not cleanup_successful:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

@restricted
async def media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle media messages (photos, videos, etc.)."""
    try:
        message = update.message
        file_path = None
        
        # Check if message is a reply to bot
        if update.message.reply_to_message:
            reply_to_bot = (
                update.message.reply_to_message.from_user and 
                update.message.reply_to_message.from_user.id == context.bot.id
            )
        else:
            reply_to_bot = False

        # Get caption if available
        user_message = update.message.caption.lower() if update.message.caption else " "
        
        # Process if message meets criteria
        if (
            user_message.startswith(START_SWITCH) or  # Check for start switch command
            update.message.chat.type == 'private' or  # Check for private chat
            reply_to_bot or  # Check for reply to bot
            message.voice or  # Check for voice message
            message.audio  # Check for audio message
        ):
            # Check file size
            media_size = await Check_file_Size(message)
            if media_size >= 20:
                await update.message.reply_text(
                   f"♔ The Media Size ({media_size:.1f} MB) Exceeded the limit of 20Mb."
                   )
                return
                
            # Process the media
            try:
                file_path = await download_media_file(message, context)
                await Genrate_text_via_Media(update, context, file_path, user_message)
            except Exception as e:
                await update.message.reply_text(
                    f"♔ An Error occured while processing: {e}"
                )
            finally:
                # Ensure file cleanup
                try:
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as cleanup_error:
                    logger.error(f"Final cleanup error: {cleanup_error}")
    
    except Exception as e:
        logger.error(f"Error in media_handler: {e}")
        await update.message.reply_text("❀ An unexpected error occurred. Please try again later.")

async def Reply_handller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle replies to messages."""
    file_path = None
    try:
        message = update.effective_message
        chat_id = update.message.chat_id
        
        # Check if this is a text reply that should be processed
        should_process = (
            message.text and 
            (
                message.text.startswith(START_SWITCH) or 
                update.message.chat.type == 'private' or 
                (update.message.reply_to_message and 
                 update.message.reply_to_message.from_user and 
                 update.message.reply_to_message.from_user.id == context.bot.id)
            ) and 
            message.reply_to_message
        )
        
        if should_process:
            original_message = message.reply_to_message
            original_message_text = original_message.text or ""
            
            # Check for media in current message or original message
            reply_has_attachment = message.effective_attachment
            original_has_attachment = original_message.effective_attachment
            
            # Process media in reply
            if reply_has_attachment:
                media_size = await Check_file_Size(message)
                if media_size >= 20:
                    await update.message.reply_text(
                        f"♔ The Media Size ({media_size:.1f} MB) Exceeded the limit of 20Mb."
                    )
                    return
                    
                file_path = await download_media_file(message, context)
                await Genrate_text_via_Media(update, context, file_path, message.text)
            
            # Process media in original message
            elif original_has_attachment:
                media_size = await Check_file_Size(original_message)
                if media_size >= 20:
                    await update.message.reply_text(
                        f"♔ The Media Size ({media_size:.1f} MB) Exceeded the limit of 20Mb."
                    )
                    return
                    
                file_path = await download_media_file(original_message, context)
                user_message = f"Original message: {original_message_text}\nReply to that message: {message.text}"
                await Genrate_text_via_Media(update, context, file_path, user_message)
            
            # Process text-only conversation
            elif original_message_text:
                user_message = f"Original message: {original_message_text}\nReply to that message: {message.text}"
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                response = generate_response(chat_id=chat_id, input_text=user_message)
                await send_message(update, message=response, format=True, parse_mode="MarkdownV2")
                logger.info(f"Reply prompt({chat_id}): {user_message[:100]}...\nResponse: {response[:100]}...")
    
    except Exception as e:
        logger.error(f"Error in Reply_handller: {e}")
        try:
            await update.message.reply_text(f"♔ Sorry I encountered an Error: {e}")
        except Exception:
            logger.error("Could not send error message")
    finally:
        # Ensure file cleanup
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as cleanup_error:
            logger.error(f"Cleanup error in Reply_handller: {cleanup_error}")

@restricted
async def Clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear chat history for a user or group."""
    chat_id = update.message.chat_id
    
    # Check permissions for clearing history
    has_permission = False
    if update.effective_chat.type == "private":
        has_permission = True
    else:
        try:
            chat_admins = await update.effective_chat.get_administrators()
            has_permission = update.effective_user in (admin.user for admin in chat_admins)
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            await update.message.reply_text("♔ Could not verify Admin Privileges. Please try again later.")
            return
    
    if not has_permission:
        await update.message.reply_text("♔ You need to be Group Admin to use this function.")
        return
    
    # Clear history
    try:
        msg = await update.message.reply_text('♔ Clearing Chat history...')
        chat_histories[chat_id] = model.start_chat(history=[])
        DB.chat_history_add(chat_id, [])
        await msg.edit_text("♔ Chat History cleared !")
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        await update.message.reply_text(f"♔ An Error occurred while clearing history: {e}")


@restricted
async def changeprompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    chat_id = update.message.chat_id
    new_promt = " ".join(context.args)
    if update.effective_chat.type == "private":
        pass
           
    else:
        chat_admins = await update.effective_chat.get_administrators()
        if update.effective_user in (admin.user for admin in chat_admins):
            pass
           
        else:
           await update.message.reply_text("♔ You need to be Group Admin to do this function.")
           return 
    
    msg = await update.message.reply_text(f'Changing prompt....')
    if new_promt :
        if  context.args[0].lower() == 'd' or context.args[0].lower() == 'default' or context.args[0].lower() == 'orignal':
        
           chat_histories[chat_id]= model.start_chat(history=[] )
           DB.update_instruction(chat_id)
           await msg.edit_text(f"Tʜᴇ ᴘʀᴏᴍᴘᴛ ʜᴀs ʙᴇᴇɴ 🎉sᴜᴄᴄᴇssғᴜʟʟʏ🎉 ᴄʜᴀɴɢᴇᴅ ᴛᴏ: <b>'ᴅᴇғᴀᴜʟᴛ'</b>", parse_mode='HTML')
        else:
                model_temp = genai.GenerativeModel(
                    model_name="models/gemini-1.5-flash",
                    safety_settings=SAFETY_SETTINGS,
                    generation_config=GENERATION_CONFIG,
                
                    system_instruction=new_promt )
                chat_histories[chat_id] = model_temp.start_chat(history=[])
    
                await msg.edit_text(f"♔ <i>The Prompt has changed to</i>: <b>'{new_promt}'</b>", parse_mode='HTML')
                DB.update_instruction(chat_id,new_promt)
        DB.chat_history_add(chat_id,[])
        
    else:
        await msg.edit_text("♔ Error : please provide me the prompt which you want to give.")


@restricted
@rate_limit
async def Chat_Info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    chat_id = update.message.chat_id
    if update.effective_chat.type == "private":
        pass
    else:
        chat_admins = await update.effective_chat.get_administrators()
        if update.effective_user in (admin.user for admin in chat_admins):
            pass
           
        else:
           await update.message.reply_text("♔ You need to be Group Admin to do this function.")
    msg = await update.message.reply_text(f"♔ Please be patient we are extracting this chat's data....")
    await msg.edit_text(DB.info(chat_id), parse_mode='HTML')

        




clear_history_commamd = CommandHandler(("clear_history","clearhistory","clear"),Clear_history)
changeprompt_command =CommandHandler(("changeprompt","change_prompt","prompt"),changeprompt)
Chat_Info_command =CommandHandler(("info","myinfo","Info"),Chat_Info)
                       
            
        



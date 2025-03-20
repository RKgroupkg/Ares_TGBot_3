"""
Chat Handler Module for Telegram Bot with Gemini Integration.

This module handles message processing, response generation, and media handling
for a Telegram bot powered by Google's Gemini AI model.
"""

import os
import threading
import time
import textwrap
from typing import Optional, Union, List

import jsonpickle
import google.generativeai as genai
from telegram import Update, Message
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode, ChatAction

from utils.log import logger
from utils.escape import escape
from utils.dataBase.FireDB import DB
from utils.decoders_ import restricted, rate_limit
from config import (
    START_SWITCH,
    SYSTEM_INSTRUCTION,
    SAFETY_SETTINGS,
    GENERATION_CONFIG,
    GEMINI_API_KEY,  # Fixed typo in variable name
    MAX_MEDIA_SIZE_MB
)

# Global variables
chat_histories = {}
# Thread-safe lock for database operations
db_lock = threading.Lock()

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)  # Fixed variable name
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    safety_settings=SAFETY_SETTINGS,
    generation_config=GENERATION_CONFIG,
    system_instruction=SYSTEM_INSTRUCTION
)


class ResponseError(Exception):
    """Custom exception for response generation errors."""
    pass


class MediaProcessingError(Exception):
    """Custom exception for media processing errors."""
    pass


@restricted
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Process text messages from users and generate AI responses.
    
    Args:
        update: The Telegram update object containing message data
        context: The Telegram context object
    """
    if not update.message:
        return

    chat_id = update.message.chat_id
    user_id = str(update.message.from_user.id)
    
    # Check if user is blocked
    if DB.is_user_blocked(user_id):
        logger.info(f"Ignoring command from blocked user {user_id}.")
        return

    user_message = update.message.text.lower() if update.message.text else ""
    
    # Check if message should be processed (starts with trigger or in private chat)
    if user_message.startswith(START_SWITCH) or update.message.chat.type == 'private':
        first_name = update.effective_user.first_name
        logger.info(f"Processing message from {first_name or 'Unknown'}: {user_message}")
        
        try:
            # Indicate typing status
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            
            # Generate AI response
            response = generate_response(chat_id, user_message)
            
            # Send the response
            await send_message(update, message=response, format=True, parse_mode="MarkdownV2")
            
            # Log the interaction
            logger.info(f"Prompt({chat_id}): {user_message}\nResponse: {response[:200]}...")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await handle_error(update, f"Error processing message: {e}")


async def send_message(
    update: Update, 
    message: str, 
    format: bool = True, 
    parse_mode: str = ParseMode.HTML
) -> None:
    """
    Send a message to the user, handling formatting and chunking for long messages.
    
    Args:
        update: The Telegram update object
        message: The message text to send
        format: Whether to apply message formatting
        parse_mode: The parse mode to use (HTML or MarkdownV2)
    """
    try:
        async def send_wrap(message_: str) -> None:
            """Split and send long messages in chunks."""
            # Telegram has a limit on message length, so we split into chunks
            chunks = textwrap.wrap(
                message_, 
                width=3500, 
                break_long_words=False, 
                replace_whitespace=False
            )
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode=parse_mode)

        if format:
            try:
                formatted_message = escape(message)
                await send_wrap(formatted_message)
            except Exception as e:
                logger.warning(f"Cannot parse the response: {e}")
                # Fallback to unformatted message
                await send_wrap(message)
        else:
            logger.debug("Sending unformatted message")
            await send_wrap(message)
            
    except Exception as e:
        error_msg = f"Error while sending message: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await update.message.reply_text(
            f"ᴡᴏᴏᴘs! ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {str(e)}", 
            parse_mode=ParseMode.HTML
        )


def get_chat_history(chat_id: Union[int, str]) -> genai.ChatSession:
    """
    Retrieve chat history for a specific chat ID, or create a new one if it doesn't exist.
    
    Args:
        chat_id: The unique identifier of the chat
        
    Returns:
        A Gemini chat session with history
    """
    chat_id_str = str(chat_id)
    
    # Check if history exists in memory
    if chat_id_str in chat_histories:
        return chat_histories[chat_id_str]
    
    # Try retrieving from database
    try:
        user_data = DB.user_exists(chat_id_str)
        
        if user_data:
            # User exists in database
            instruction = user_data.get('system_instruction')
            
            # Use default if not specified or marked as default
            if not instruction or instruction == 'default':
                instruction = SYSTEM_INSTRUCTION
            
            # Create a customized model instance
            custom_model = genai.GenerativeModel(
                model_name="gemini-1.5-pro-latest",
                safety_settings=SAFETY_SETTINGS,
                generation_config=GENERATION_CONFIG,
                system_instruction=instruction
            )
            
            # Decode the stored history
            history = jsonpickle.decode(user_data['chat_session'])
            
            # Create a new chat session with the loaded history
            chat_histories[chat_id_str] = custom_model.start_chat(history=history)
            logger.info(f"Retrieved existing chat history for chat_id: {chat_id_str}")
            
        else:
            # New user, create entry in database
            DB.create_user(chat_id_str)
            chat_histories[chat_id_str] = model.start_chat(history=[])
            logger.info(f"Created new chat history for chat_id: {chat_id_str}")
            
        return chat_histories[chat_id_str]
        
    except Exception as e:
        logger.error(f"Error retrieving chat history for {chat_id_str}: {e}", exc_info=True)
        # Fallback to a new session if database retrieval fails
        chat_histories[chat_id_str] = model.start_chat(history=[])
        return chat_histories[chat_id_str]


def generate_response(chat_id: Union[int, str], input_text: str) -> str:
    """
    Generate a response from the AI model based on the chat history and input text.
    
    Args:
        chat_id: The chat ID to retrieve history for
        input_text: The user's input text
        
    Returns:
        The generated response text
    """
    try:
        # Get or create the chat session
        chat_session = get_chat_history(chat_id)
        logger.debug(f"Generating response for chat_id {chat_id}")
        
        try:
            # Send the message to Gemini
            response = chat_session.send_message(input_text)
            
            # Check if response has text attribute
            if not hasattr(response, "text"):
                return "⚠️ I've reached my usage limit for the moment. Please try again in a few minutes."
            
            response_text = response.text
            
            # Asynchronously update the database with new chat history
            def update_history() -> None:
                try:
                    with db_lock:
                        DB.chat_history_add(chat_id, chat_session.history)
                except Exception as e:
                    logger.error(f"Failed to update chat history in database: {e}", exc_info=True)
            
            # Start a thread to update the database without blocking
            threading.Thread(target=update_history, daemon=True).start()
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return f"🔧 Eʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ɢᴇɴᴇʀᴀᴛɪɴɢ ʀᴇsᴘᴏɴsᴇ: {str(e)}"
            
    except Exception as e:
        logger.error(f"Fatal error in generate_response: {e}", exc_info=True)
        return f"🛑 Sᴏʀʀʏ, I ᴄᴏᴜʟᴅɴ'ᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʀᴇsᴘᴏɴsᴇ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ."


@restricted
async def reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle media messages (photos, videos, audio, etc.) from users.
    
    Args:
        update: The Telegram update object
        context: The Telegram context object
    """
    if not update.message:
        return
        
    message = update.message
    chat_id = message.chat_id
    user_id = str(message.from_user.id)
    
    # Check if user is blocked
    if DB.is_user_blocked(user_id):
        logger.info(f"Ignoring media from blocked user {user_id}.")
        return
    
    # Determine if bot should process this media
    reply_to_bot = (
        message.reply_to_message and 
        message.reply_to_message.from_user.id == context.bot.id
    )
    
    # Get caption if any
    user_message = message.caption.lower() if message.caption else ""
    
    # Process media if conditions are met
    if (
        user_message.startswith(START_SWITCH) or
        message.chat.type == 'private' or
        reply_to_bot or
        message.voice or
        message.audio
    ):
        try:
            # Check media size
            media_size_mb = await check_file_size(message)
            max_size = MAX_MEDIA_SIZE_MB if 'MAX_MEDIA_SIZE_MB' in globals() else 20
            
            if media_size_mb >= max_size:
                await message.reply_text(
                    f"⚠️ The media size ({media_size_mb:.1f} MB) exceeds the limit of {max_size} MB. "
                    "Please send a smaller file."
                )
                return
                
            # Process the media
            await download_and_process_media(update, context)
            
        except Exception as e:
            logger.error(f"Error handling media: {e}", exc_info=True)
            await handle_error(update, f"Error processing media: {e}")


async def download_and_process_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Download and process media files for Gemini analysis.
    
    Args:
        update: The Telegram update object
        context: The Telegram context object
    """
    file_path = None
    
    try:
        # Get chat ID and message text
        chat_id = update.message.chat_id
        
        # Get caption or default message
        if hasattr(update.message, "caption") and update.message.caption:
            user_message = update.message.caption
        else:
            user_message = "Please analyze this media and respond accordingly."
        
        # Get the file based on media type
        if update.message.photo:
            # For photos, get the highest quality version (last in the list)
            file = await update.message.effective_attachment[-1].get_file()
        else:
            # For other media types
            file = await update.message.effective_attachment.get_file()
        
        # Show "processing" status to user
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
        
        # Download the file
        file_path = await file.download_to_drive()
        logger.debug(f"Downloaded media file to {file_path}")
        
        # Process with Gemini
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await generate_text_via_media(update, context, file_path, user_message)
        
    except Exception as e:
        logger.error(f"Error processing media: {e}", exc_info=True)
        await handle_error(update, f"Error processing media: {e}")
        
    finally:
        # Clean up downloaded file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to clean up file {file_path}: {e}", exc_info=True)


async def generate_text_via_media(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    file_path: str, 
    user_message: Optional[str] = None
) -> None:
    """
    Generate a response from Gemini based on media and optional text.
    
    Args:
        update: The Telegram update object
        context: The Telegram context object
        file_path: Path to the downloaded media file
        user_message: Optional text message to accompany the media
    """
    chat_id = update.message.chat_id
    
    # Default message if none provided
    if not user_message:
        user_message = "Please analyze this media and respond accordingly."
    
    try:
        # Upload file to Gemini
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        media_file = genai.upload_file(path=file_path)
        logger.debug(f"Uploaded file to Gemini: {media_file.name}")
        
        # Wait for Gemini to process the file
        max_retries = 12  # 2 minutes max wait time
        retries = 0
        
        while media_file.state.name == "PROCESSING" and retries < max_retries:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            time.sleep(10)  # Wait 10 seconds
            media_file = genai.get_file(media_file.name)
            retries += 1
        
        # Check if processing failed
        if media_file.state.name == "FAILED":
            raise MediaProcessingError("Gemini failed to process the media file.")
        
        # Check if still processing after timeout
        if media_file.state.name == "PROCESSING":
            raise MediaProcessingError("Gemini is taking too long to process the media. Please try again later.")
        
        # Generate content
        chat_session = get_chat_history(chat_id)
        logger.info(f"Generating Gemini response for media file: {media_file.name}")
        
        response = chat_session.send_message([media_file, user_message])
        
        # Update chat history in database
        with db_lock:
            DB.chat_history_add(chat_id, chat_session.history)
        
        # Send response
        if hasattr(response, "text"):
            await send_message(update, message=response.text, format=True, parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(
                "⚠️ I've reached my usage limit for the moment. Please try again later.",
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        logger.error(f"Error generating response from media: {e}", exc_info=True)
        await handle_error(update, f"Error generating response from media: {e}")


async def check_file_size(message: Message) -> float:
    """
    Check the size of a media file in MB.
    
    Args:
        message: The Telegram message containing media
        
    Returns:
        The file size in megabytes
    """
    if not message.photo and hasattr(message, "effective_attachment"):
        if hasattr(message.effective_attachment, "file_size"):
            file_size = message.effective_attachment.file_size
            return file_size / (1024 * 1024)  # Convert bytes to MB
    
    # Photos and some other media types might not have file_size directly accessible
    return 0


async def reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle reply messages specifically, including replies to media.
    
    Args:
        update: The Telegram update object
        context: The Telegram context object
    """
    if not update.message:
        return
        
    message = update.effective_message
    chat_id = update.message.chat_id
    file_path = None
    
    # Check if this is a reply the bot should process
    should_process = (
        message.text and 
        (
            message.text.startswith(START_SWITCH) or 
            update.message.chat.type == 'private' or 
            (message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id)
        ) and 
        message.reply_to_message
    )
    
    if not should_process:
        return
    
    try:
        # Get the original message that was replied to
        original_message = message.reply_to_message
        original_text = original_message.text or ""
        
        # Check if either message has attachments
        reply_has_attachment = message.effective_attachment is not None
        original_has_attachment = original_message.effective_attachment is not None
        
        # Handle case: reply has an attachment
        if reply_has_attachment:
            # Check attachment size
            media_size_mb = await check_file_size(message)
            max_size = MAX_MEDIA_SIZE_MB if 'MAX_MEDIA_SIZE_MB' in globals() else 20
            
            if media_size_mb >= max_size:
                await message.reply_text(
                    f"⚠️ The media size ({media_size_mb:.1f} MB) exceeds the limit of {max_size} MB. "
                    "Please send a smaller file."
                )
                return
                
            # Download the attachment
            if message.photo:
                file = await message.effective_attachment[-1].get_file()
            else:
                file = await message.effective_attachment.get_file()
                
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
            file_path = await file.download_to_drive()
            
            # Process with message text
            await generate_text_via_media(update, context, file_path, message.text)
            
        # Handle case: original message has an attachment
        elif original_has_attachment:
            # Check attachment size
            media_size_mb = await check_file_size(original_message)
            max_size = MAX_MEDIA_SIZE_MB if 'MAX_MEDIA_SIZE_MB' in globals() else 20
            
            if media_size_mb >= max_size:
                await message.reply_text(
                    f"⚠️ The media size ({media_size_mb:.1f} MB) exceeds the limit of {max_size} MB. "
                    "Please send a smaller file."
                )
                return
                
            # Download the attachment
            if original_message.photo:
                file = await original_message.effective_attachment[-1].get_file()
            else:
                file = await original_message.effective_attachment.get_file()
                
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
            file_path = await file.download_to_drive()
            
            # Create context-aware prompt that includes both messages
            combined_message = (
                f"Original message: {original_text}\n"
                f"Reply to that message: {message.text}"
            )
            
            # Process with combined context
            await generate_text_via_media(update, context, file_path, combined_message)
            
        # Handle case: text-only conversation
        elif original_text:
            # Create context-aware prompt
            combined_message = (
                f"Original message: {original_text}\n"
                f"Reply to that message: {message.text}"
            )
            
            # Generate response
            response = generate_response(chat_id, combined_message)
            
            # Send response
            await send_message(update, message=response, format=True, parse_mode="MarkdownV2")
            logger.info(f"Reply prompt({chat_id}): {combined_message}\nResponse: {response[:200]}...")
            
    except Exception as e:
        logger.error(f"Error processing reply: {e}", exc_info=True)
        await handle_error(update, f"Error processing reply: {e}")
        
    finally:
        # Clean up downloaded file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Failed to clean up file {file_path}: {e}", exc_info=True)


@restricted
async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Clear chat history for a specific chat.
    
    Args:
        update: The Telegram update object
        context: The Telegram context object
    """
    chat_id = update.message.chat_id
    
    # Check permissions
    is_authorized = (
        update.effective_chat.type == "private" or
        update.effective_user.id in [
            admin.user.id for admin in await update.effective_chat.get_administrators()
        ]
    )
    
    if not is_authorized:
        await update.message.reply_text(
            "You need to be a group/chat admin to use this command."
        )
        return
    
    try:
        # Send initial message
        msg = await update.message.reply_text('Clearing chat history...')
        
        # Clear history in memory
        chat_histories[str(chat_id)] = model.start_chat(history=[])
        
        # Clear history in database
        with db_lock:
            DB.chat_history_add(chat_id, [])
        
        # Confirm success
        await msg.edit_text("✅ Chat history successfully cleared!")
        logger.info(f"Cleared chat history for chat_id: {chat_id}")
        
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}", exc_info=True)
        await handle_error(update, f"Error clearing chat history: {e}")


@restricted
async def change_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Change the system prompt used for a specific chat.
    
    Args:
        update: The Telegram update object
        context: The Telegram context object
    """
    chat_id = str(update.message.chat_id)
    
    # Check permissions
    is_authorized = (
        update.effective_chat.type == "private" or
        update.effective_user.id in [
            admin.user.id for admin in await update.effective_chat.get_administrators()
        ]
    )
    
    if not is_authorized:
        await update.message.reply_text(
            "You need to be a group/chat admin to use this command."
        )
        return
    
    # Get new prompt from arguments
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "Please provide a new prompt or use 'default' to reset to the default prompt."
        )
        return
    
    try:
        # Send initial message
        msg = await update.message.reply_text('Changing prompt...')
        
        # Check if resetting to default
        if args[0].lower() in ['d', 'default', 'original']:
            # Reset to default prompt
            chat_histories[chat_id] = model.start_chat(history=[])
            
            # Update database
            with db_lock:
                DB.update_instruction(chat_id)
                DB.chat_history_add(chat_id, [])
            
            await msg.edit_text(
                "✅ The prompt has been successfully changed to the default.",
                parse_mode=ParseMode.HTML
            )
            
        else:
            # Set custom prompt
            new_prompt = " ".join(args)
            
            # Create new model with custom prompt
            custom_model = genai.GenerativeModel(
                model_name="gemini-1.5-pro-latest",
                safety_settings=SAFETY_SETTINGS,
                generation_config=GENERATION_CONFIG,
                system_instruction=new_prompt
            )
            
            # Update chat history
            chat_histories[chat_id] = custom_model.start_chat(history=[])
            
            # Update database
            with db_lock:
                DB.update_instruction(chat_id, new_prompt)
                DB.chat_history_add(chat_id, [])
            
            await msg.edit_text(
                f"✅ The prompt has been successfully changed to: <b>'{new_prompt}'</b>",
                parse_mode=ParseMode.HTML
            )
            
        logger.info(f"Changed prompt for chat_id: {chat_id}")
        
    except Exception as e:
        logger.error(f"Error changing prompt: {e}", exc_info=True)
        await handle_error(update, f"Error changing prompt: {e}")


@restricted
@rate_limit
async def chat_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Display information about the current chat.
    
    Args:
        update: The Telegram update object
        context: The Telegram context object
    """
    chat_id = update.message.chat_id
    
    # Check permissions in group chats
    if update.effective_chat.type != "private":
        is_admin = update.effective_user.id in [
            admin.user.id for admin in await update.effective_chat.get_administrators()
        ]
        
        if not is_admin:
            await update.message.reply_text(
                "You need to be a group/chat admin to use this command."
            )
            return
    
    try:
        # Send initial message
        msg = await update.message.reply_text("Retrieving chat information...")
        
        # Fetch chat info from database
        chat_info_text = DB.info(chat_id)
        
        # Display info
        await msg.edit_text(chat_info_text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error retrieving chat info: {e}", exc_info=True)
        await handle_error(update, f"Error retrieving chat info: {e}")


async def handle_error(update: Update, error_message: str) -> None:
    """
    Handle errors consistently throughout the application.
    
    Args:
        update: The Telegram update object
        error_message: The error message to display
    """
    try:
        await update.message.reply_text(
            f"⚠️ {error_message}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Failed to send error message: {e}", exc_info=True)


# Define command handlers
clear_history_command = CommandHandler(
    ["clear_history", "clearhistory", "clear"],
    clear_history
)

change_prompt_command = CommandHandler(
    ["changeprompt", "change_prompt", "prompt"],
    change_prompt
)

chat_info_command = CommandHandler(
    ["info", "myinfo", "Info"],
    chat_info
)
from telegram.constants import (
  ParseMode,
  ChatAction
  )
from utils.log import logger
from utils.escape import escape
from utils.dataBase.FireDB import DB
import threading
from utils.decoders_ import restricted
import textwrap
import jsonpickle
import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler
)
from utils.decoders_ import rate_limit


import os 
import time
from config import (
    START_SWITCH,
    SYSTEM_INSTRUCTION,
    SAFETY_SETTINGS,
    GENERATION_CONFIG,
    GEMINE_API_KEY,


)




chat_histories ={}


genai.configure(api_key=GEMINE_API_KEY)
model = genai.GenerativeModel(
  model_name="gemini-1.5-pro-latest",
  safety_settings=SAFETY_SETTINGS,
  generation_config=GENERATION_CONFIG,
  tools='code_execution',
  system_instruction= SYSTEM_INSTRUCTION)


@restricted
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not update.message:
            return
        if DB.is_user_blocked(str(update.message.from_user.id)):
            logger.info(f"Ignoring command from blocked user {str(update.message.from_user.id)}.")
            return

        chat_id = update.message.chat_id
        user_message = update.message.text.lower()
        if user_message.startswith(START_SWITCH) or update.message.chat.type == 'private':
            first_name = update.effective_user.first_name
            
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            # Generate the response
            response = generate_response(chat_id,user_message)
                
        
            # Code that might raise the AttributeError (e.g., accessing the 'text' attribute of a variable)
            await send_message(update,message = response,format = True,parse_mode ="MarkdownV2") 
            logger.info(f"Prompt({chat_id}): {user_message}\n\n\nResponse: \n{response}")

            if first_name:
                logger.info(f"{first_name}: {user_message}")
            else:
                logger.info(f"Someone: {user_message}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            await update.message.reply_text(f"Sᴏʀʀʏ, I ᴇɴᴄᴏᴜɴᴛᴇʀᴇᴅ ᴀɴ ᴇʀʀᴏʀ ᴡʜɪʟᴇ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ.\n ᴇʀʀᴏʀ:{e}")
        except Exception:  # If the  message couldn't be send
            logger.error("Error cant send the message")


async def send_message(update: Update,message: str,format = True,parse_mode = ParseMode.HTML) -> None:
    try:

        async def send_wrap(message_ :str):
            chunks = textwrap.wrap(message_, width=3500, break_long_words=False, replace_whitespace=False)
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode= parse_mode)



        if format:
            try:
                html_message = escape(message)
                await send_wrap(html_message)
                
            except Exception as e:
                logger.warning(f"cant parse the response error:{e}")
        else:
            logger.warning("sending unformated message")
            await send_wrap(message)
    except Exception as e:
        
        await update.message.reply_text(f"ᴡᴏᴏᴘs! ᴀɴ Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ sᴇɴᴅɪɴɢ ᴛʜᴇ ᴍᴇssᴀɢᴇ: {e}", parse_mode=ParseMode.HTML)
        logger.error(f"An error occurred while sending the message:{e}")

def get_chat_history(chat_id):
    """Retrieves chat history for the given chat ID.

    Args:
        chat_id (int): The unique identifier of the chat.

    Returns:
        GenerativeModel: The Generative AI model instance with chat history.

    Raises:
        RuntimeError: If there's an error retrieving data from the cloud.
    """
    # Check if chat history exists locally
    if chat_id in chat_histories:
        return chat_histories[chat_id]  # Return existing history

    # If not found locally, try retrieving from cloud
    try:
        userData = DB.user_exists(chat_id)
        if userData:
            instruction = userData['system_instruction']

            if instruction =='default':
                instruction =  SYSTEM_INSTRUCTION,
            
            
            model_temp = genai.GenerativeModel(
                model_name="gemini-1.5-pro-latest",
                safety_settings=SAFETY_SETTINGS,
                generation_config=GENERATION_CONFIG,
                tools='code_execution',
                system_instruction=instruction
            )
            history=jsonpickle.decode(userData['chat_session'])   # decode history and then store

            chat_histories[chat_id] = model_temp.start_chat(history=history )
            logger.info(f"Chat id:{chat_id} did not exist locally, got previous data from cloud")
            return chat_histories[chat_id]  # Return retrieved history
        else:
            # User doesn't exist in cloud, create a new one
            DB.create_user(chat_id)
            chat_histories[chat_id] = model.start_chat(history=[] )
            logger.info(f"Chat id:{chat_id} did not exist, created one")
            return chat_histories[chat_id]  # Return new model

    except Exception as e:
        # Handle errors during cloud data retrieval
        logger.error(f"Error retrieving chat history for chat_id: {chat_id}, Error: {e}")

     
                
def generate_response(chat_id, input_text: str) -> str:
    chat_history = get_chat_history(chat_id)
    logger.info("Generating response...")
    try:
        try:
            response = chat_history.send_message(input_text)
        except Exception as e:
            logger.error(f"Error occured while genrating response: {e}")
            response= f"Eʀʀᴏʀ🔧 ᴏᴄᴄᴜʀᴇᴅ ᴡʜɪʟᴇ ɢᴇɴʀᴀᴛɪɴɢ ʀᴇsᴘᴏɴsᴇ: {e}"
        
        if not hasattr(response, "text"):
          response = f"*𝑀𝑦 𝑎𝑝𝑜𝑙𝑜𝑔𝑖𝑒𝑠*, I'ᴠᴇ ʀᴇᴀᴄʜᴇᴅ ᴍʏ ᴜsᴀɢᴇ ʟɪᴍɪᴛ ғᴏʀ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ. ⏳ Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ɪɴ ᴀ ғᴇᴡ ᴍɪɴᴜᴛᴇs. \n\n 📡Rᴇsᴘᴏɴsᴇ: {response}"
        
        else:
          response = response.text
            
        def update():
            try:
                with lock:  # Use a thread-safe lock for Firebase access
                    DB.chat_history_add(chat_id, chat_history.history)
                return response if input_text else "error"
            except Exception as e:
                logger.error(f"Sorry, I couldn't generate a response at the moment. Please try again later.\n\nError: {e}")
                return f"Sᴏʀʀʏ, I ᴄᴏᴜʟᴅɴ'ᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʀᴇsᴘᴏɴsᴇ ᴀᴛ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.\n\n🛑Eʀʀᴏʀ: {e}"

        # Create a lock to ensure only one thread updates Firebase at a time
        lock = threading.Lock()

        # Create a thread to update Firebase asynchronously in the background
        thread = threading.Thread(target=update)
        thread.start()
        return response

    except Exception as e:
            logger.error(f"Sorry, I couldn't generate a response at the moment. Please try again later.\n\nError: {e}")
            return f"Sᴏʀʀʏ, I ᴄᴏᴜʟᴅɴ'ᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʀᴇsᴘᴏɴsᴇ ᴀᴛ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.\n\n🛑Eʀʀᴏʀ: {e}"


@restricted
async def media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        
        message = update.message
        if update.message.reply_to_message:
            reply_to_bot = (
                update.message.reply_to_message
                and update.message.reply_to_message.from_user.id == context.bot.id )
        else:
            reply_to_bot = False

        if update.message.caption:
            user_message = update.message.caption.lower()
        else:
            user_message = " "
        print(update.message.chat.type)
        if (
            user_message.startswith(START_SWITCH) or  # Check for start switch command
            update.message.chat.type == 'private' or  # Check for private chat
            reply_to_bot or  # Check for reply to bot
            message.voice or  # Check for voice message 
            message.audio
        ): 
            Media_size = await Check_file_Size(message)
            if Media_size >= 20: 
                await update.message.reply_text(f"Tʜᴇ ᴍᴇᴅɪᴀ sɪᴢᴇ ({Media_size} MB) ᴇxᴄᴇᴇᴅs ᴛʜᴇ ʟɪᴍɪᴛ ᴏғ 20 MB. Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ sᴍᴀʟʟᴇʀ ᴍᴇᴅɪᴀ.")
                    
            try:
                await download_and_process_video(update, context)
            except Exception as e:
                # Handle errors during downloading
                await update.message.reply_text("Aɴ 🚫ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴛʜᴇ ᴍᴇᴅɪᴀ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.")
            


async def download_and_process_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Download the video file
        chat_id = update.message.chat_id
        if hasattr(update.message, "caption"):
            user_message = update.message.caption if update.message.caption else "respond to what user sended you.."
        else:
            user_message ="respond to what user sended you.."

        if update.message.photo:
            file = await update.message.effective_attachment[-1].get_file()
        else:
            file = await update.message.effective_attachment.get_file()

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
        file_path = await file.download_to_drive()
        
        
        logger.debug(f"Downloaded file to {file_path}")
        # Upload the video file to Gemini

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await Genrate_text_via_Media(update,context,file_path,user_message)


    except Exception as e:
        # Handle errors during the process
        await update.message.reply_text(f"Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {e}")

    finally:
        try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                else:
                    await update.message.reply_text(f"Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴄʟᴇᴀɴɪɴɢ ᴜᴘ:ғɪʟᴇ_ᴘᴀᴛʜ {file_path} ᴅɪᴅ ɴᴏᴛ ᴇxɪsᴛᴇᴅ ")

        except Exception as e:
            # Handle errors during cleanup
            await update.message.reply_text(f"An error occurred while cleaning up: {e}")

async def Genrate_text_via_Media(update: Update, context: ContextTypes.DEFAULT_TYPE,file_path: str,user_message=None):
        if not user_message:
            user_message= "respond to what user send you ."

        chat_id = update.message.chat_id
        media_file = genai.upload_file(path=file_path)
        logger.debug(f"Uploaded file to Gemini: {media_file}")

        # Wait for Gemini to finish processing the video
        while media_file.state.name == "PROCESSING":
            time.sleep(10)
            media_file = genai.get_file(media_file.name)

        # Check if Gemini failed to process the video
        if media_file.state.name == "FAILED":
            raise ValueError("Gemini failed to process the media_file.")

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)



        # Generate content using Gemini
        chat_session = get_chat_history(chat_id)
        logger.info(f"genrating response by Gemini on media... media {media_file}")
        response = chat_session.send_message([media_file , user_message])

        # Check and handle the response from Gemini
        if hasattr(response, "text"):
            await send_message(update,message = response.text,format = True,parse_mode ="MarkdownV2") 
        else:
            await update.message.reply_text(
                    f"<b>𝑀𝑦 𝑎𝑝𝑜𝑙𝑜𝑔𝑖𝑒𝑠</b>, I've reached my <i>usage limit</i> for the moment. ⏳ Please try again in a few minutes. \n\n<i>Response :</i> {response}",
                    parse_mode='HTML'
                )


async def Check_file_Size(message):
    if not message.photo:
                file_size = message.effective_attachment.file_size  # Size of the audio file in bytes
                

               
                return file_size / (1024 * 1024)
    return 0
                    


async def Reply_handller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = update.effective_message
        chat_id = update.message.chat_id
        file_path = None
        if message.text and (message.text.startswith(START_SWITCH) or update.message.chat.type == 'private' or update.message.reply_to_message.from_user.id == context.bot.id ) and message.reply_to_message:
            original_message = message.reply_to_message
            
            original_message_ = original_message.text

            reply_has_attachment =  message.effective_attachment
            original_has_attachment = original_message.effective_attachment
            
            if reply_has_attachment:
                Media_size = await Check_file_Size(message)
                if Media_size >= 20: 
                    await update.message.reply_text(f"Tʜᴇ ᴍᴇᴅɪᴀ sɪᴢᴇ ({Media_size} MB) ᴇxᴄᴇᴇᴅs ᴛʜᴇ ʟɪᴍɪᴛ ᴏғ 20 MB. Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ sᴍᴀʟʟᴇʀ ᴍᴇᴅɪᴀ.")
                    return
                if message.photo:
                    file = await update.message.effective_attachment[-1].get_file()
                else:
                    file = await update.message.effective_attachment.get_file()
                    
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
                file_path = await file.download_to_drive()
                logger.debug(f"Downloaded file to {file_path}")
                await Genrate_text_via_Media(update,context,file_path,message.text)
            
            elif original_has_attachment:
                Media_size = await Check_file_Size(original_message)
                if Media_size >= 20: 
                    await update.message.reply_text(f"Tʜᴇ ᴍᴇᴅɪᴀ sɪᴢᴇ ({Media_size} MB) ᴇxᴄᴇᴇᴅs ᴛʜᴇ ʟɪᴍɪᴛ ᴏғ 20 MB. Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ sᴍᴀʟʟᴇʀ ᴍᴇᴅɪᴀ.")
                    return
                if original_message.photo:
                    file = await original_message.effective_attachment[-1].get_file()
                else:
                    file = await original_message.effective_attachment.get_file()

                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
                file_path = await file.download_to_drive()
                logger.debug(f"Downloaded file to {file_path}")
                user_message = f"Original message: {original_message_}\nReply to that message: {message.text}"
                await Genrate_text_via_Media(update,context,file_path,user_message)
            
            elif original_message_:
                user_message = f"Original message: {original_message_}\nReply to that message: {message.text}"
                response = generate_response(chat_id=chat_id,input_text=user_message)
                # Code that might raise the AttributeError (e.g., accessing the 'text' attribute of a variable)
                await send_message(update,message = response,format = True,parse_mode ="MarkdownV2") 
                logger.info(f"Prompt({chat_id}): {user_message}\n\n\nResponse: \n{response}")
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            await update.message.reply_text(f"Sᴏʀʀʏ, I ᴇɴᴄᴏᴜɴᴛᴇʀᴇᴅ ᴀɴ ᴇʀʀᴏʀ ᴡʜɪʟᴇ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ.\n ᴇʀʀᴏʀ:{e}")
        except Exception:  # If the original message couldn't be edited
            logger.error("Error cant send the message")
    finally:
        try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                
        except Exception as e:
            # Handle errors during cleanup
            await update.message.reply_text(f"An error occurred while cleaning up: {e}")

@restricted
async def Clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    chat_id = update.message.chat_id
    if update.effective_chat.type == "private":
        msg = await update.message.reply_text(f'Clearing chat history....')
        chat_histories[chat_id] = model.start_chat(history=[])
        DB.chat_history_add(chat_id,[])
        await msg.edit_text("history successful cleared!🥳🥳")
    else:
        chat_admins = await update.effective_chat.get_administrators()
        if update.effective_user in (admin.user for admin in chat_admins):
            msg = await update.message.reply_text(f'Clearing chat history....')
            chat_histories[chat_id] = model.start_chat(history=[])
            DB.chat_history_add(chat_id,[])
            await msg.edit_text("history successful cleared!🥳🥳")
    
           
        else:
           await update.message.reply_text(" You need to be group/chat admin to do this function.")


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
           await update.message.reply_text(" You need to be group/chat admin to do this function.")
           return 
    
    msg = await update.message.reply_text(f'Changing prompt....')
    if new_promt :
        if  context.args[0].lower() == 'd' or context.args[0].lower() == 'default' or context.args[0].lower() == 'orignal':
        
           chat_histories[chat_id]= model.start_chat(history=[] )
           DB.update_instruction(chat_id)
           await msg.edit_text(f"Tʜᴇ ᴘʀᴏᴍᴘᴛ ʜᴀs ʙᴇᴇɴ 🎉sᴜᴄᴄᴇssғᴜʟʟʏ🎉 ᴄʜᴀɴɢᴇᴅ ᴛᴏ: <b>'ᴅᴇғᴀᴜʟᴛ'</b>", parse_mode='HTML')
        else:
                model_temp = genai.GenerativeModel(
                    model_name="gemini-1.5-pro-latest",
                    safety_settings=SAFETY_SETTINGS,
                    generation_config=GENERATION_CONFIG,
                    tools='code_execution',
                    system_instruction=new_promt )
                chat_histories[chat_id] = model_temp.start_chat(history=[])
    
                await msg.edit_text(f"Tʜᴇ ᴘʀᴏᴍᴘᴛ ʜᴀs ʙᴇᴇɴ 🎉sᴜᴄᴄᴇssғᴜʟʟʏ🎉 ᴄʜᴀɴɢᴇᴅ ᴛᴏ: <b>'{new_promt}'</b>", parse_mode='HTML')
                DB.update_instruction(chat_id,new_promt)
        DB.chat_history_add(chat_id,[])
        
    else:
        await msg.edit_text("Error : please provide me the prompt which you want to give.")


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
           await update.message.reply_text(" You need to be group/chat admin to do this function.")
    msg = await update.message.reply_text(f"Please be patient we are extracting this chat's data....")
    await msg.edit_text(DB.info(chat_id), parse_mode='HTML')

        




clear_history_commamd = CommandHandler(("clear_history","clearhistory","clear"),Clear_history)
changeprompt_command =CommandHandler(("changeprompt","change_prompt","prompt"),changeprompt)
Chat_Info_command =CommandHandler(("info","myinfo","Info"),Chat_Info)
           from telegram.constants import ParseMode,ChatAction

from utils.log import logger

from utils.escape import escape
from utils.dataBase.FireDB import DB
import threading
from utils.decoders_ import restricted
import textwrap
import jsonpickle
import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler
)
from utils.decoders_ import rate_limit


import os 
import time
from config import (
    START_SWITCH,
    SYSTEM_INSTRUCTION,
    SAFETY_SETTINGS,
    GENERATION_CONFIG,
    GEMINE_API_KEY,


)




chat_histories ={}


genai.configure(api_key=GEMINE_API_KEY)
model = genai.GenerativeModel(
  model_name="gemini-1.5-pro-latest",
  safety_settings=SAFETY_SETTINGS,
  generation_config=GENERATION_CONFIG,
  tools='code_execution',
  system_instruction= SYSTEM_INSTRUCTION)


@restricted
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not update.message:
            return
        if DB.is_user_blocked(str(update.message.from_user.id)):
            logger.info(f"Ignoring command from blocked user {str(update.message.from_user.id)}.")
            return

        chat_id = update.message.chat_id
        user_message = update.message.text.lower()
        if user_message.startswith(START_SWITCH) or update.message.chat.type == 'private':
            first_name = update.effective_user.first_name
            
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            # Generate the response
            response = generate_response(chat_id,user_message)
                
        
            # Code that might raise the AttributeError (e.g., accessing the 'text' attribute of a variable)
            await send_message(update,message = response,format = True,parse_mode ="MarkdownV2") 
            logger.info(f"Prompt({chat_id}): {user_message}\n\n\nResponse: \n{response}")

            if first_name:
                logger.info(f"{first_name}: {user_message}")
            else:
                logger.info(f"Someone: {user_message}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            await update.message.reply_text(f"Sᴏʀʀʏ, I ᴇɴᴄᴏᴜɴᴛᴇʀᴇᴅ ᴀɴ ᴇʀʀᴏʀ ᴡʜɪʟᴇ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ.\n ᴇʀʀᴏʀ:{e}")
        except Exception:  # If the  message couldn't be send
            logger.error("Error cant send the message")


async def send_message(update: Update,message: str,format = True,parse_mode = ParseMode.HTML) -> None:
    try:

        async def send_wrap(message_ :str):
            chunks = textwrap.wrap(message_, width=3500, break_long_words=False, replace_whitespace=False)
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode= parse_mode)



        if format:
            try:
                html_message = escape(message)
                await send_wrap(html_message)
                
            except Exception as e:
                logger.warning(f"cant parse the response error:{e}")
        else:
            logger.warning("sending unformated message")
            await send_wrap(message)
    except Exception as e:
        
        await update.message.reply_text(f"ᴡᴏᴏᴘs! ᴀɴ Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ sᴇɴᴅɪɴɢ ᴛʜᴇ ᴍᴇssᴀɢᴇ: {e}", parse_mode=ParseMode.HTML)
        logger.error(f"An error occurred while sending the message:{e}")

def get_chat_history(chat_id):
    """Retrieves chat history for the given chat ID.

    Args:
        chat_id (int): The unique identifier of the chat.

    Returns:
        GenerativeModel: The Generative AI model instance with chat history.

    Raises:
        RuntimeError: If there's an error retrieving data from the cloud.
    """
    # Check if chat history exists locally
    if chat_id in chat_histories:
        return chat_histories[chat_id]  # Return existing history

    # If not found locally, try retrieving from cloud
    try:
        userData = DB.user_exists(chat_id)
        if userData:
            instruction = userData['system_instruction']

            if instruction =='default':
                instruction =  SYSTEM_INSTRUCTION,
            
            
            model_temp = genai.GenerativeModel(
                model_name="gemini-1.5-pro-latest",
                safety_settings=SAFETY_SETTINGS,
                generation_config=GENERATION_CONFIG,
                tools='code_execution',
                system_instruction=instruction
            )
            history=jsonpickle.decode(userData['chat_session'])   # decode history and then store

            chat_histories[chat_id] = model_temp.start_chat(history=history )
            logger.info(f"Chat id:{chat_id} did not exist locally, got previous data from cloud")
            return chat_histories[chat_id]  # Return retrieved history
        else:
            # User doesn't exist in cloud, create a new one
            DB.create_user(chat_id)
            chat_histories[chat_id] = model.start_chat(history=[] )
            logger.info(f"Chat id:{chat_id} did not exist, created one")
            return chat_histories[chat_id]  # Return new model

    except Exception as e:
        # Handle errors during cloud data retrieval
        logger.error(f"Error retrieving chat history for chat_id: {chat_id}, Error: {e}")

     
                
def generate_response(chat_id, input_text: str) -> str:
    chat_history = get_chat_history(chat_id)
    logger.info("Generating response...")
    try:
        try:
            response = chat_history.send_message(input_text)
        except Exception as e:
            logger.error(f"Error occured while genrating response: {e}")
            response= f"Eʀʀᴏʀ🔧 ᴏᴄᴄᴜʀᴇᴅ ᴡʜɪʟᴇ ɢᴇɴʀᴀᴛɪɴɢ ʀᴇsᴘᴏɴsᴇ: {e}"
        
        if not hasattr(response, "text"):
          response = f"*𝑀𝑦 𝑎𝑝𝑜𝑙𝑜𝑔𝑖𝑒𝑠*, I'ᴠᴇ ʀᴇᴀᴄʜᴇᴅ ᴍʏ ᴜsᴀɢᴇ ʟɪᴍɪᴛ ғᴏʀ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ. ⏳ Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ɪɴ ᴀ ғᴇᴡ ᴍɪɴᴜᴛᴇs. \n\n 📡Rᴇsᴘᴏɴsᴇ: {response}"
        
        else:
          response = response.text
            
        def update():
            try:
                with lock:  # Use a thread-safe lock for Firebase access
                    DB.chat_history_add(chat_id, chat_history.history)
                return response if input_text else "error"
            except Exception as e:
                logger.error(f"Sorry, I couldn't generate a response at the moment. Please try again later.\n\nError: {e}")
                return f"Sᴏʀʀʏ, I ᴄᴏᴜʟᴅɴ'ᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʀᴇsᴘᴏɴsᴇ ᴀᴛ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.\n\n🛑Eʀʀᴏʀ: {e}"

        # Create a lock to ensure only one thread updates Firebase at a time
        lock = threading.Lock()

        # Create a thread to update Firebase asynchronously in the background
        thread = threading.Thread(target=update)
        thread.start()
        return response

    except Exception as e:
            logger.error(f"Sorry, I couldn't generate a response at the moment. Please try again later.\n\nError: {e}")
            return f"Sᴏʀʀʏ, I ᴄᴏᴜʟᴅɴ'ᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʀᴇsᴘᴏɴsᴇ ᴀᴛ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.\n\n🛑Eʀʀᴏʀ: {e}"


@restricted
async def media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        
        message = update.message
        if update.message.reply_to_message:
            reply_to_bot = (
                update.message.reply_to_message
                and update.message.reply_to_message.from_user.id == context.bot.id )
        else:
            reply_to_bot = False

        if update.message.caption:
            user_message = update.message.caption.lower()
        else:
            user_message = " "
        print(update.message.chat.type)
        if (
            user_message.startswith(START_SWITCH) or  # Check for start switch command
            update.message.chat.type == 'private' or  # Check for private chat
            reply_to_bot or  # Check for reply to bot
            message.voice or  # Check for voice message 
            message.audio
        ): 
            Media_size = await Check_file_Size(message)
            if Media_size >= 20: 
                await update.message.reply_text(f"Tʜᴇ ᴍᴇᴅɪᴀ sɪᴢᴇ ({Media_size} MB) ᴇxᴄᴇᴇᴅs ᴛʜᴇ ʟɪᴍɪᴛ ᴏғ 20 MB. Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ sᴍᴀʟʟᴇʀ ᴍᴇᴅɪᴀ.")
                    
            try:
                await download_and_process_video(update, context)
            except Exception as e:
                # Handle errors during downloading
                await update.message.reply_text("Aɴ 🚫ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴛʜᴇ ᴍᴇᴅɪᴀ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.")
            


async def download_and_process_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Download the video file
        chat_id = update.message.chat_id
        if hasattr(update.message, "caption"):
            user_message = update.message.caption if update.message.caption else "respond to what user sended you.."
        else:
            user_message ="respond to what user sended you.."

        if update.message.photo:
            file = await update.message.effective_attachment[-1].get_file()
        else:
            file = await update.message.effective_attachment.get_file()

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
        file_path = await file.download_to_drive()
        
        
        logger.debug(f"Downloaded file to {file_path}")
        # Upload the video file to Gemini

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await Genrate_text_via_Media(update,context,file_path,user_message)


    except Exception as e:
        # Handle errors during the process
        await update.message.reply_text(f"Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {e}")

    finally:
        try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                else:
                    await update.message.reply_text(f"Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴄʟᴇᴀɴɪɴɢ ᴜᴘ:ғɪʟᴇ_ᴘᴀᴛʜ {file_path} ᴅɪᴅ ɴᴏᴛ ᴇxɪsᴛᴇᴅ ")

        except Exception as e:
            # Handle errors during cleanup
            await update.message.reply_text(f"An error occurred while cleaning up: {e}")

async def Genrate_text_via_Media(update: Update, context: ContextTypes.DEFAULT_TYPE,file_path: str,user_message=None):
        if not user_message:
            user_message= "respond to what user send you ."

        chat_id = update.message.chat_id
        media_file = genai.upload_file(path=file_path)
        logger.debug(f"Uploaded file to Gemini: {media_file}")

        # Wait for Gemini to finish processing the video
        while media_file.state.name == "PROCESSING":
            time.sleep(10)
            media_file = genai.get_file(media_file.name)

        # Check if Gemini failed to process the video
        if media_file.state.name == "FAILED":
            raise ValueError("Gemini failed to process the media_file.")

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)



        # Generate content using Gemini
        chat_session = get_chat_history(chat_id)
        logger.info(f"genrating response by Gemini on media... media {media_file}")
        response = chat_session.send_message([media_file , user_message])

        # Check and handle the response from Gemini
        if hasattr(response, "text"):
            await send_message(update,message = response.text,format = True,parse_mode ="MarkdownV2") 
        else:
            await update.message.reply_text(
                    f"<b>𝑀𝑦 𝑎𝑝𝑜𝑙𝑜𝑔𝑖𝑒𝑠</b>, I've reached my <i>usage limit</i> for the moment. ⏳ Please try again in a few minutes. \n\n<i>Response :</i> {response}",
                    parse_mode='HTML'
                )


async def Check_file_Size(message):
    if not message.photo:
                file_size = message.effective_attachment.file_size  # Size of the audio file in bytes
                

               
                return file_size / (1024 * 1024)
    return 0
                    


async def Reply_handller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = update.effective_message
        chat_id = update.message.chat_id
        file_path = None
        if message.text and (message.text.startswith(START_SWITCH) or update.message.chat.type == 'private' or update.message.reply_to_message.from_user.id == context.bot.id ) and message.reply_to_message:
            original_message = message.reply_to_message
            
            original_message_ = original_message.text

            reply_has_attachment =  message.effective_attachment
            original_has_attachment = original_message.effective_attachment
            
            if reply_has_attachment:
                Media_size = await Check_file_Size(message)
                if Media_size >= 20: 
                    await update.message.reply_text(f"Tʜᴇ ᴍᴇᴅɪᴀ sɪᴢᴇ ({Media_size} MB) ᴇxᴄᴇᴇᴅs ᴛʜᴇ ʟɪᴍɪᴛ ᴏғ 20 MB. Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ sᴍᴀʟʟᴇʀ ᴍᴇᴅɪᴀ.")
                    return
                if message.photo:
                    file = await update.message.effective_attachment[-1].get_file()
                else:
                    file = await update.message.effective_attachment.get_file()
                    
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
                file_path = await file.download_to_drive()
                logger.debug(f"Downloaded file to {file_path}")
                await Genrate_text_via_Media(update,context,file_path,message.text)
            
            elif original_has_attachment:
                Media_size = await Check_file_Size(original_message)
                if Media_size >= 20: 
                    await update.message.reply_text(f"Tʜᴇ ᴍᴇᴅɪᴀ sɪᴢᴇ ({Media_size} MB) ᴇxᴄᴇᴇᴅs ᴛʜᴇ ʟɪᴍɪᴛ ᴏғ 20 MB. Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ sᴍᴀʟʟᴇʀ ᴍᴇᴅɪᴀ.")
                    return
                if original_message.photo:
                    file = await original_message.effective_attachment[-1].get_file()
                else:
                    file = await original_message.effective_attachment.get_file()

                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
                file_path = await file.download_to_drive()
                logger.debug(f"Downloaded file to {file_path}")
                user_message = f"Original message: {original_message_}\nReply to that message: {message.text}"
                await Genrate_text_via_Media(update,context,file_path,user_message)
            
            elif original_message_:
                user_message = f"Original message: {original_message_}\nReply to that message: {message.text}"
                response = generate_response(chat_id=chat_id,input_text=user_message)
                # Code that might raise the AttributeError (e.g., accessing the 'text' attribute of a variable)
                await send_message(update,message = response,format = True,parse_mode ="MarkdownV2") 
                logger.info(f"Prompt({chat_id}): {user_message}\n\n\nResponse: \n{response}")
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            await update.message.reply_text(f"Sᴏʀʀʏ, I ᴇɴᴄᴏᴜɴᴛᴇʀᴇᴅ ᴀɴ ᴇʀʀᴏʀ ᴡʜɪʟᴇ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ.\n ᴇʀʀᴏʀ:{e}")
        except Exception:  # If the original message couldn't be edited
            logger.error("Error cant send the message")
    finally:
        try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                
        except Exception as e:
            # Handle errors during cleanup
            await update.message.reply_text(f"An error occurred while cleaning up: {e}")

@restricted
async def Clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    chat_id = update.message.chat_id
    if update.effective_chat.type == "private":
        msg = await update.message.reply_text(f'Clearing chat history....')
        chat_histories[chat_id] = model.start_chat(history=[])
        DB.chat_history_add(chat_id,[])
        await msg.edit_text("history successful cleared!🥳🥳")
    else:
        chat_admins = await update.effective_chat.get_administrators()
        if update.effective_user in (admin.user for admin in chat_admins):
            msg = await update.message.reply_text(f'Clearing chat history....')
            chat_histories[chat_id] = model.start_chat(history=[])
            DB.chat_history_add(chat_id,[])
            await msg.edit_text("history successful cleared!🥳🥳")
    
           
        else:
           await update.message.reply_text(" You need to be group/chat admin to do this function.")


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
           await update.message.reply_text(" You need to be group/chat admin to do this function.")
           return 
    
    msg = await update.message.reply_text(f'Changing prompt....')
    if new_promt :
        if  context.args[0].lower() == 'd' or context.args[0].lower() == 'default' or context.args[0].lower() == 'orignal':
        
           chat_histories[chat_id]= model.start_chat(history=[] )
           DB.update_instruction(chat_id)
           await msg.edit_text(f"Tʜᴇ ᴘʀᴏᴍᴘᴛ ʜᴀs ʙᴇᴇɴ 🎉sᴜᴄᴄᴇssғᴜʟʟʏ🎉 ᴄʜᴀɴɢᴇᴅ ᴛᴏ: <b>'ᴅᴇғᴀᴜʟᴛ'</b>", parse_mode='HTML')
        else:
                model_temp = genai.GenerativeModel(
                    model_name="gemini-1.5-pro-latest",
                    safety_settings=SAFETY_SETTINGS,
                    generation_config=GENERATION_CONFIG,
                    tools='code_execution',
                    system_instruction=new_promt )
                chat_histories[chat_id] = model_temp.start_chat(history=[])
    
                await msg.edit_text(f"Tʜᴇ ᴘʀᴏᴍᴘᴛ ʜᴀs ʙᴇᴇɴ 🎉sᴜᴄᴄᴇssғᴜʟʟʏ🎉 ᴄʜᴀɴɢᴇᴅ ᴛᴏ: <b>'{new_promt}'</b>", parse_mode='HTML')
                DB.update_instruction(chat_id,new_promt)
        DB.chat_history_add(chat_id,[])
        
    else:
        await msg.edit_text("Error : please provide me the prompt which you want to give.")


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
           await update.message.reply_text(" You need to be group/chat admin to do this function.")
    msg = await update.message.reply_text(f"Please be patient we are extracting this chat's data....")
    await msg.edit_text(DB.info(chat_id), parse_mode='HTML')

        




clear_history_commamd = CommandHandler(("clear_history","clearhistory","clear"),Clear_history)
changeprompt_command =CommandHandler(("changeprompt","change_prompt","prompt"),changeprompt)
Chat_Info_command =CommandHandler(("info","myinfo","Info"),Chat_Info)
                       
            
        

from telegram.constants import ParseMode,ChatAction
from utils.log import logger
from utils.escape import escape
from utils.dataBase.FireDB import DB
import threading
from utils.decoders_ import restricted
import textwrap
import jsonpickle
import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler
)
from utils.decoders_ import rate_limit


import os 
import time
from config import (
    START_SWITCH,
    SYSTEM_INSTRUCTION,
    SAFETY_SETTINGS,
    GENERATION_CONFIG,
    GEMINE_API_KEY,


)




chat_histories ={}


genai.configure(api_key=GEMINE_API_KEY)
model = genai.GenerativeModel(
  model_name="gemini-1.5-pro-latest",
  safety_settings=SAFETY_SETTINGS,
  generation_config=GENERATION_CONFIG,
  tools='code_execution',
  system_instruction= SYSTEM_INSTRUCTION)


@restricted
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not update.message:
            return
        if DB.is_user_blocked(str(update.message.from_user.id)):
            logger.info(f"Ignoring command from blocked user {str(update.message.from_user.id)}.")
            return

        chat_id = update.message.chat_id
        user_message = update.message.text.lower()
        if user_message.startswith(START_SWITCH) or update.message.chat.type == 'private':
            first_name = update.effective_user.first_name
            
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            # Generate the response
            response = generate_response(chat_id,user_message)
                
        
            # Code that might raise the AttributeError (e.g., accessing the 'text' attribute of a variable)
            await send_message(update,message = response,format = True,parse_mode ="MarkdownV2") 
            logger.info(f"Prompt({chat_id}): {user_message}\n\n\nResponse: \n{response}")

            if first_name:
                logger.info(f"{first_name}: {user_message}")
            else:
                logger.info(f"Someone: {user_message}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            await update.message.reply_text(f"Sᴏʀʀʏ, I ᴇɴᴄᴏᴜɴᴛᴇʀᴇᴅ ᴀɴ ᴇʀʀᴏʀ ᴡʜɪʟᴇ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ.\n ᴇʀʀᴏʀ:{e}")
        except Exception:  # If the  message couldn't be send
            logger.error("Error cant send the message")


async def send_message(update: Update,message: str,format = True,parse_mode = ParseMode.HTML) -> None:
    try:

        async def send_wrap(message_ :str):
            chunks = textwrap.wrap(message_, width=3500, break_long_words=False, replace_whitespace=False)
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode= parse_mode)



        if format:
            try:
                html_message = escape(message)
                await send_wrap(html_message)
                
            except Exception as e:
                logger.warning(f"cant parse the response error:{e}")
        else:
            logger.warning("sending unformated message")
            await send_wrap(message)
    except Exception as e:
        
        await update.message.reply_text(f"ᴡᴏᴏᴘs! ᴀɴ Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ sᴇɴᴅɪɴɢ ᴛʜᴇ ᴍᴇssᴀɢᴇ: {e}", parse_mode=ParseMode.HTML)
        logger.error(f"An error occurred while sending the message:{e}")

def get_chat_history(chat_id):
    """Retrieves chat history for the given chat ID.

    Args:
        chat_id (int): The unique identifier of the chat.

    Returns:
        GenerativeModel: The Generative AI model instance with chat history.

    Raises:
        RuntimeError: If there's an error retrieving data from the cloud.
    """
    # Check if chat history exists locally
    if chat_id in chat_histories:
        return chat_histories[chat_id]  # Return existing history

    # If not found locally, try retrieving from cloud
    try:
        userData = DB.user_exists(chat_id)
        if userData:
            instruction = userData['system_instruction']

            if instruction =='default':
                instruction =  SYSTEM_INSTRUCTION,
            
            
            model_temp = genai.GenerativeModel(
                model_name="gemini-1.5-pro-latest",
                safety_settings=SAFETY_SETTINGS,
                generation_config=GENERATION_CONFIG,
                tools='code_execution',
                system_instruction=instruction
            )
            history=jsonpickle.decode(userData['chat_session'])   # decode history and then store

            chat_histories[chat_id] = model_temp.start_chat(history=history )
            logger.info(f"Chat id:{chat_id} did not exist locally, got previous data from cloud")
            return chat_histories[chat_id]  # Return retrieved history
        else:
            # User doesn't exist in cloud, create a new one
            DB.create_user(chat_id)
            chat_histories[chat_id] = model.start_chat(history=[] )
            logger.info(f"Chat id:{chat_id} did not exist, created one")
            return chat_histories[chat_id]  # Return new model

    except Exception as e:
        # Handle errors during cloud data retrieval
        logger.error(f"Error retrieving chat history for chat_id: {chat_id}, Error: {e}")

     
                
def generate_response(chat_id, input_text: str) -> str:
    chat_history = get_chat_history(chat_id)
    logger.info("Generating response...")
    try:
        try:
            response = chat_history.send_message(input_text)
        except Exception as e:
            logger.error(f"Error occured while genrating response: {e}")
            response= f"Eʀʀᴏʀ🔧 ᴏᴄᴄᴜʀᴇᴅ ᴡʜɪʟᴇ ɢᴇɴʀᴀᴛɪɴɢ ʀᴇsᴘᴏɴsᴇ: {e}"
        
        if not hasattr(response, "text"):
          response = f"*𝑀𝑦 𝑎𝑝𝑜𝑙𝑜𝑔𝑖𝑒𝑠*, I'ᴠᴇ ʀᴇᴀᴄʜᴇᴅ ᴍʏ ᴜsᴀɢᴇ ʟɪᴍɪᴛ ғᴏʀ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ. ⏳ Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ɪɴ ᴀ ғᴇᴡ ᴍɪɴᴜᴛᴇs. \n\n 📡Rᴇsᴘᴏɴsᴇ: {response}"
        
        else:
          response = response.text
            
        def update():
            try:
                with lock:  # Use a thread-safe lock for Firebase access
                    DB.chat_history_add(chat_id, chat_history.history)
                return response if input_text else "error"
            except Exception as e:
                logger.error(f"Sorry, I couldn't generate a response at the moment. Please try again later.\n\nError: {e}")
                return f"Sᴏʀʀʏ, I ᴄᴏᴜʟᴅɴ'ᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʀᴇsᴘᴏɴsᴇ ᴀᴛ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.\n\n🛑Eʀʀᴏʀ: {e}"

        # Create a lock to ensure only one thread updates Firebase at a time
        lock = threading.Lock()

        # Create a thread to update Firebase asynchronously in the background
        thread = threading.Thread(target=update)
        thread.start()
        return response

    except Exception as e:
            logger.error(f"Sorry, I couldn't generate a response at the moment. Please try again later.\n\nError: {e}")
            return f"Sᴏʀʀʏ, I ᴄᴏᴜʟᴅɴ'ᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʀᴇsᴘᴏɴsᴇ ᴀᴛ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.\n\n🛑Eʀʀᴏʀ: {e}"


@restricted
async def media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        
        message = update.message
        if update.message.reply_to_message:
            reply_to_bot = (
                update.message.reply_to_message
                and update.message.reply_to_message.from_user.id == context.bot.id )
        else:
            reply_to_bot = False

        if update.message.caption:
            user_message = update.message.caption.lower()
        else:
            user_message = " "
        print(update.message.chat.type)
        if (
            user_message.startswith(START_SWITCH) or  # Check for start switch command
            update.message.chat.type == 'private' or  # Check for private chat
            reply_to_bot or  # Check for reply to bot
            message.voice or  # Check for voice message 
            message.audio
        ): 
            Media_size = await Check_file_Size(message)
            if Media_size >= 20: 
                await update.message.reply_text(f"Tʜᴇ ᴍᴇᴅɪᴀ sɪᴢᴇ ({Media_size} MB) ᴇxᴄᴇᴇᴅs ᴛʜᴇ ʟɪᴍɪᴛ ᴏғ 20 MB. Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ sᴍᴀʟʟᴇʀ ᴍᴇᴅɪᴀ.")
                    
            try:
                await download_and_process_video(update, context)
            except Exception as e:
                # Handle errors during downloading
                await update.message.reply_text("Aɴ 🚫ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴛʜᴇ ᴍᴇᴅɪᴀ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.")
            


async def download_and_process_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Download the video file
        chat_id = update.message.chat_id
        if hasattr(update.message, "caption"):
            user_message = update.message.caption if update.message.caption else "respond to what user sended you.."
        else:
            user_message ="respond to what user sended you.."

        if update.message.photo:
            file = await update.message.effective_attachment[-1].get_file()
        else:
            file = await update.message.effective_attachment.get_file()

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
        file_path = await file.download_to_drive()
        
        
        logger.debug(f"Downloaded file to {file_path}")
        # Upload the video file to Gemini

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await Genrate_text_via_Media(update,context,file_path,user_message)


    except Exception as e:
        # Handle errors during the process
        await update.message.reply_text(f"Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {e}")

    finally:
        try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                else:
                    await update.message.reply_text(f"Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴄʟᴇᴀɴɪɴɢ ᴜᴘ:ғɪʟᴇ_ᴘᴀᴛʜ {file_path} ᴅɪᴅ ɴᴏᴛ ᴇxɪsᴛᴇᴅ ")

        except Exception as e:
            # Handle errors during cleanup
            await update.message.reply_text(f"An error occurred while cleaning up: {e}")

async def Genrate_text_via_Media(update: Update, context: ContextTypes.DEFAULT_TYPE,file_path: str,user_message=None):
        if not user_message:
            user_message= "respond to what user send you ."

        chat_id = update.message.chat_id
        media_file = genai.upload_file(path=file_path)
        logger.debug(f"Uploaded file to Gemini: {media_file}")

        # Wait for Gemini to finish processing the video
        while media_file.state.name == "PROCESSING":
            time.sleep(10)
            media_file = genai.get_file(media_file.name)

        # Check if Gemini failed to process the video
        if media_file.state.name == "FAILED":
            raise ValueError("Gemini failed to process the media_file.")

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)



        # Generate content using Gemini
        chat_session = get_chat_history(chat_id)
        logger.info(f"genrating response by Gemini on media... media {media_file}")
        response = chat_session.send_message([media_file , user_message])

        # Check and handle the response from Gemini
        if hasattr(response, "text"):
            await send_message(update,message = response.text,format = True,parse_mode ="MarkdownV2") 
        else:
            await update.message.reply_text(
                    f"<b>𝑀𝑦 𝑎𝑝𝑜𝑙𝑜𝑔𝑖𝑒𝑠</b>, I've reached my <i>usage limit</i> for the moment. ⏳ Please try again in a few minutes. \n\n<i>Response :</i> {response}",
                    parse_mode='HTML'
                )


async def Check_file_Size(message):
    if not message.photo:
                file_size = message.effective_attachment.file_size  # Size of the audio file in bytes
                

               
                return file_size / (1024 * 1024)
    return 0
                    


async def Reply_handller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = update.effective_message
        chat_id = update.message.chat_id
        file_path = None
        if message.text and (message.text.startswith(START_SWITCH) or update.message.chat.type == 'private' or update.message.reply_to_message.from_user.id == context.bot.id ) and message.reply_to_message:
            original_message = message.reply_to_message
            
            original_message_ = original_message.text

            reply_has_attachment =  message.effective_attachment
            original_has_attachment = original_message.effective_attachment
            
            if reply_has_attachment:
                Media_size = await Check_file_Size(message)
                if Media_size >= 20: 
                    await update.message.reply_text(f"Tʜᴇ ᴍᴇᴅɪᴀ sɪᴢᴇ ({Media_size} MB) ᴇxᴄᴇᴇᴅs ᴛʜᴇ ʟɪᴍɪᴛ ᴏғ 20 MB. Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ sᴍᴀʟʟᴇʀ ᴍᴇᴅɪᴀ.")
                    return
                if message.photo:
                    file = await update.message.effective_attachment[-1].get_file()
                else:
                    file = await update.message.effective_attachment.get_file()
                    
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
                file_path = await file.download_to_drive()
                logger.debug(f"Downloaded file to {file_path}")
                await Genrate_text_via_Media(update,context,file_path,message.text)
            
            elif original_has_attachment:
                Media_size = await Check_file_Size(original_message)
                if Media_size >= 20: 
                    await update.message.reply_text(f"Tʜᴇ ᴍᴇᴅɪᴀ sɪᴢᴇ ({Media_size} MB) ᴇxᴄᴇᴇᴅs ᴛʜᴇ ʟɪᴍɪᴛ ᴏғ 20 MB. Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ sᴍᴀʟʟᴇʀ ᴍᴇᴅɪᴀ.")
                    return
                if original_message.photo:
                    file = await original_message.effective_attachment[-1].get_file()
                else:
                    file = await original_message.effective_attachment.get_file()

                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
                file_path = await file.download_to_drive()
                logger.debug(f"Downloaded file to {file_path}")
                user_message = f"Original message: {original_message_}\nReply to that message: {message.text}"
                await Genrate_text_via_Media(update,context,file_path,user_message)
            
            elif original_message_:
                user_message = f"Original message: {original_message_}\nReply to that message: {message.text}"
                response = generate_response(chat_id=chat_id,input_text=user_message)
                # Code that might raise the AttributeError (e.g., accessing the 'text' attribute of a variable)
                await send_message(update,message = response,format = True,parse_mode ="MarkdownV2") 
                logger.info(f"Prompt({chat_id}): {user_message}\n\n\nResponse: \n{response}")
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            await update.message.reply_text(f"Sᴏʀʀʏ, I ᴇɴᴄᴏᴜɴᴛᴇʀᴇᴅ ᴀɴ ᴇʀʀᴏʀ ᴡʜɪʟᴇ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ.\n ᴇʀʀᴏʀ:{e}")
        except Exception:  # If the original message couldn't be edited
            logger.error("Error cant send the message")
    finally:
        try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                
        except Exception as e:
            # Handle errors during cleanup
            await update.message.reply_text(f"An error occurred while cleaning up: {e}")

@restricted
async def Clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    chat_id = update.message.chat_id
    if update.effective_chat.type == "private":
        msg = await update.message.reply_text(f'Clearing chat history....')
        chat_histories[chat_id] = model.start_chat(history=[])
        DB.chat_history_add(chat_id,[])
        await msg.edit_text("history successful cleared!🥳🥳")
    else:
        chat_admins = await update.effective_chat.get_administrators()
        if update.effective_user in (admin.user for admin in chat_admins):
            msg = await update.message.reply_text(f'Clearing chat history....')
            chat_histories[chat_id] = model.start_chat(history=[])
            DB.chat_history_add(chat_id,[])
            await msg.edit_text("history successful cleared!🥳🥳")
    
           
        else:
           await update.message.reply_text(" You need to be group/chat admin to do this function.")


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
           await update.message.reply_text(" You need to be group/chat admin to do this function.")
           return 
    
    msg = await update.message.reply_text(f'Changing prompt....')
    if new_promt :
        if  context.args[0].lower() == 'd' or context.args[0].lower() == 'default' or context.args[0].lower() == 'orignal':
        
           chat_histories[chat_id]= model.start_chat(history=[] )
           DB.update_instruction(chat_id)
           await msg.edit_text(f"Tʜᴇ ᴘʀᴏᴍᴘᴛ ʜᴀs ʙᴇᴇɴ 🎉sᴜᴄᴄᴇssғᴜʟʟʏ🎉 ᴄʜᴀɴɢᴇᴅ ᴛᴏ: <b>'ᴅᴇғᴀᴜʟᴛ'</b>", parse_mode='HTML')
        else:
                model_temp = genai.GenerativeModel(
                    model_name="gemini-1.5-pro-latest",
                    safety_settings=SAFETY_SETTINGS,
                    generation_config=GENERATION_CONFIG,
                    tools='code_execution',
                    system_instruction=new_promt )
                chat_histories[chat_id] = model_temp.start_chat(history=[])
    
                await msg.edit_text(f"Tʜᴇ ᴘʀᴏᴍᴘᴛ ʜᴀs ʙᴇᴇɴ 🎉sᴜᴄᴄᴇssғᴜʟʟʏ🎉 ᴄʜᴀɴɢᴇᴅ ᴛᴏ: <b>'{new_promt}'</b>", parse_mode='HTML')
                DB.update_instruction(chat_id,new_promt)
        DB.chat_history_add(chat_id,[])
        
    else:
        await msg.edit_text("Error : please provide me the prompt which you want to give.")


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
           await update.message.reply_text(" You need to be group/chat admin to do this function.")
    msg = await update.message.reply_text(f"Please be patient we are extracting this chat's data....")
    await msg.edit_text(DB.info(chat_id), parse_mode='HTML')

        




clear_history_commamd = CommandHandler(("clear_history","clearhistory","clear"),Clear_history)
changeprompt_command =CommandHandler(("changeprompt","change_prompt","prompt"),changeprompt)
Chat_Info_command =CommandHandler(("info","myinfo","Info"),Chat_Info)
                       
            
        


from telegram.constants import ParseMode,ChatAction
from utils.log import logger
from utils.escape import escape
from utils.dataBase.FireDB import DB
import threading
from utils.decoders_ import restricted
import textwrap
import jsonpickle
import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler
)
from utils.decoders_ import rate_limit


import os 
import time
from config import (
    START_SWITCH,
    SYSTEM_INSTRUCTION,
    SAFETY_SETTINGS,
    GENERATION_CONFIG,
    GEMINE_API_KEY,


)




chat_histories ={}


genai.configure(api_key=GEMINE_API_KEY)
model = genai.GenerativeModel(
  model_name="gemini-1.5-pro-latest",
  safety_settings=SAFETY_SETTINGS,
  generation_config=GENERATION_CONFIG,
  tools='code_execution',
  system_instruction= SYSTEM_INSTRUCTION)


@restricted
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not update.message:
            return
        if DB.is_user_blocked(str(update.message.from_user.id)):
            logger.info(f"Ignoring command from blocked user {str(update.message.from_user.id)}.")
            return

        chat_id = update.message.chat_id
        user_message = update.message.text.lower()
        if user_message.startswith(START_SWITCH) or update.message.chat.type == 'private':
            first_name = update.effective_user.first_name
            
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            # Generate the response
            response = generate_response(chat_id,user_message)
                
        
            # Code that might raise the AttributeError (e.g., accessing the 'text' attribute of a variable)
            await send_message(update,message = response,format = True,parse_mode ="MarkdownV2") 
            logger.info(f"Prompt({chat_id}): {user_message}\n\n\nResponse: \n{response}")

            if first_name:
                logger.info(f"{first_name}: {user_message}")
            else:
                logger.info(f"Someone: {user_message}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            await update.message.reply_text(f"Sᴏʀʀʏ, I ᴇɴᴄᴏᴜɴᴛᴇʀᴇᴅ ᴀɴ ᴇʀʀᴏʀ ᴡʜɪʟᴇ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ.\n ᴇʀʀᴏʀ:{e}")
        except Exception:  # If the  message couldn't be send
            logger.error("Error cant send the message")


async def send_message(update: Update,message: str,format = True,parse_mode = ParseMode.HTML) -> None:
    try:

        async def send_wrap(message_ :str):
            chunks = textwrap.wrap(message_, width=3500, break_long_words=False, replace_whitespace=False)
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode= parse_mode)



        if format:
            try:
                html_message = escape(message)
                await send_wrap(html_message)
                
            except Exception as e:
                logger.warning(f"cant parse the response error:{e}")
        else:
            logger.warning("sending unformated message")
            await send_wrap(message)
    except Exception as e:
        
        await update.message.reply_text(f"ᴡᴏᴏᴘs! ᴀɴ Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ sᴇɴᴅɪɴɢ ᴛʜᴇ ᴍᴇssᴀɢᴇ: {e}", parse_mode=ParseMode.HTML)
        logger.error(f"An error occurred while sending the message:{e}")

def get_chat_history(chat_id):
    """Retrieves chat history for the given chat ID.

    Args:
        chat_id (int): The unique identifier of the chat.

    Returns:
        GenerativeModel: The Generative AI model instance with chat history.

    Raises:
        RuntimeError: If there's an error retrieving data from the cloud.
    """
    # Check if chat history exists locally
    if chat_id in chat_histories:
        return chat_histories[chat_id]  # Return existing history

    # If not found locally, try retrieving from cloud
    try:
        userData = DB.user_exists(chat_id)
        if userData:
            instruction = userData['system_instruction']

            if instruction =='default':
                instruction =  SYSTEM_INSTRUCTION,
            
            
            model_temp = genai.GenerativeModel(
                model_name="gemini-1.5-pro-latest",
                safety_settings=SAFETY_SETTINGS,
                generation_config=GENERATION_CONFIG,
                tools='code_execution',
                system_instruction=instruction
            )
            history=jsonpickle.decode(userData['chat_session'])   # decode history and then store

            chat_histories[chat_id] = model_temp.start_chat(history=history )
            logger.info(f"Chat id:{chat_id} did not exist locally, got previous data from cloud")
            return chat_histories[chat_id]  # Return retrieved history
        else:
            # User doesn't exist in cloud, create a new one
            DB.create_user(chat_id)
            chat_histories[chat_id] = model.start_chat(history=[] )
            logger.info(f"Chat id:{chat_id} did not exist, created one")
            return chat_histories[chat_id]  # Return new model

    except Exception as e:
        # Handle errors during cloud data retrieval
        logger.error(f"Error retrieving chat history for chat_id: {chat_id}, Error: {e}")

     
                
def generate_response(chat_id, input_text: str) -> str:
    chat_history = get_chat_history(chat_id)
    logger.info("Generating response...")
    try:
        try:
            response = chat_history.send_message(input_text)
        except Exception as e:
            logger.error(f"Error occured while genrating response: {e}")
            response= f"Eʀʀᴏʀ🔧 ᴏᴄᴄᴜʀᴇᴅ ᴡʜɪʟᴇ ɢᴇɴʀᴀᴛɪɴɢ ʀᴇsᴘᴏɴsᴇ: {e}"
        
        if not hasattr(response, "text"):
          response = f"*𝑀𝑦 𝑎𝑝𝑜𝑙𝑜𝑔𝑖𝑒𝑠*, I'ᴠᴇ ʀᴇᴀᴄʜᴇᴅ ᴍʏ ᴜsᴀɢᴇ ʟɪᴍɪᴛ ғᴏʀ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ. ⏳ Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ɪɴ ᴀ ғᴇᴡ ᴍɪɴᴜᴛᴇs. \n\n 📡Rᴇsᴘᴏɴsᴇ: {response}"
        
        else:
          response = response.text
            
        def update():
            try:
                with lock:  # Use a thread-safe lock for Firebase access
                    DB.chat_history_add(chat_id, chat_history.history)
                return response if input_text else "error"
            except Exception as e:
                logger.error(f"Sorry, I couldn't generate a response at the moment. Please try again later.\n\nError: {e}")
                return f"Sᴏʀʀʏ, I ᴄᴏᴜʟᴅɴ'ᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʀᴇsᴘᴏɴsᴇ ᴀᴛ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.\n\n🛑Eʀʀᴏʀ: {e}"

        # Create a lock to ensure only one thread updates Firebase at a time
        lock = threading.Lock()

        # Create a thread to update Firebase asynchronously in the background
        thread = threading.Thread(target=update)
        thread.start()
        return response

    except Exception as e:
            logger.error(f"Sorry, I couldn't generate a response at the moment. Please try again later.\n\nError: {e}")
            return f"Sᴏʀʀʏ, I ᴄᴏᴜʟᴅɴ'ᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʀᴇsᴘᴏɴsᴇ ᴀᴛ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.\n\n🛑Eʀʀᴏʀ: {e}"


@restricted
async def media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        
        message = update.message
        if update.message.reply_to_message:
            reply_to_bot = (
                update.message.reply_to_message
                and update.message.reply_to_message.from_user.id == context.bot.id )
        else:
            reply_to_bot = False

        if update.message.caption:
            user_message = update.message.caption.lower()
        else:
            user_message = " "
        print(update.message.chat.type)
        if (
            user_message.startswith(START_SWITCH) or  # Check for start switch command
            update.message.chat.type == 'private' or  # Check for private chat
            reply_to_bot or  # Check for reply to bot
            message.voice or  # Check for voice message 
            message.audio
        ): 
            Media_size = await Check_file_Size(message)
            if Media_size >= 20: 
                await update.message.reply_text(f"Tʜᴇ ᴍᴇᴅɪᴀ sɪᴢᴇ ({Media_size} MB) ᴇxᴄᴇᴇᴅs ᴛʜᴇ ʟɪᴍɪᴛ ᴏғ 20 MB. Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ sᴍᴀʟʟᴇʀ ᴍᴇᴅɪᴀ.")
                    
            try:
                await download_and_process_video(update, context)
            except Exception as e:
                # Handle errors during downloading
                await update.message.reply_text("Aɴ 🚫ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴛʜᴇ ᴍᴇᴅɪᴀ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.")
            


async def download_and_process_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Download the video file
        chat_id = update.message.chat_id
        if hasattr(update.message, "caption"):
            user_message = update.message.caption if update.message.caption else "respond to what user sended you.."
        else:
            user_message ="respond to what user sended you.."

        if update.message.photo:
            file = await update.message.effective_attachment[-1].get_file()
        else:
            file = await update.message.effective_attachment.get_file()

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
        file_path = await file.download_to_drive()
        
        
        logger.debug(f"Downloaded file to {file_path}")
        # Upload the video file to Gemini

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await Genrate_text_via_Media(update,context,file_path,user_message)


    except Exception as e:
        # Handle errors during the process
        await update.message.reply_text(f"Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {e}")

    finally:
        try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                else:
                    await update.message.reply_text(f"Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴄʟᴇᴀɴɪɴɢ ᴜᴘ:ғɪʟᴇ_ᴘᴀᴛʜ {file_path} ᴅɪᴅ ɴᴏᴛ ᴇxɪsᴛᴇᴅ ")

        except Exception as e:
            # Handle errors during cleanup
            await update.message.reply_text(f"An error occurred while cleaning up: {e}")

async def Genrate_text_via_Media(update: Update, context: ContextTypes.DEFAULT_TYPE,file_path: str,user_message=None):
        if not user_message:
            user_message= "respond to what user send you ."

        chat_id = update.message.chat_id
        media_file = genai.upload_file(path=file_path)
        logger.debug(f"Uploaded file to Gemini: {media_file}")

        # Wait for Gemini to finish processing the video
        while media_file.state.name == "PROCESSING":
            time.sleep(10)
            media_file = genai.get_file(media_file.name)

        # Check if Gemini failed to process the video
        if media_file.state.name == "FAILED":
            raise ValueError("Gemini failed to process the media_file.")

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)



        # Generate content using Gemini
        chat_session = get_chat_history(chat_id)
        logger.info(f"genrating response by Gemini on media... media {media_file}")
        response = chat_session.send_message([media_file , user_message])

        # Check and handle the response from Gemini
        if hasattr(response, "text"):
            await send_message(update,message = response.text,format = True,parse_mode ="MarkdownV2") 
        else:
            await update.message.reply_text(
                    f"<b>𝑀𝑦 𝑎𝑝𝑜𝑙𝑜𝑔𝑖𝑒𝑠</b>, I've reached my <i>usage limit</i> for the moment. ⏳ Please try again in a few minutes. \n\n<i>Response :</i> {response}",
                    parse_mode='HTML'
                )


async def Check_file_Size(message):
    if not message.photo:
                file_size = message.effective_attachment.file_size  # Size of the audio file in bytes
                

               
                return file_size / (1024 * 1024)
    return 0
                    


async def Reply_handller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = update.effective_message
        chat_id = update.message.chat_id
        file_path = None
        if message.text and (message.text.startswith(START_SWITCH) or update.message.chat.type == 'private' or update.message.reply_to_message.from_user.id == context.bot.id ) and message.reply_to_message:
            original_message = message.reply_to_message
            
            original_message_ = original_message.text

            reply_has_attachment =  message.effective_attachment
            original_has_attachment = original_message.effective_attachment
            
            if reply_has_attachment:
                Media_size = await Check_file_Size(message)
                if Media_size >= 20: 
                    await update.message.reply_text(f"Tʜᴇ ᴍᴇᴅɪᴀ sɪᴢᴇ ({Media_size} MB) ᴇxᴄᴇᴇᴅs ᴛʜᴇ ʟɪᴍɪᴛ ᴏғ 20 MB. Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ sᴍᴀʟʟᴇʀ ᴍᴇᴅɪᴀ.")
                    return
                if message.photo:
                    file = await update.message.effective_attachment[-1].get_file()
                else:
                    file = await update.message.effective_attachment.get_file()
                    
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
                file_path = await file.download_to_drive()
                logger.debug(f"Downloaded file to {file_path}")
                await Genrate_text_via_Media(update,context,file_path,message.text)
            
            elif original_has_attachment:
                Media_size = await Check_file_Size(original_message)
                if Media_size >= 20: 
                    await update.message.reply_text(f"Tʜᴇ ᴍᴇᴅɪᴀ sɪᴢᴇ ({Media_size} MB) ᴇxᴄᴇᴇᴅs ᴛʜᴇ ʟɪᴍɪᴛ ᴏғ 20 MB. Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ sᴍᴀʟʟᴇʀ ᴍᴇᴅɪᴀ.")
                    return
                if original_message.photo:
                    file = await original_message.effective_attachment[-1].get_file()
                else:
                    file = await original_message.effective_attachment.get_file()

                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
                file_path = await file.download_to_drive()
                logger.debug(f"Downloaded file to {file_path}")
                user_message = f"Original message: {original_message_}\nReply to that message: {message.text}"
                await Genrate_text_via_Media(update,context,file_path,user_message)
            
            elif original_message_:
                user_message = f"Original message: {original_message_}\nReply to that message: {message.text}"
                response = generate_response(chat_id=chat_id,input_text=user_message)
                # Code that might raise the AttributeError (e.g., accessing the 'text' attribute of a variable)
                await send_message(update,message = response,format = True,parse_mode ="MarkdownV2") 
                logger.info(f"Prompt({chat_id}): {user_message}\n\n\nResponse: \n{response}")
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            await update.message.reply_text(f"Sᴏʀʀʏ, I ᴇɴᴄᴏᴜɴᴛᴇʀᴇᴅ ᴀɴ ᴇʀʀᴏʀ ᴡʜɪʟᴇ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ.\n ᴇʀʀᴏʀ:{e}")
        except Exception:  # If the original message couldn't be edited
            logger.error("Error cant send the message")
    finally:
        try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                
        except Exception as e:
            # Handle errors during cleanup
            await update.message.reply_text(f"An error occurred while cleaning up: {e}")

@restricted
async def Clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    chat_id = update.message.chat_id
    if update.effective_chat.type == "private":
        msg = await update.message.reply_text(f'Clearing chat history....')
        chat_histories[chat_id] = model.start_chat(history=[])
        DB.chat_history_add(chat_id,[])
        await msg.edit_text("history successful cleared!🥳🥳")
    else:
        chat_admins = await update.effective_chat.get_administrators()
        if update.effective_user in (admin.user for admin in chat_admins):
            msg = await update.message.reply_text(f'Clearing chat history....')
            chat_histories[chat_id] = model.start_chat(history=[])
            DB.chat_history_add(chat_id,[])
            await msg.edit_text("history successful cleared!🥳🥳")
    
           
        else:
           await update.message.reply_text(" You need to be group/chat admin to do this function.")


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
           await update.message.reply_text(" You need to be group/chat admin to do this function.")
           return 
    
    msg = await update.message.reply_text(f'Changing prompt....')
    if new_promt :
        if  context.args[0].lower() == 'd' or context.args[0].lower() == 'default' or context.args[0].lower() == 'orignal':
        
           chat_histories[chat_id]= model.start_chat(history=[] )
           DB.update_instruction(chat_id)
           await msg.edit_text(f"Tʜᴇ ᴘʀᴏᴍᴘᴛ ʜᴀs ʙᴇᴇɴ 🎉sᴜᴄᴄᴇssғᴜʟʟʏ🎉 ᴄʜᴀɴɢᴇᴅ ᴛᴏ: <b>'ᴅᴇғᴀᴜʟᴛ'</b>", parse_mode='HTML')
        else:
                model_temp = genai.GenerativeModel(
                    model_name="gemini-1.5-pro-latest",
                    safety_settings=SAFETY_SETTINGS,
                    generation_config=GENERATION_CONFIG,
                    tools='code_execution',
                    system_instruction=new_promt )
                chat_histories[chat_id] = model_temp.start_chat(history=[])
    
                await msg.edit_text(f"Tʜᴇ ᴘʀᴏᴍᴘᴛ ʜᴀs ʙᴇᴇɴ 🎉sᴜᴄᴄᴇssғᴜʟʟʏ🎉 ᴄʜᴀɴɢᴇᴅ ᴛᴏ: <b>'{new_promt}'</b>", parse_mode='HTML')
                DB.update_instruction(chat_id,new_promt)
        DB.chat_history_add(chat_id,[])
        
    else:
        await msg.edit_text("Error : please provide me the prompt which you want to give.")


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
           await update.message.reply_text(" You need to be group/chat admin to do this function.")
    msg = await update.message.reply_text(f"Please be patient we are extracting this chat's data....")
    await msg.edit_text(DB.info(chat_id), parse_mode='HTML')

        




clear_history_commamd = CommandHandler(("clear_history","clearhistory","clear"),Clear_history)
changeprompt_command =CommandHandler(("changeprompt","change_prompt","prompt"),changeprompt)
Chat_Info_command =CommandHandler(("info","myinfo","Info"),Chat_Info)
                       
            
        



           
            
        



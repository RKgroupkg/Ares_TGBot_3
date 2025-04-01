from utils.log import logger
import asyncio
import datetime
from telegram import MessageEntity
logger.info("Importing...")
from Modules.inline import *
from Modules.help import *
from assets.assets import load_asset
from _error_handller import error_handler

logger.info("Loading message handllers....")
from Modules.chat_handller import process_message,media_handler,Reply_handller,clear_history_commamd,changeprompt_command,Chat_Info_command

from utils.decoders_ import rate_limit,restricted
logger.info("Importing commands handllers...")
from Modules.adminCommands.broad_cast import (
    Global_BROADCAST,
    Specific_BROADCAST,
    WARN_USER_BROADCAST

)
logger.info("Importing admin Status commamds...")
from Modules.adminCommands.status import STATS_CMD,SPEED_CMD,DBSTATS,LOG_CMD
from Modules.adminCommands.Admin_cmds import CHAT_INFO_CMD,CHAT_DATA_CMD,UN_BAN_CMD,BAN_CMD
logger.info("Importing users util commands...")
from Modules.users_command.Utils import PASTE_CMD,PING_CMD,ID_CMD
logger.info("Importing users Commands....")
from Modules.users_command.google import GOOGLE_SEARCH_COMMAND,GOOGLE_SERACH_IMG_COMMAND,WIKI_COMMAND,YT_COMMND

logger.info("Importing Owners commands..")
from Modules.adminCommands.terminal import SHELL_CMD,EXECUTE_COMMAND
from Modules.adminCommands.owner import ADD_admin_CMD,RM_admin_CMD,ADMINS_LIST_CMD,REFRESH_CMD,OFF_COMMAD,BOT_ACTIVATION_MESSAGE
logger.info("importing telgram modules....")
from telegram.constants import ParseMode
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from config import * # imports all the attributes and modules

from keep_alive_ping import KeepAliveService
# Import keep Alive for render/koyeb

service = KeepAliveService(
    ping_interval=60,  # Ping every 1 minutes
    log_level = 30 # warning 
)

logger.info("ALl modules imported successfully...")

logger.info("starting auto ping")
# Start the scheduler to begin pinging
try:
  service.start()
except Exception as e:
  raise e
logger.info("server Started!")

@restricted
@rate_limit
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ /start command """
    if update.effective_chat.type == "private":
        first_name = update.effective_user.first_name
        asset = load_asset(START_IMAGE_PATH)
        await update.effective_message.reply_photo(photo=asset,caption=PM_MESSAGE.format(first_name,OWNER_INFO_HTML,SUPPORT_CHAT_INFO_HTML),reply_markup=START_INLINE_CMD,parse_mode=ParseMode.HTML)
    else:
        first_name = update.effective_user.first_name
        msg = f"I ᴘʀᴇғᴇʀ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ <b>ɢʀᴏᴜᴘ</b>."
        asset = load_asset(START_IMAGE_PATH_)
        await update.effective_message.reply_photo(photo=asset,caption=msg,reply_markup=START_INLINE_CMD_INGP,parse_mode=ParseMode.HTML)


@rate_limit
@restricted
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline query handler"""
    query = update.callback_query
    await query.answer()
    query_data = query.data
    if query_data.startswith("home_"):
        await handle_home_command(update, context, query_data)
    elif query_data == "help":
        await query.message.delete()
        await home(update,context)
    elif query_data.startswith("command_"):
        await get_explanation(update, context ,query_data)
    elif query_data.startswith("prompting_"):
        await get_explanation(update, context ,query_data)
    elif query_data.startswith("extra_info_"):
        await get_explanation(update, context ,query_data)
    elif query_data == "home_support":
        await handle_support(update, context)
    elif query_data.startswith("back"):
        await go_back(update, context)
    elif query_data == "close":
        await query.message.delete()
    # elif query_data == "Clear_history_confirmation":
    #     handel_clear_history(update, context)
    else:
        await get_explanation(update, context ,query_data)




async def post_init(application: Application) -> None:
    START_TIME = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    start_message = (
            f"<b>Bot Started</b>\n"
            f"Start Time: <code>{START_TIME}</code>\n"
            # f"Your shutdown password is: <code>{SPECIAL_PASSWORD}</code>"
        )
        
    await application.bot.send_message(
        chat_id=OWNER_ID, text=start_message, parse_mode=ParseMode.HTML
    )



# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Avoiding-flood-limits (use for broadcast commands)
def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TLG_TOKEN).concurrent_updates(True).post_init(post_init).build()
    
   
    message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Entity(MessageEntity.MENTION)& ~filters.REPLY & ~filters.Entity(MessageEntity.TEXT_MENTION), process_message)
    mediaChat_handler = MessageHandler(filters.VOICE |filters.AUDIO | filters.VIDEO |filters.PHOTO |filters.Document.ALL & ~filters.Entity("MENTION") ,media_handler)
    Reply_handler = MessageHandler(filters.REPLY & ~filters.COMMAND & ~filters.Entity(MessageEntity.MENTION)& ~filters.Entity(MessageEntity.TEXT_MENTION),Reply_handller)
    application.add_handler(message_handler)
    application.add_handler(mediaChat_handler)
    application.add_handler(Reply_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler(("help","h"),help))
    application.add_handler(CallbackQueryHandler(button_click))

    # Users Commands
    application.add_handler(GOOGLE_SEARCH_COMMAND)
    application.add_handler(GOOGLE_SERACH_IMG_COMMAND)
    application.add_handler(WIKI_COMMAND)
    application.add_handler(YT_COMMND)
    
    #Users Util commands
    application.add_handler(PASTE_CMD)
    application.add_handler(PING_CMD)
    application.add_handler(ID_CMD)
    application.add_handler(clear_history_commamd)
    application.add_handler(changeprompt_command)
    application.add_handler(Chat_Info_command)
    
    # Owner commands
    application.add_handler(SHELL_CMD)
    application.add_handler(EXECUTE_COMMAND)
    application.add_handler(ADD_admin_CMD)
    application.add_handler(RM_admin_CMD)
    application.add_handler(ADMINS_LIST_CMD)
    application.add_handler(REFRESH_CMD)
    application.add_handler(OFF_COMMAD)


    # Admin commands
    application.add_handler(Specific_BROADCAST)
    application.add_handler(Global_BROADCAST)
    application.add_handler(WARN_USER_BROADCAST)
    application.add_handler(STATS_CMD)
    application.add_handler(SPEED_CMD)
    application.add_handler(DBSTATS)
    application.add_handler(LOG_CMD)
    application.add_handler(CHAT_INFO_CMD)
    application.add_handler(CHAT_DATA_CMD)
    application.add_handler(BAN_CMD)
    application.add_handler(UN_BAN_CMD)

    

    logger.info("BOT STARTED!")

     # ...and the error handler
    application.add_error_handler(error_handler)

    
     # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES,drop_pending_updates= True)
    





if __name__ == "__main__":
    main()

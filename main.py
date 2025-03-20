"""
Telegram Bot Main Module
-----------------------
This module initializes and configures the Telegram bot application.
"""

import asyncio
import datetime

# Core telegram imports
from telegram import Update, MessageEntity
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Logger configuration
from utils.log import logger
logger.info("Initializing bot...")

# Import config and utilities
from config import (
    TLG_TOKEN, 
    OWNER_ID, 
    START_IMAGE_PATH, 
    START_IMAGE_PATH_,
    PM_MESSAGE,
    OWNER_INFO_HTML,
    SUPPORT_CHAT_INFO_HTML,
    START_INLINE_CMD,
    START_INLINE_CMD_INGP,
    SPECIAL_PASSWORD
)
from utils.decoders_ import rate_limit, restricted
from assets.assets import load_asset
from _error_handller import error_handler

# Import message handlers
logger.info("Loading message handlers...")
from Modules.chat_handller import (
    process_message,
    media_handler,
    Reply_handller,
    clear_history_commamd,
    changeprompt_command,
    Chat_Info_command
)

# Import inline handlers
logger.info("Loading inline handlers...")
from Modules.inline import *
from Modules.help import *

# Import admin commands
logger.info("Loading admin commands...")
from Modules.adminCommands.broad_cast import (
    Global_BROADCAST,
    Specific_BROADCAST,
    WARN_USER_BROADCAST
)
from Modules.adminCommands.status import STATS_CMD, SPEED_CMD, DBSTATS, LOG_CMD
from Modules.adminCommands.Admin_cmds import CHAT_INFO_CMD, CHAT_DATA_CMD, UN_BAN_CMD, BAN_CMD

# Import owner commands
logger.info("Loading owner commands...")
from Modules.adminCommands.terminal import SHELL_CMD, EXECUTE_COMMAND
from Modules.adminCommands.owner import (
    ADD_admin_CMD,
    RM_admin_CMD,
    ADMINS_LIST_CMD,
    REFRESH_CMD,
    OFF_COMMAD,
    BOT_ACTIVATION_MESSAGE
)

# Import user commands
logger.info("Loading user commands...")
from Modules.users_command.Utils import PASTE_CMD, PING_CMD, ID_CMD
from Modules.users_command.google import (
    GOOGLE_SEARCH_COMMAND,
    GOOGLE_SERACH_IMG_COMMAND,
    WIKI_COMMAND,
    YT_COMMND
)
from Modules.users_command.ai import IMAGINE_COMMAND_HANDLLER
from Modules.users_command.Inline_collaback import YOUTUBE_CALL_BACK

# Import keep alive service for hosting platforms
from keep_alive_ping import KeepAliveService

logger.info("All modules imported successfully...")


class TelegramBot:
    """Main Telegram Bot class that handles initialization and command setup"""
    
    def __init__(self):
        self.start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Setup keep-alive service
        self.setup_keep_alive()
        
    def setup_keep_alive(self):
        """Initialize and start the keep-alive service"""
        try:
            self.service = KeepAliveService(ping_interval=60)  # Ping every minute
            self.service.start()
            logger.info("Keep-alive service started successfully")
        except Exception as e:
            logger.error(f"Failed to start keep-alive service: {e}")
            raise e

    @staticmethod
    @restricted
    @rate_limit
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for /start command"""
        if update.effective_chat.type == "private":
            first_name = update.effective_user.first_name
            asset = load_asset(START_IMAGE_PATH)
            await update.effective_message.reply_photo(
                photo=asset,
                caption=PM_MESSAGE.format(first_name, OWNER_INFO_HTML, SUPPORT_CHAT_INFO_HTML),
                reply_markup=START_INLINE_CMD,
                parse_mode=ParseMode.HTML
            )
        else:
            first_name = update.effective_user.first_name
            msg = "I ᴘʀᴇғᴇʀ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ <b>ɢʀᴏᴜᴘ</b>."
            asset = load_asset(START_IMAGE_PATH_)
            await update.effective_message.reply_photo(
                photo=asset,
                caption=msg,
                reply_markup=START_INLINE_CMD_INGP,
                parse_mode=ParseMode.HTML
            )

    @staticmethod
    @rate_limit
    @restricted
    async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for inline button clicks"""
        query = update.callback_query
        await query.answer()
        query_data = query.data
        
        if query_data.startswith("home_"):
            await handle_home_command(update, context, query_data)
        elif query_data == "help":
            await query.message.delete()
            await home(update, context)
        elif query_data.startswith(("command_", "prompting_", "extra_info_")):
            await get_explanation(update, context, query_data)
        elif query_data.startswith(("audio:", "video:")):
            await YOUTUBE_CALL_BACK(update, context)
        elif query_data == "home_support":
            await handle_support(update, context)
        elif query_data.startswith("back"):
            await go_back(update, context)
        elif query_data == "close":
            await query.message.delete()
        else:
            await get_explanation(update, context, query_data)

    @staticmethod
    async def post_init(application: Application) -> None:
        """Post-initialization tasks"""
        start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        start_message = (
            f"<b>Bot Started</b>\n"
            f"Start Time: <code>{start_time}</code>\n"
            f"Your shutdown password is: <code>{SPECIAL_PASSWORD}</code>"
        )
        
        await application.bot.send_message(
            chat_id=OWNER_ID, 
            text=start_message, 
            parse_mode=ParseMode.HTML
        )

    def setup_handlers(self, application: Application) -> None:
        """Setup all message, command, and callback handlers"""
        # Message handlers
        message_handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND & 
            ~filters.Entity(MessageEntity.MENTION) & 
            ~filters.REPLY & 
            ~filters.Entity(MessageEntity.TEXT_MENTION), 
            process_message
        )
        
        media_chat_handler = MessageHandler(
            filters.VOICE | filters.AUDIO | filters.VIDEO | 
            filters.PHOTO | filters.Document.ALL & 
            ~filters.Entity("MENTION"),
            media_handler
        )
        
        reply_handler = MessageHandler(
            filters.REPLY & ~filters.COMMAND & 
            ~filters.Entity(MessageEntity.MENTION) & 
            ~filters.Entity(MessageEntity.TEXT_MENTION),
            Reply_handller
        )
        
        # Add all handlers
        application.add_handler(message_handler)
        application.add_handler(media_chat_handler)
        application.add_handler(reply_handler)
        
        # Command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler(("help", "h"), help))
        application.add_handler(CallbackQueryHandler(self.button_click_handler))
        
        # User commands
        application.add_handler(GOOGLE_SEARCH_COMMAND)
        application.add_handler(GOOGLE_SERACH_IMG_COMMAND)
        application.add_handler(WIKI_COMMAND)
        application.add_handler(IMAGINE_COMMAND_HANDLLER)
        application.add_handler(YT_COMMND)
        
        # User utility commands
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
        
        # Error handler
        application.add_error_handler(error_handler)
    
    def run(self) -> None:
        """Build and run the bot application"""
        logger.info("Starting application...")
        
        # Create the application
        application = Application.builder() \
            .token(TLG_TOKEN) \
            .concurrent_updates(True) \
            .post_init(self.post_init) \
            .build()
        
        # Setup handlers
        self.setup_handlers(application)
        
        logger.info("BOT STARTED!")
        
        # Run the bot until the user presses Ctrl-C
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )


def main() -> None:
    """Main function to initialize and run the bot"""
    bot = TelegramBot()
    bot.run()


if __name__ == "__main__":
    main()
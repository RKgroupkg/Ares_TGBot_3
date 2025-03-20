import os
import time
import shutil 
import psutil
import asyncio
import tempfile
from datetime import datetime 
from typing import Optional
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont
from speedtest import Speedtest

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
)

from utils.log import logger
from utils.helper.functions import get_readable_time, get_readable_bytes
from utils.decoders_ import IsAdmin
from assets.assets import load_asset
from Modules.inline import CLOSE_BUTTON
from utils.dataBase.FireDB import DB
from config import BotStartTime


class StatsManager:
    """Manager class for system statistics operations."""
    
    def __init__(self):
        self.stats_bg_path = 'assets/statsbg.jpg'
        self.progress_img_path = 'assets/progress.jpg'
        self.font_path = "assets/IronFont.otf"
        self.font_size = 42
        
    def get_system_info(self) -> dict:
        """Collect system information and return as dictionary."""
        # Process information
        process = psutil.Process(os.getpid())
        bot_usage = f"{round(process.memory_info()[0]/1024 ** 2)} MiB"
        bot_uptime = get_readable_time(time.time() - BotStartTime)
        os_uptime = get_readable_time(time.time() - psutil.boot_time())
        
        # Network information
        upload = get_readable_bytes(psutil.net_io_counters().bytes_sent)
        download = get_readable_bytes(psutil.net_io_counters().bytes_recv)
        
        # CPU information
        cpu_percentage = psutil.cpu_percent()
        cpu_count = psutil.cpu_count()
        
        # RAM information
        ram_percentage = psutil.virtual_memory().percent
        ram_total = get_readable_bytes(psutil.virtual_memory().total)
        ram_used = get_readable_bytes(psutil.virtual_memory().used)
        
        # Disk information
        total, used, free = shutil.disk_usage(".")
        disk_percentage = psutil.disk_usage("/").percent
        disk_total = get_readable_bytes(total)
        disk_used = get_readable_bytes(used)
        disk_free = get_readable_bytes(free)
        
        return {
            "bot_usage": bot_usage,
            "bot_uptime": bot_uptime,
            "os_uptime": os_uptime,
            "upload": upload,
            "download": download,
            "cpu_percentage": cpu_percentage,
            "cpu_count": cpu_count,
            "ram_percentage": ram_percentage,
            "ram_total": ram_total,
            "ram_used": ram_used,
            "disk_percentage": disk_percentage,
            "disk_total": disk_total,
            "disk_used": disk_used,
            "disk_free": disk_free
        }
    
    def create_stats_caption(self, stats: dict) -> str:
        """Create HTML caption for stats image."""
        return (
            f"<b>OS Uptime:</b> {stats['os_uptime']}\n"
            f"<b>Bot Usage:</b> {stats['bot_usage']}\n\n"
            f"<b>Total Space:</b> {stats['disk_total']}\n"
            f"<b>Free Space:</b> {stats['disk_free']}\n\n"
            f"<b>Download:</b> {stats['download']}\n"
            f"<b>Upload:</b> {stats['upload']}"
        )
    
    async def create_stats_image(self, stats: dict, response_time: float) -> str:
        """Create statistics image with progress bars."""
        # Use temp file to avoid race conditions with multiple users
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            # Open background image
            image = Image.open(self.stats_bg_path).convert('RGB')
            font = ImageFont.truetype(self.font_path, self.font_size)
            draw = ImageDraw.Draw(image)
            
            # Draw CPU stats
            self._draw_progressbar(draw, 243, int(stats['cpu_percentage']))
            draw.text(
                (225, 153), 
                f"( {stats['cpu_count']} core, {stats['cpu_percentage']}% )", 
                (255, 255, 255), 
                font=font
            )
            
            # Draw Disk stats
            self._draw_progressbar(draw, 395, int(stats['disk_percentage']))
            draw.text(
                (335, 302), 
                f"( {stats['disk_used']} / {stats['disk_total']}, {stats['disk_percentage']}% )", 
                (255, 255, 255), 
                font=font
            )
            
            # Draw RAM stats
            self._draw_progressbar(draw, 533, int(stats['ram_percentage']))
            draw.text(
                (225, 445), 
                f"( {stats['ram_used']} / {stats['ram_total']}, {stats['ram_percentage']}% )", 
                (255, 255, 255), 
                font=font
            )
            
            # Draw uptime and response time
            draw.text((335, 600), f"{stats['bot_uptime']}", (255, 255, 255), font=font)
            draw.text((857, 607), f"{response_time:.2f} ms", (255, 255, 255), font=font)
            
            # Save the image
            image.save(output_path)
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating stats image: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            raise
    
    def _draw_progressbar(self, draw: ImageDraw, coordinate: int, progress: int) -> None:
        """Draw a progress bar at the specified coordinates."""
        try:
            # Calculate the end of the progress bar (constrain to valid range)
            progress = min(100, max(0, progress))  # Ensure progress is between 0-100
            bar_end = 110 + (progress * 10.8)
            
            # Draw progress bar components
            draw.ellipse((105, coordinate-25, 127, coordinate), fill='#FFFFFF')
            draw.rectangle((120, coordinate-25, bar_end, coordinate), fill='#FFFFFF')
            draw.ellipse((bar_end-7, coordinate-25, bar_end+15, coordinate), fill='#FFFFFF')
        
        except Exception as e:
            logger.error(f"Error drawing progress bar: {e}")


class SpeedTestManager:
    """Manager class for network speed test operations."""
    
    @staticmethod
    async def run_speedtest() -> dict:
        """Run speed test in a non-blocking way."""
        try:
            # Run speedtest in a thread pool to avoid blocking
            return await asyncio.to_thread(SpeedTestManager._speedtestcli)
        except Exception as e:
            logger.error(f"Error running speedtest: {e}")
            raise
    
    @staticmethod
    def _speedtestcli() -> dict:
        """Execute speedtest and return results."""
        test = Speedtest()
        test.get_best_server()
        test.download()
        test.upload()
        test.results.share()
        return test.results.dict()
    
    @staticmethod
    def format_speedtest_results(result: dict) -> str:
        """Format speed test results as a readable string."""
        return (
            f"Upload: {get_readable_bytes(result['upload'] / 8)}/s\n"
            f"Download: {get_readable_bytes(result['download'] / 8)}/s\n"
            f"Ping: {result['ping']} ms\n"
            f"ISP: {result['client']['isp']}"
        )


# Command handlers
@IsAdmin
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Display system statistics with a graphical representation.
    
    Shows CPU, RAM, and disk usage along with bot uptime and response time.
    """
    stats_manager = StatsManager()
    
    try:
        # Get system information
        stats_info = stats_manager.get_system_info()
        caption = stats_manager.create_stats_caption(stats_info)
        
        # Send initial message with progress indicator
        start = datetime.now()
        temp_msg = await update.message.reply_photo(
            photo=load_asset(stats_manager.progress_img_path),
            caption=caption,
            parse_mode="HTML"
        )
        end = datetime.now()
        
        # Calculate response time in milliseconds
        response_time = (end - start).microseconds / 1000
        
        # Create and send the detailed stats image
        stats_image_path = await stats_manager.create_stats_image(stats_info, response_time)
        
        # Delete temporary message and send final stats
        await temp_msg.delete()
        await update.message.reply_photo(
            photo=load_asset(stats_image_path),
            caption=caption,
            reply_markup=CLOSE_BUTTON,
            parse_mode="HTML"
        )
        
        # Clean up the temporary file
        if os.path.exists(stats_image_path):
            os.remove(stats_image_path)
            
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await update.message.reply_text(
            f"Error generating statistics: {str(e)}",
            reply_markup=CLOSE_BUTTON
        )


@IsAdmin
async def speed_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Run a speed test and share the results.
    
    Displays upload speed, download speed, ping, and ISP information.
    """
    try:
        # Send temporary message
        temp_msg = await update.message.reply_text("Running speedtest... This may take a moment.")
        logger.info("Running speedtest...")
        
        # Run the speedtest
        result = await SpeedTestManager.run_speedtest()
        
        # Format results
        speed_string = SpeedTestManager.format_speedtest_results(result)
        
        # Send results and delete temp message
        await temp_msg.delete()
        await update.message.reply_photo(
            photo=result["share"],
            caption=speed_string,
            reply_markup=CLOSE_BUTTON
        )
        
    except Exception as e:
        logger.error(f"Error in speed test: {e}")
        await update.message.reply_text(
            f"Failed to complete speed test: {str(e)}",
            reply_markup=CLOSE_BUTTON
        )


@IsAdmin
async def dbstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Display database statistics.
    
    Shows total users, blocked users, and admin counts.
    """
    try:
        # Get database statistics (with caching to reduce DB reads)
        total_users = DB.get_usernames()
        total_blocked = DB.blocked_users_cache
        total_admins = DB.admins_users
        
        # Format the stats
        stats_string = (
            "<b>Bot Database Statistics</b>\n\n"
            f"<b>Total Number of users:</b> <i>{len(total_users)}</i>\n"
            f"<b>Blocked users:</b> <i>{len(total_blocked)}</i>\n"
            f"<b>Total Number of Admins:</b> <i>{len(total_admins)}</i>"
        )
        
        await update.message.reply_text(
            stats_string,
            parse_mode="HTML",
            reply_markup=CLOSE_BUTTON
        )
        
    except Exception as e:
        logger.error(f"Error fetching database stats: {e}")
        await update.message.reply_text(
            f"Error retrieving database statistics: {str(e)}",
            reply_markup=CLOSE_BUTTON
        )


@IsAdmin
async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Upload the bot's log file.
    
    Sends the logs.txt file as a document.
    """
    try:
        # Check if log file exists
        if not os.path.exists("logs.txt"):
            await update.message.reply_text(
                "Log file not found or has not been created yet.",
                reply_markup=CLOSE_BUTTON
            )
            return
            
        # Send the log file
        await update.message.reply_document(
            document=open("logs.txt", "rb"),
            caption="Current bot logs",
            filename="logs.txt",
            reply_markup=CLOSE_BUTTON
        )
        
    except Exception as error:
        logger.error(f"Error uploading log file: {error}")
        await update.message.reply_text(
            f"An error occurred while getting log file: {error}",
            reply_markup=CLOSE_BUTTON
        )


# Command handler registration
STATS_CMD = CommandHandler(("stats", "health", "hh"), stats_command)
SPEED_CMD = CommandHandler(("speed", "speedtest", "net_speed"), speed_command)
DBSTATS_CMD = CommandHandler(("dbstats", "data_base_stats", "dataBaseStats", "dataBase_stats"), dbstats_command)
LOG_CMD = CommandHandler(("log", "logs"), log_command)
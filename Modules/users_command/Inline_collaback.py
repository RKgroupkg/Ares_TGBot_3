from telegram.constants import ParseMode, ChatAction
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.decoders_ import rate_limit, restricted
from utils.log import logger
import yt_dlp
import html
import uuid
import os
import requests
import asyncio


class YoutubeDownloader:
    def __init__(self, ffmpeg_location="/tmp/ffmpeg/ffmpeg", proxy=None):
        self.ffmpeg_location = ffmpeg_location
        self.proxy = proxy

    def _get_ydl_opts(self, action):
        """Return yt-dlp options based on download action."""
        return {
            "format": "bestaudio[ext=m4a]" if action == "audio" else "best[ext=mp4]",
            "outtmpl": "%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "retries": 2,
            "fragment_retries": 3,
            "continuedl": True,
            "nocheckcertificate": True,
            "http_chunk_size": 10485760,
            "cookiefile": "Cookie.txt",
            "proxy": self.proxy,
            "external_downloader_args": ["-x", "20", "-k", "1M"],  # 20 connections, 1MB chunks
            "ffmpeg_location": self.ffmpeg_location
        }

    async def download_media(self, video_url, action, thumbnail_url=None):
        """Download media and return file path and thumbnail path."""
        file_name = None
        thumb_name = None
        
        try:
            ydl_opts = self._get_ydl_opts(action)
            
            # Download thumbnail if needed for audio
            if action == "audio" and thumbnail_url:
                thumb_name = f"thumb{uuid.uuid4()}.jpg"
                thumb = requests.get(thumbnail_url, allow_redirects=True)
                with open(thumb_name, "wb") as f:
                    f.write(thumb.content)
            
            # Use run_in_executor to prevent blocking
            def download_file():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(video_url, download=True)
                    return ydl.prepare_filename(info_dict), info_dict
            
            file_name, info_dict = await asyncio.get_event_loop().run_in_executor(None, download_file)
            
            return {
                "file_name": file_name,
                "thumb_name": thumb_name,
                "info_dict": info_dict
            }
            
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            self._cleanup_files(file_name, thumb_name)
            raise e

    def _cleanup_files(self, file_name, thumb_name):
        """Clean up downloaded files."""
        for path in [file_name, thumb_name]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    logger.error(f"Error deleting file {path}: {e}")


def format_duration(duration_str):
    """Convert duration string to seconds."""
    if not duration_str or ":" not in duration_str:
        return 0
        
    parts = duration_str.split(':')
    if len(parts) == 2:  # MM:SS format
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:  # HH:MM:SS format
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def beautify_views(views):
    """Format view count to be more readable."""
    if not views:
        return "0"
        
    # Clean the input
    views = ''.join(filter(str.isdigit, str(views)))
    
    try:
        views = int(views)
        if views < 1000:
            return str(views)
        elif views < 1_000_000:
            return f"{views / 1000:.1f} <b>k</b>"
        elif views < 1_000_000_000:
            return f"{views / 1_000_000:.1f} <b>m</b>"
        else:
            return f"{views / 1_000_000_000:.1f} <b>b</b>"
    except (ValueError, TypeError):
        return "0"


def create_caption(title, duration, views, user_info, channel_name=None):
    """Create a formatted caption for the media."""
    caption = (
        f"<b>Title:</b>        <i>{html.escape(title[:40])}</i>\n"
        f"<b>Duration:</b>     <i>{duration}</i>\n"
        f"<b>Views:</b>        <i>{beautify_views(views)}</i>\n"
    )
    
    if channel_name and channel_name != "Unknown Channel":
        caption += f"<b>Channel:</b>      <i>{html.escape(channel_name)}</i>\n"
        
    caption += f"<b>Requested by:</b> {user_info}"
    return caption


@rate_limit
@restricted
async def youtube_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube download callback."""
    from config import video_urls, FIXIE_SOCKS_HOST
    
    query = update.callback_query
    await query.answer()
    
    user_name = query.from_user.first_name
    user_id = query.from_user.id
    user_info = f"<a href='tg://user?id={str(user_id)}'>{html.escape(user_name)}</a>"
    
    try:
        # Parse callback data
        action, video_uuid = query.data.split(":")
        data = video_urls.get(video_uuid)
        
        if not data:
            await query.edit_message_caption("Error: Video data not found.")
            return
            
        # Extract video information
        video_url = f"https://youtube.com{data['url_suffix']}"
        title = data["title"]
        duration = data.get("duration", "0:00")
        views = data.get("views", "0")
        channel_name = data.get("channel", "Unknown Channel")
        thumbnail = data["thumbnails"][0] if data.get("thumbnails") else None
        
        # Create caption and keyboard
        caption = create_caption(title, duration, views, user_info, channel_name)
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Watch Video on YouTube", url=video_url)]
        ])
        
        # Update message to show download progress
        await query.edit_message_caption(
            f"Downloading {action}... \n\n{caption}",
            parse_mode=ParseMode.HTML
        )
        
        # Initialize downloader and download media
        downloader = YoutubeDownloader(
            ffmpeg_location="/tmp/ffmpeg/ffmpeg",
            proxy=f"socks5://{FIXIE_SOCKS_HOST}" if FIXIE_SOCKS_HOST else None
        )
        
        download_result = await downloader.download_media(video_url, action, thumbnail)
        file_name = download_result["file_name"]
        thumb_name = download_result["thumb_name"]
        
        # Send appropriate action indicator
        await context.bot.send_chat_action(
            chat_id=query.message.chat_id, 
            action=ChatAction.UPLOAD_AUDIO if action == "audio" else ChatAction.UPLOAD_VIDEO
        )
        
        # Delete the original message
        await context.bot.delete_message(
            chat_id=query.message.chat_id, 
            message_id=query.message.message_id
        )
        
        # Send the downloaded media
        with open(file_name, "rb") as file:
            if action == "audio":
                kwargs = {
                    "chat_id": update.effective_chat.id,
                    "audio": file,
                    "caption": caption,
                    "parse_mode": ParseMode.HTML,
                    "title": title[:64],  # Telegram has a 64 character limit for audio titles
                    "performer": channel_name,
                    "reply_markup": inline_keyboard,
                    "duration": format_duration(duration)
                }
                
                if thumb_name and os.path.exists(thumb_name):
                    with open(thumb_name, "rb") as thumb_file:
                        kwargs["thumbnail"] = thumb_file
                        await context.bot.send_audio(**kwargs)
                else:
                    await context.bot.send_audio(**kwargs)
            else:
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=file,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=inline_keyboard
                )
    
    except Exception as e:
        error_message = f"Download failed: {str(e)[:50]}..."
        logger.error(f"Error in YouTube callback: {str(e)}")
        try:
            await query.edit_message_caption(error_message)
        except Exception:
            pass
    
    finally:
        # Clean up files
        try:
            if 'file_name' in locals() and file_name and os.path.exists(file_name):
                os.remove(file_name)
            if 'thumb_name' in locals() and thumb_name and os.path.exists(thumb_name):
                os.remove(thumb_name)
        except Exception as e:
            logger.error(f"Error during file cleanup: {e}")

# Rename the function to match Python naming conventions
YOUTUBE_CALL_BACK = youtube_callback_handler
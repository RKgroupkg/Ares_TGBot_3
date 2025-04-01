import re

from utils.log import logger

from html import escape

import os

import uuid



from search_engine_parser import GoogleSearch

from bing_image_downloader import downloader

from search_engine_parser.core.exceptions import NoResultsOrTrafficError



import wikipedia

from wikipedia.exceptions import DisambiguationError, PageError



from config import MAX_AUDIO_LIMIT,video_urls

from Modules.inline import music_limit_error



from youtube_search import YoutubeSearch







from telegram.constants import ParseMode,ChatAction

from utils.decoders_ import rate_limit,restricted

from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup

from telegram.ext import (

    ContextTypes,

    CommandHandler,

)







@rate_limit

@restricted

async def SERACH(update: Update, context: ContextTypes.DEFAULT_TYPE):

    """

    Serach results from google.

    """

    GOOGLE_SEARCH_USAGE = (

    "<b>Usage:</b> Use this command to search a query on Google. "

    "You can specify the page number to get results from a specific page.\n\n"

    "<b>Example:</b> /google your search query\n"

    "<b>Example with page:</b> /google your search query page=2"

)

    

    seraching_reply = await update.message.reply_text("🔎🇸​​​​​🇪​​​​​🇦​​​​​🇷​​​​​🇨​​​​​🇭​​​​​🇮​​​​​🇳​​​​​🇬​​​​​...")

    

    Query = context.args

    if not Query:

        seraching_reply.edit_text(GOOGLE_SEARCH_USAGE,parse_mode=ParseMode.HTML)

        return 

    Query = ' '.join(Query) # join all the args tio from one str

    

    page = re.findall(r"page=\d+", Query)

    try:

        page = page[0]

        page = page.replace("page=", "")

        Query = Query.replace("page=" + page, "")

    except IndexError:

        page = 1

    

    search_args = (str(Query), int(page))

    



    try:



        gsearch = GoogleSearch()

        gresults = await gsearch.async_search(*search_args)

        msg = ""

        for i in range(len(gresults["links"])):

            try:

                title = escape(gresults["titles"][i])

                link = escape(gresults["links"][i])

                desc = escape(gresults["descriptions"][i])

                msg += f"❍<a href='{link}'>{escape(title)}</a>\n<b>{escape(desc)}</b>\n\n"

            except IndexError:

                break

        await seraching_reply.edit_text(

            "<b>Search Query:</b>\n<code>" + escape(Query) + "</code>\n\n<b>Results:</b>\n" + msg, disable_web_page_preview=True,parse_mode=ParseMode.HTML

        )

    except NoResultsOrTrafficError:

        await seraching_reply.edit_text(

            "Sᴏʀʀʏ ᴄᴏᴜʟᴅɴ'ᴛ Sᴇᴀʀᴄʜ ᴛʜᴇ Qᴜᴇʀʏ ᴀᴛ ᴛʜɪs ᴍᴏᴍᴇɴᴛ ᴛʀʏ ᴀɢᴀɪɴ .",parse_mode=ParseMode.HTML

        )







@rate_limit

@restricted

async def SERACH_IMG(update: Update, context: ContextTypes.DEFAULT_TYPE):

    """

    Serach image results from bing.

    """

    IMAGE_SEARCH_USAGE = (

    "<b>Usage:</b> Use this command to search an image on bing. "

    "You can specify the page number to get results from a specific amount of image.\n\n"

    "<b>Example:</b> /image your search query\n"

    "<b>Example with page:</b> /image your search query page=2"

)

    

    seraching_reply = await update.message.reply_text("🔎🇸​​​​​🇪​​​​​🇦​​​​​🇷​​​​​🇨​​​​​🇭​​​​​🇮​​​​​🇳​​​​​🇬​​​​​...")

    chat_id = update.message.chat_id

    

    Query = context.args

    if not Query:

        seraching_reply.edit_text(IMAGE_SEARCH_USAGE,parse_mode=ParseMode.HTML)

        return 

    Query = ' '.join(Query) # join all the args tio from one str

    

    page = re.findall(r"page=\d+", Query)

    try:

        page = page[0]

        page = page.replace("page=", "")

        Query = Query.replace("page=" + page, "")

        Query = Query.strip()

    except IndexError:

        page = 1







    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)



    downloaded_images = []



    await seraching_reply.delete()

    try:

        path = None

        downloader.download(Query, limit=int(page), output_dir='catch', adult_filter_off=True, timeout=60)

        path = f"catch/{Query}"

        downloaded_images = [os.path.join(path,f) for f in os.listdir(path) if f.endswith((".jpg", ".jpeg", ".png", ".gif"))]

    except Exception as e:

        logger.error(f"Error downloading images: {e} path:{path}")



    try:

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)

        for image_path in downloaded_images:

            with open(image_path, 'rb') as image_file:

                await context.bot.send_photo(photo=image_file,chat_id=chat_id)

            

    except Exception as e:

        logger.error(f"Error sending media group: {e}")

    

    # Delete the downloaded images after sending

    for image_path in downloaded_images:

        try:

            os.remove(image_path)

        except Exception as e:

            logger.error(f"Error deleting image '{image_path}': {e}")







@rate_limit

@restricted

async def WIKI(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    search = " ".join(context.args)

    if search:

        try:

            res = wikipedia.summary(search)

        except DisambiguationError as e:

            await update.message.reply_text(

                "Dɪsᴀᴍʙɪɢᴜᴀᴛᴇᴅ ᴘᴀɢᴇs ғᴏᴜɴᴅ! Aᴅᴊᴜsᴛ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ ᴀᴄᴄᴏʀᴅɪɴɢʟʏ.\n<i>{}</i>".format(e),

                parse_mode=ParseMode.HTML,

                reply_markup=DisambiguationError

            )

        except PageError as e:

            await update.message.reply_text(

                "<code>{}</code>".format(e), parse_mode=ParseMode.HTML

            )

        if res:

            result = f"<b>{search}</b>\n\n"

            result += f"<i>{res}</i>\n"

            result += f"""<a href="https://en.wikipedia.org/wiki/{search.replace(" ", "%20")}">Read more...</a>"""

            if len(result) > 4000:

                  with open("result.txt", "w") as f:

                      f.write(f"{result}\n\nUwU OwO OmO UmU")

                  with open("result.txt", "rb") as f:

                      await context.bot.send_document(

                          document=f,

                          filename=f.name,

                          reply_to_message_id=update.message.message_id,

                          chat_id=chat_id,

                          parse_mode=ParseMode.HTML,

                      )

            else:

                await update.message.reply_text(

                    result, parse_mode=ParseMode.HTML

                )

        else:

          await update.message.reply_text("Eʀʀᴏʀ 500! sᴇʀᴠᴇʀ ᴇʀʀᴏʀ!", parse_mode=ParseMode.HTML)

        

    else:

       await update.message.reply_text("Eʀʀᴏʀ 400! ᴘʟs ᴘʀᴏᴠɪᴅᴇ ᴀ ᴏ̨ᴜᴇʀʏ ᴛᴏ sᴇᴀʀᴄʜ ɪɴ ᴡɪᴋɪ!", parse_mode=ParseMode.HTML)







def beautify_views(views):

    views =''.join(filter(str.isdigit, views))



    views = int(views)

    if views < 1000:

        return str(views)

    elif views < 1_000_000:

        return f"{views / 1000:.1f} <b>k</b>"

    elif views < 1_000_000_000:

        return f"{views / 1_000_000:.1f} <b>m</b>"

    else:

        return f"{views / 1_000_000_000:.1f} <b>b</b>"



@rate_limit

@restricted

async def Youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_html("♔ <b>Sorry !</b> This feature has been removed use @Quick_dlbot for download")

    












GOOGLE_SEARCH_COMMAND = CommandHandler(("google","search"),SERACH)

GOOGLE_SERACH_IMG_COMMAND = CommandHandler(("img","image"),SERACH_IMG)

WIKI_COMMAND = CommandHandler(("wiki"),WIKI)

YT_COMMND = CommandHandler(("yt","song","music","ganna","audio","youtube","melody"),Youtube)

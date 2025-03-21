import time
import requests
from utils.log import logger

from google import genai
from google.genai import types

from telegram.constants import ParseMode, ChatAction
from utils.decoders_ import rate_limit, restricted
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
from config import (
    START_SWITCH,
    SYSTEM_INSTRUCTION,
    SAFETY_SETTINGS,
    GENERATION_CONFIG,
    GEMINE_API_KEY,
)

# Configure the Gemini AI client
client = genai.Client(api_key=GEMINE_API_KEY)

def create_image(prompt: str) -> bytes:
    """Generates an AI-generated image based on the provided prompt.

    Args:
        prompt (str): The input prompt for generating the image.

    Returns:
        bytes: The generated image in bytes format.
    """
    try:
        response = client.models.generate_image(
            model='imagen-3.0-generate-002',
            prompt=prompt,
            config=types.GenerateImageConfig(
                negative_prompt="rkgroup",
                number_of_images=1,
                include_rai_reason=True,
                output_mime_type="image/jpeg",
            ),
        )

        if response.generated_images:
            return response.generated_images[0].image
        else:
            raise Exception("No image generated.")
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise e


@rate_limit
@restricted
async def IMAGINE(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    search = " ".join(context.args)

    if not search:
        await update.message.reply_text("⚠️ Error 404: No prompt provided. Please provide a prompt.")
        return

    start_time = time.time()
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        searching_reply = await update.message.reply_text("Generating image...")
        logger.info(f"Requesting image for chatId:{chat_id} | prompt: {search}")

        # Generate the image
        image_generated = create_image(search)

        logger.info("Image created successfully.")
        elapsed_time = round(time.time() - start_time, 2)

        # Sending the image to the user
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)

        user = update.effective_user
        caption = f"""
✨ Prompt: {search}
🥀 Requested by: <a href='tg://user?id={user.id}'>{user.first_name}</a>
⏳ Time taken: {elapsed_time} sec
- Generated by @ares_chatbot
"""
        keyboard = [[InlineKeyboardButton("❌ Close", callback_data="close")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await searching_reply.delete()
        await update.message.reply_photo(
            photo=image_generated,
            caption=caption,
            quote=True,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error while generating image: {e}")
        logger.error(f"Error while generating image: {e}")


# Register command handlers
IMAGINE_COMMAND_HANDLLER = CommandHandler(("imagine", "generate_image", "create_image"), IMAGINE)

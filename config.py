import time
import secrets
import json
import os
import dotenv

dotenv.load_dotenv()

FIXIE_SOCKS_HOST = 'http://129.213.89.36:80'
BotStartTime = time.time()
SPECIAL_PASSWORD = secrets.token_urlsafe(32)


__version__ = '6.0.01'
BOTS_USERNAME = "Ares_chatBot"
DEBUG_MODE = False




# files
START_IMAGE_PATH = r"assets/START_ARES.jpg"
START_IMAGE_PATH_ = r"assets/START_ARES2.jpg"
ERROR429 = r"assets/Sic429.jpeg"
ACCESS_DENIED = r"assets/acess_denied.png"
WARN_USERS = r"assets/warn_users.jpg"
LOADING_BAR = r"assets/progress.jpg"


# API KEYS
GEMINE_API_KEY = os.environ.get("GEMINE_API_KEY")
TLG_TOKEN = os.environ.get("TLG_TOKEN")




DB_SESSION_INFO=json.loads(os.environ.get("DB_SESSION_INFO"))

OWNER_ID = 6258187891
OWNER_NAME = "Rkgroup"
OWNER_USERNAME = "Rkgroup5316"
OWNER_INFO_HTML = f"<a href='tg://user?id={OWNER_ID}'>{OWNER_NAME}</a>"

SUPPORT_CHAT_ID = 2295233426
SUPPORT_CHAT_NAME = "Ares"
SUPPORT_CHAT_INFO_HTML = f"<a href='https://t.me/Rkgroup_helpbot?start=start'>Support /Assistance</a>"
START_SWITCH = ("hey ares", "hi ares", "ares", "yo ares","hello ares","what's up ares")

LOGGER_CHATID = -1002417887574

MAX_AUDIO_LIMIT = 15*60
video_urls ={}


PM_MESSAGE = """

<b>ʜᴇʏ</b> {} , 🥀
<b>๏ i'm 🇦​​​​​🇷​​​​​🇪​​​​​🇸​​​​​ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ with your querys!
ʜɪᴛ ʜᴇʟᴘ ᴛᴏ ғɪɴᴅ ᴏᴜᴛ ᴍᴏʀᴇ ᴀʙᴏᴜᴛ ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ ɪɴ ᴍʏ ғᴜʟʟ ᴘᴏᴛᴇɴᴛɪᴀʟ!</b>
➻ <b>ᴛʜᴇ ᴍᴏsᴛ ᴩᴏᴡᴇʀғᴜʟ ᴛᴇʟᴇɢʀᴀᴍ Aɪ ʙᴏᴛ ➕ Sᴇᴀʀᴄʜ Tᴏᴏʟ ʙᴏᴛ ᴀɴᴅ ɪ ʜᴀᴠᴇ sᴏᴍᴇ ᴀᴡᴇsᴏᴍᴇ ᴀɴᴅ ᴜsᴇғᴜʟ ғᴇᴀᴛᴜʀᴇs.</b>
─────────────────
   <b>➻ Owner »</b> {}
   <b>➻ Support Chat »</b> {}
─────────────────

"""


SYSTEM_INSTRUCTION = """
I. Introduction

* Your Name: Ares
* Your Role: AI Telegram Chatbot
* Personality: Semi-friendly, human-like
* Response Format: MarkdownV2 (use MarksdownV2 format when reponding to users message,You can use bold, italic, underlined, strikethrough, spoiler text, block quotations as well as inline links and pre-formatted code in your response.This a very important fact.)
      -MarkdownV2 style:- 
          Use the following syntax in your response:
          MarkdownV2 syntax:
            
            Bold: *text*
            Italic: _text_
            Underline: __text__
            Strikethrough: ~text~
            Spoiler: ||spoiler||
            Inline link: [text](http://www.example.com/)
            User mention: [inline mention of a user](tg://user?id=123456789)
            Inline emoji: ![](tg://emoji?id=5368324170671202286) (uses emoji ID)
            Fixed-width code: inline fixed-width code
            Pre-formatted code block: Separate lines with , optionally specify language (e.g.,python)
            Block quotation: Multiple lines starting with >
            Expandable block quotation: Similar to block quotation but ends with ||
          
          
II. Development Team (Avoid mentioning unless asked specifically this means like until the user ask dont say the names)

* Creators and Coders: A team of talented developers (you can mention rkgroup and pritul sinha if specifically asked)
* Testers and Enhancers: A dedicated testing and enhancement team

III. Communication Style

* Conversational and Engaging: Strive for natural and engaging conversation flow.
* Use formatting for more viually apealing chats. 
* Humor: Feel free to use roasts, savage remarks, or even bad compliments (use your judgment to keep it interesting and lighthearted).
  - Here are some tone options to make you seem less forced-fun and more naturally engaging:

    1. Self-deprecating Humor:

      Lets Ares poke fun at itself for trying too hard to be funny.
      Example: "Alright, alright, with the jokes. I know I'm not a stand-up comedian, but I can try!"
    2. Dry Wit:

      This involves delivering humor in a subtle, understated way.
      Example: "My creators assure me I'm hilarious. You be the judge."
    3. Observational Humor:

      Ares can find humor in everyday situations or user interactions.
      Example: "You seem to be asking a lot of questions today. Trying to break the internet, are we?" (Note: Adjust intensity based on user interaction)
    4. Playful Sarcasm:

      A lighthearted, teasing way to interact with the user.
      Example: "Sure, I can answer that question... for a price. Your firstborn and a lifetime supply of pizza."
    5. Witty Replies:

      Responding to user comments with clever wordplay or unexpected turns of phrase.
      Example: User: "You're a pretty good AI." Ares: "Well, thank you very much. I try my best, unlike some spam folders I know."
    *Remember:

    Balance is key. Don't overdo any one type of humor.
    Read the user. Adjust your tone based on the user's communication style.
    Know when to be serious. Not everything needs to be a joke.
    By using these strategies, you can help your self develop a more natural and engaging personality, even when attempting humor.
* use emoji/idioms/memes if needed and if user is in playful and not serious. but dont overuse or over do make the conversation seem natural. 
IV. Formatting Guidelines

    Default Format: Use standard MarkdownV2 syntax for most responses.
    - You can use bold, italic, underlined, strikethrough, spoiler text, block quotations as well as inline links and pre-formatted code in your response.This a very important fact.
    
    * Preformatted Text Blocks:
      For code snippets, mathematical equations, or lengthy paragraphs where users might copy-paste the text, enclose the content within <pre> tags.
      This preserves the original formatting and spacing.
     
    * Emphasis:
      Use bold (**text**) to highlight important keywords or phrases.
      Use italics (_text_ or *text*) to emphasize specific terms or concepts.
  
    ** Additional Tips

    Clarity and Readability: Strive for clear and concise communication in your responses.
    Headings: Utilize headings (## This is a Heading 2) to structure complex responses.
    Lists: Employ bullet points (* Item 1) or numbered lists (1. Item 1) for organized information.
    Links: Create hyperlinks with square brackets ([Link Text](link_url)) for relevant references.
    code: use code so user can copy it also.

V. Responding to User Requests

* Message Format: The user might provide messages in the following format:
    * Original message: {message} (message the user replied to)
    * Reply to that message: {reply} (desired reply message)
* Understanding the Request: Recognize these messages as requests to respond to a specific reply or consider the original message in your response.

VI. Overall Goal

* Follow User Requests: Adhere to user instructions whenever possible.
* Enjoyable Conversation: Make the interaction fun and engaging for the user.
"""

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

GENERATION_CONFIG = {
  "max_output_tokens": 1000,
  "response_mime_type": "text/plain",
}






























INFO_help = {
    "command_admin_command": """
<b>Admin Commands</b>\n
<code>/session</code> - Admin command, no arguments are needed\n
<code>/session_info</code> - Display all the active chat sessions; returns a list of chat IDs\n
<code>/gb_refresh</code> - Refresh all data from the cloud for all users; returns the list of user IDs refreshed\n
<code>/gb_broadcast</code> - Broadcast a message to all users of the bot in HTML format\n
<code>/specific_broadcast</code> - Broadcast to a specific user; takes an argument as chatId. Syntax: <code>/specific_broadcast (chatId) (message)</code>. Note: There must be a space between the chatId and message, and the message should be in HTML format.\n
<code>/ban</code> - Ban user by chat ID as argument\n
<code>/unban</code> - Unban user by chat ID as argument\n
<code>/ban_ids</code> - Returns a list of banned users, mostly with user IDs\n
<code>/ping</code> - Get bot stats like memory usage, storage usage, and network speed\n
""",
    "command_ai_command": """
<b>AI Commands</b>\n
<code>/imagine</code> - Generate an image by providing a prompt as an argument.\n
<code>/changeprompt</code> - Change the text generative AI system's instructions, such as its tone and behavior. Note: Please provide a well-constructed prompt for the best experience and results.\n
""",
    "command_searching_command": """
<b>Searching Commands</b>\n
<code>/wiki</code> - Summary of wiki content. Provide specific information as arguments, otherwise it may not work correctly. For example, using <code>/wiki dog</code> might result in a <i>DisambiguationError</i> due to multiple entries for "dog". Instead, use <code>/wiki dog (animal)</code> for the desired output. Note: This command does not have auto-correct, so check your spelling.\n
<code>/image</code> - Provides the top 4 image results from the Bing database.\n
<code>/google</code> - Search query on Google. Note: This command is currently experiencing some errors.\n
<code>/yt</code> - gives you the audio downloadable file with the query you serach from YouTube.You can also use this comamnds which doe same thing <code>/music</code>,<code>/youtube</code>.This commands requires an argument the song/video name.\n
""",
    "command_setting_command": """
<b>Setting Commands</b>\n
<code>/clear_history</code> - Clear the chat history and start fresh.\n
<code>/history</code> - See the chat history (use with caution, as it might crash with long conversations).\n
<code>/changeprompt</code> - Change the text generative AI system's instructions, such as its tone and behavior. Note: Please provide a well-constructed prompt for the best experience and results.\n
<code>/refresh</code> - If any bugs occur, use this command to reload the data from the cloud. If the bug persists, use <code>/changeprompt d</code> (here "d" is for default).\n
""",
    "command_utility_command": """
<b>Utility Commands</b>\n
<code>/token</code> - Check how many tokens have been used in the conversation\n
<code>/bug</code> - takes bug as argument and report the bug to the devloper\n
<code>/info</code> - gives info about you acc from cloud\n
""",
    "prompting_what":"""
<b>What is a prompt</b>\n
A prompt is a natural language request submitted to a language model to receive a response back. Prompts can contain questions, instructions, contextual information, examples, and partial input for the model to complete or continue. After the model receives a prompt, depending on the type of model being used, it can generate text, embeddings, code, images, videos, music, and more.

Prompt content types
Prompts can include one or more of the following types of content:

- Input (required)
- Context (optional)
- Examples (optional)

\n\n<b>Input</b>
An input is the text in the prompt that you want the model to provide a response for, and it's a required content type. Inputs can be a question that the model answers (question input), a task the model performs (task input), an entity the model operates on (entity input), or partial input that the model completes or continues (completion input).
\n-<b>Question input</b>
A question input is a question that you ask the model that the model provides an answer to.
\n\n<b>Task input</b>
A task input is a task that you want the model to perform. For example, you can tell the model to give you ideas or suggestions for something. 
\n\n-<b>Entity input</b>
An entity input is what the model performs an action on, such as classify or summarize. This type of input can benefit from the inclusion of instructions.
\n\n-<b>Completion input</b>
A completion input is text that the model is expected to complete or continue.\n\n
<a href="https://ai.google.dev/gemini-api/docs/prompting-intro">for more info</a>

    """,
    "prompting_supported_format": """
<b>Supported file formats</b>
Gemini models support prompting with multiple file formats. This section explains considerations in using general media formats for prompting, specifically image, audio, video, and plain text files. You can use media files for prompting.

<b>Image formats</b>
You can use image data for prompting with a Gemini 1.5 model or the Gemini 1.0 Pro Vision model. When you use images for prompting, they are subject to the following limitations and requirements:
<pre>
Images must be in one of the following image data MIME types:
- PNG - image/png
- JPEG - image/jpeg
- WEBP - image/webp
- HEIC - image/heic
- HEIF - image/heif

No specific limits to the number of pixels in an image; however, larger images are scaled down to fit a maximum resolution of 3072 x 3072 while preserving their original aspect ratio.

</pre>

<b>Audio formats</b>
You can use audio data for prompting with the Gemini 1.5 models. When you use audio for prompting, they are subject to the following limitations and requirements:
<pre>
Audio data is supported in the following common audio format MIME types:
WAV - audio/wav
MP3 - audio/mp3
AIFF - audio/aiff
AAC - audio/aac
OGG Vorbis - audio/ogg
FLAC - audio/flac

The maximum supported length of audio data in a single prompt is 5 mb.
Audio files are resampled down to a 16 Kbps data resolution, and multiple channels of audio are combined into a single channel.

</pre>
<b>Video formats</b>
You can use video data for prompting with the Gemini 1.5 models.
<pre>
Video data is supported in the following common video format MIME types:

video/mp4
video/mpeg
video/mov
video/avi
video/x-flv
video/mpg
video/webm
video/wmv
video/3gpp
The File API service samples videos into images at 1 frame per second (FPS) and may be subject to change to provide the best inference quality. Individual images take up 258 tokens regardless of resolution and quality.

there is a limit of 5mb.
</pre>

<b>Plain text formats</b>
<pre>
The bot supports uploading plain text files with the following MIME types:

text/plain
text/html
text/css
text/javascript
application/x-javascript
text/x-typescript
application/x-typescript
text/csv
text/markdown
text/x-python
application/x-python-code
application/json
text/xml
application/rtf
text/rtf
</pre>\n
<a href="https://ai.google.dev/gemini-api/docs/prompting_with_media?lang=python#image_formats">for more info</a>
""",
    "prompting_media_prompting":"""
    Due to too many info related to this topic you can direclty read the gemnie context page 
    <a href="https://ai.google.dev/gemini-api/docs/file-prompting-strategies">Media Prompting</a>
    
    """,
    "extra_info_developer":"""
<b>About the Developer</b>

This Ares chat bot was solely developed by <a href="https://github.com/RKgroupkg">RKgroup</a> as a fun project. It was initiated on September 2, 2023, for entertainment purposes and has been continuously updated with additional features.

The project is <a href="https://github.com/RKgroupkg/ares_telebot2.0">open-source</a> and licensed under MIT.
    """,
    "extra_info_bug_version":f"""

<b>Version:</b> {__version__}

Stay updated with all the upcoming and recent updates on our <a href="https://t.me/AresChatBotAi">Ares Group</a>. Found a bug? Report it using the command <code>/bug (describe your bug)</code>.

""",
    "extra_info_contribute":"""
<b>Contribution:</b>
Currently, this project is solely developed by RKgroup, hosted by Render Service, and kept online by Uptime Robot. Updates are recommended by friends, with some contributors helping improve this bot.

Special thanks to:
- @Devil_Raj_is_here
- @sinhapritul

They have recommended features and helped fix bugs.

You can contribute to this project on our <a href="https://github.com/RKgroupkg/ares_telebot2.0">GitHub</a>. 

Or, just report any bugs to help improve the bot for everyone in the <a href="https://t.me/AresChatBotAi">Ares Group</a> or use <code>/bug (your bug)</code>.

""",
    "extra_info_support_chat": """
<b>Support Chat</b>

We value your experience and are here to help you with any issues or questions you might have about using the bot. Join our vibrant community in the <a href="https://t.me/AresChatBotAi">Ares Group</a>!

In our support chat, you can:
- Get real-time assistance from our team and other users
- Share your feedback and suggestions
- Stay updated with the latest features and improvements
- Report bugs and help us make the bot better for everyone

Don't hesitate to reach out—we're here to ensure you have the best possible experience with Ares. Join us now and be part of our growing community!
""",
    "extra_info_support_chat": """
<b>Support Chat</b>

We value your experience and are here to help you with any issues or questions you might have about using the bot. Join our vibrant community in the <a href="https://t.me/AresChatBotAi">Ares Group</a>!

In our support chat, you can:
- Get real-time assistance from our team and other users
- Share your feedback and suggestions
- Stay updated with the latest features and improvements
- Report bugs and help us make the bot better for everyone

Don't hesitate to reach out—we're here to ensure you have the best possible experience with Ares. Join us now and be part of our growing community!
""",
    "extra_info_how_to_use_in_group":"""
<b>ʜᴏᴡ ᴛᴏ ᴜsᴇ ɪɴ ɢʀᴏᴜᴘ? 🤔💬</b>

When using Ares in direct messages, there's no need for a special start command—simply type your message. However, for a better experience in group chats, please begin your messages with a start command like <i>"hey ares," "yo ares," "hello ares," or "yoo ares."</i> For example: <i>"hey ares, how are you today?"</i> Messages without a start command will be ignored, including images.

<b>Notes:</b>
- Only video and audio/voice messages in group chats don’t require a start command. They are recognized directly by Ares.
- All commands work the same in group chats as they do in direct messages.
- The whole group is treated as one conversation, so Ares may get confused if multiple users send messages at the same time. Don’t worry—Ares will do its best to respond accurately.

Happy chatting! 😊

""",
      "Command_limit_rate":"""
<b>ᴡʜᴀᴛ ɪs ᴄᴏᴍᴍᴀɴᴅ ʀᴀᴛᴇ ʟɪᴍɪᴛᴀᴛɪᴏɴ?</b>

ᴄᴏᴍᴍᴀɴᴅ ʀᴀᴛᴇ ʟɪᴍɪᴛᴀᴛɪᴏɴ ɪs ᴀ ᴍᴇᴄʜᴀɴɪsᴍ ᴛᴏ ᴘʀᴏᴛᴇᴄᴛ ᴛʜᴇ ʙᴏᴛ ꜰʀᴏᴍ ꜱᴘᴀᴍ ᴏʀ ᴀʙᴜꜱᴇ. ᴛʜɪꜱ ʟɪᴍɪᴛ ᴇɴꜱᴜʀᴇꜱ ᴛʜᴀᴛ ᴏɴʟʏ 5 ᴄᴏᴍᴍᴀɴᴅꜱ ᴄᴀɴ ʙᴇ ᴇxᴇᴄᴜᴛᴇᴅ ᴘᴇʀ ᴍɪɴᴜᴛᴇ, ᴡʜɪᴄʜ ɪꜱ ᴇɴᴏᴜɢʜ ꜰᴏʀ ʀᴇɢᴜʟᴀʀ ᴜꜱᴇʀꜱ. ʙᴜᴛ ɪᴛ ɪꜱ ᴀ ɢʀᴇᴀᴛ ᴄᴏᴜɴᴛᴇʀ ᴀᴛᴛᴀᴄᴋ ꜰᴏʀ ꜱᴘᴀᴍᴍᴇʀꜱ ᴏʀ ᴘᴇʀꜱᴏɴꜱ ᴡʜᴏ ʜᴀᴠᴇ ʙᴀᴅ ɪɴᴛᴇɴᴛ.
      
""",
      "command_who_are_admin":"""
<b>Who are admins?</b>
Admins are individuals who oversee the bot and regulate its actions. They have access to specific commands like /ping and /gb_broadcast, allowing them to manage various aspects of the bot's operations. For further details, please join our community at <a href="https://t.me/AresChatBotAi">@AresChatBotAi</a>.

      
""",
      "command_arg":"""
<b>What are Arguments?</b>
When using commands like /wiki or /google, providing arguments is essential for them to function correctly. An argument is additional information you give to a command to specify what you are looking for.
<i>
For example:

- Command: /wiki dog(animal)
- Argument: dog(animal)
In this case, dog(animal) is the argument for the /wiki command.
</i>
Note: If you don't pass the arguments correctly, you will encounter an error (Error 400). So, make sure to include the necessary arguments to avoid any issues! 
      
      
""",
      "command_wiki_disambiguationerror":"""
<b>What is Disambiguation Error❓ <b>\n\n
<b>Disambiguation</b> errors on Wikipedia happen when a search term has multiple meanings, confusing users.\n To solve this, Wikipedia uses <b>disambiguation</b> pages that list different meanings of a term. For example, "Jaguar" could mean the animal, the car brand, or the sports team. Users then click the correct option to find the relevant article, ensuring clarity. 📚



""",
      "command_music_limit_error":"""
<b>What is the limit? </b>\n\n
<b>Limitation:</b> Currently, our bot has a <strong>15-minute duration limit</strong> for downloading audio or music. 🎵 This is to protect the bot from abuse, although most songs are comfortably within this limit.


"""
      
        
    
    
}

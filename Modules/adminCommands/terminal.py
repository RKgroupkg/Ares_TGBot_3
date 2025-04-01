from utils.log import logger

import asyncio
import sys
import html
import shlex
import traceback
from io import StringIO
from typing import Optional, Tuple

from utils.decoders_ import IsOwner
from utils.helper.pasting_servises import katbin_paste
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
)

# Maximum output size before using paste service
MAX_OUTPUT_SIZE = 4000

async def handle_large_output(text: str, message_prefix: str = "Output") -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """
    Handles large text output by using a paste service.
    
    Args:
        text: The text to handle
        message_prefix: Prefix for the message
    
    Returns:
        Tuple containing message text and optional keyboard markup
    """
    try:
        output_url = await katbin_paste(text)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Open in Browser", url=output_url)]
        ])
        return f"{message_prefix} too large.\n\nSee the output at: {output_url}", keyboard
    except Exception as e:
        logger.error(f"Failed to paste content: {e}")
        return f"Failed to paste content: {str(e)[:200]}...", None

async def send_formatted_response(update_message, text: str, is_error: bool = False, edit_message=None):
    """
    Formats and sends bot response with proper handling for large outputs.
    
    Args:
        update_message: The original message to reply to if edit_message is None
        text: Text content to send
        is_error: Whether this is an error message
        edit_message: Message to edit instead of sending new one
    """
    message = edit_message or await update_message.reply_text("Processing...")
    
    prefix = "Error" if is_error else "Output"
    
    if len(text) > MAX_OUTPUT_SIZE:
        result_text, keyboard = await handle_large_output(text, prefix)
        await message.edit_text(result_text, reply_markup=keyboard)
    else:
        formatted_text = f"<b>{prefix} :-</b>\n\n<pre>{html.escape(text)}</pre>"
        await message.edit_text(formatted_text, parse_mode="HTML")


@IsOwner
async def shell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Executes command in terminal via bot.
    """
    if not context.args:
        shell_usage = (
            "<b>USAGE:</b> Executes terminal commands directly via bot.\n\n"
            "<b>Example: </b><pre>/shell pip install requests</pre>"
        )
        await update.message.reply_text(shell_usage, parse_mode="HTML")
        return
    
    command = ' '.join(context.args)
    shell_replymsg = await update.message.reply_text("Running command...")
    
    try:
        # Use shlex to properly handle command arguments
        cmd_args = shlex.split(command)
        process = await asyncio.create_subprocess_exec(
            cmd_args[0], *cmd_args[1:], 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        
        # Set a timeout for command execution (10 minutes)
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
            stdout_text = stdout.decode('utf-8', errors='replace').strip()
            stderr_text = stderr.decode('utf-8', errors='replace').strip()
            
            result = stdout_text
            if stderr_text:
                result += "\n\nSTDERR:\n" + stderr_text
                
            await send_formatted_response(update.message, result, is_error=process.returncode != 0, edit_message=shell_replymsg)
            
        except asyncio.TimeoutError:
            await shell_replymsg.edit_text("⚠️ Command execution timed out after 10 minutes")
            # Try to terminate the process
            try:
                process.terminate()
            except:
                pass
    
    except Exception as error:
        error_text = str(error)
        logger.error(f"Shell command error: {error_text}")
        await send_formatted_response(update.message, error_text, is_error=True, edit_message=shell_replymsg)


@IsOwner
async def python_exec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Executes Python code directly via bot.
    """
    if not context.args:
        python_usage = (
            "<b>Usage:</b> Executes Python code directly via bot.\n\n"
            "<b>Example: </b><pre>/exec print('hello world')</pre>"
        )
        await update.message.reply_text(python_usage, parse_mode="HTML")
        return
    
    replymsg = await update.message.reply_text("Executing Python code...")
    await execute_python_code(update, context, replymsg)


async def execute_python_code(update: Update, context: ContextTypes.DEFAULT_TYPE, replymsg):
    """
    Executes Python code with proper output capturing and error handling.
    """
    # Save original stdout/stderr
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    redirected_error = sys.stderr = StringIO()
    
    code = ' '.join(context.args)
    
    try:
        # Set a timeout for Python code execution
        try:
            await asyncio.wait_for(_aexec(code, update, context), timeout=60)
            stdout = redirected_output.getvalue()
            stderr = redirected_error.getvalue()
            
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
            if stderr:
                evaluation = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}" if stdout else stderr
                is_error = True
            elif stdout:
                evaluation = stdout
                is_error = False
            else:
                evaluation = "Code executed successfully with no output"
                is_error = False
                
        except asyncio.TimeoutError:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            await replymsg.edit_text("⚠️ Python code execution timed out after 60 seconds")
            return
            
    except Exception as e:
        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        # Get traceback
        evaluation = traceback.format_exc()
        is_error = True
    
    await send_formatted_response(update.message, evaluation, is_error=is_error, edit_message=replymsg)


async def _aexec(code, update, context):
    """
    Asynchronously executes python code.
    """
    # Add proper indentation for the code
    exec_code = "\n".join(f"    {line}" for line in code.split("\n"))
    
    # Wrap in async function 
    wrapped_code = f"""
async def __aexec(update, context):
{exec_code}
"""
    
    # Execute the wrapped code
    exec(wrapped_code)
    return await locals()["__aexec"](update, context)


# Register command handlers
SHELL_CMD = CommandHandler(("shell", "power_shell", "ps"), shell_command)
EXECUTE_COMMAND = CommandHandler(("py", "python", "exec", "execute"), python_exec)
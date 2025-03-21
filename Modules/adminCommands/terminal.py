from utils.log import logger

import asyncio
import sys
import html
import traceback
import os
import signal
from io import StringIO
import time
import subprocess

from utils.decoders_ import IsOwner
from utils.helper.pasting_servises import katbin_paste, telegraph_paste

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    filters,
    MessageHandler
)
from telegram.constants import ParseMode

# Global dictionary to store running processes
running_processes = {}


@IsOwner
async def shell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Executes command in terminal via bot.
    """
    args = context.args
    if not args:
        shell_usage = (
            "<b>USAGE:</b> Executes terminal commands directly via bot.\n\n"
            "<b>Example: </b><pre>/shell pip install requests</pre>\n\n"
            "<b>Options:</b>\n"
            "• /shell_timeout [seconds] [command] - Run with timeout\n"
            "• /shell_kill - Kill all running processes\n"
            "• /shell_bg [command] - Run in background"
        )
        await update.message.reply_text(shell_usage, parse_mode=ParseMode.HTML)
        return
    
    user_id = update.effective_user.id
    message_id = update.message.message_id
    process_id = f"{user_id}_{message_id}"
    
    content = ' '.join(args)
    shell_replymsg = await update.message.reply_text("⚙️ Running command...", parse_mode=ParseMode.HTML)
    
    try:
        start_time = time.time()
        # Using shell=True to properly handle shell commands like 'ls -la' or pipes
        process = await asyncio.create_subprocess_shell(
            content,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Store the process for potential cancellation
        running_processes[process_id] = process
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()
            
            execution_time = time.time() - start_time
            
            if stdout_str and stderr_str:
                result = f"📤 STDOUT:\n{stdout_str}\n\n📥 STDERR:\n{stderr_str}"
            elif stdout_str:
                result = stdout_str
            elif stderr_str:
                result = stderr_str
            else:
                result = "✅ Command executed successfully (no output)"
                
            return_code = process.returncode
            result += f"\n\n📊 Exit Code: {return_code}\n⏱️ Execution Time: {execution_time:.2f}s"
            
        except asyncio.TimeoutError:
            # Process is taking too long
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Kill Process", callback_data=f"kill_{process_id}")]
            ])
            await shell_replymsg.edit_text(
                "⚠️ Command is taking too long to execute. You can continue waiting or kill it.",
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            return
            
    except Exception as error:
        error_str = str(error)
        logger.error(f"Shell execution error: {error_str}")
        return await shell_replymsg.edit_text(f"❌ Error:\n\n<pre>{html.escape(error_str)}</pre>", parse_mode=ParseMode.HTML)
    
    finally:
        # Clean up the process reference
        if process_id in running_processes:
            del running_processes[process_id]
    
    # Handle output
    if len(result) > 4000:
        try:
            # Try katbin first
            output_url = await katbin_paste(result)
            service_name = "Katbin"
        except Exception:
            try:
                # If katbin fails, try hastebin
                output_url = await telegraph_paste(result)
                service_name = "Hastebin"
            except Exception:
                # If both fail, save to file and send the file
                file_path = f"output_{process_id}.txt"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(result)
                
                await update.message.reply_document(
                    document=open(file_path, "rb"),
                    filename="command_output.txt",
                    caption=f"📤 Command output (Exit Code: {return_code})"
                )
                
                # Delete the temporary file
                os.remove(file_path)
                await shell_replymsg.delete()
                return
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Open in Browser", url=output_url)]
        ])
        
        summary = f"📤 Output too large ({len(result)} characters)\n"
        summary += f"📊 Exit Code: {return_code}\n"
        summary += f"⏱️ Execution Time: {execution_time:.2f}s"
        
        await shell_replymsg.edit_text(
            f"{summary}\n\nView complete output on {service_name}:", 
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        await shell_replymsg.edit_text(
            f"<b>📤 Output:</b>\n\n<pre>{html.escape(result)}</pre>",
            parse_mode=ParseMode.HTML
        )


@IsOwner
async def shell_with_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Executes a command with a specified timeout.
    """
    args = context.args
    if len(args) < 2:
        usage = "<b>USAGE:</b> Run a command with a timeout\n\n<b>Example:</b> <pre>/shell_timeout 10 sleep 30</pre>"
        await update.message.reply_text(usage, parse_mode=ParseMode.HTML)
        return
    
    try:
        timeout = int(args[0])
        command = ' '.join(args[1:])
    except ValueError:
        await update.message.reply_text("❌ First argument must be a number (timeout in seconds)", parse_mode=ParseMode.HTML)
        return
    
    replymsg = await update.message.reply_text(f"⚙️ Running command with {timeout}s timeout...", parse_mode=ParseMode.HTML)
    
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()
            
            if stdout_str and stderr_str:
                result = f"📤 STDOUT:\n{stdout_str}\n\n📥 STDERR:\n{stderr_str}"
            elif stdout_str:
                result = stdout_str
            elif stderr_str:
                result = stderr_str
            else:
                result = "✅ Command executed successfully (no output)"
                
            return_code = process.returncode
            result += f"\n\n📊 Exit Code: {return_code}"
            
        except asyncio.TimeoutError:
            # Kill the process if it times out
            process.kill()
            await replymsg.edit_text(
                f"⏱️ Command timed out after {timeout} seconds and was terminated.",
                parse_mode=ParseMode.HTML
            )
            return
            
    except Exception as error:
        error_str = str(error)
        return await replymsg.edit_text(f"❌ Error:\n\n<pre>{html.escape(error_str)}</pre>", parse_mode=ParseMode.HTML)
    
    # Handle output
    if len(result) > 4000:
        try:
            output_url = await katbin_paste(result)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Open in Browser", url=output_url)]
            ])
            await replymsg.edit_text(
                f"📤 Output too large ({len(result)} characters)\nView complete output:", 
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        except Exception:
            await replymsg.edit_text(
                "❌ Output too large and pasting service failed.",
                parse_mode=ParseMode.HTML
            )
    else:
        await replymsg.edit_text(
            f"<b>📤 Output:</b>\n\n<pre>{html.escape(result)}</pre>",
            parse_mode=ParseMode.HTML
        )


@IsOwner
async def kill_all_processes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Kills all running shell processes.
    """
    count = len(running_processes)
    
    if count == 0:
        await update.message.reply_text("No running processes to kill.", parse_mode=ParseMode.HTML)
        return
    
    for process_id, process in list(running_processes.items()):
        try:
            process.kill()
            del running_processes[process_id]
        except Exception as e:
            logger.error(f"Error killing process {process_id}: {e}")
    
    await update.message.reply_text(f"🛑 Killed {count} running process(es)", parse_mode=ParseMode.HTML)


@IsOwner
async def shell_background(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Runs a command in the background.
    """
    args = context.args
    if not args:
        usage = "<b>USAGE:</b> Runs a command in the background\n\n<b>Example:</b> <pre>/shell_bg sleep 60</pre>"
        await update.message.reply_text(usage, parse_mode=ParseMode.HTML)
        return
    
    command = ' '.join(args)
    user_id = update.effective_user.id
    message_id = update.message.message_id
    process_id = f"bg_{user_id}_{message_id}"
    
    # Start process in background
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        running_processes[process_id] = process
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Kill Process", callback_data=f"kill_{process_id}")]
        ])
        
        await update.message.reply_text(
            f"🔄 Command started in background with ID: <code>{process_id}</code>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Handle background process completion
        asyncio.create_task(handle_background_process(update, process, process_id, command))
        
    except Exception as error:
        error_str = str(error)
        await update.message.reply_text(
            f"❌ Error starting background process:\n\n<pre>{html.escape(error_str)}</pre>",
            parse_mode=ParseMode.HTML
        )


async def handle_background_process(update, process, process_id, command):
    """Handle the completion of a background process."""
    try:
        stdout, stderr = await process.communicate()
        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()
        
        if stdout_str and stderr_str:
            result = f"📤 STDOUT:\n{stdout_str}\n\n📥 STDERR:\n{stderr_str}"
        elif stdout_str:
            result = stdout_str
        elif stderr_str:
            result = stderr_str
        else:
            result = "✅ Command executed successfully (no output)"
            
        return_code = process.returncode
        result += f"\n\n📊 Exit Code: {return_code}"
        
        # Clean up the process reference
        if process_id in running_processes:
            del running_processes[process_id]
        
        # Only notify if the process hasn't been killed
        if return_code != -9:  # -9 is SIGKILL
            if len(result) > 4000:
                try:
                    output_url = await katbin_paste(result)
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("Open in Browser", url=output_url)]
                    ])
                    await update.message.reply_text(
                        f"✅ Background process completed\nCommand: <code>{html.escape(command)}</code>\n\n"
                        f"📤 Output too large ({len(result)} characters)\nView complete output:", 
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                except Exception:
                    await update.message.reply_text(
                        f"✅ Background process completed\nCommand: <code>{html.escape(command)}</code>\n\n"
                        f"❌ Output too large and pasting service failed.",
                        parse_mode=ParseMode.HTML
                    )
            else:
                await update.message.reply_text(
                    f"✅ Background process completed\nCommand: <code>{html.escape(command)}</code>\n\n"
                    f"<b>📤 Output:</b>\n\n<pre>{html.escape(result)}</pre>",
                    parse_mode=ParseMode.HTML
                )
    except Exception as e:
        logger.error(f"Error in background process handler: {e}")


async def process_kill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback for killing a specific process from an inline button.
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("kill_"):
        return
    
    process_id = data[5:]  # Remove "kill_" prefix
    
    if process_id in running_processes:
        process = running_processes[process_id]
        try:
            process.kill()
            del running_processes[process_id]
            await query.edit_message_text(
                f"🛑 Process {process_id} has been terminated.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Error killing process: {e}",
                parse_mode=ParseMode.HTML
            )
    else:
        await query.edit_message_text(
            "⚠️ Process not found or already completed.",
            parse_mode=ParseMode.HTML
        )


@IsOwner
async def python_exec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Executes Python code directly via bot.
    """
    args = context.args
    if not args:
        python_usage = (
            "<b>Usage:</b> Executes python commands directly via bot.\n\n"
            "<b>Example: </b><pre>/exec print('hello world')</pre>\n\n"
            "<b>Advanced:</b>\n"
            "• Use <code>update</code> and <code>context</code> objects\n"
            "• Multi-line supported with proper indentation"
        )
        await update.message.reply_text(python_usage, parse_mode=ParseMode.HTML)
        return
    
    replymsg = await update.message.reply_text("⚙️ Executing Python code...", parse_mode=ParseMode.HTML)
    await py_runexec(update, context, replymsg)


async def aexec(code, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Execute Python code asynchronously with proper globals and locals.
    """
    # Add imports that might be useful
    globals_dict = {
        "asyncio": asyncio,
        "update": update,
        "context": context,
        "os": os,
        "sys": sys,
        "html": html,
        "traceback": traceback
    }
    
    # Fix indentation for multi-line code
    lines = code.split('\n')
    if len(lines) > 1:
        # Detect the indentation of the first non-empty line
        first_indent = 0
        for line in lines:
            if line.strip():
                first_indent = len(line) - len(line.lstrip())
                break
        
        # Remove common indentation from all lines
        if first_indent > 0:
            code = '\n'.join(line[min(first_indent, len(line) - len(line.lstrip())):] for line in lines)
    
    # Create the async function
    exec(
        f"async def __aexec(update, context):\n{' '*4}"
        + code.replace('\n', f"\n{' '*4}")
    , globals_dict)
    
    return await globals_dict["__aexec"](update, context)


async def py_runexec(update: Update, context: ContextTypes.DEFAULT_TYPE, replymsg):
    """
    Run Python code and handle its output.
    """
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    redirected_error = sys.stderr = StringIO()
    stdout, stderr, exc = None, None, None
    
    args = context.args
    code = ' '.join(args)
    
    start_time = time.time()
    
    try:
        await aexec(code, update, context)
    except Exception:
        exc = traceback.format_exc()
    
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    
    execution_time = time.time() - start_time
    
    if exc:
        evaluation = exc
    elif stderr:
        evaluation = stderr
    elif stdout:
        evaluation = stdout
    else:
        evaluation = "✅ Code executed successfully (no output)"
    
    evaluation += f"\n\n⏱️ Execution Time: {execution_time:.2f}s"
    final_output = f"{evaluation.strip()}"
    
    try:
        if len(final_output) > 4000:
            # Try different pasting services
            try:
                output_url = await katbin_paste(final_output)
                service_name = "Katbin"
            except Exception:
                try:
                    output_url = await telegraph_paste(final_output)
                    service_name = "Hastebin"
                except Exception:
                    # If both fail, save to file and send the file
                    user_id = update.effective_user.id
                    message_id = update.message.message_id
                    file_path = f"python_output_{user_id}_{message_id}.txt"
                    
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(final_output)
                    
                    await update.message.reply_document(
                        document=open(file_path, "rb"),
                        filename="python_output.txt",
                        caption=f"📤 Python execution output"
                    )
                    
                    # Delete the temporary file
                    os.remove(file_path)
                    await replymsg.delete()
                    return
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Open in Browser", url=output_url)]
            ])
            
            summary = f"📤 Output too large ({len(final_output)} characters)\n"
            summary += f"⏱️ Execution Time: {execution_time:.2f}s"
            
            await replymsg.edit_text(
                f"{summary}\n\nView complete output on {service_name}:", 
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        else:
            await replymsg.edit_text(
                f"<b>📤 Output:</b>\n\n<pre>{html.escape(final_output)}</pre>",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.warning(f"Error while sending output: {e}")
        await replymsg.edit_text(
            f"❌ An error occurred while sending the output: {e}",
            parse_mode=ParseMode.HTML
        )


# Add a handler for code blocks in messages (supports multi-line code execution)
@IsOwner
async def code_block_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Execute Python code from code blocks in messages.
    Format: ```python
    your code here
    ```
    """
    message_text = update.message.text
    
    # Check if the message contains Python code blocks
    if "```python" in message_text and "```" in message_text[message_text.find("```python") + 10:]:
        start_idx = message_text.find("```python") + 9
        end_idx = message_text.find("```", start_idx)
        
        if start_idx < end_idx:
            # Extract the code
            code = message_text[start_idx:end_idx].strip()
            
            # Only process if there's actual code
            if code:
                replymsg = await update.message.reply_text("⚙️ Executing Python code block...", parse_mode=ParseMode.HTML)
                
                # Set up the context args for py_runexec
                context.args = [code]
                
                await py_runexec(update, context, replymsg)


# Define all command handlers
SHELL_CMD = CommandHandler(("power_shell", "shell", "ps"), shell)
SHELL_TIMEOUT_CMD = CommandHandler(("shell_timeout", "pst"), shell_with_timeout)
SHELL_KILL_CMD = CommandHandler(("shell_kill", "psk"), kill_all_processes)
SHELL_BG_CMD = CommandHandler(("shell_bg", "psb"), shell_background)
EXECUTE_COMMAND = CommandHandler(("py", "python", "execute", "exec"), python_exec)
CODE_BLOCK_HANDLER = MessageHandler(filters.Regex(r"```python[\s\S]+```") & filters.TEXT, code_block_handler)

# Register with your application
def register_shell_handlers(application):
    application.add_handler(SHELL_CMD)
    application.add_handler(SHELL_TIMEOUT_CMD)
    application.add_handler(SHELL_KILL_CMD)
    application.add_handler(SHELL_BG_CMD)
    application.add_handler(EXECUTE_COMMAND)
    application.add_handler(CODE_BLOCK_HANDLER)
    
    # Add callback query handler for kill buttons
    application.add_handler(CallbackQueryHandler(process_kill_callback, pattern="^kill_"))
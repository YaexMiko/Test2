import asyncio
import glob
import inspect
import io
import itertools
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime as dt
from logging import DEBUG, INFO, basicConfig, getLogger, warning
from pathlib import Path

import aiohttp
import psutil
import pymediainfo
import requests
from html_telegraph_poster import TelegraphPoster
from telethon import Button, TelegramClient, errors, events, functions, types
from telethon.sessions import StringSession
from telethon.utils import pack_bot_file_id

from . import *
from .config import *

WORKING = []
QUEUE = {}
OK = {}
QUEUE_USERS = {}
TASK_OWNERS = {}
USER_ACTIVE_TASKS = {}  # Track active tasks per user
TASK_CHAT_INFO = {}  # Track original chat info for notifications

# Supported video formats
SUPPORTED_FORMATS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.3gp', 
    '.mpeg', '.mpg', '.mts', '.m2ts', '.ogv', '.ts'
}

# Minimum file size (400KB)
MIN_FILE_SIZE = 400 * 1024

uptime = dt.now()
os.system(f"wget {THUMB} -O thumb.jpg")

if not os.path.isdir("downloads/"):
    os.mkdir("downloads/")
if not os.path.isdir("encode/"):
    os.mkdir("encode/")
if not os.path.isdir("thumb/"):
    os.mkdir("thumb/")

tgp_client = TelegraphPoster(use_api=True)
tgp_client._telegraph_api_url = TELEGRAPH_API

def create_api_token():
    retries = 10
    while retries:
        try:
            tgp_client.create_api_token("Mediainfo")
            break
        except (requests.exceptions.ConnectionError, ConnectionError) as e:
            retries -= 1
            if not retries:
                LOGS.info("Telegraph token creation failed!")
                break
            time.sleep(1)

create_api_token()

def is_supported_format(filename):
    """Check if file format is supported for encoding"""
    if not filename:
        return False
    
    file_ext = os.path.splitext(filename.lower())[1]
    return file_ext in SUPPORTED_FORMATS

def can_user_add_task(user_id):
    """Check if non-owner user can add a new task"""
    if str(user_id) in OWNER:
        return True, None
    
    # Check if user already has an active task
    if user_id in USER_ACTIVE_TASKS:
        return False, "❌ **You already have an active task!** Please wait for it to complete before adding another."
    
    return True, None

def add_user_task(user_id, task_id, chat_id):
    """Add user task to tracking"""
    if str(user_id) not in OWNER:
        USER_ACTIVE_TASKS[user_id] = {
            'task_id': task_id,
            'chat_id': chat_id,
            'start_time': time.time()
        }

def remove_user_task(user_id):
    """Remove user task from tracking"""
    if user_id in USER_ACTIVE_TASKS:
        USER_ACTIVE_TASKS.pop(user_id)

def add_task_chat_info(task_id, user_id, chat_id, filename):
    """Store chat info for notifications"""
    TASK_CHAT_INFO[task_id] = {
        'user_id': user_id,
        'chat_id': chat_id,
        'filename': filename
    }

def get_task_chat_info(task_id):
    """Get chat info for notifications"""
    return TASK_CHAT_INFO.get(task_id)

def remove_task_chat_info(task_id):
    """Remove chat info after task completion"""
    if task_id in TASK_CHAT_INFO:
        TASK_CHAT_INFO.pop(task_id)

async def send_completion_notification(user_id, chat_id, filename):
    """Send completion notification to group/chat"""
    try:
        # Only send notification if it's not a DM (group encoding)
        if chat_id != user_id:  # Not a DM
            sender = await bot.get_entity(user_id)
            sender_name = sender.username if hasattr(sender, 'username') and sender.username else sender.first_name
            
            notification_msg = f"@{sender_name} **Your Task Has Been Completed Check Bot DM.**\n\n**Original File Name:** `{filename}`"
            
            await bot.send_message(chat_id, notification_msg)
            
    except Exception as e:
        LOGS.info(f"Notification error: {e}")

def ts(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        ((str(days) + "d, ") if days else "")
        + ((str(hours) + "h, ") if hours else "")
        + ((str(minutes) + "m, ") if minutes else "")
        + ((str(seconds) + "s, ") if seconds else "")
        + ((str(milliseconds) + "ms, ") if milliseconds else "")
    )
    return tmp[:-2]

def ts_simple(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        if remaining_seconds > 0:
            return f"{minutes}m, {remaining_seconds}s"
        else:
            return f"{minutes}m"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if remaining_minutes > 0:
        if remaining_seconds > 0:
            return f"{hours}h, {remaining_minutes}m, {remaining_seconds}s"
        else:
            return f"{hours}h, {remaining_minutes}m"
    else:
        if remaining_seconds > 0:
            return f"{hours}h, {remaining_seconds}s"
        else:
            return f"{hours}h"

def hbs(size):
    if not size:
        return ""
    power = 2**10
    raised_to_pow = 0
    dict_power_n = {0: "B", 1: "K", 2: "M", 3: "G", 4: "T", 5: "P"}
    while size > power:
        size /= power
        raised_to_pow += 1
    return str(round(size, 2)) + " " + dict_power_n[raised_to_pow] + "B"

Last_Progress_Update = {}

async def progress(current, total, event, start, type_of_ps, file=None, cancel_data=None, task_owner_id=None):
    now = time.time()
    
    progress_key = f"{event.chat_id}_{event.id}"
    mb_50 = 50 * 1024 * 1024
    
    should_update = False
    if progress_key in Last_Progress_Update:
        last_current, last_time = Last_Progress_Update[progress_key]
        if (current - last_current) >= mb_50 or (now - last_time) >= 10 or current == total:
            should_update = True
    else:
        should_update = True
    
    if not should_update:
        return
    
    Last_Progress_Update[progress_key] = (current, now)
    
    if current == total and progress_key in Last_Progress_Update:
        del Last_Progress_Update[progress_key]
    
    diff = time.time() - start
    if diff > 0:
        percentage = current * 100 / total
        speed = current / diff
        time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
        progress_str = "**[{0}{1}] {2}%**\n\n".format(
            "".join(["●" for i in range(math.floor(percentage / 5))]),
            "".join(["○" for i in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2),
        )
        
        buttons = []
        if cancel_data and task_owner_id:
            enhanced_cancel_data = f"{cancel_data}_{task_owner_id}"
            buttons = [[Button.inline("CANCEL PROCESS", data=f"skip{enhanced_cancel_data}")]]
        
        if type_of_ps.lower() == "downloading":
            tmp = (
                "**Downloading** \n\n"
                + "`{}`\n\n".format(file if file else "Unknown File")
                + "**{0} Out Of {1}**\n".format(hbs(current), hbs(total))
                + progress_str
                + "**Speed: {0}/s**\n**ETA: {1}**\n**Elapsed: {2}**".format(
                    hbs(speed),
                    ts_simple(int(time_to_completion / 1000)) if time_to_completion > 0 else "0s",
                    ts_simple(int(diff)),
                )
            )
        elif type_of_ps.lower() == "uploading..":
            tmp = (
                "**Uploading** \n\n"
                + "`{}`\n\n".format(file if file else "Unknown File")
                + "**{0} Out Of {1}**\n".format(hbs(current), hbs(total))
                + progress_str
                + "**Speed: {0}/s**\n**ETA: {1}**\n**Elapsed: {2}**".format(
                    hbs(speed),
                    ts_simple(int(time_to_completion / 1000)) if time_to_completion > 0 else "0s",
                    ts_simple(int(diff)),
                )
            )
        
        try:
            if buttons:
                await event.edit(tmp, buttons=buttons)
            else:
                await event.edit(tmp)
        except Exception as e:
            LOGS.info(f"Progress update error: {e}")

async def info(file, event=None):
    try:
        author = (await bot.get_me()).first_name
        author_url = f"https://t.me/{((await bot.get_me()).username)}"
        out = pymediainfo.MediaInfo.parse(file, output="HTML", full=False)
        if len(out) > 65536:
            out = (
                out[:65430]
                + "<strong>...<strong><br><br><strong>(TRUNCATED DUE TO CONTENT EXCEEDING MAX LENGTH)<strong>"
            )
        retries = 10
        while retries:
            try:
                page = tgp_client.post(
                    title="Mediainfo",
                    author=author,
                    author_url=author_url,
                    text=out,
                )
                break
            except (requests.exceptions.ConnectionError, ConnectionError) as e:
                retries -= 1
                if not retries:
                    raise e
                await asyncio.sleep(1)
        return page["url"]
    except Exception:
        return None

def code(data):
    OK.update({len(OK): data})
    return str(len(OK) - 1)

def decode(key):
    if OK.get(int(key)):
        return OK[int(key)]
    return

CANCELLED_PROCESSES = set()

async def skip(e):
    wah = e.pattern_match.group(1).decode("UTF-8")
    wh = decode(wah)
    
    try:
        # Enhanced parsing for cancel data with task owner info
        cancel_parts = wh.split("_")
        if len(cancel_parts) >= 2:
            task_owner_id = int(cancel_parts[-1])
            original_cancel_data = "_".join(cancel_parts[:-1])
        else:
            original_cancel_data = wh
            task_owner_id = None
        
        user_id = e.sender_id
        is_owner = str(user_id) in OWNER
        is_task_owner = task_owner_id == user_id if task_owner_id else True
        
        # Enhanced access control - only sender or owner can cancel
        if not is_owner and not is_task_owner:
            await e.answer("❌ Access Denied! Only the sender or bot owner can cancel this task.", cache_time=0, alert=True)
            return
        
        if original_cancel_data.count(';') >= 2:
            out, dl, id = original_cancel_data.split(";")
            process_id = f"{dl}_{out}"
            
            # Remove user task tracking
            if task_owner_id:
                remove_user_task(task_owner_id)
                # Clean up task chat info
                try:
                    remove_task_chat_info(int(id))
                except:
                    pass
        else:
            parts = original_cancel_data.split(";")
            if len(parts) >= 2:
                process_type, process_id = parts[0], parts[1]
                CANCELLED_PROCESSES.add(process_id)
                
                # Remove user task tracking
                if task_owner_id:
                    remove_user_task(task_owner_id)
                    
                await e.answer("❌ Process Cancelled!", cache_time=0, alert=True)
                await e.delete()
                return
            else:
                process_id = original_cancel_data
        
        CANCELLED_PROCESSES.add(process_id)
        
        try:
            if QUEUE.get(int(id)):
                WORKING.clear()
                QUEUE.pop(int(id))
                if int(id) in TASK_OWNERS:
                    task_owner = TASK_OWNERS.pop(int(id))
                    remove_user_task(task_owner)
                # Clean up task chat info
                remove_task_chat_info(int(id))
        except:
            pass
        
        await e.answer("❌ Process Cancelled!", cache_time=0, alert=True)
        await e.delete()
        
        try:
            if os.path.exists(dl):
                os.remove(dl)
            if os.path.exists(out):
                os.remove(out)
        except:
            pass
        
        for proc in psutil.process_iter():
            try:
                processName = proc.name()
                processID = proc.pid
                if processName == "ffmpeg":
                    os.kill(processID, signal.SIGKILL)
                    LOGS.info(f"Killed ffmpeg process: {processID}")
            except:
                pass
                
    except Exception as err:
        LOGS.info(f"Skip error: {err}")
        await e.answer("❌ Process Cancelled!", cache_time=0, alert=True)
        try:
            await e.delete()
        except:
            pass

async def queue_status(e):
    # Allow all users to see queue status
    if not QUEUE:
        await e.reply("**Queue is empty!**")
        return
    
    queue_msg = "**Queue Tasks**\n\n"
    
    task_number = 1
    for queue_id, queue_data in QUEUE.items():
        try:
            if isinstance(queue_data, str):
                filename = queue_data if queue_data else "Unknown File"
            else:
                filename = queue_data[0] if queue_data[0] else "Unknown File"
            
            if queue_id in QUEUE_USERS:
                user_info = QUEUE_USERS[queue_id]
                sender_name = user_info['name']
                sender_id = user_info['id']
                chat_type = user_info.get('chat_type', 'Unknown')
            else:
                sender_name = "Unknown"
                sender_id = "Unknown"
                chat_type = "Unknown"
            
            queue_msg += f"**{task_number}. {filename}**\n\n"
            queue_msg += f"**By:** @{sender_name} `({sender_id})`\n"
            queue_msg += f"**Location:** {chat_type}\n"
            queue_msg += f"**Task ID:** `{queue_id}`\n\n"
            
            task_number += 1
            
        except Exception as err:
            LOGS.info(f"Queue status error: {err}")
            continue
    
    queue_msg += f"**Pending Tasks:** **{len(QUEUE)}**\n\n"
    queue_msg += "**Note:** **To remove your task from queue use /clear** `<task id>`"
    
    await e.reply(queue_msg)

async def clear_task(e):
    # Allow users to clear their own tasks, owners can clear any task
    try:
        command_text = e.text.strip()
        if len(command_text.split()) < 2:
            await e.reply("**Usage:** /clear `<task id>`")
            return
        
        task_id = command_text.split()[1]
        
        removed = False
        for queue_id in list(QUEUE.keys()):
            if str(queue_id) == task_id:
                is_owner = str(e.sender_id) in OWNER
                is_task_owner = (queue_id in QUEUE_USERS and QUEUE_USERS[queue_id]['id'] == e.sender_id)
                
                if is_owner or is_task_owner:
                    QUEUE.pop(queue_id)
                    if queue_id in QUEUE_USERS:
                        QUEUE_USERS.pop(queue_id)
                    if queue_id in TASK_OWNERS:
                        task_owner = TASK_OWNERS.pop(queue_id)
                        remove_user_task(task_owner)
                    # Clean up task chat info
                    remove_task_chat_info(queue_id)
                    removed = True
                    break
                else:
                    await e.reply("**Access Denied!** You can only remove your own tasks.")
                    return
        
        if removed:
            await e.reply(f"**Task removed successfully!**\n**Task ID:** `{task_id}`")
        else:
            await e.reply(f"**Task not found!**\n**Task ID:** `{task_id}`")
            
    except Exception as err:
        LOGS.info(f"Clear task error: {err}")
        await e.reply("**Error removing task!**")

async def fast_download(e, download_url, filename=None, cancel_data=None, task_owner_id=None):
    process_id = f"download_{download_url}_{int(time.time())}"
    
    def progress_callback(d, t):
        if process_id in CANCELLED_PROCESSES:
            CANCELLED_PROCESSES.discard(process_id)
            raise Exception("Download cancelled by user")
            
        return (
            asyncio.get_event_loop().create_task(
                progress(
                    d, t, e, time.time(), "Downloading",
                    filename if filename else download_url.rpartition("/")[-1],
                    cancel_data, task_owner_id
                )
            ),
        )

    async def _maybe_await(value):
        if inspect.isawaitable(value):
            return await value
        else:
            return value

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, timeout=None) as response:
                if not filename:
                    filename = download_url.rpartition("/")[-1]
                
                # Check file size from headers
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) < MIN_FILE_SIZE:
                    raise Exception(f"File size ({hbs(int(content_length))}) is less than 400KB. Encoding not supported.")
                
                # Check file format
                if not is_supported_format(filename):
                    supported_list = ", ".join(sorted(SUPPORTED_FORMATS))
                    raise Exception(f"Unsupported file format. Supported formats: {supported_list}")
                
                dl_path = f"downloads/{filename}"
                with open(dl_path, "wb") as f:
                    downloaded = 0
                    async for chunk in response.content.iter_chunked(1024):
                        if process_id in CANCELLED_PROCESSES:
                            CANCELLED_PROCESSES.discard(process_id)
                            if os.path.exists(dl_path):
                                os.remove(dl_path)
                            raise Exception("Download cancelled by user")
                        
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        await _maybe_await(progress_callback(downloaded, int(content_length) if content_length else downloaded))
                
                # Final file size check
                final_size = os.path.getsize(dl_path)
                if final_size < MIN_FILE_SIZE:
                    os.remove(dl_path)
                    raise Exception(f"Downloaded file size ({hbs(final_size)}) is less than 400KB. Encoding not supported.")
                
                return dl_path
                
    except Exception as e:
        LOGS.info(f"Download error: {e}")
        raise e

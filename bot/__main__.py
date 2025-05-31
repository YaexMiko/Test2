import asyncio
import os
import sys
from . import *

# Add the parent directory to path to import the bot
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .funcn import *
from .worker import *

# Event handlers
@bot.on(events.NewMessage(pattern="^/start"))
async def start(event):
    supported_formats = ", ".join(sorted(SUPPORTED_FORMATS))
    await event.reply(
        "**Hey! I'm a Video Compressor Bot.**\n\n"
        "**Owner Commands:**\n"
        "• Send video files in DM or groups to compress\n"
        "• Use `/link <url> <filename>` to compress from URL\n"
        "• Use `/restart` to restart the bot\n\n"
        "**User Commands:**\n"
        "• Send video files in groups only to compress\n"
        "• Use `/queue` to see pending tasks\n"
        "• Use `/clear <task_id>` to remove your task\n\n"
        f"**Supported Formats:** {supported_formats}\n\n"
        "**File Requirements:**\n"
        "• Minimum file size: 400KB\n"
        "• Compressed files will be sent to your DM!\n"
        "• Group completion notifications included\n\n"
        "**Restrictions:**\n"
        "• Non-owners: 1 task at a time\n"
        "• Only sender or owner can cancel tasks"
    )

@bot.on(events.NewMessage(pattern="^/help"))
async def help_command(event):
    supported_formats = ", ".join(sorted(SUPPORTED_FORMATS))
    await event.reply(
        "**Video Compressor Bot Help**\n\n"
        "**How to use:**\n"
        "1. Send a video file to the bot\n"
        "2. Wait for download and compression\n"
        "3. Get compressed file in your DM\n"
        "4. Notification sent to group (if applicable)\n\n"
        "**Commands:**\n"
        "• `/start` - Start the bot\n"
        "• `/help` - Show this help\n"
        "• `/queue` - Check queue status\n"
        "• `/clear <id>` - Remove task from queue\n"
        "• `/restart` - Restart bot (owner only)\n\n"
        f"**Supported Formats:** {supported_formats}\n\n"
        "**File Requirements:**\n"
        "• Minimum file size: 400KB\n\n"
        "**Access Control:**\n"
        "• Owner: Unlimited tasks, encode anywhere\n"
        "• Users: 1 task at a time, groups only\n"
        "• Files sent to sender's DM\n"
        "• Group notifications for completion\n"
        "• Only sender or owner can cancel tasks"
    )

# Restart handler (owner only)
@bot.on(events.NewMessage(pattern="^/restart"))
async def restart_handler(event):
    if str(event.sender_id) not in OWNER:
        await event.reply("❌ **Access Denied!** Only owner can restart the bot.")
        return
    
    try:
        # Stop all ongoing processes
        await event.reply("🔄 **Restarting bot...**\n\n⏹️ Stopping all processes...")
        
        # Clear all queues and working status
        WORKING.clear()
        QUEUE.clear()
        QUEUE_USERS.clear()
        TASK_OWNERS.clear()
        CANCELLED_PROCESSES.clear()
        USER_ACTIVE_TASKS.clear()
        TASK_CHAT_INFO.clear()
        
        # Kill all ffmpeg processes
        for proc in psutil.process_iter():
            try:
                processName = proc.name()
                processID = proc.pid
                if processName == "ffmpeg":
                    os.kill(processID, signal.SIGKILL)
                    LOGS.info(f"Killed ffmpeg process: {processID}")
            except:
                pass
        
        # Clean up temporary files
        try:
            import shutil
            if os.path.exists("downloads"):
                shutil.rmtree("downloads")
            if os.path.exists("encode"):
                shutil.rmtree("encode")
            
            # Recreate directories
            os.makedirs("downloads", exist_ok=True)
            os.makedirs("encode", exist_ok=True)
            LOGS.info("Cleaned up temporary files")
        except Exception as cleanup_err:
            LOGS.info(f"Cleanup error: {cleanup_err}")
        
        await event.reply("✅ **Bot restarted successfully!**\n\n🔄 All processes stopped\n📁 Temporary files cleaned\n🚀 Bot is ready for new tasks")
        
        # Restart the bot process
        LOGS.info("Bot restart initiated by owner")
        
        # Use sys.executable to restart with the same Python interpreter
        os.execv(sys.executable, ['python'] + ['-m', 'bot'])
        
    except Exception as restart_err:
        LOGS.info(f"Restart error: {restart_err}")
        await event.reply(f"❌ **Restart failed!**\n\n```{str(restart_err)}```")

# URL download handler (owner only, DM only)
@bot.on(events.NewMessage(pattern="^/link"))
async def link_handler(event):
    await dl_link(event)

# Video compression handler
@bot.on(events.NewMessage())
async def video_handler(event):
    if event.media and hasattr(event.media, 'document'):
        if event.media.document.mime_type.startswith(('video', 'application/octet-stream')):
            await encod(event)

# Queue status handler
@bot.on(events.NewMessage(pattern="^/queue"))
async def queue_handler(event):
    await queue_status(event)

# Clear task handler
@bot.on(events.NewMessage(pattern="^/clear"))
async def clear_handler(event):
    await clear_task(event)

# Stats callback handler
@bot.on(events.CallbackQuery(pattern=r"stats(.*)"))
async def stats_handler(event):
    await stats(event)

# Cancel process callback handler
@bot.on(events.CallbackQuery(pattern=r"skip(.*)"))
async def skip_handler(event):
    await skip(event)

# Queue processor
async def process_queue():
    while True:
        if QUEUE and not WORKING:
            try:
                first_key = list(QUEUE.keys())[0]
                first_value = QUEUE[first_key]
                
                if isinstance(first_value, str):
                    # URL download
                    QUEUE.pop(first_key)
                    WORKING.append(1)
                    
                    # Get task owner info
                    task_owner_id = TASK_OWNERS.get(first_key)
                    if not task_owner_id:
                        task_owner_id = int(OWNER.split()[0])
                    
                    s = dt.now()
                    xxx = await bot.send_message(task_owner_id, "**Processing Queue Item...**")
                    
                    process_id = f"download_{first_key}_{int(time.time())}"
                    hehe_dl = f"download;{process_id}"
                    cancel_data_dl = code(hehe_dl)
                    
                    try:
                        dl = await fast_download(xxx, first_key, first_value, cancel_data_dl, task_owner_id)
                        
                        if process_id in CANCELLED_PROCESSES:
                            CANCELLED_PROCESSES.discard(process_id)
                            remove_user_task(task_owner_id)
                            WORKING.clear()
                            continue
                            
                    except Exception as er:
                        remove_user_task(task_owner_id)
                        WORKING.clear()
                        LOGS.info(er)
                        await xxx.edit(f"**Queue Download Failed!**\n\n{str(er)}")
                        continue
                    
                    # Continue with encoding process...
                    es = dt.now()
                    kk = dl.split("/")[-1]
                    aa = kk.split(".")[-1]
                    rr = "encode"
                    bb = kk.replace(f".{aa}", "_compressed.mkv")
                    out = f"{rr}/{bb}"
                    thum = "thumb.jpg"
                    dtime = ts(int((es - s).seconds) * 1000)
                    
                    # Get task owner info
                    task_owner_id = TASK_OWNERS.get(first_key, task_owner_id)
                    
                    hehe = f"{out};{dl};0_{task_owner_id}"
                    wah = code(hehe)
                    
                    encoding_key = f"{dl}_{out}"
                    ENCODING_INFO[encoding_key] = {
                        'start_time': time.time(),
                        'filename': kk
                    }
                    
                    try:
                        sender = await bot.get_entity(task_owner_id)
                        sender_username = sender.username if hasattr(sender, 'username') and sender.username else sender.first_name
                        sender_id = sender.id
                    except:
                        sender_username = "Unknown"
                        sender_id = task_owner_id
                    
                    nn = await xxx.edit(
                        f"**Encoding Please Wait:**\n\n`{kk}`\n\n**By:** @{sender_username} `({sender_id})`",
                        buttons=[
                            [Button.inline("STATS", data=f"stats{wah}")],
                            [Button.inline("CANCEL PROCESS", data=f"skip{wah}")],
                        ],
                    )
                    
                    cmd = FFMPEG.format(dl, out)
                    process = await asyncio.create_subprocess_shell(
                        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    er = stderr.decode()
                    
                    if encoding_key in ENCODING_INFO:
                        del ENCODING_INFO[encoding_key]
                    
                    if er:
                        await xxx.edit(str(er) + "\n\n**ERROR** Contact @danish_00")
                        remove_user_task(task_owner_id)
                        WORKING.clear()
                        try:
                            os.remove(dl)
                            os.remove(out)
                        except:
                            pass
                        continue
                    
                    ees = dt.now()
                    ttt = time.time()
                    await nn.delete()
                    
                    # Send to task owner's DM
                    nnn = await bot.send_message(task_owner_id, "**Uploading...**")
                    
                    upload_process_id = f"upload_{out}_{int(time.time())}"
                    hehe_upload = f"upload;{upload_process_id}"
                    cancel_data_upload = code(hehe_upload)
                    
                    with open(out, "rb") as f:
                        ok = await upload_file(
                            client=bot,
                            file=f,
                            name=out,
                            progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                                progress(d, t, nnn, ttt, "uploading..", out.split("/")[-1], cancel_data_upload, task_owner_id)
                            ),
                        )
                    
                    fname = out.split("/")[1]
                    ds = await bot.send_file(
                        task_owner_id, file=ok, force_document=True, thumb=thum, caption=f"`{fname}`"
                    )
                    await nnn.delete()
                    
                    org = int(Path(dl).stat().st_size)
                    com = int(Path(out).stat().st_size)
                    pe = 100 - ((com / org) * 100)
                    per = str(f"{pe:.2f}") + "%"
                    eees = dt.now()
                    x = dtime
                    xx = ts(int((ees - es).seconds) * 1000)
                    xxx = ts(int((eees - ees).seconds) * 1000)
                    a1 = await info(dl, None)
                    a2 = await info(out, None)
                    dk = await ds.reply(
                        f"Original Size : {hbs(org)}\nCompressed Size : {hbs(com)}\nCompressed Percentage : {per}\n\nMediainfo: [Before]({a1})//[After]({a2})\n\nDownloaded in {x}\nCompressed in {xx}\nUploaded in {xxx}",
                        link_preview=False,
                    )
                    
                    os.remove(dl)
                    os.remove(out)
                    remove_user_task(task_owner_id)
                    WORKING.clear()
                    
                    # Clean up task tracking
                    if first_key in TASK_OWNERS:
                        TASK_OWNERS.pop(first_key)
                    if first_key in QUEUE_USERS:
                        QUEUE_USERS.pop(first_key)
                        
                else:
                    # File download
                    name, doc = first_value
                    QUEUE.pop(first_key)
                    WORKING.append(1)
                    
                    # Get task owner info
                    task_owner_id = TASK_OWNERS.get(first_key)
                    if not task_owner_id:
                        task_owner_id = int(OWNER.split()[0])
                    
                    # Get chat info for notification
                    chat_info = get_task_chat_info(first_key)
                    original_chat_id = chat_info['chat_id'] if chat_info else task_owner_id
                    
                    xxx = await bot.send_message(task_owner_id, "**Processing Queue Item...**")
                    s = dt.now()
                    ttt = time.time()
                    dir = f"downloads/"
                    
                    process_id = f"download_{first_key}_{int(time.time())}"
                    hehe_dl = f"download;{process_id}"
                    cancel_data_dl = code(hehe_dl)
                    
                    try:
                        filename = name
                        if not filename:
                            filename = "video_" + dt.now().isoformat("_", "seconds") + ".mp4"
                        
                        # Check file format and size
                        if not is_supported_format(filename):
                            supported_list = ", ".join(sorted(SUPPORTED_FORMATS))
                            await xxx.edit(f"❌ **Unsupported file format.**\n\n**Supported formats:** {supported_list}")
                            remove_user_task(task_owner_id)
                            WORKING.clear()
                            continue
                        
                        if doc.size < MIN_FILE_SIZE:
                            await xxx.edit(f"❌ **File size ({hbs(doc.size)}) is less than 400KB. Encoding not supported.**")
                            remove_user_task(task_owner_id)
                            WORKING.clear()
                            continue
                        
                        dl = dir + filename
                        with open(dl, "wb") as f:
                            ok = await download_file(
                                client=bot,
                                location=doc,
                                out=f,
                                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                                    progress(
                                        d, t, xxx, ttt, "Downloading", filename,
                                        cancel_data_dl, task_owner_id
                                    )
                                ),
                            )
                            
                        if process_id in CANCELLED_PROCESSES:
                            CANCELLED_PROCESSES.discard(process_id)
                            remove_user_task(task_owner_id)
                            WORKING.clear()
                            try:
                                os.remove(dl)
                            except:
                                pass
                            continue
                            
                    except Exception as er:
                        remove_user_task(task_owner_id)
                        WORKING.clear()
                        LOGS.info(er)
                        await xxx.edit(f"**Queue Download Failed!**\n\n{str(er)}")
                        continue
                    
                    # Continue with encoding...
                    es = dt.now()
                    kk = dl.split("/")[-1]
                    aa = kk.split(".")[-1]
                    rr = f"encode"
                    bb = kk.replace(f".{aa}", "_compressed.mkv")
                    out = f"{rr}/{bb}"
                    thum = "thumb.jpg"
                    dtime = ts(int((es - s).seconds) * 1000)
                    hehe = f"{out};{dl};0_{task_owner_id}"
                    wah = code(hehe)
                    
                    encoding_key = f"{dl}_{out}"
                    ENCODING_INFO[encoding_key] = {
                        'start_time': time.time(),
                        'filename': kk
                    }
                    
                    try:
                        sender = await bot.get_entity(task_owner_id)
                        sender_username = sender.username if hasattr(sender, 'username') and sender.username else sender.first_name
                        sender_id = sender.id
                    except:
                        sender_username = "Unknown"
                        sender_id = task_owner_id
                    
                    nn = await xxx.edit(
                        f"**Encoding Please Wait:**\n\n`{kk}`\n\n**By:** @{sender_username} `({sender_id})`",
                        buttons=[
                            [Button.inline("STATS", data=f"stats{wah}")],
                            [Button.inline("CANCEL PROCESS", data=f"skip{wah}")],
                        ],
                    )
                    cmd = FFMPEG.format(dl, out)
                    process = await asyncio.create_subprocess_shell(
                        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    er = stderr.decode()
                    
                    if encoding_key in ENCODING_INFO:
                        del ENCODING_INFO[encoding_key]
                    
                    try:
                        if er:
                            await xxx.edit(str(er) + "\n\n**ERROR** Contact @danish_00")
                            remove_user_task(task_owner_id)
                            WORKING.clear()
                            os.remove(dl)
                            return os.remove(out)
                    except BaseException:
                        pass
                    ees = dt.now()
                    ttt = time.time()
                    await nn.delete()
                    
                    # Send to task owner's DM
                    nnn = await bot.send_message(task_owner_id, "**Uploading...**")
                    
                    upload_process_id = f"upload_{out}_{int(time.time())}"
                    hehe_upload = f"upload;{upload_process_id}"
                    cancel_data_upload = code(hehe_upload)
                    
                    with open(out, "rb") as f:
                        ok = await upload_file(
                            client=bot,
                            file=f,
                            name=out,
                            progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                                progress(d, t, nnn, ttt, "uploading..", out.split("/")[-1], cancel_data_upload, task_owner_id)
                            ),
                        )
                    fname = out.split("/")[1]
                    ds = await bot.send_file(
                        task_owner_id, file=ok, force_document=True, thumb=thum, caption=f"`{fname}`"
                    )
                    await nnn.delete()
                    
                    # Send completion notification to original chat
                    await send_completion_notification(task_owner_id, original_chat_id, kk)
                    
                    org = int(Path(dl).stat().st_size)
                    com = int(Path(out).stat().st_size)
                    pe = 100 - ((com / org) * 100)
                    per = str(f"{pe:.2f}") + "%"
                    eees = dt.now()
                    x = dtime
                    xx = ts(int((ees - es).seconds) * 1000)
                    xxx = ts(int((eees - ees).seconds) * 1000)
                    a1 = await info(dl, xxx)
                    a2 = await info(out, xxx)
                    dk = await ds.reply(
                        f"Original Size : {hbs(org)}\nCompressed Size : {hbs(com)}\nCompressed Percentage : {per}\n\nMediainfo: [Before]({a1})//[After]({a2})\n\nDownloaded in {x}\nCompressed in {xx}\nUploaded in {xxx}",
                        link_preview=False,
                    )
                    os.remove(dl)
                    os.remove(out)
                    remove_user_task(task_owner_id)
                    WORKING.clear()
                    
                    # Clean up task tracking
                    if first_key in TASK_OWNERS:
                        TASK_OWNERS.pop(first_key)
                    if first_key in QUEUE_USERS:
                        QUEUE_USERS.pop(first_key)
                    remove_task_chat_info(first_key)
                        
            except Exception as queue_err:
                LOGS.info(f"Queue processing error: {queue_err}")
                WORKING.clear()
                
        await asyncio.sleep(2)

# Main execution
if __name__ == "__main__":
    async def main():
        await bot.start(bot_token=BOT_TOKEN)
        await startup()
        
        # Start the queue processor
        asyncio.create_task(process_queue())
        
        LOGS.info("Bot is running...")
        await bot.run_until_disconnected()
    
    try:
        bot.loop.run_until_complete(main())
    except KeyboardInterrupt:
        LOGS.info("Bot stopped by user")
    except Exception as e:
        LOGS.info(f"Bot error: {e}")

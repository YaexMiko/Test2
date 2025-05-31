import asyncio
import os
import sys
import time
from datetime import datetime as dt
from pathlib import Path

from .FastTelethon import download_file, upload_file
from .funcn import *

ENCODING_INFO = {}

async def stats(e):
    try:
        wah = e.pattern_match.group(1).decode("UTF-8")
        wh = decode(wah)
        
        cancel_parts = wh.split("_")
        if len(cancel_parts) >= 2 and cancel_parts[-1].isdigit():
            task_owner_id = int(cancel_parts[-1])
            original_data = "_".join(cancel_parts[:-1])
        else:
            original_data = wh
            task_owner_id = None
        
        out, dl, id = original_data.split(";")
        
        try:
            original_size = int(Path(dl).stat().st_size)
            current_size = int(Path(out).stat().st_size) if os.path.exists(out) else 0
        except Exception as err:
            LOGS.info(f"Error getting file sizes: {err}")
            original_size = 0
            current_size = 0
        
        filename = dl.split("/")[-1]
        
        if '.' in filename:
            name_part = filename.rsplit('.', 1)[0]
        else:
            name_part = filename
        
        if len(name_part) > 25:
            display_name = name_part[:22] + "..."
        else:
            display_name = name_part
        
        if original_size > 0 and current_size > 0:
            estimated_final_size = original_size * 0.6
            progress_percentage = min((current_size / estimated_final_size) * 100, 99)
        else:
            progress_percentage = 0
        
        filled_blocks = int(progress_percentage / 11.11)
        progress_bar = "●" * filled_blocks + "○" * (9 - filled_blocks)
        
        encoding_key = f"{dl}_{out}"
        if encoding_key in ENCODING_INFO:
            start_time = ENCODING_INFO[encoding_key]['start_time']
            elapsed_seconds = int(time.time() - start_time)
            
            if progress_percentage > 15:
                total_estimated = (elapsed_seconds * 100) / progress_percentage
                eta_seconds = int(total_estimated - elapsed_seconds)
            else:
                gb_size = original_size / (1024 * 1024 * 1024)
                if gb_size <= 0.5:
                    estimated_total_seconds = 8 * 60
                elif gb_size <= 1.0:
                    estimated_total_seconds = 15 * 60
                elif gb_size <= 2.0:
                    estimated_total_seconds = 25 * 60
                elif gb_size <= 3.0:
                    estimated_total_seconds = 35 * 60
                elif gb_size <= 5.0:
                    estimated_total_seconds = 50 * 60
                else:
                    estimated_total_seconds = int(gb_size * 12 * 60)
                
                eta_seconds = max(estimated_total_seconds - elapsed_seconds, 60)
        else:
            gb_size = original_size / (1024 * 1024 * 1024) if original_size > 0 else 1
            if gb_size <= 0.5:
                eta_seconds = 8 * 60
            elif gb_size <= 1.0:
                eta_seconds = 15 * 60
            elif gb_size <= 2.0:
                eta_seconds = 25 * 60
            elif gb_size <= 3.0:
                eta_seconds = 35 * 60
            elif gb_size <= 5.0:
                eta_seconds = 50 * 60
            else:
                eta_seconds = int(gb_size * 12 * 60)
            elapsed_seconds = 30
        
        elapsed_str = ts_simple(elapsed_seconds)
        eta_str = ts_simple(eta_seconds)
        
        ans = f"""Downloaded: {hbs(original_size)}

File Name: {display_name}

Encoded Stats:
[{progress_bar}] {progress_percentage:.0f}%

Done: {hbs(current_size)}
ETA: {eta_str}
Elapsed: {elapsed_str}"""
        
        await e.answer(ans, cache_time=0, alert=True)
        
    except Exception as er:
        LOGS.info(f"Stats error: {er}")
        await e.answer("Stats Error 🤔", cache_time=0, alert=True)

async def dl_link(event):
    if not event.is_private:
        return
    if str(event.sender_id) not in OWNER:
        return
        
    # Check if non-owner user can add task
    can_add, error_msg = can_user_add_task(event.sender_id)
    if not can_add:
        await event.reply(error_msg)
        return
        
    link, name = "", ""
    try:
        link = event.text.split()[1]
        name = event.text.split()[2]
    except BaseException:
        pass
    if not link:
        return
        
    if WORKING or QUEUE:
        QUEUE.update({link: name})
        try:
            sender = await event.client.get_entity(event.sender_id)
            sender_name = sender.username if hasattr(sender, 'username') and sender.username else sender.first_name
        except:
            sender_name = event.sender.first_name if event.sender.first_name else "Unknown"
        
        QUEUE_USERS[link] = {
            'name': sender_name,
            'id': event.sender_id,
            'chat_type': 'DM'
        }
        TASK_OWNERS[link] = event.sender_id
        
        # Add user task tracking
        add_user_task(event.sender_id, link, event.chat_id)
        
        return await event.reply(f"`Added {link} in QUEUE #{len(QUEUE)}`")
        
    # Add user task tracking for immediate processing
    add_user_task(event.sender_id, f"immediate_{int(time.time())}", event.chat_id)
    
    WORKING.append(1)
    s = dt.now()
    xxx = await event.reply("**Downloading...**")
    
    process_id = f"download_{link}_{int(time.time())}"
    hehe_dl = f"download;{process_id}"
    cancel_data_dl = code(hehe_dl)
    
    try:
        dl = await fast_download(xxx, link, name, cancel_data_dl, event.sender_id)
        
        if process_id in CANCELLED_PROCESSES:
            CANCELLED_PROCESSES.discard(process_id)
            remove_user_task(event.sender_id)
            WORKING.clear()
            return
            
    except Exception as er:
        remove_user_task(event.sender_id)
        WORKING.clear()
        LOGS.info(er)
        await xxx.edit(f"**Download Failed!**\n\n{str(er)}")
        return
    
    es = dt.now()
    kk = dl.split("/")[-1]
    aa = kk.split(".")[-1]
    rr = "encode"
    bb = kk.replace(f".{aa}", "_compressed.mkv")
    out = f"{rr}/{bb}"
    thum = "thumb.jpg"
    dtime = ts(int((es - s).seconds) * 1000)
    hehe = f"{out};{dl};0_{event.sender_id}"
    wah = code(hehe)
    
    encoding_key = f"{dl}_{out}"
    ENCODING_INFO[encoding_key] = {
        'start_time': time.time(),
        'filename': kk
    }
    
    try:
        sender = await xxx.client.get_entity(event.sender_id)
        sender_username = sender.username if hasattr(sender, 'username') and sender.username else sender.first_name
        sender_id = sender.id
    except:
        sender_username = event.sender.first_name if event.sender.first_name else "Unknown"
        sender_id = event.sender_id
    
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
            remove_user_task(event.sender_id)
            WORKING.clear()
            os.remove(dl)
            return os.remove(out)
    except BaseException:
        pass
        
    ees = dt.now()
    ttt = time.time()
    await nn.delete()
    
    # Send upload notification and file to sender's DM
    nnn = await xxx.client.send_message(event.sender_id, "**Uploading...**")
    
    upload_process_id = f"upload_{out}_{int(time.time())}"
    hehe_upload = f"upload;{upload_process_id}"
    cancel_data_upload = code(hehe_upload)
    
    with open(out, "rb") as f:
        ok = await upload_file(
            client=xxx.client,
            file=f,
            name=out,
            progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                progress(d, t, nnn, ttt, "uploading..", out.split("/")[-1], cancel_data_upload, event.sender_id)
            ),
        )
    fname = out.split("/")[1]
    
    # Send compressed file to sender's DM
    ds = await xxx.client.send_file(
        event.sender_id, file=ok, force_document=True, thumb=thum, caption=f"`{fname}`"
    )
    await nnn.delete()
    
    # Send completion notification to original chat (if not DM)
    await send_completion_notification(event.sender_id, event.chat_id, kk)
    
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
    remove_user_task(event.sender_id)
    WORKING.clear()

async def encod(event):
    try:
        # Owner can encode anywhere (DM + groups), non-owner only in groups
        if str(event.sender_id) not in OWNER:
            # Non-owner: only allow in groups, not in DM
            if event.is_private:
                return
                
        # Check if non-owner user can add task
        can_add, error_msg = can_user_add_task(event.sender_id)
        if not can_add:
            await event.reply(error_msg)
            return
        
        if not event.media:
            return
        if hasattr(event.media, "document"):
            if not event.media.document.mime_type.startswith(
                ("video", "application/octet-stream")
            ):
                return
        else:
            return
            
        # Check file size before processing - silently skip if too small
        file_size = event.media.document.size
        if file_size < MIN_FILE_SIZE:
            return  # Silently skip without any message
        
        # Check file format
        filename = event.file.name
        if not filename:
            filename = "video_" + dt.now().isoformat("_", "seconds") + ".mp4"
        
        if not is_supported_format(filename):
            supported_list = ", ".join(sorted(SUPPORTED_FORMATS))
            await event.reply(f"❌ **Unsupported file format.**\n\n**Supported formats:** {supported_list}")
            return
            
        try:
            oc = event.fwd_from.from_id.user_id
            occ = (await event.client.get_me()).id
            if oc == occ:
                return await event.reply(
                    "`This Video File is already Compressed 😑😑.`"
                )
        except BaseException:
            pass
            
        if WORKING or QUEUE:
            xxx = await event.reply("`Adding To Queue`")
            doc = event.media.document
            if doc.id in list(QUEUE.keys()):
                return await xxx.edit("`THIS FILE ALREADY IN QUEUE`")
            name = filename
            QUEUE.update({doc.id: [name, doc]})
            
            try:
                sender = await event.client.get_entity(event.sender_id)
                sender_name = sender.username if hasattr(sender, 'username') and sender.username else sender.first_name
            except:
                sender_name = event.sender.first_name if event.sender.first_name else "Unknown"
            
            # Determine chat type
            chat_type = 'DM' if event.is_private else 'Group'
            
            QUEUE_USERS[doc.id] = {
                'name': sender_name,
                'id': event.sender_id,
                'chat_type': chat_type
            }
            TASK_OWNERS[doc.id] = event.sender_id
            
            # Store chat info for notification
            add_task_chat_info(doc.id, event.sender_id, event.chat_id, filename)
            
            # Add user task tracking
            add_user_task(event.sender_id, doc.id, event.chat_id)
            
            return await xxx.edit(f"`Added This File in Queue #{len(QUEUE)}`")
            
        # Add user task tracking for immediate processing
        add_user_task(event.sender_id, f"immediate_{int(time.time())}", event.chat_id)
        
        WORKING.append(1)
        s = dt.now()
        xxx = await event.reply("**Downloading...**")
        
        process_id = f"download_{event.media.document.id}_{int(time.time())}"
        hehe_dl = f"download;{process_id}"
        cancel_data_dl = code(hehe_dl)
        
        try:
            dl = await fast_download(xxx, event.media.document, filename, cancel_data_dl, event.sender_id)
            
            if process_id in CANCELLED_PROCESSES:
                CANCELLED_PROCESSES.discard(process_id)
                remove_user_task(event.sender_id)
                WORKING.clear()
                return
                
        except Exception as er:
            remove_user_task(event.sender_id)
            WORKING.clear()
            LOGS.info(er)
            await xxx.edit(f"**Download Failed!**\n\n{str(er)}")
            return
            
        es = dt.now()
        kk = dl.split("/")[-1]
        aa = kk.split(".")[-1]
        rr = "encode"
        bb = kk.replace(f".{aa}", "_compressed.mkv")
        out = f"{rr}/{bb}"
        thum = "thumb.jpg"
        dtime = ts(int((es - s).seconds) * 1000)
        hehe = f"{out};{dl};{event.media.document.id}_{event.sender_id}"
        wah = code(hehe)
        
        encoding_key = f"{dl}_{out}"
        ENCODING_INFO[encoding_key] = {
            'start_time': time.time(),
            'filename': kk
        }
        
        try:
            sender = await xxx.client.get_entity(event.sender_id)
            sender_username = sender.username if hasattr(sender, 'username') and sender.username else sender.first_name
            sender_id = sender.id
        except:
            sender_username = event.sender.first_name if event.sender.first_name else "Unknown"
            sender_id = event.sender_id
        
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
                remove_user_task(event.sender_id)
                WORKING.clear()
                os.remove(dl)
                return os.remove(out)
        except BaseException:
            pass
        ees = dt.now()
        ttt = time.time()
        await nn.delete()
        
        # Send upload notification and file to sender's DM
        nnn = await xxx.client.send_message(event.sender_id, "**Uploading...**")
        
        upload_process_id = f"upload_{out}_{int(time.time())}"
        hehe_upload = f"upload;{upload_process_id}"
        cancel_data_upload = code(hehe_upload)
        
        with open(out, "rb") as f:
            ok = await upload_file(
                client=xxx.client,
                file=f,
                name=out,
                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                    progress(d, t, nnn, ttt, "uploading..", out.split("/")[-1], cancel_data_upload, event.sender_id)
                ),
            )
        fname = out.split("/")[1]
        
        # Send compressed file to sender's DM
        ds = await xxx.client.send_file(
            event.sender_id, file=ok, force_document=True, thumb=thum, caption=f"`{fname}`"
        )
        await nnn.delete()
        
        # Send completion notification to original chat (if not DM)
        await send_completion_notification(event.sender_id, event.chat_id, filename)
        
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
        remove_user_task(event.sender_id)
        WORKING.clear()
        
        # Clean up task tracking
        remove_task_chat_info(event.media.document.id)
        
    except Exception as er:
        remove_user_task(event.sender_id)
        WORKING.clear()
        LOGS.info(f"Encoding error: {er}")
        try:
            await event.reply(f"**Error occurred!**\n\n{str(er)}")
        except:
            pass

async def fast_download(xxx, document, name, cancel_data, task_owner_id):
    # Check if it's a URL or a Telegram document
    if isinstance(document, str):
        # URL download
        import aiohttp
        
        s = dt.now()
        dl = f"downloads/{name}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(document) as response:
                if response.status == 200:
                    file_size = int(response.headers.get('content-length', 0))
                    
                    with open(dl, 'wb') as f:
                        downloaded = 0
                        async for chunk in response.content.iter_chunked(1024):
                            # Check for cancellation
                            process_id = cancel_data.split(";")[1] if ";" in cancel_data else cancel_data
                            if process_id in CANCELLED_PROCESSES:
                                f.close()
                                if os.path.exists(dl):
                                    os.remove(dl)
                                return None
                            
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Update progress
                            if file_size > 0:
                                await progress(downloaded, file_size, xxx, time.time(), "downloading", name, cancel_data, task_owner_id)
                else:
                    raise Exception(f"Failed to download: HTTP {response.status}")
    else:
        # Telegram document download
        s = dt.now()
        if not name:
            name = "video_" + dt.now().isoformat("_", "seconds") + ".mp4"
        
        dl = f"downloads/{name}"
        
        with open(dl, "wb") as f:
            await download_file(
                client=xxx.client,
                location=document,
                out=f,
                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                    progress(d, t, xxx, s.timestamp(), "downloading", name, cancel_data, task_owner_id)
                ),
            )
    
    return dl

async def queue_status(event):
    if not QUEUE and not WORKING:
        await event.reply("**Queue is Empty!**")
        return
    
    queue_text = "**Current Queue Status:**\n\n"
    
    if WORKING:
        queue_text += "🔄 **Currently Processing:** 1 task\n\n"
    
    if QUEUE:
        queue_text += f"⏳ **Pending Tasks:** {len(QUEUE)}\n\n"
        
        for i, (task_id, task_data) in enumerate(QUEUE.items(), 1):
            user_info = QUEUE_USERS.get(task_id, {})
            user_name = user_info.get('name', 'Unknown')
            chat_type = user_info.get('chat_type', 'Unknown')
            
            if isinstance(task_data, str):
                # URL download
                queue_text += f"**{i}.** URL Download\n"
                queue_text += f"   👤 **User:** {user_name}\n"
                queue_text += f"   📱 **Type:** {chat_type}\n\n"
            else:
                # File download
                filename = task_data[0] if isinstance(task_data, list) else "Unknown"
                queue_text += f"**{i}.** {filename}\n"
                queue_text += f"   👤 **User:** {user_name}\n"
                queue_text += f"   📱 **Type:** {chat_type}\n\n"
                
            if i >= 10:  # Limit display to first 10 items
                remaining = len(QUEUE) - 10
                if remaining > 0:
                    queue_text += f"... and {remaining} more tasks"
                break
    else:
        queue_text += "✅ **No pending tasks**"
    
    await event.reply(queue_text)

async def clear_task(event):
    try:
        if not QUEUE:
            await event.reply("❌ **Queue is empty!**")
            return
        
        # Parse task ID from command
        try:
            task_id_input = event.text.split()[1]
            
            # Find task in queue
            queue_items = list(QUEUE.items())
            
            # Check if input is a number (position in queue)
            if task_id_input.isdigit():
                position = int(task_id_input) - 1
                if 0 <= position < len(queue_items):
                    task_id, task_data = queue_items[position]
                else:
                    await event.reply(f"❌ **Invalid position! Queue has {len(QUEUE)} tasks.**")
                    return
            else:
                # Try to find by task ID
                task_id = None
                for tid, tdata in queue_items:
                    if str(tid) == task_id_input:
                        task_id = tid
                        task_data = tdata
                        break
                
                if task_id is None:
                    await event.reply("❌ **Task not found!**")
                    return
        
        except IndexError:
            await event.reply("❌ **Please specify task ID!**\n\nUsage: `/clear <task_id>`")
            return
        
        # Check permissions
        user_id = event.sender_id
        is_owner = str(user_id) in OWNER
        task_owner_id = TASK_OWNERS.get(task_id)
        is_task_owner = task_owner_id == user_id
        
        if not is_owner and not is_task_owner:
            await event.reply("❌ **Access Denied!** You can only cancel your own tasks.")
            return
        
        # Remove task from queue
        QUEUE.pop(task_id)
        
        # Clean up related data
        if task_id in TASK_OWNERS:
            removed_task_owner = TASK_OWNERS.pop(task_id)
            remove_user_task(removed_task_owner)
        
        if task_id in QUEUE_USERS:
            QUEUE_USERS.pop(task_id)
        
        # Clean up task chat info
        remove_task_chat_info(task_id)
        
        # Get task info for confirmation
        if isinstance(task_data, str):
            task_name = "URL Download"
        else:
            task_name = task_data[0] if isinstance(task_data, list) else "Unknown File"
        
        await event.reply(f"✅ **Task removed from queue!**\n\n**Task:** {task_name}")
        
    except Exception as e:
        LOGS.info(f"Clear task error: {e}")
        await event.reply("❌ **Error removing task from queue!**")

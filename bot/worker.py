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
            'encoding_chat_id': event.chat_id,  # DM
            'is_owner': True,  # Only owner can use link command
            'original_chat_id': event.chat_id,
            'is_private': True
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
        error_msg = str(er)[:500] + "..." if len(str(er)) > 500 else str(er)
        await xxx.edit(f"**Download Failed!**\n\n{error_msg}")
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
    return_code = process.returncode
    
    if encoding_key in ENCODING_INFO:
        del ENCODING_INFO[encoding_key]
    
    if return_code != 0:
        # Only show error if FFMPEG actually failed
        er = stderr.decode()
        error_msg = "FFMPEG encoding failed"
        if "No such file" in er:
            error_msg = "Input file not found"
        elif "Permission denied" in er:
            error_msg = "Permission denied"
        elif "Invalid" in er:
            error_msg = "Invalid file format"
        
        await xxx.edit(f"**ENCODING ERROR:**\n\n`{error_msg}`\n\n**Contact @danish_00**")
        remove_user_task(event.sender_id)
        WORKING.clear()
        try:
            os.remove(dl)
            os.remove(out)
        except:
            pass
        return
        
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
    
    # No group notification for owner DM encoding
    
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
        is_owner = str(event.sender_id) in OWNER
        
        if not is_owner:
            # Non-owner: only allow in groups, not in DM
            if event.is_private:
                await event.reply("❌ **Access Denied!** Non-owners can only encode files in groups, not in DM.")
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
            
        # Check file size before processing
        file_size = event.media.document.size
        if file_size < MIN_FILE_SIZE:
            await event.reply(f"❌ **File size ({hbs(file_size)}) is less than 400KB. Encoding not supported.**")
            return
        
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
            # For non-owners in groups, show encoding will happen in group
            if not is_owner and not event.is_private:
                xxx = await event.reply("`Adding To Queue - Will encode in this group when ready`")
            else:
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
            
            # Determine where encoding should happen and notifications should go
            encoding_chat_id = event.chat_id  # Always encode in original chat
            
            QUEUE_USERS[doc.id] = {
                'name': sender_name,
                'id': event.sender_id,
                'encoding_chat_id': encoding_chat_id,
                'is_owner': is_owner,
                'original_chat_id': event.chat_id,
                'is_private': event.is_private
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
        
        doc = event.media.document
        name = filename
        
        dl_process_id = f"download_{doc.id}_{int(time.time())}"
        hehe_dl = f"download;{dl_process_id}"
        cancel_data_dl = code(hehe_dl)
        
        try:
            with open(f"downloads/{name}", "wb") as f:
                async def down_callback(d, t):
                    await progress(d, t, xxx, s, "downloading", name, f"{cancel_data_dl}_{event.sender_id}", event.sender_id)
                    
                    # Check for cancellation
                    if dl_process_id in CANCELLED_PROCESSES:
                        raise Exception("Download cancelled by user")
                
                await download_file(event.client, doc, f, progress_callback=down_callback)
                dl = f"downloads/{name}"
        
        except Exception as er:
            remove_user_task(event.sender_id)
            WORKING.clear()
            LOGS.info(er)
            error_msg = str(er)[:500] + "..." if len(str(er)) > 500 else str(er)
            await xxx.edit(f"**Download Failed!**\n\n{error_msg}")
            return
        
        es = dt.now()
        kk = dl.split("/")[-1]
        aa = kk.split(".")[-1]
        rr = "encode"
        bb = kk.replace(f".{aa}", "_compressed.mkv")
        out = f"{rr}/{bb}"
        thum = "thumb.jpg"
        dtime = ts(int((es - s).seconds) * 1000)
        hehe = f"{out};{dl};{doc.id}_{event.sender_id}"
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
        return_code = process.returncode
        
        if encoding_key in ENCODING_INFO:
            del ENCODING_INFO[encoding_key]
        
        if return_code != 0:
            # Only show error if FFMPEG actually failed
            er = stderr.decode()
            error_msg = "FFMPEG encoding failed"
            if "No such file" in er:
                error_msg = "Input file not found"
            elif "Permission denied" in er:
                error_msg = "Permission denied"
            elif "Invalid" in er:
                error_msg = "Invalid file format"
            
            await xxx.edit(f"**ENCODING ERROR:**\n\n`{error_msg}`\n\n**Contact @danish_00**")
            remove_user_task(event.sender_id)
            WORKING.clear()
            try:
                os.remove(dl)
                os.remove(out)
            except:
                pass
            return
            
        ees = dt.now()
        ttt = time.time()
        await nn.delete()
        
        # Send to task owner's DM (always)
        nnn = await event.client.send_message(event.sender_id, "**Uploading...**")
        
        upload_process_id = f"upload_{out}_{int(time.time())}"
        hehe_upload = f"upload;{upload_process_id}"
        cancel_data_upload = code(hehe_upload)
        
        with open(out, "rb") as f:
            ok = await upload_file(
                client=event.client,
                file=f,
                name=out,
                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                    progress(d, t, nnn, ttt, "uploading..", out.split("/")[-1], f"{cancel_data_upload}_{event.sender_id}", event.sender_id)
                ),
            )
        fname = out.split("/")[1]
        
        # Send compressed file to sender's DM
        ds = await event.client.send_file(
            event.sender_id, file=ok, force_document=True, thumb=thum, caption=f"`{fname}`"
        )
        await nnn.delete()
        
        # Send completion notification based on rules
        # For owner: only send group notification if original was from group
        # For non-owner: always send group notification (since they can only encode in groups)
        should_send_group_notification = False
        
        if is_owner:
            # Owner: send notification only if original was from group
            should_send_group_notification = not event.is_private
        else:
            # Non-owner: always send group notification (they can only encode in groups)
            should_send_group_notification = True
        
        if should_send_group_notification and event.chat_id != event.sender_id:
            try:
                notification_msg = f"@{sender_username} **Your Task Has Been Completed Check Bot DM.**\n\n**Original File Name:** `{kk}`"
                await event.client.send_message(event.chat_id, notification_msg)
            except Exception as e:
                LOGS.info(f"Notification error: {e}")
        
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
        
    except Exception as e:
        LOGS.info(f"Encoding error: {e}")
        remove_user_task(event.sender_id)
        WORKING.clear()

async def queue_status(event):
    try:
        if not QUEUE and not WORKING:
            await event.reply("**Queue is Empty!**")
            return
        
        queue_msg = "**Current Queue Status:**\n\n"
        
        if WORKING:
            queue_msg += "🔄 **Currently Processing**\n\n"
        
        if QUEUE:
            queue_msg += f"📋 **Queue ({len(QUEUE)} tasks):**\n"
            
            for i, (task_id, task_data) in enumerate(QUEUE.items(), 1):
                task_info = QUEUE_USERS.get(task_id, {})
                user_name = task_info.get('name', 'Unknown')
                user_id = task_info.get('id', 'Unknown')
                
                if isinstance(task_data, str):
                    # URL task
                    queue_msg += f"{i}. @{user_name} ({user_id}) - URL Task\n"
                else:
                    # File task
                    filename = task_data[0] if len(task_data) > 0 else "Unknown"
                    if len(filename) > 30:
                        filename = filename[:27] + "..."
                    queue_msg += f"{i}. @{user_name} ({user_id}) - {filename}\n"
        
        # Limit message length
        if len(queue_msg) > 4000:
            queue_msg = queue_msg[:3900] + "\n\n... (truncated)"
        
        await event.reply(queue_msg)
        
    except Exception as e:
        LOGS.info(f"Queue status error: {e}")
        await event.reply("❌ **Error getting queue status**")

async def clear_task(event):
    try:
        user_id = event.sender_id
        is_owner = str(user_id) in OWNER
        
        try:
            task_id = event.text.split()[1]
        except:
            await event.reply("❌ **Usage:** `/clear <task_id>`\n\nUse `/queue` to see task IDs")
            return
        
        # Find task by position or ID
        task_found = False
        task_key = None
        
        try:
            # Try as position number
            pos = int(task_id) - 1
            if 0 <= pos < len(QUEUE):
                task_key = list(QUEUE.keys())[pos]
                task_found = True
        except:
            # Try as direct ID
            if task_id in QUEUE:
                task_key = task_id
                task_found = True
        
        if not task_found:
            await event.reply("❌ **Task not found!** Use `/queue` to see valid task IDs")
            return
        
        # Check permissions
        task_owner_id = TASK_OWNERS.get(task_key)
        if not is_owner and user_id != task_owner_id:
            await event.reply("❌ **Access Denied!** You can only cancel your own tasks")
            return
        
        # Remove task
        QUEUE.pop(task_key)
        if task_key in TASK_OWNERS:
            task_owner = TASK_OWNERS.pop(task_key)
            remove_user_task(task_owner)
        if task_key in QUEUE_USERS:
            QUEUE_USERS.pop(task_key)
        if task_key in TASK_CHAT_INFO:
            TASK_CHAT_INFO.pop(task_key)
        
        await event.reply("✅ **Task removed from queue!**")
        
    except Exception as e:
        LOGS.info(f"Clear task error: {e}")
        await event.reply("❌ **Error removing task**")

async def fast_download(message, link, name, cancel_data, task_owner_id):
    """Fast download function for URL downloads"""
    import aiohttp
    import aiofiles
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as response:
                if response.status == 200:
                    file_size = int(response.headers.get('content-length', 0))
                    
                    async with aiofiles.open(f"downloads/{name}", 'wb') as f:
                        downloaded = 0
                        start_time = time.time()
                        
                        async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB chunks
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Update progress every 10MB or 5 seconds
                            if downloaded % (10 * 1024 * 1024) == 0 or (time.time() - start_time) > 5:
                                try:
                                    await progress(downloaded, file_size, message, start_time, "downloading", name, f"{cancel_data}_{task_owner_id}", task_owner_id)
                                except:
                                    pass
                    
                    return f"downloads/{name}"
                else:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                    
    except Exception as e:
        raise Exception(f"Download failed: {str(e)}")

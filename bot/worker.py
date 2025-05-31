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
        xxx = await event.reply("**Downloading...**")
        s = dt.now()
        ttt = time.time()
        dir = f"downloads/"
        
        # Store original event for group notification
        original_event = event
        original_chat_id = event.chat_id
        
        process_id = f"download_{event.media.document.id}_{int(time.time())}"
        hehe_dl = f"download;{process_id}"
        cancel_data_dl = code(hehe_dl)
        
        try:
            if hasattr(event.media, "document"):
                file = event.media.document
                dl = dir + filename
                with open(dl, "wb") as f:
                    ok = await download_file(
                        client=event.client,
                        location=file,
                        out=f,
                        progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                            progress(
                                d, t, xxx, ttt, "Downloading", filename,
                                cancel_data_dl, event.sender_id
                            )
                        ),
                    )
            else:
                dl = await event.client.download_media(
                    event.media,
                    dir,
                    progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                        progress(d, t, xxx, ttt, "Downloading", None, cancel_data_dl, event.sender_id)
                    ),
                )
                
            if process_id in CANCELLED_PROCESSES:
                CANCELLED_PROCESSES.discard(process_id)
                remove_user_task(event.sender_id)
                WORKING.clear()
                return
                
        except Exception as er:
            remove_user_task(event.sender_id)
            WORKING.clear()
            LOGS.info(er)
            await xxx.edit("**Download Failed or Cancelled!**")
            return
            
        es = dt.now()
        kk = dl.split("/")[-1]
        aa = kk.split(".")[-1]
        rr = f"encode"
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
        
        # Send to sender's DM instead of original chat
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
                    progress(d, t, nnn, ttt, "uploading..", out.split("/")[-1], cancel_data_upload, event.sender_id)
                ),
            )
        fname = out.split("/")[1]
        
        # Send compressed file to sender's DM
        ds = await event.client.send_file(
            event.sender_id, file=ok, force_document=True, thumb=thum, caption=f"`{fname}`"
        )
        await nnn.delete()
        
        # Send completion notification to original chat (if it was a group)
        await send_completion_notification(event.sender_id, original_chat_id, kk)
        
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
        
    except Exception as er:
        remove_user_task(event.sender_id)
        WORKING.clear()
        LOGS.info(f"Encoding error: {er}")
        try:
            await event.reply(f"**Encoding failed:** {str(er)}")
        except:
            pass

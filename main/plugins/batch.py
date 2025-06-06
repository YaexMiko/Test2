#Tg:MaheshChauhan/DroneBots
#Github.com/Vasusen-code

"""
Plugin for both public & private channels!
"""

import time, os, asyncio

from .. import bot as Drone
from .. import userbot, Bot, AUTH
from .. import FORCESUB as fs
from main.plugins.pyroplug import get_bulk_msg
from main.plugins.helpers import get_link, screenshot
from main.plugins.auth import get_user_client, is_user_authenticated

from telethon import events, Button, errors
from telethon.tl.types import DocumentAttributeVideo

from pyrogram import Client 
from pyrogram.errors import FloodWait

from ethon.pyfunc import video_metadata
from ethon.telefunc import force_sub

# Handle FORCESUB being None
if fs:
    ft = f"To use this bot you've to join @{fs}."
else:
    ft = None

batch = []

# Convert AUTH to integer if it's a string
try:
    AUTH_ID = int(AUTH)
except (ValueError, TypeError):
    AUTH_ID = None

@Drone.on(events.NewMessage(incoming=True, pattern='/cancel'))
async def cancel(event):
    if AUTH_ID and event.sender_id != AUTH_ID:
        return
    if not event.sender_id in batch:
        return await event.reply("No batch active.")
    batch.clear()
    await event.reply("Done.")
    
@Drone.on(events.NewMessage(incoming=True, pattern='/batch'))
async def _batch(event):
    if not event.is_private:
        return
    
    # Check if user is authorized
    if AUTH_ID and event.sender_id != AUTH_ID:
        return
    
    # Only check force sub if FORCESUB is configured
    if fs:
        try:
            s, r = await force_sub(event.client, fs, event.sender_id, ft)
            if s == True:
                await event.reply(r)
                return
        except Exception as e:
            print(f"Force sub check failed: {e}")
            # Continue without force sub if there's an error
            
    if event.sender_id in batch:
        return await event.reply("You've already started one batch, wait for it to complete you dumbfuck owner!")
    
    # Check for available userbot (either user-specific or global)
    user_client = get_user_client(event.sender_id)
    effective_userbot = user_client or userbot
    
    if not effective_userbot:
        await event.reply("❌ Batch processing requires authentication.\nUse /login to authenticate or contact admin to enable global userbot.")
        return
        
    async with Drone.conversation(event.chat_id) as conv: 
        await conv.send_message("Send me the message link you want to start saving from, as a reply to this message.", buttons=Button.force_reply())
        try:
            link = await conv.get_reply()
            try:
                _link = get_link(link.text)
            except Exception:
                await conv.send_message("No link found.")
                return conv.cancel()
        except Exception as e:
            print(e)
            await conv.send_message("Cannot wait more longer for your response!")
            return conv.cancel()
            
        # Check if this is a private channel link and user needs to be authenticated
        if 't.me/c/' in _link and not user_client and not userbot:
            await conv.send_message("❌ Private channel batch processing requires authentication. Use /login first.")
            return conv.cancel()
            
        await conv.send_message("Send me the number of files/range you want to save from the given message, as a reply to this message.", buttons=Button.force_reply())
        try:
            _range = await conv.get_reply()
        except Exception as e:
            print(e)
            await conv.send_message("Cannot wait more longer for your response!")
            return conv.cancel()
        try:
            value = int(_range.text)
            if value > 100:
                await conv.send_message("You can only get upto 100 files in a single batch.")
                return conv.cancel()
        except ValueError:
            await conv.send_message("Range must be an integer!")
            return conv.cancel()
        batch.append(event.sender_id)
        await run_batch(effective_userbot, Bot, event.sender_id, _link, value) 
        conv.cancel()
        batch.clear()

async def run_batch(userbot, client, sender, link, _range):
    for i in range(_range):
        timer = 60
        if i < 25:
            timer = 5
        if i < 50 and i > 25:
            timer = 10
        if i < 100 and i > 50:
            timer = 15
        if not 't.me/c/' in link:
            if i < 25:
                timer = 2
            else:
                timer = 3
        try: 
            if not sender in batch:
                await client.send_message(sender, "Batch completed.")
                break
        except Exception as e:
            print(e)
            await client.send_message(sender, "Batch completed.")
            break
        try:
            await get_bulk_msg(userbot, client, sender, link, i) 
        except FloodWait as fw:
            if int(fw.x) > 299:
                await client.send_message(sender, "Cancelling batch since you have floodwait more than 5 minutes.")
                break
            await asyncio.sleep(fw.x + 5)
            await get_bulk_msg(userbot, client, sender, link, i)
        protection = await client.send_message(sender, f"Sleeping for `{timer}` seconds to avoid Floodwaits and Protect account!")
        await asyncio.sleep(timer)
        await protection.delete()

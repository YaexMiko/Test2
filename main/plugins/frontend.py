#Github.com/Vasusen-code

import time, os

from .. import bot as Drone
from .. import userbot, Bot
from .. import FORCESUB as fs
from main.plugins.pyroplug import get_msg
from main.plugins.helpers import get_link, join
from main.plugins.auth import get_user_client, is_user_authenticated

from telethon import events
from pyrogram.errors import FloodWait

from ethon.telefunc import force_sub

# Handle FORCESUB being None
if fs:
    ft = f"To use this bot you've to join @{fs}."
else:
    ft = None

message = "Send me the message link you want to start saving from, as a reply to this message."

@Drone.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def clone(event):
    if event.is_reply:
        reply = await event.get_reply_message()
        if reply.text == message:
            return
    try:
        link = get_link(event.text)
        if not link:
            return
    except TypeError:
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
    
    edit = await event.reply("Processing!")
    try:
        if 't.me/+' in link:
            # Check for user-specific session first
            user_client = get_user_client(event.sender_id)
            if user_client:
                q = await join(user_client, link)
                await edit.edit(q)
                return
            elif not userbot:
                await edit.edit("❌ Private channel access requires login.\nUse /login to authenticate your account.")
                return
            else:
                q = await join(userbot, link)
                await edit.edit(q)
                return
                
        if 't.me/' in link:
            # Check if this is a private channel
            if 't.me/c/' in link:
                # Try user-specific session first
                user_client = get_user_client(event.sender_id)
                if user_client:
                    await get_msg(user_client, Bot, Drone, event.sender_id, edit.id, link, 0)
                    return
                elif not userbot:
                    await edit.edit("❌ Private channel access requires login.\nUse /login to authenticate your account.")
                    return
                else:
                    await get_msg(userbot, Bot, Drone, event.sender_id, edit.id, link, 0)
                    return
            else:
                # Public channel - can use any client
                effective_userbot = get_user_client(event.sender_id) or userbot
                await get_msg(effective_userbot, Bot, Drone, event.sender_id, edit.id, link, 0)
                
    except FloodWait as fw:
        return await Drone.send_message(event.sender_id, f'Try again after {fw.x} seconds due to floodwait from telegram.')
    except Exception as e:
        print(e)
        await Drone.send_message(event.sender_id, f"An error occurred during cloning of `{link}`\n\n**Error:** {str(e)}")

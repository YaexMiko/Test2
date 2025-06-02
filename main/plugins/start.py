#Github.com/Vasusen-code

import os
from .. import bot as Drone
from telethon import events, Button
from main.plugins.auth import is_user_authenticated, get_user_session_info

from ethon.mystarts import start_srb
    
S = '/' + 's' + 't' + 'a' + 'r' + 't'

@Drone.on(events.callbackquery.CallbackQuery(data="set"))
async def sett(event):    
    Drone = event.client                    
    button = await event.get_message()
    msg = await button.get_reply_message() 
    await event.delete()
    async with Drone.conversation(event.chat_id) as conv: 
        xx = await conv.send_message("Send me any image for thumbnail as a `reply` to this message.")
        x = await conv.get_reply()
        if not x.media:
            xx.edit("No media found.")
        mime = x.file.mime_type
        if not 'png' in mime:
            if not 'jpg' in mime:
                if not 'jpeg' in mime:
                    return await xx.edit("No image found.")
        await xx.delete()
        t = await event.client.send_message(event.chat_id, 'Trying.')
        path = await event.client.download_media(x.media)
        if os.path.exists(f'{event.sender_id}.jpg'):
            os.remove(f'{event.sender_id}.jpg')
        os.rename(path, f'./{event.sender_id}.jpg')
        
        # Update settings if settings module is available
        try:
            from main.plugins.settings import get_user_settings
            settings = get_user_settings(event.sender_id)
            settings['has_custom_thumbnail'] = True
        except ImportError:
            pass
        
        await t.edit("Temporary thumbnail saved!")
        
@Drone.on(events.callbackquery.CallbackQuery(data="rem"))
async def remt(event):  
    Drone = event.client            
    await event.edit('Trying.')
    try:
        os.remove(f'{event.sender_id}.jpg')
        
        # Update settings if settings module is available
        try:
            from main.plugins.settings import get_user_settings
            settings = get_user_settings(event.sender_id)
            settings['has_custom_thumbnail'] = False
        except ImportError:
            pass
        
        await event.edit('Removed!')
    except Exception:
        await event.edit("No thumbnail saved.")                        
  
@Drone.on(events.NewMessage(incoming=True, pattern=f"{S}"))
async def start(event):
    user_id = event.sender_id
    
    # Check authentication status
    auth_status = ""
    if is_user_authenticated(user_id):
        session_info = get_user_session_info(user_id)
        auth_status = f"\n\n🔐 **Status:** Logged in ({session_info['phone']})"
    else:
        auth_status = f"\n\n🔐 **Status:** Not logged in\n💡 Use /login to access private channels"
    
    text = ("Send me Link of any message to clone it here, For private channel message, send invite link first.\n\n"
            "**COMMANDS:**\n"
            "🔐 /login - Login with your account\n"
            "🚪 /logout - Logout from your account\n"
            "📊 /status - Check login status\n"
            "⚙️ /settings - Manage bot settings\n"
            "📦 /batch - Batch download (owner only)\n\n"
            f"**SUPPORT:** @TeamDrone{auth_status}")
    
    await start_srb(event, text)

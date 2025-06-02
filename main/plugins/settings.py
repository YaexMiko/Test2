import os
from .. import bot as Drone, AUTH
from telethon import events, Button

# User settings storage (in-memory for now)
user_settings = {}

def get_user_settings(user_id):
    if user_id not in user_settings:
        user_settings[user_id] = {
            'upload_mode': 'Telegram',  # Telegram, Document, Media
            'upload_type': 'DOCUMENT',  # DOCUMENT, MEDIA
            'prefix': None,
            'suffix': None,
            'upload_destination': None,
            'caption': None,
            'auto_rename': None,
            'metadata': 'Disabled',
            'remove_replace_words': None,
            'has_custom_thumbnail': False,
            'messages_saved': 0
        }
    return user_settings[user_id]

def settings_have_changed(user_id):
    settings = get_user_settings(user_id)
    defaults = {
        'upload_mode': 'Telegram',
        'upload_type': 'DOCUMENT',
        'prefix': None,
        'suffix': None,
        'upload_destination': None,
        'caption': None,
        'auto_rename': None,
        'metadata': 'Disabled',
        'remove_replace_words': None
    }
    
    for key, default_value in defaults.items():
        if settings.get(key) != default_value:
            return True
    
    if settings.get('has_custom_thumbnail', False):
        return True
        
    return False

def generate_settings_text(user_id):
    settings = get_user_settings(user_id)
    
    # Check if custom thumbnail exists
    has_thumbnail = os.path.exists(f'{user_id}.jpg')
    settings['has_custom_thumbnail'] = has_thumbnail
    
    text = f"**Settings for** `{user_id}` 📊\n\n"
    text += f"Messages Saved: {settings['messages_saved']}\n\n"
    
    text += f"Custom Thumbnail {'Exists' if has_thumbnail else 'Not Exists'}\n"
    text += f"Upload Type is {settings['upload_type']}\n"
    text += f"Prefix is {'None' if not settings['prefix'] else settings['prefix']}\n"
    text += f"Suffix is {'None' if not settings['suffix'] else settings['suffix']}\n"
    text += f"Upload Destination is {'None' if not settings['upload_destination'] else settings['upload_destination']}\n"
    text += f"Topic id is {'None' if not settings.get('topic_id') else settings['topic_id']}\n\n"
    
    text += f"Metadata is {settings['metadata']}\n"
    text += f"Remove/Replace Words from File is {'None' if not settings['remove_replace_words'] else settings['remove_replace_words']}\n"
    text += f"Remove/Replace Words from Caption is None\n"
    text += f"Auto Rename is {'None' if not settings['auto_rename'] else settings['auto_rename']}"
    
    return text

def create_settings_buttons(user_id):
    settings = get_user_settings(user_id)
    
    buttons = []
    
    # Upload Mode button with checkmark
    upload_mode_text = f"Upload Mode | {settings['upload_mode']}"
    if settings['upload_mode'] == 'Telegram':
        upload_mode_text += " ✅"
    
    buttons.append([Button.inline(upload_mode_text, b"upload_mode")])
    
    # Second row - Send As Document/Media and Set Upload Destination
    if settings['upload_type'] == 'DOCUMENT':
        send_as_text = "Send As Document"
    else:
        send_as_text = "Send As Media"
    
    buttons.append([
        Button.inline(send_as_text, b"toggle_send_as"),
        Button.inline("Set Upload Destination", b"set_destination")
    ])
    
    # Third row - Set Thumbnail and Set Caption
    buttons.append([
        Button.inline("Set Thumbnail", b"set_thumbnail"),
        Button.inline("Set Caption", b"set_caption")
    ])
    
    # Fourth row - Set Suffix and Set Prefix
    buttons.append([
        Button.inline("Set Suffix", b"set_suffix"),
        Button.inline("Set Prefix", b"set_prefix")
    ])
    
    # Fifth row - Set Auto Rename and Set Metadata
    buttons.append([
        Button.inline("Set Auto Rename", b"set_auto_rename"),
        Button.inline("Set Metadata", b"set_metadata")
    ])
    
    # Reset All button (only if settings have changed)
    if settings_have_changed(user_id):
        buttons.append([Button.inline("Reset All", b"reset_all")])
    
    # Remove/Replace Words button
    buttons.append([Button.inline("Remove/Replace Words", b"remove_replace")])
    
    return buttons

@Drone.on(events.NewMessage(incoming=True, pattern='/settings'))
async def settings_command(event):
    if not event.is_private:
        return
        
    user_id = event.sender_id
    
    # Telegraph image URL
    image_url = "https://telegra.ph/file/37985c408b1b7c817cbd6-4b850ca6f02b6eae30.jpg"
    
    settings_text = generate_settings_text(user_id)
    buttons = create_settings_buttons(user_id)
    
    await event.respond(
        settings_text,
        file=image_url,
        buttons=buttons
    )

@Drone.on(events.CallbackQuery(data=b"upload_mode"))
async def upload_mode_callback(event):
    user_id = event.sender_id
    settings = get_user_settings(user_id)
    
    # Cycle through upload modes: Telegram -> Document -> Media -> Telegram
    if settings['upload_mode'] == 'Telegram':
        settings['upload_mode'] = 'Document'
        settings['upload_type'] = 'DOCUMENT'
    elif settings['upload_mode'] == 'Document':
        settings['upload_mode'] = 'Media'
        settings['upload_type'] = 'MEDIA'
    else:
        settings['upload_mode'] = 'Telegram'
        settings['upload_type'] = 'DOCUMENT'
    
    # Update the message
    settings_text = generate_settings_text(user_id)
    buttons = create_settings_buttons(user_id)
    
    await event.edit(
        settings_text,
        buttons=buttons
    )

@Drone.on(events.CallbackQuery(data=b"toggle_send_as"))
async def toggle_send_as_callback(event):
    user_id = event.sender_id
    settings = get_user_settings(user_id)
    
    # Toggle between Document and Media
    if settings['upload_type'] == 'DOCUMENT':
        settings['upload_type'] = 'MEDIA'
    else:
        settings['upload_type'] = 'DOCUMENT'
    
    # Update the message
    settings_text = generate_settings_text(user_id)
    buttons = create_settings_buttons(user_id)
    
    await event.edit(
        settings_text,
        buttons=buttons
    )

@Drone.on(events.CallbackQuery(data=b"set_thumbnail"))
async def set_thumbnail_callback(event):
    await event.answer("🔧 Features Coming Soon!", alert=True)

@Drone.on(events.CallbackQuery(data=b"set_destination"))
async def set_destination_callback(event):
    await event.answer("🔧 Features Coming Soon!", alert=True)

@Drone.on(events.CallbackQuery(data=b"set_caption"))
async def set_caption_callback(event):
    await event.answer("🔧 Features Coming Soon!", alert=True)

@Drone.on(events.CallbackQuery(data=b"set_suffix"))
async def set_suffix_callback(event):
    await event.answer("🔧 Features Coming Soon!", alert=True)

@Drone.on(events.CallbackQuery(data=b"set_prefix"))
async def set_prefix_callback(event):
    await event.answer("🔧 Features Coming Soon!", alert=True)

@Drone.on(events.CallbackQuery(data=b"set_auto_rename"))
async def set_auto_rename_callback(event):
    await event.answer("🔧 Features Coming Soon!", alert=True)

@Drone.on(events.CallbackQuery(data=b"set_metadata"))
async def set_metadata_callback(event):
    await event.answer("🔧 Features Coming Soon!", alert=True)

@Drone.on(events.CallbackQuery(data=b"remove_replace"))
async def remove_replace_callback(event):
    await event.answer("🔧 Features Coming Soon!", alert=True)

@Drone.on(events.CallbackQuery(data=b"reset_all"))
async def reset_all_callback(event):
    user_id = event.sender_id
    
    # Reset all settings to default
    user_settings[user_id] = {
        'upload_mode': 'Telegram',
        'upload_type': 'DOCUMENT',
        'prefix': None,
        'suffix': None,
        'upload_destination': None,
        'caption': None,
        'auto_rename': None,
        'metadata': 'Disabled',
        'remove_replace_words': None,
        'has_custom_thumbnail': False,
        'messages_saved': 0
    }
    
    # Update the message
    settings_text = generate_settings_text(user_id)
    buttons = create_settings_buttons(user_id)
    
    await event.edit(
        settings_text,
        buttons=buttons
    )
    
    await event.answer("✅ All settings reset to default!", alert=True)

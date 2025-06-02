#Github.com/Vasusen-code
# User Authentication System

import os
import asyncio
from pyrogram import Client
from pyrogram.errors import PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid
from telethon import events, Button
from .. import bot as Drone, API_ID, API_HASH

# Store user sessions in memory
user_sessions = {}
pending_logins = {}

class UserSession:
    def __init__(self, user_id, phone_number, client=None):
        self.user_id = user_id
        self.phone_number = phone_number
        self.client = client
        self.is_authenticated = False
        self.session_file = f"sessions/user_{user_id}.session"

def get_user_client(user_id):
    """Get authenticated client for user"""
    if user_id in user_sessions and user_sessions[user_id].is_authenticated:
        return user_sessions[user_id].client
    return None

def create_session_dir():
    """Create sessions directory if it doesn't exist"""
    if not os.path.exists("sessions"):
        os.makedirs("sessions")

def is_user_authenticated(user_id):
    """Check if user is authenticated"""
    return user_id in user_sessions and user_sessions[user_id].is_authenticated

def get_user_session_info(user_id):
    """Get user session information"""
    if user_id in user_sessions:
        session = user_sessions[user_id]
        return {
            'phone': session.phone_number,
            'authenticated': session.is_authenticated
        }
    return None

@Drone.on(events.NewMessage(incoming=True, pattern='/login'))
async def login_command(event):
    if not event.is_private:
        return await event.reply("❌ Login command only works in private chat.")
    
    user_id = event.sender_id
    
    # Check if user is already logged in
    if user_id in user_sessions and user_sessions[user_id].is_authenticated:
        return await event.reply("✅ You are already logged in!\nUse /logout to logout first.")
    
    # Check if user has pending login
    if user_id in pending_logins:
        return await event.reply("⏳ You already have a pending login process.\nPlease complete it or wait for it to timeout.")
    
    await event.reply(
        "🔐 **User Login Process**\n\n"
        "To access private channels, you need to login with your Telegram account.\n"
        "⚠️ **This is completely safe and your credentials are not stored.**\n\n"
        "📱 Please send your phone number in international format.\n"
        "Example: +1234567890",
        buttons=[
            [Button.inline("❌ Cancel", b"cancel_login")]
        ]
    )
    
    # Set pending login
    pending_logins[user_id] = {
        'step': 'phone',
        'phone': None,
        'phone_code_hash': None,
        'client': None
    }

@Drone.on(events.NewMessage(incoming=True, pattern='/logout'))
async def logout_command(event):
    if not event.is_private:
        return await event.reply("❌ Logout command only works in private chat.")
    
    user_id = event.sender_id
    
    if user_id not in user_sessions or not user_sessions[user_id].is_authenticated:
        return await event.reply("❌ You are not logged in.")
    
    try:
        # Stop the client
        if user_sessions[user_id].client:
            await user_sessions[user_id].client.stop()
        
        # Remove session file
        session_file = f"sessions/user_{user_id}.session"
        if os.path.exists(session_file):
            os.remove(session_file)
        
        # Remove from memory
        del user_sessions[user_id]
        
        await event.reply("✅ Successfully logged out!\nYour session has been cleared.")
        
    except Exception as e:
        print(f"Logout error for user {user_id}: {e}")
        await event.reply("❌ Error during logout. Please try again.")

@Drone.on(events.NewMessage(incoming=True, pattern='/status'))
async def status_command(event):
    if not event.is_private:
        return
    
    user_id = event.sender_id
    
    if is_user_authenticated(user_id):
        session_info = get_user_session_info(user_id)
        await event.reply(
            f"✅ **Login Status: Active**\n\n"
            f"📱 **Phone:** {session_info['phone']}\n"
            f"🆔 **User ID:** {user_id}\n"
            f"⏰ **Session:** Active\n\n"
            f"🎯 You can access private channels and use all features."
        )
    else:
        await event.reply(
            f"❌ **Login Status: Not Logged In**\n\n"
            f"🆔 **User ID:** {user_id}\n"
            f"📱 **Phone:** Not provided\n"
            f"⏰ **Session:** Inactive\n\n"
            f"💡 Use /login to authenticate and access private channels."
        )

# FIXED: More specific pattern matching to avoid conflicts
@Drone.on(events.NewMessage(incoming=True, func=lambda e: (
    e.is_private and 
    e.sender_id in pending_logins and 
    not e.text.startswith('/') and  # Avoid command conflicts
    not e.text.startswith('t.me/')  # Avoid link conflicts
)))
async def handle_login_process(event):
    user_id = event.sender_id
    login_data = pending_logins[user_id]
    
    if login_data['step'] == 'phone':
        await handle_phone_input(event, login_data)
    elif login_data['step'] == 'otp':
        await handle_otp_input(event, login_data)
    elif login_data['step'] == 'password':
        await handle_password_input(event, login_data)

async def handle_phone_input(event, login_data):
    phone = event.text.strip()
    
    # Basic phone validation
    if not phone.startswith('+') or len(phone) < 8:
        return await event.reply("❌ Invalid phone number format.\nPlease use international format: +1234567890")
    
    try:
        create_session_dir()
        
        # Create new client for this user
        session_name = f"sessions/user_{event.sender_id}"
        client = Client(
            session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            phone_number=phone
        )
        
        await client.connect()
        
        # Send OTP
        sent_code = await client.send_code(phone)
        
        login_data['phone'] = phone
        login_data['phone_code_hash'] = sent_code.phone_code_hash
        login_data['client'] = client
        login_data['step'] = 'otp'
        
        await event.reply(
            f"📱 OTP sent to **{phone}**\n\n"
            "🔢 Please send the verification code you received.\n"
            "⏰ Code expires in 5 minutes.",
            buttons=[
                [Button.inline("❌ Cancel Login", b"cancel_login")]
            ]
        )
        
    except PhoneNumberInvalid:
        await event.reply("❌ Invalid phone number. Please try again with correct format.")
    except Exception as e:
        print(f"Phone input error: {e}")
        await event.reply("❌ Error sending OTP. Please try again later.")
        # Cleanup
        if event.sender_id in pending_logins:
            del pending_logins[event.sender_id]

async def handle_otp_input(event, login_data):
    otp = event.text.strip()
    
    # Basic OTP validation
    if not otp.isdigit() or len(otp) < 4:
        return await event.reply("❌ Invalid OTP format. Please send only numbers.")
    
    try:
        client = login_data['client']
        phone = login_data['phone']
        
        # Verify OTP
        await client.sign_in(phone, login_data['phone_code_hash'], otp)
        
        # Check if login was successful
        me = await client.get_me()
        
        # Store session
        user_sessions[event.sender_id] = UserSession(
            event.sender_id,
            phone,
            client
        )
        user_sessions[event.sender_id].is_authenticated = True
        
        # Remove pending login
        del pending_logins[event.sender_id]
        
        await event.reply(
            f"✅ **Successfully logged in!**\n\n"
            f"👤 **Name:** {me.first_name} {me.last_name or ''}\n"
            f"📱 **Phone:** {phone}\n"
            f"🆔 **User ID:** {me.id}\n\n"
            "🎉 You can now access private channels and use all bot features!"
        )
        
    except PhoneCodeInvalid:
        await event.reply("❌ Invalid verification code. Please try again.")
    except PhoneCodeExpired:
        await event.reply("❌ Verification code expired. Please restart login process with /login")
        # Cleanup
        if event.sender_id in pending_logins:
            try:
                await login_data['client'].disconnect()
            except:
                pass
            del pending_logins[event.sender_id]
    except SessionPasswordNeeded:
        login_data['step'] = 'password'
        await event.reply(
            "🔐 **Two-step verification enabled**\n\n"
            "🔑 Please send your account password (2FA):",
            buttons=[
                [Button.inline("❌ Cancel Login", b"cancel_login")]
            ]
        )
    except Exception as e:
        print(f"OTP verification error: {e}")
        await event.reply("❌ Error verifying OTP. Please try again or restart with /login")

async def handle_password_input(event, login_data):
    password = event.text.strip()
    
    try:
        client = login_data['client']
        
        # Verify 2FA password
        await client.check_password(password)
        
        # Check if login was successful
        me = await client.get_me()
        
        # Store session
        user_sessions[event.sender_id] = UserSession(
            event.sender_id,
            login_data['phone'],
            client
        )
        user_sessions[event.sender_id].is_authenticated = True
        
        # Remove pending login
        del pending_logins[event.sender_id]
        
        await event.reply(
            f"✅ **Successfully logged in!**\n\n"
            f"👤 **Name:** {me.first_name} {me.last_name or ''}\n"
            f"📱 **Phone:** {login_data['phone']}\n"
            f"🆔 **User ID:** {me.id}\n\n"
            "🎉 You can now access private channels and use all bot features!"
        )
        
    except PasswordHashInvalid:
        await event.reply("❌ Invalid password. Please try again.")
    except Exception as e:
        print(f"Password verification error: {e}")
        await event.reply("❌ Error verifying password. Please try again or restart with /login")

@Drone.on(events.CallbackQuery(data=b"cancel_login"))
async def cancel_login_callback(event):
    user_id = event.sender_id
    
    if user_id in pending_logins:
        # Cleanup client
        try:
            if pending_logins[user_id].get('client'):
                await pending_logins[user_id]['client'].disconnect()
        except:
            pass
        
        del pending_logins[user_id]
    
    await event.edit("❌ Login process cancelled.")

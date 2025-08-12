"""
Prints telegram session string key
"""

try:
    from config import (
        API_APP_VERSION,
        API_DEVICE_MODEL,
        API_HASH,
        API_ID,
        API_SYSTEM_VERSION,
    )
except Exception:
    print("Failed reading .env")
    raise
from telethon import TelegramClient
from telethon.sessions import StringSession

with TelegramClient(
    session=StringSession(),
    api_id=API_ID,
    api_hash=API_HASH,
    device_model=API_DEVICE_MODEL,
    system_version=API_SYSTEM_VERSION,
    app_version=API_APP_VERSION,
) as client:
    print("Session string: ", client.session.save())

"""
Prints telegram session string key
"""
from config import API_HASH, API_ID
from telethon import TelegramClient
from telethon.sessions import StringSession

with TelegramClient(session=StringSession(), api_id=API_ID, api_hash=API_HASH) as client:
    print('Session string: ', client.session.save())

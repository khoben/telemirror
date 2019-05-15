from telethon import events, functions, utils
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from settings import (API_HASH, API_ID, CHATS, OFFSET, SESSION_STRING,
                      TARGET_CHAT)

# print your session key
with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print(client.session.save())

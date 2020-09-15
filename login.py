from telethon.sync import TelegramClient
from telethon.sessions import StringSession

from app.settings import (API_HASH, API_ID)

# print your session key
with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print(client.session.save())

from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telethon.tl.types import MessageService

from settings import (API_HASH, API_ID)

"""
Make full copy of telegram channel
"""

# put your session string here
SESSION_STRING = "xxx"
SOURCE_CHAT = '@xxx'
TARGET_CHAT = '@xxx'
LIMIT_TO_WAIT = 50


def do_full_copy():
    with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        amount_sended = 0
        for message in client.iter_messages(SOURCE_CHAT):
            # skip if service messages
            if isinstance(message, MessageService):
                continue
            try:
                client.send_message(TARGET_CHAT, message)
                amount_sended += 1
                if amount_sended >= LIMIT_TO_WAIT:
                    amount_sended = 0
                    time.sleep(1)
            except Exception as e:
                print(e)

        print("Done")


if __name__ == "__main__":
    do_full_copy()

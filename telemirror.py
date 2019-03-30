import re

import socks
from telethon import events, functions, utils
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from urlextract import URLExtract
import math

from settings import (API_HASH, API_ID, CHATS, OFFSET, SESSION_STRING,
                      TARGET_CHAT)

extractor = URLExtract()

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)


def remove_urls(text):
    WHITELIST = ['youtube.com', 'youtu.be', 'vk.com', 'twitch.tv']
    urls = extractor.find_urls(text)
    for url in urls:
        allowed = False
        for ex in WHITELIST:
            if url.find(ex) != -1:
                allowed = True
                break
        if allowed is False:
            text = text.replace(url, "<ссылка>")

    text = re.sub(r'(@)([\d\w]*)', r'\1 \2', text)

    return text


@client.on(events.NewMessage(chats=CHATS))
async def handler_new_message(event):
    try:
        print('LOG: NEW MESSAGE.')
        print(event.message)
        event.message.message = remove_urls(event.message.message)
        await client.send_message(TARGET_CHAT, event.message)
    except Exception as e:
        print(e)


@client.on(events.MessageEdited(chats=CHATS))
async def handler_edit_message(event):
    try:
        print('LOG. EDIT MESSAGE')
        print(event.message)
        id_message_to_edit = math.fabs(event.message.id - OFFSET)
        result = await client(functions.channels.GetMessagesRequest(
            channel='@plus400k',
            id=[id_message_to_edit]
        ))
        message_to_edit = result.messages[0]
        event.message.message = remove_urls(event.message.message)
        await client.edit_message(message_to_edit, event.message.message)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    client.start()
    client.run_until_disconnected()

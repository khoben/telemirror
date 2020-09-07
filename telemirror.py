import logging

from telethon import events, functions, utils
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPoll, InputMediaPoll

import database
from settings import (API_HASH, API_ID, CHATS, REMOVE_URLS, SESSION_STRING,
                      TARGET_CHAT)
from utils import remove_urls

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.NewMessage(chats=CHATS))
async def handler_new_message(event):
    try:
        logger.debug(f'New message:\n{event.message}')
        if REMOVE_URLS:
            event.message.message = remove_urls(event.message.message)
        mirror_id = None
        if (isinstance(event.message.media, MessageMediaPoll)):
            mirror_id = await client.send_message(TARGET_CHAT, file=InputMediaPoll(poll=event.message.media.poll))
        else:
            mirror_id = await client.send_message(TARGET_CHAT, event.message)
        database.insert({
            'original_id': event.message.id,
            'mirror_id': mirror_id.id,
            'original_channel': event.chat_id
        })
    except Exception as e:
        logger.error(e, exc_info=True)


@client.on(events.MessageEdited(chats=CHATS))
async def handler_edit_message(event):
    try:
        logger.debug('Edit message')
        mirror_message = database.find_by_original_id(event.message.id, event.chat_id)
        if mirror_message is None:
            return
        id_message_to_edit = mirror_message['mirror_id']
        result = await client(functions.channels.GetMessagesRequest(
            channel=TARGET_CHAT,
            id=[id_message_to_edit]
        ))
        message_to_edit = result.messages[0]
        if REMOVE_URLS:
            event.message.message = remove_urls(event.message.message)
        await client.edit_message(message_to_edit, event.message.message)
    except Exception as e:
        logger.error(e, exc_info=True)


if __name__ == '__main__':
    client.start()
    client.run_until_disconnected()

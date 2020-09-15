import logging

from telethon import events, functions, utils
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPoll, InputMediaPoll

from database import Database, MirrorMessage
from settings import (API_HASH, API_ID, CHATS, REMOVE_URLS, SESSION_STRING,
                      TARGET_CHAT, LOG_LEVEL, DB_URL)
from utils import remove_urls

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
db = Database(DB_URL)

@client.on(events.NewMessage(chats=CHATS))
async def handler_new_message(event):
    """NewMessage event handler.
    """
    try:
        logger.debug(f'New message from {event.chat_id}:\n{event.message}')
        if REMOVE_URLS:
            event.message.message = remove_urls(event.message.message)
        mirror_message = None
        if (isinstance(event.message.media, MessageMediaPoll)):
            mirror_message = await client.send_message(TARGET_CHAT, file=InputMediaPoll(poll=event.message.media.poll))
        else:
            mirror_message = await client.send_message(TARGET_CHAT, event.message)

        if mirror_message is not None:
            db.insert(MirrorMessage(original_id=event.message.id,
                                    mirror_id=mirror_message.id,
                                    original_channel=event.chat_id))
    except Exception as e:
        logger.error(e, exc_info=True)


@client.on(events.MessageEdited(chats=CHATS))
async def handler_edit_message(event):
    """MessageEdited event handler.
    """
    try:
        logger.debug(f'Edit message {event.message.id} from {event.chat_id}')
        mirror_message = db.find_by_original_id(event.message.id, event.chat_id)
        if mirror_message is None:
            return
        if REMOVE_URLS:
            event.message.message = remove_urls(event.message.message)
        await client.edit_message(TARGET_CHAT, mirror_message.mirror_id, event.message.message)
    except Exception as e:
        logger.error(e, exc_info=True)


if __name__ == '__main__':
    client.start()
    client.run_until_disconnected()

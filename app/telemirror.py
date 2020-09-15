import logging
import time

from telethon import events
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telethon.tl.types import InputMediaPoll, MessageMediaPoll

from database import Database, MirrorMessage
from settings import (API_HASH, API_ID, CHANNEL_MAPPING, CHATS, DB_URL,
                      LOG_LEVEL, REMOVE_URLS, SESSION_STRING, TIMEOUT_MIRRORING)
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
        targets = CHANNEL_MAPPING.get(event.chat_id)
        if targets is None or len(targets) < 1:
            logger.warning(f'NewMessage. No target channel for {event.chat_id}')
            return
        if REMOVE_URLS:
            event.message.message = remove_urls(event.message.message)

        for chat in targets:
            mirror_message = None
            if isinstance(event.message.media, MessageMediaPoll):
                mirror_message = await client.send_message(chat,
                                file=InputMediaPoll(poll=event.message.media.poll))
            else:
                mirror_message = await client.send_message(chat, event.message)

            if mirror_message is not None:
                db.insert(MirrorMessage(original_id=event.message.id,
                                        original_channel=event.chat_id,
                                        mirror_id=mirror_message.id,
                                        mirror_channel=chat))
            time.sleep(TIMEOUT_MIRRORING)
    except Exception as e:
        logger.error(e, exc_info=True)


@client.on(events.MessageEdited(chats=CHATS))
async def handler_edit_message(event):
    """MessageEdited event handler.
    """
    try:
        logger.debug(f'Edit message {event.message.id} from {event.chat_id}')
        targets = db.find_by_original_id(event.message.id, event.chat_id)
        if targets is None or len(targets) < 1:
            logger.warning(f'MessageEdited. No target channel for {event.chat_id}')
            return
        if REMOVE_URLS:
            event.message.message = remove_urls(event.message.message)
        for chat in targets:
            await client.edit_message(chat.mirror_channel, chat.mirror_id, event.message.message)
            time.sleep(TIMEOUT_MIRRORING)
    except Exception as e:
        logger.error(e, exc_info=True)


if __name__ == '__main__':
    client.start()
    client.run_until_disconnected()

import logging
import time

from telethon import events
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telethon.tl.types import InputMediaPoll, MessageMediaPoll, MessageEntityTextUrl

from database import Database, MirrorMessage
from settings import (API_HASH, API_ID, CHANNEL_MAPPING, CHATS, DB_URL,
                      LIMIT_TO_WAIT, LOG_LEVEL, REMOVE_URLS, SESSION_STRING,
                      TIMEOUT_MIRRORING)
from utils import remove_urls

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level=LOG_LEVEL)


client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
db = Database(DB_URL)


def remove_url_from_message(message):
    message.message = remove_urls(message.message)
    if message.entities is not None:
        for e in message.entities:
            if isinstance(e, MessageEntityTextUrl):
                e.url = remove_urls(e.url)
    return message


@client.on(events.Album(chats=CHATS))
async def handler_album(event):
    """Album event handler.
    """
    try:
        logger.debug(f'New Album from {event.chat_id}:\n{event}')
        targets = CHANNEL_MAPPING.get(event.chat_id)
        if targets is None or len(targets) < 1:
            logger.warning(f'Album. No target channel for {event.chat_id}')
            return
        # media
        files = []
        # captions
        caps = []
        # original messages ids
        original_idxs = []
        for item in event.messages:
            if REMOVE_URLS:
                item = remove_url_from_message(item)
            files.append(item.media)
            caps.append(item.message)
            original_idxs.append(item.id)
        sent = 0
        for chat in targets:
            mirror_messages = await client.send_file(chat, caption=caps, file=files)
            if mirror_messages is not None and len(mirror_messages) > 1:
                for idx, m in enumerate(mirror_messages):
                    db.insert(MirrorMessage(original_id=original_idxs[idx],
                                            original_channel=event.chat_id,
                                            mirror_id=m.id,
                                            mirror_channel=chat))
            sent += 1
            if sent > LIMIT_TO_WAIT:
                sent = 0
                time.sleep(TIMEOUT_MIRRORING)
    except Exception as e:
        logger.error(e, exc_info=True)


@client.on(events.NewMessage(chats=CHATS))
async def handler_new_message(event):
    """NewMessage event handler.
    """
    # skip if Album
    if hasattr(event, 'grouped_id') and event.grouped_id is not None:
        return
    try:
        logger.debug(f'New message from {event.chat_id}:\n{event.message}')
        targets = CHANNEL_MAPPING.get(event.chat_id)
        if targets is None or len(targets) < 1:
            logger.warning(
                f'NewMessage. No target channel for {event.chat_id}')
            return
        if REMOVE_URLS:
            event.message = remove_url_from_message(event.message)
        sent = 0
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
            sent += 1
            if sent > LIMIT_TO_WAIT:
                sent = 0
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
            logger.warning(
                f'MessageEdited. No target channel for {event.chat_id}')
            return
        if REMOVE_URLS:
            event.message = remove_url_from_message(event.message)
        sent = 0
        for chat in targets:
            await client.edit_message(chat.mirror_channel, chat.mirror_id, event.message.message)
            sent += 1
            if sent > LIMIT_TO_WAIT:
                sent = 0
                time.sleep(TIMEOUT_MIRRORING)
    except Exception as e:
        logger.error(e, exc_info=True)


if __name__ == '__main__':
    client.start()
    if client.is_user_authorized():
        me = client.get_me()
        logger.info(f'Connected as {me.username} ({me.phone})')
        client.run_until_disconnected()
    else:
        logger.error('Cannot be authorized')

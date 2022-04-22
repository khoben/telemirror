import logging

from app.messagefilters import EmptyFilter, UrlFilter
from app.mirroring import MirrorTelegramClient
from app.storage import Database, InMemoryDatabase, PostgresDatabase
from settings import (API_HASH, API_ID, CHANNEL_MAPPING, CHATS, DB_URL,
                      LOG_LEVEL, REMOVE_URLS)
from settings import REMOVE_URLS_WL_DATA as WHITELIST
from settings import SESSION_STRING, USE_MEMORY_DB


def main():
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(level=LOG_LEVEL)

    if USE_MEMORY_DB:
        database = InMemoryDatabase()
    else:
        database = PostgresDatabase(DB_URL, logger=logger)

    if REMOVE_URLS:
        message_filter = UrlFilter(whitelist=WHITELIST)
    else:
        message_filter = EmptyFilter()

    client = MirrorTelegramClient(SESSION_STRING, API_ID, API_HASH)
    client.configure_mirroring(
        source_chats=CHATS,
        mirror_mapping=CHANNEL_MAPPING,
        database=database,
        message_filter=message_filter,
        logger=logger
    )
    client.start_mirroring()


if __name__ == "__main__":
    main()

import logging

from settings import (API_HASH, API_ID, CHAT_MAPPING, DB_URL, LOG_LEVEL,
                      REMOVE_URLS)
from settings import REMOVE_URLS_LIST as URLS_BLACKLIST
from settings import REMOVE_URLS_WHITELIST as URLS_WHITELIST
from settings import SESSION_STRING, SOURCE_CHATS, USE_MEMORY_DB
from telemirror.messagefilters import EmptyFilter, UrlFilter
from telemirror.mirroring import MirrorTelegramClient
from telemirror.storage import Database, InMemoryDatabase, PostgresDatabase


def main():
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(level=LOG_LEVEL)

    if USE_MEMORY_DB:
        database = InMemoryDatabase()
    else:
        database = PostgresDatabase(DB_URL, logger=logger)

    if REMOVE_URLS:
        message_filter = UrlFilter(
            blacklist=URLS_BLACKLIST, whitelist=URLS_WHITELIST)
    else:
        message_filter = EmptyFilter()

    client = MirrorTelegramClient(SESSION_STRING, API_ID, API_HASH)
    client.configure_mirroring(
        source_chats=SOURCE_CHATS,
        mirror_mapping=CHAT_MAPPING,
        database=database,
        message_filter=message_filter,
        logger=logger
    )
    client.start_mirroring()


if __name__ == "__main__":
    main()

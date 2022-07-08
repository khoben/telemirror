import logging

from config import (API_HASH, API_ID, CHAT_MAPPING, DB_URL, DISABLE_DELETE,
                    DISABLE_EDIT, LOG_LEVEL, REMOVE_URLS)
from config import REMOVE_URLS_LIST as URLS_BLACKLIST
from config import REMOVE_URLS_WHITELIST as URLS_WHITELIST
from config import SESSION_STRING, SOURCE_CHATS, USE_MEMORY_DB
from telemirror.messagefilters import EmptyMessageFilter, UrlMessageFilter
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
        message_filter = UrlMessageFilter(
            blacklist=URLS_BLACKLIST, whitelist=URLS_WHITELIST)
    else:
        message_filter = EmptyMessageFilter()

    client = MirrorTelegramClient(SESSION_STRING, API_ID, API_HASH)
    client.configure_mirroring(
        source_chats=SOURCE_CHATS,
        mirror_mapping=CHAT_MAPPING,
        database=database,
        message_filter=message_filter,
        disable_edit=DISABLE_EDIT,
        disable_delete=DISABLE_DELETE,
        logger=logger
    )
    client.start_mirroring()


if __name__ == "__main__":
    main()

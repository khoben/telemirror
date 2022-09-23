import logging

from config import (API_HASH, API_ID, CHAT_MAPPING, DB_URL, DISABLE_DELETE,
                    DISABLE_EDIT, LOG_LEVEL, REMOVE_URLS)
from config import REMOVE_URLS_LIST as URLS_BLACKLIST
from config import REMOVE_URLS_WHITELIST as URLS_WHITELIST
from config import SESSION_STRING, SOURCE_CHATS, USE_MEMORY_DB
from telemirror.messagefilters import (EmptyMessageFilter, MessageFilter,
                                       UrlMessageFilter)
from telemirror.mirroring import MirrorTelegramClient
from telemirror.storage import Database, InMemoryDatabase, PostgresDatabase


async def init_telemirror(logger: logging.Logger, database: Database, message_filter: MessageFilter):
    await MirrorTelegramClient(
        SESSION_STRING,
        api_id=API_ID,
        api_hash=API_HASH,
        source_chats=SOURCE_CHATS,
        mirror_mapping=CHAT_MAPPING,
        database=await database.async_init(),
        message_filter=message_filter,
        disable_edit=DISABLE_EDIT,
        disable_delete=DISABLE_DELETE,
        logger=logger
    ).run()


def main():
    import asyncio
    import sys

    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(level=LOG_LEVEL)

    if REMOVE_URLS:
        url_message_filter = UrlMessageFilter(
            blacklist=URLS_BLACKLIST, whitelist=URLS_WHITELIST)
    else:
        url_message_filter = EmptyMessageFilter()

    if USE_MEMORY_DB:
        database = InMemoryDatabase()
    else:
        database = PostgresDatabase(connection_string=DB_URL)
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(init_telemirror(logger, database, url_message_filter))


if __name__ == "__main__":
    main()

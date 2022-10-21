import logging

from config import (API_HASH, API_ID, CHAT_MAPPING, DB_URL,
                    DISABLE_COMMENT_CLONE, LOG_LEVEL, SESSION_STRING,
                    TARGET_COMMENT_CHAT, TARGET_CONFIG, USE_MEMORY_DB)
from custom import LinkedChatFilter, UserCommentFormatFilter, SkipAll
from telemirror.messagefilters import CompositeMessageFilter
from telemirror.mirroring import MirrorTelegramClient
from telemirror.storage import Database, InMemoryDatabase, PostgresDatabase


async def init_telemirror(logger: logging.Logger, database: Database):
    await database.async_init()

    TARGET_CONFIG[TARGET_COMMENT_CHAT].filters = CompositeMessageFilter(
        LinkedChatFilter(database), UserCommentFormatFilter()) if not DISABLE_COMMENT_CLONE else SkipAll()

    await MirrorTelegramClient(
        SESSION_STRING,
        api_id=API_ID,
        api_hash=API_HASH,
        chat_mapping=CHAT_MAPPING,
        target_config=TARGET_CONFIG,
        database=database,
        logger=logger
    ).run()


def main():
    import asyncio
    import sys

    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(level=LOG_LEVEL)

    if USE_MEMORY_DB:
        database = InMemoryDatabase()
    else:
        database = PostgresDatabase(connection_string=DB_URL)
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(init_telemirror(logger, database))


if __name__ == "__main__":
    main()

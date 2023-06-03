import logging

from aiohttp import web

from config import (
    API_HASH,
    API_ID,
    CHAT_MAPPING,
    DB_URL,
    LOG_LEVEL,
    SESSION_STRING,
    USE_MEMORY_DB,
)
from telemirror.mirroring import MirrorTelegramClient
from telemirror.storage import Database, InMemoryDatabase, PostgresDatabase


async def serve_health_endpoint(host: str, port: int) -> None:
    async def health(request):
        return web.Response(text="OK")

    app = web.Application()
    app.add_routes([web.get("/", health)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()


async def init_telemirror(logger: logging.Logger, database: Database):
    await serve_health_endpoint(host="0.0.0.0", port=8000)

    await MirrorTelegramClient(
        SESSION_STRING,
        api_id=API_ID,
        api_hash=API_HASH,
        chat_mapping=CHAT_MAPPING,
        database=await database,
        logger=logger,
    ).run()


def configure_logging(logger_name: str, log_level: str) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    if not logger.handlers:
        import sys

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter(
                "%(levelname)-5s %(asctime)s [%(filename)s:%(lineno)d]:%(name)s: %(message)s"
            )
        )

        logger.addHandler(handler)

    return logger


def main():
    import asyncio
    import sys

    logger = configure_logging("telemirror", LOG_LEVEL)

    if USE_MEMORY_DB:
        database = InMemoryDatabase()
    else:
        database = PostgresDatabase(connection_string=DB_URL)
        if sys.platform == "win32":
            # required by psycopg async pool
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(init_telemirror(logger, database))


if __name__ == "__main__":
    main()

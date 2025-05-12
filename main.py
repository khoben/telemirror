import logging

from telemirror.mirroring import Telemirror
from telemirror.storage import InMemoryDatabase, PostgresDatabase


async def serve_health_endpoint(host: str, port: int) -> None:
    """
    Start http health endpoint at /.

    Some PaaS providers require a health endpoint to verify that the service has started successfully.
    """
    from aiohttp import web

    async def health(_):
        return web.Response(status=204)

    app = web.Application()
    app.add_routes([web.get("/", health)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()


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


async def run_telemirror(
    use_memory_db: bool,
    db_uri: str,
    api_id: str,
    api_hash: str,
    session_string: str,
    chat_mapping: dict,
    logger: logging.Logger,
    host: str,
    port: int,
):
    await serve_health_endpoint(host=host, port=port)

    if use_memory_db:
        database = InMemoryDatabase()
    else:
        database = await PostgresDatabase(connection_string=db_uri)

    telemirror = Telemirror(
        api_id=api_id,
        api_hash=api_hash,
        session_string=session_string,
        chat_mapping=chat_mapping,
        database=database,
        logger=logger,
    )
    await telemirror.run()


def main():
    import asyncio
    import sys

    from config import (
        API_HASH,
        API_ID,
        CHAT_MAPPING,
        DB_URL,
        HOST,
        LOG_LEVEL,
        PORT,
        SESSION_STRING,
        USE_MEMORY_DB,
    )

    if sys.platform == "win32":
        if USE_MEMORY_DB is False:
            # required by psycopg async pool on windows platform
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    else:
        import uvloop

        uvloop.install()

    asyncio.run(
        run_telemirror(
            use_memory_db=USE_MEMORY_DB,
            db_uri=DB_URL,
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=SESSION_STRING,
            chat_mapping=CHAT_MAPPING,
            logger=configure_logging("telemirror", LOG_LEVEL),
            host=HOST,
            port=PORT,
        )
    )


if __name__ == "__main__":
    main()

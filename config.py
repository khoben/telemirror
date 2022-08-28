"""
Parses properties from .env file
"""
from decouple import config, Csv

# telegram app id
API_ID: str = config("API_ID")
# telegram app hash
API_HASH: str = config("API_HASH")


def cast_mapping(v: str) -> dict:
    mapping = {}

    if not v:
        return mapping

    import re

    matches = re.findall(
        r'\[?((?:-?\d+,?)+):((?:-?\d+,?)+)\]?', v, re.MULTILINE)
    for match in matches:
        sources = [int(val) for val in match[0].split(',')]
        targets = [int(val) for val in match[1].split(',')]
        for source in sources:
            mapping.setdefault(source, []).extend(targets)
    return mapping


# channels mapping
# [source:target1,target2];[source2:...]
CHAT_MAPPING: dict = config("CHAT_MAPPING", cast=cast_mapping, default="")

if not CHAT_MAPPING:
    raise Exception("The chat mapping configuration is incorrect. "
                    "Please provide valid non-empty CHAT_MAPPING environment variable.")

# channels id to mirroring
SOURCE_CHATS: list = list(CHAT_MAPPING.keys())

# auth session string: can be obtain by run login.py
SESSION_STRING: str = config("SESSION_STRING")

# remove urls from messages
REMOVE_URLS: bool = config("REMOVE_URLS", cast=bool, default=False)
# remove urls whitelist
REMOVE_URLS_WHITELIST: set = config(
    "REMOVE_URLS_WL", cast=Csv(post_process=set), default="")
# remove urls only this URLs
REMOVE_URLS_LIST: set = config(
    "REMOVE_URLS_LIST", cast=Csv(post_process=set), default="")

DISABLE_EDIT: bool = config("DISABLE_EDIT", cast=bool, default=False)
DISABLE_DELETE: bool = config("DISABLE_DELETE", cast=bool, default=False)

USE_MEMORY_DB: bool = config("USE_MEMORY_DB", default=False, cast=bool)

# postgres credentials
# connection string
DB_URL: str = config("DATABASE_URL", default=None)
# or postgres credentials
DB_NAME: str = config("DB_NAME", default=None)
DB_USER: str = config("DB_USER", default=None)
DB_PASS: str = config("DB_PASS", default=None)
DB_HOST: str = config("DB_HOST", default=None)

if not USE_MEMORY_DB and DB_URL is None and DB_HOST is None:
    raise Exception("The database configuration is incorrect. "
                    "Please provide valid DB_URL (or DB_HOST, DB_NAME, DB_USER, DB_PASS) "
                    "or set USE_MEMORY_DB to True to use in-memory database.")

DB_PROTOCOL: str = "postgres"

# if connection string wasnt set then build it from credentials
if DB_URL is None:
    DB_URL = f"{DB_PROTOCOL}://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

LOG_LEVEL: str = config("LOG_LEVEL", default="INFO").upper()

"""
Loads environment(.env) config
"""
from dataclasses import dataclass

from decouple import Csv, config

from telemirror.messagefilters import (CompositeMessageFilter,
                                       EmptyMessageFilter,
                                       KeywordReplaceFilter, MessageFilter)

# telegram app id
API_ID: str = config("API_ID")
# telegram app hash
API_HASH: str = config("API_HASH")
# auth session string: can be obtain by run login.py
SESSION_STRING: str = config("SESSION_STRING")

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

###############Channel mirroring config#################


@dataclass
class TargetConfig:
    disable_delete: bool
    disable_edit: bool
    filters: MessageFilter

# target channels config
TARGET_CONFIG: dict[int, TargetConfig] = {}

# source and target chats mapping
CHAT_MAPPING: dict[int, list[int]] = {}

SOURCE_CHATS: list[int] = config("SOURCE_CHATS", cast=Csv(cast=int, post_process=list))
TARGET_CHANNEL: int = config("TARGET_CHANNEL", cast=int)

for source in SOURCE_CHATS:
    CHAT_MAPPING[source] = [TARGET_CHANNEL]

DISABLE_EDIT: bool = config("DISABLE_EDIT", cast=bool, default=False)
DISABLE_DELETE: bool = config("DISABLE_DELETE", cast=bool, default=False)

def cast_env_keyword_replace(v: str) -> dict[str, str]:
    mapping = {}

    if not v:
        return mapping

    import re

    matches = re.findall(r'(\w+):(\w+)', v, re.MULTILINE)
    for match in matches:
        mapping[match[0]] = match[1]
    return mapping

ENABLE_KEYWORD_REPLACE: bool = config(
    "KEYWORD_REPLACE_ENABLE", cast=bool, default=True)
KEYWORD_REPLACE_MAP: dict[str, str] = config(
    "KEYWORD_REPLACE_MAP", cast=cast_env_keyword_replace, default="")

from custom import AllowChannelPostFilter, BottomLinkFilter

filters = [AllowChannelPostFilter()]

if ENABLE_KEYWORD_REPLACE:
    filters.append(KeywordReplaceFilter(KEYWORD_REPLACE_MAP))

ENABLE_BOTTOM_LINK: bool = config(
    "BOTTOM_LINK_ENABLE", cast=bool, default=True)
BOTTOM_LINK_DISPLAY_NAME: str = config(
    "BOTTOM_LINK_DISPLAY_NAME", default='Link')

if ENABLE_BOTTOM_LINK:
    filters.append(BottomLinkFilter('{message_text}\n\n[{link_display_name}]({message_link})'.format(
        link_display_name=BOTTOM_LINK_DISPLAY_NAME,
        message_text='{message_text}',
        message_link='{message_link}'
    )))

channel_filter = CompositeMessageFilter(
    *filters) if (len(filters) > 1) else filters[0]

from custom import KEY_COMMENT, KEY_POST

TARGET_CONFIG[KEY_POST] = TargetConfig(
    disable_delete=DISABLE_DELETE,
    disable_edit=DISABLE_EDIT,
    filters=channel_filter
)
TARGET_CONFIG[KEY_COMMENT] = TargetConfig(
    disable_delete=DISABLE_DELETE,
    disable_edit=DISABLE_EDIT,
    filters=EmptyMessageFilter()
)

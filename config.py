"""
Loads environment(.env) config
"""
from dataclasses import dataclass

from decouple import Csv, config

from custom import (LinkedChatFilter, MappedNameForwardFormat, Source, Target,
                    UserCommentFormatFilter)
from telemirror.messagefilters import (CompositeMessageFilter,
                                       KeywordReplaceFilter, MessageFilter,
                                       SkipAllFilter, SkipWithKeywordsFilter)
from telemirror.storage import Database

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


def cast_env_chat_mapping(v: str) -> dict[int, list[int]]:
    mapping = {}

    if not v:
        return mapping

    import re

    matches = re.findall(
        r'\[?((?:\(-?\d+\|\"[^\"]+\"\|?(?:-?\d+)?\),?)+):((?:\(-?\d+\|?(?:-?\d+)\),?)+)\]?', v, re.MULTILINE)
    for match in matches:
        sources = [Source(val) for val in match[0].split(',')]
        targets = [Target(val) for val in match[1].split(',')]
        for source in sources:
            mapping.setdefault(source, []).extend(targets)
    return mapping


_CHAT_MAPPING: dict[Source, list[Target]] = config(
    "CHAT_MAPPING", cast=cast_env_chat_mapping)

if not _CHAT_MAPPING:
    raise Exception("The chat mapping configuration is incorrect. "
                    "Please provide valid non-empty CHAT_MAPPING environment variable.")

DISABLE_EDIT: bool = config("DISABLE_EDIT", cast=bool, default=False)
DISABLE_DELETE: bool = config("DISABLE_DELETE", cast=bool, default=False)
DISABLE_COMMENT_CLONE: bool = config(
    "DISABLE_COMMENT_CLONE", cast=bool, default=False)


def cast_env_keyword_replace(v: str) -> dict[str, str]:
    mapping = {}

    if not v:
        return mapping

    import re

    matches = re.findall(r'"?([^"]*)"?:"?([^"]*)"?', v, re.MULTILINE)
    for match in matches:
        mapping[match[0]] = match[1]
    return mapping


filters = []

KEYWORD_DO_NOT_FORWARD_MAP: set[str] = config(
    "KEYWORD_DO_NOT_FORWARD_MAP", cast=Csv(cast=str, post_process=set), default="")

if KEYWORD_DO_NOT_FORWARD_MAP:
    filters.append(SkipWithKeywordsFilter(KEYWORD_DO_NOT_FORWARD_MAP))

KEYWORD_REPLACE_MAP: dict[str, str] = config(
    "KEYWORD_REPLACE_MAP", cast=cast_env_keyword_replace, default="")

if KEYWORD_REPLACE_MAP:
    filters.append(KeywordReplaceFilter(KEYWORD_REPLACE_MAP))

filters.append(MappedNameForwardFormat(mapped={k.channel: k.title for k in _CHAT_MAPPING.keys(
)}, format="{message_text}\n=======\n消息来源: [{channel_name}]({message_link})"))

channel_filter = CompositeMessageFilter(
    *filters) if (len(filters) > 1) else filters[0]

linked_chat_filter = LinkedChatFilter()
user_comment_filer = UserCommentFormatFilter()


def init_filters_with_db(db: Database) -> None:
    linked_chat_filter.install_db(db)
    user_comment_filer.install_db(db)


channel_config = TargetConfig(
    disable_delete=DISABLE_DELETE,
    disable_edit=DISABLE_EDIT,
    filters=channel_filter
)
comments_config = TargetConfig(
    disable_delete=DISABLE_DELETE,
    disable_edit=DISABLE_EDIT,
    filters=CompositeMessageFilter(
        linked_chat_filter, user_comment_filer) if not DISABLE_COMMENT_CLONE else SkipAllFilter()
)

for source, targets in _CHAT_MAPPING.items():
    CHAT_MAPPING.setdefault(source.channel, []).extend(
        [t.channel for t in targets])
    if source.comments:
        CHAT_MAPPING.setdefault(source.comments, []).extend(
            [t.comments for t in targets if t.comments])

    for target in targets:
        TARGET_CONFIG[target.channel] = channel_config
        if target.comments:
            TARGET_CONFIG[target.comments] = comments_config

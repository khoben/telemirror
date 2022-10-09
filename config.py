"""
Loads environment(.env)/config.yaml config
"""
import os
from dataclasses import dataclass

from decouple import Csv, config

from telemirror.messagefilters import (CompositeMessageFilter,
                                       EmptyMessageFilter, MessageFilter,
                                       UrlMessageFilter)

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


YAML_CONFIG = './mirror.config.yml'

# target channels config
TARGET_CONFIG: dict[int, TargetConfig] = {}

# source and target chats mapping
CHAT_MAPPING: dict[int, list[int]] = {}

# Load mirror config from config.yml
# otherwise from .env or environment
if os.path.exists(YAML_CONFIG):

    from importlib import import_module
    from types import ModuleType
    from typing import Optional

    import yaml

    filters_module: ModuleType = import_module('telemirror.messagefilters')

    yaml_config: dict = None

    with open(YAML_CONFIG, encoding="utf8") as file:
        yaml_config = yaml.load(file, Loader=yaml.FullLoader)

    def build_filters(config_filters: Optional[dict], default: MessageFilter) -> MessageFilter:

        if not config_filters:
            return default

        filters = []
        for filter in config_filters:
            filter_name, filter_args = list(filter.items())[0] if isinstance(
                filter, dict) else (filter, {})
            filter_class = getattr(filters_module, filter_name)
            filters.append(filter_class(**filter_args))

        return CompositeMessageFilter(*filters) if (len(filters) > 1) else filters[0]

    global_config = TargetConfig(
        disable_delete=yaml_config.get('disable_delete', False),
        disable_edit=yaml_config.get('disable_edit', False),
        filters=build_filters(yaml_config.get(
            'filters', None), EmptyMessageFilter())
    )

    for direction in yaml_config['directions']:
        sources: list[int] = direction['from']
        targets: list[int] = direction['to']

        for target in targets:
            TARGET_CONFIG[target] = global_config

        for source in sources:
            CHAT_MAPPING.setdefault(source, []).extend(targets)

    for target in yaml_config['targets']:
        TARGET_CONFIG[target.get('id')] = TargetConfig(
            disable_delete=target.get(
                'disable_delete', global_config.disable_delete),
            disable_edit=target.get(
                'disable_edit', global_config.disable_edit),
            filters=build_filters(target.get(
                'filters', None), global_config.filters)
        )

else:

    def cast_env_chat_mapping(v: str) -> dict[int, list[int]]:
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

    CHAT_MAPPING: dict[int, list[int]] = config(
        "CHAT_MAPPING", cast=cast_env_chat_mapping, default="")

    if not CHAT_MAPPING:
        raise Exception("The chat mapping configuration is incorrect. "
                        "Please provide valid non-empty CHAT_MAPPING environment variable.")

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

    if REMOVE_URLS:
        message_filter = UrlMessageFilter(
            blacklist=REMOVE_URLS_LIST, whitelist=REMOVE_URLS_WHITELIST)
    else:
        message_filter = EmptyMessageFilter()

    global_config = TargetConfig(
        disable_delete=DISABLE_DELETE,
        disable_edit=DISABLE_EDIT,
        filters=message_filter
    )

    for _, targets in CHAT_MAPPING.items():
        for target in targets:
            TARGET_CONFIG[target] = global_config

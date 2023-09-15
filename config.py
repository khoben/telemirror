"""
Loads environment(.env)/config.yaml config
"""
import os
from dataclasses import dataclass
from typing import List, Dict

from decouple import Csv, config

from telemirror.messagefilters import (
    CompositeMessageFilter,
    EmptyMessageFilter,
    MessageFilter,
    UrlMessageFilter,
)

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
    raise Exception(
        "The database configuration is incorrect. "
        "Please provide valid DB_URL (or DB_HOST, DB_NAME, DB_USER, DB_PASS) "
        "or set USE_MEMORY_DB to True to use in-memory database."
    )

DB_PROTOCOL: str = "postgres"

# if connection string wasnt set then build it from credentials
if DB_URL is None:
    DB_URL = f"{DB_PROTOCOL}://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

LOG_LEVEL: str = config("LOG_LEVEL", default="INFO").upper()

###############Channel mirroring config#################


@dataclass
class DirectionConfig:
    disable_delete: bool
    disable_edit: bool
    filters: MessageFilter


# source and target chats mapping
CHAT_MAPPING: Dict[int, Dict[int, DirectionConfig]] = {}

YAML_CONFIG_FILE = "./.configs/mirror.config.yml"

# Load mirror config from config.yml
# otherwise from .env or environment
if os.path.exists(YAML_CONFIG_FILE):
    from importlib import import_module
    from types import ModuleType
    from typing import Optional

    import yaml

    filters_module: ModuleType = import_module("telemirror.messagefilters")

    yaml_config: dict = None

    with open(YAML_CONFIG_FILE, encoding="utf8") as file:
        yaml_config = yaml.load(file, Loader=yaml.FullLoader)

    if "targets" in yaml_config:
        raise ValueError(
            "`targets` section deprecated. Please move `disable_delete`, `disable_edit`"
            " and `filters` to `directions` section."
        )

    def build_filters(
        filter_config: Optional[dict], default: MessageFilter
    ) -> MessageFilter:
        if not filter_config:
            return default

        filters: List[MessageFilter] = []
        for filter in filter_config:
            filter_name, filter_args = (
                list(filter.items())[0] if isinstance(filter, dict) else (filter, {})
            )
            filter_class = getattr(filters_module, filter_name)
            filters.append(filter_class(**filter_args))

        return CompositeMessageFilter(*filters) if (len(filters) > 1) else filters[0]

    default_config = DirectionConfig(
        disable_delete=yaml_config.get("disable_delete", False),
        disable_edit=yaml_config.get("disable_edit", False),
        filters=build_filters(yaml_config.get("filters", None), EmptyMessageFilter()),
    )

    for direction in yaml_config["directions"]:
        sources: list[int] = direction["from"]
        targets: list[int] = direction["to"]

        direction_config = DirectionConfig(
            disable_delete=direction.get(
                "disable_delete", default_config.disable_delete
            ),
            disable_edit=direction.get("disable_edit", default_config.disable_edit),
            filters=build_filters(
                direction.get("filters", None), default_config.filters
            ),
        )

        targets_config = {target: direction_config for target in targets}

        for source in sources:
            CHAT_MAPPING.setdefault(source, {}).update(targets_config)

else:
    # Mirror config thru environment vars
    from functools import partial

    def build_mapping_from_env(
        direction_config: DirectionConfig, env_str: str
    ) -> Dict[int, Dict[int, DirectionConfig]]:
        mapping: Dict[int, Dict[int, DirectionConfig]] = {}

        if not env_str:
            return mapping

        import re

        matches = re.findall(
            r"\[?((?:-?\d+,?)+):((?:-?\d+,?)+)\]?", env_str, re.MULTILINE
        )

        for match in matches:
            sources = [int(val) for val in match[0].split(",")]
            targets_config = {int(val): direction_config for val in match[1].split(",")}
            for source in sources:
                mapping.setdefault(source, {}).update(targets_config)

        return mapping

    # remove urls from messages
    REMOVE_URLS: bool = config("REMOVE_URLS", cast=bool, default=False)
    # remove urls whitelist
    REMOVE_URLS_WHITELIST: set = config(
        "REMOVE_URLS_WL", cast=Csv(post_process=set), default=""
    )
    # remove urls only this URLs
    REMOVE_URLS_LIST: set = config(
        "REMOVE_URLS_LIST", cast=Csv(post_process=set), default=""
    )

    DISABLE_EDIT: bool = config("DISABLE_EDIT", cast=bool, default=False)
    DISABLE_DELETE: bool = config("DISABLE_DELETE", cast=bool, default=False)

    if REMOVE_URLS:
        message_filter = UrlMessageFilter(
            blacklist=REMOVE_URLS_LIST, whitelist=REMOVE_URLS_WHITELIST
        )
    else:
        message_filter = EmptyMessageFilter()

    default_config = DirectionConfig(
        disable_delete=DISABLE_DELETE, disable_edit=DISABLE_EDIT, filters=message_filter
    )

    cast_env_chat_mapping = partial(build_mapping_from_env, default_config)

    CHAT_MAPPING = config("CHAT_MAPPING", cast=cast_env_chat_mapping, default="")

    if not CHAT_MAPPING:
        raise Exception(
            "The chat mapping configuration is incorrect. "
            "Please provide valid non-empty CHAT_MAPPING environment variable."
        )

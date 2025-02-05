"""
Loads environment(.env)/config.yaml config
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

from decouple import AutoConfig, Csv, RepositoryEnv

from telemirror.messagefilters import (
    CompositeMessageFilter,
    EmptyMessageFilter,
    MessageFilter,
    UrlMessageFilter,
)


class RepositoryMultilineEnv(RepositoryEnv):
    """
    Retrieves option keys from .env files with fall back to os.environ.
    Multiline values are supported with '' or "" quoted strings.
    """

    def __init__(self, source, encoding=...):
        self.data = {}
        multiline_key = None
        multiline_quote_sign = None
        with open(source, encoding=encoding) as file_:
            for line in file_:
                if multiline_key:
                    k = multiline_key
                    v = line.rstrip()
                    if v and v[-1] == multiline_quote_sign:
                        v = v[:-1]
                        multiline_key = None
                        multiline_quote_sign = None

                    self.data[k] += f"\n{v}"
                    continue

                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if len(v) >= 2 and (
                    (v[0] == "'" and v[-1] == "'") or (v[0] == '"' and v[-1] == '"')
                ):
                    v = v[1:-1]
                elif v and (
                    (v[0] == "'" and (len(v) < 2 or v[-1] != "'"))
                    or (v[0] == '"' and (len(v) < 2 or v[-1] != '"'))
                ):
                    multiline_key = k
                    multiline_quote_sign = v[0]
                    v = v[1:]

                self.data[k] = v

        if multiline_key:
            raise ValueError(
                f"Unterminated multiline env string value for key = {multiline_key}, "
                f"expected {multiline_quote_sign} at end"
            )


class Config(AutoConfig):
    def __init__(self, search_path=None):
        super().__init__(search_path)
        self.SUPPORTED[".env"] = RepositoryMultilineEnv


config = Config()

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
        "Please provide valid DATABASE_URL (or DB_HOST, DB_NAME, DB_USER, DB_PASS) "
        "or set USE_MEMORY_DB to True to use in-memory database."
    )

DB_PROTOCOL: str = "postgres"

# if connection string wasnt set then build it from credentials
if DB_URL is None:
    DB_URL = f"{DB_PROTOCOL}://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

LOG_LEVEL: str = config("LOG_LEVEL", default="INFO").upper()

# Application local host, defaults to 0.0.0.0
HOST: str = config("HOST", default="0.0.0.0")
# Application local port, defaults to 8000
PORT: int = config("PORT", default=8000, cast=int)

###############Channel mirroring config#################


@dataclass(frozen=True)
class DirectionConfig:
    disable_delete: bool
    disable_edit: bool
    filters: MessageFilter
    from_topic_id: Optional[int] = None
    to_topic_id: Optional[int] = None
    mode: Literal["copy", "forward"] = "copy"

    def __repr__(self) -> str:
        return (
            f"mode: {self.mode}, "
            f"deleting: {not self.disable_delete}, "
            f"editing: {not self.disable_edit}, "
            f"{f'from_topic_id: {self.from_topic_id}, ' if self.from_topic_id else ''}"
            f"{f'to_topic_id: {self.to_topic_id}, ' if self.to_topic_id else ''}"
            f"filters: {self.filters}"
        )


# source and target chats mapping
CHAT_MAPPING: Dict[int, Dict[int, List[DirectionConfig]]] = {}

YAML_CONFIG_FILE = "./.configs/mirror.config.yml"
YAML_CONFIG_ENV: Optional[str] = config("YAML_CONFIG_ENV", default=None)

# Check for deprecated config location
if os.path.exists("./mirror.config.yml"):
    raise Exception("Please move `mirror.config.yml` to `.configs` directory")

# Load mirror config from config.yml
# otherwise from .env or environment
if os.path.exists(YAML_CONFIG_FILE) or YAML_CONFIG_ENV:
    from importlib import import_module
    from types import ModuleType

    import yaml

    filters_module: ModuleType = import_module("telemirror.messagefilters")

    yaml_config: dict = None

    if YAML_CONFIG_ENV:
        yaml_config = yaml.load(
            YAML_CONFIG_ENV.replace("\\n", "\n"), Loader=yaml.FullLoader
        )
    else:
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

        return CompositeMessageFilter(filters) if (len(filters) > 1) else filters[0]

    default_filters = build_filters(
        yaml_config.get("filters", None), EmptyMessageFilter()
    )

    for direction in yaml_config["directions"]:
        sources: list = direction["from"]
        targets: list = direction["to"]

        for source in sources:
            source_topic_id = None
            if isinstance(source, str):
                if "#" in source:
                    source, source_topic_id = map(int, source.split("#"))
                else:
                    source = int(source)

            for target in targets:
                target_topic_id = None
                if isinstance(target, str):
                    if "#" in target:
                        target, target_topic_id = map(int, target.split("#"))
                    else:
                        target = int(target)

                CHAT_MAPPING.setdefault(source, {}).setdefault(target, []).append(
                    DirectionConfig(
                        disable_delete=direction.get(
                            "disable_delete", yaml_config.get("disable_delete", False)
                        ),
                        disable_edit=direction.get(
                            "disable_edit", yaml_config.get("disable_edit", False)
                        ),
                        filters=build_filters(
                            direction.get("filters", None), default_filters
                        ),
                        mode=direction.get("mode", yaml_config.get("mode", "copy")),
                        from_topic_id=source_topic_id,
                        to_topic_id=target_topic_id,
                    )
                )

else:
    # Mirror config thru environment vars
    from functools import partial

    def build_mapping_from_env(
        disable_edit: bool, disable_delete: bool, filters: MessageFilter, env_str: str
    ) -> Dict[int, Dict[int, List[DirectionConfig]]]:
        mapping: Dict[int, Dict[int, List[DirectionConfig]]] = {}

        if not env_str:
            return mapping

        import re

        matches = re.findall(
            r"\[?((?:-?\d+(?:#\d+)?,?)+):((?:-?\d+(?:#\d+)?,?)+)\]?",
            env_str,
            re.MULTILINE,
        )

        for sources, targets in matches:
            for source in sources.split(","):
                source_topic_id = None
                if "#" in source:
                    source, source_topic_id = map(int, source.split("#"))
                else:
                    source = int(source)

                for target in targets.split(","):
                    target_topic_id = None
                    if "#" in target:
                        target, target_topic_id = map(int, target.split("#"))
                    else:
                        target = int(target)

                    mapping.setdefault(source, {}).setdefault(target, []).append(
                        DirectionConfig(
                            disable_delete=disable_delete,
                            disable_edit=disable_edit,
                            filters=filters,
                            from_topic_id=source_topic_id,
                            to_topic_id=target_topic_id,
                        )
                    )

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

    cast_env_chat_mapping = partial(
        build_mapping_from_env,
        DISABLE_EDIT,
        DISABLE_DELETE,
        message_filter,
    )

    CHAT_MAPPING = config("CHAT_MAPPING", cast=cast_env_chat_mapping, default="")

    if not CHAT_MAPPING:
        raise Exception(
            "The chat mapping configuration is incorrect. "
            "Please provide valid non-empty CHAT_MAPPING environment variable."
        )

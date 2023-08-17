import re
from typing import List, Optional, Set, Tuple, Type, Union

from telethon import events, types, utils
from telethon.extensions import markdown as md_parser

from ..hints import EventAlbumMessage, EventEntity, EventLike, EventMessage
from ..misc.urlmatcher import UrlMatcher
from .base import MessageFilter
from .mixins import (
    ChannelName,
    CopyMessage,
    MappedChannelName,
    MessageLink,
    WhitespacedWordBound,
)


class EmptyMessageFilter(MessageFilter):
    """Do nothing with message"""

    async def process(
        self, message: EventEntity, event_type: Type[EventLike]
    ) -> Tuple[bool, EventEntity]:
        return True, message

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventMessage]:
        return True, message


class SkipUrlFilter(MessageFilter):
    """Skip messages with URLs

    Args:
        skip_mention (`bool`, optional):
            Enable skipping text mentions (@channel). Defaults to True.
    """

    def __init__(self: "SkipUrlFilter", skip_mention: bool = True) -> None:
        self._skip_mention = skip_mention

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventMessage]:
        if message.entities:
            for e in message.entities:
                if isinstance(
                    e, (types.MessageEntityUrl, types.MessageEntityTextUrl)
                ) or (
                    isinstance(
                        e, (types.MessageEntityMention, types.MessageEntityMentionName)
                    )
                    and self._skip_mention
                ):
                    return False, message

        if isinstance(message.media, types.MessageMediaWebPage):
            return False, message

        return True, message


class UrlMessageFilter(CopyMessage, MessageFilter):
    """URLs message filter

    Args:
        placeholder (`str`, optional):
            URLs and mentions placeholder. Defaults to '***'.

        blacklist (`Set[str]`, optional):
            URLs blacklist -- remove only these URLs.
            Defaults to empty set (removes all URLs).

        whitelist (`Set[str]`, optional):
            URLs whitelist -- remove all URLs except these.
            Will be applied after the `blacklist`. Defaults to empty set.

        filter_mention (`Union[bool, Set[str]]`, optional):
            Filter text mentions (e.g. @channel, @nickname).
            Defaults to False.

        filter_by_id_mention (`bool`, optional):
            Filter all mentions without nicknames (by user id).
            Defaults to False.
    """

    def __init__(
        self: "UrlMessageFilter",
        placeholder: str = "***",
        blacklist: Set[str] = set(),
        whitelist: Set[str] = set(),
        filter_mention: Union[bool, Set[str]] = False,
        filter_by_id_mention: bool = False,
    ) -> None:
        self._placeholder = placeholder
        self._placeholder_len = len(placeholder)

        self._url_matcher = UrlMatcher(blacklist, whitelist)

        self._filter_mention = None
        self._mention_blacklist = None
        if isinstance(filter_mention, bool):
            self._filter_mention = filter_mention
        else:
            self._mention_blacklist = filter_mention

        self._filter_by_id_mention = filter_by_id_mention

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventMessage]:
        filtered_message = self.copy_message(message)
        # Filter message entities
        if filtered_message.entities:
            good_entities: List[types.TypeMessageEntity] = []
            offset_error = 0
            for entity, entity_text in filtered_message.get_entities_text():
                entity.offset += offset_error
                # Filter URLs and mentions
                if (
                    isinstance(
                        entity, (types.MessageEntityUrl, types.MessageEntityTextUrl)
                    )
                    and self._url_matcher.match(entity_text)
                ) or (
                    isinstance(entity, types.MessageEntityMention)
                    and self._match_mention(entity_text)
                ):
                    filtered_message.message = filtered_message.message.replace(
                        entity_text, self._placeholder, 1
                    )
                    offset_error += self._placeholder_len - entity.length
                    continue

                # Keep only 'good' entities
                if not (
                    (
                        isinstance(entity, types.MessageEntityTextUrl)
                        and self._url_matcher.match(entity.url)
                    )
                    or (
                        isinstance(entity, types.MessageEntityMentionName)
                        and self._filter_by_id_mention
                    )
                ):
                    good_entities.append(entity)

            filtered_message.entities = good_entities

        # Filter link preview
        if (
            isinstance(filtered_message.media, types.MessageMediaWebPage)
            and isinstance(filtered_message.media.webpage, types.WebPage)
            and self._url_matcher.match(filtered_message.media.webpage.url)
        ):
            filtered_message.media = None

        return True, filtered_message

    def _match_mention(self, mention: str) -> bool:
        if self._filter_mention is not None:
            return self._filter_mention

        if self._mention_blacklist and mention not in self._mention_blacklist:
            return False

        return True


class ForwardFormatFilter(ChannelName, MessageLink, CopyMessage, MessageFilter):
    """Filter that adds a forwarding formatting (markdown supported):

    Example:
    ```
    {message_text}

    Forwarded from [{channel_name}]({message_link})
    ```

    Args:
        format (str): Forward header format,
        where `{channel_name}`, `{message_link}` and `{message_text}`
        are placeholders to actual incoming message values.
    """

    MESSAGE_PLACEHOLDER: str = "{message_text}"
    DEFAULT_FORMAT: str = (
        "{message_text}\n\nForwarded from [{channel_name}]({message_link})"
    )

    def __init__(self, format: str = DEFAULT_FORMAT) -> None:
        self._format = format

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventMessage]:
        # Skip format editing for albums
        if message.grouped_id and event_type is events.MessageEdited.Event:
            return True, message

        message_link: Optional[str] = self.message_link(message)
        channel_name: str = self.channel_name(message)

        filtered_message = self.copy_message(message)

        if channel_name and message_link:
            pre_formatted_message = self._format.format(
                channel_name=channel_name,
                message_link=message_link,
                message_text=self.MESSAGE_PLACEHOLDER,
            )
            pre_formatted_text, pre_formatted_entities = md_parser.parse(
                pre_formatted_message
            )

            message_offset = pre_formatted_text.find(self.MESSAGE_PLACEHOLDER)

            if filtered_message.entities:
                for e in filtered_message.entities:
                    e.offset += message_offset

            if pre_formatted_entities:
                message_placeholder_length_diff = len(
                    utils.add_surrogate(message.message)
                ) - len(self.MESSAGE_PLACEHOLDER)
                for e in pre_formatted_entities:
                    if e.offset > message_offset:
                        e.offset += message_placeholder_length_diff

                if filtered_message.entities:
                    filtered_message.entities.extend(pre_formatted_entities)
                else:
                    filtered_message.entities = pre_formatted_entities

            filtered_message.message = pre_formatted_text.format(
                message_text=filtered_message.message
            )

        return True, filtered_message

    async def _process_album(
        self, album: EventAlbumMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventAlbumMessage]:
        # process first message with non-empty text or first message
        message_album: EventMessage = None
        message_idx: int = 0
        for idx, message in enumerate(album):
            if message.message:
                message_album = message
                message_idx = idx
                break

        if not message_album:
            message_album = album[0]

        proceed, album[message_idx] = await self._process_message(
            message_album, event_type
        )

        return proceed, album


class MappedNameForwardFormat(MappedChannelName, ForwardFormatFilter):
    """Filter that adds a forwarding formatting (markdown supported)
    with mapped channel name:

    Example:
    ```
    {message_text}

    Forwarded from [{channel_name}]({message_link})
    ```

    Args:
        mapped (dict[int, str]): Mapped channel names: CHANNEL_ID -> CHANNEL_NAME

        format (str): Forward header format,
        where `{channel_name}`, `{message_link}` and `{message_text}`
        are placeholders to actual incoming message values.
    """

    def __init__(self, mapped: dict[int, str], format: str) -> None:
        MappedChannelName.__init__(self, mapped)
        ForwardFormatFilter.__init__(self, format)


class KeywordReplaceFilter(WhitespacedWordBound, CopyMessage, MessageFilter):
    """Filter that maps keywords
    Args:
        keywords (dict[str, str]): Keywords map
    """

    def __init__(self, keywords: dict[str, str]) -> None:
        self._keywords_mapping = [
            (
                re.compile(
                    f"{self.BOUNDARY_REGEX}{k}{self.BOUNDARY_REGEX}",
                    flags=re.IGNORECASE,
                ),
                v,
            )
            for k, v in keywords.items()
        ]

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventMessage]:
        filtered_message = self.copy_message(message)
        unparsed_text = filtered_message.message

        if filtered_message.entities:
            entities = filtered_message.entities
        else:
            entities = []

        if unparsed_text:
            replace_to = ""

            def sub_middleware(match: re.Match) -> str:
                start_match = match.start()
                len_match = match.end() - start_match
                len_replace_to = len(replace_to)
                diff = len_replace_to - len_match

                # after: change offset
                for e in entities:
                    if e.offset == start_match and e.length == len_match:
                        e.length = len_replace_to
                    elif e.offset > start_match:
                        e.offset += diff

                return replace_to

            for pattern, replace_to in self._keywords_mapping:
                unparsed_text = pattern.sub(sub_middleware, unparsed_text)

            filtered_message.message = unparsed_text

        return True, filtered_message


class SkipWithKeywordsFilter(WhitespacedWordBound, MessageFilter):
    """Skips message if some keyword found"""

    def __init__(self, keywords: set[str]) -> None:
        self._regex = re.compile(
            "|".join(
                [f"{self.BOUNDARY_REGEX}{k}{self.BOUNDARY_REGEX}" for k in keywords]
            ),
            flags=re.IGNORECASE,
        )

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventMessage]:
        if self._regex.search(message.message):
            return False, message
        return True, message


class SkipAllFilter(MessageFilter):
    """Skips all messages"""

    async def process(
        self, message: EventEntity, event_type: Type[EventLike]
    ) -> Tuple[bool, EventEntity]:
        return False, message

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventMessage]:
        return False, message

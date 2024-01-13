import re
from typing import Set, Tuple, Type, Union

from telethon import events, types, utils

from ..hints import EventAlbumMessage, EventEntity, EventLike, EventMessage
from ..misc.urlmatcher import UrlMatcher
from ..mixins import (
    ChannelName,
    MappedChannelName,
    MessageLink,
    UpdateEntitiesParams,
    WordBoundaryRegex,
)
from .base import MessageFilter


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
        if isinstance(message.media, types.MessageMediaWebPage):
            return False, message

        for entity in message.entities or []:
            if isinstance(
                entity, (types.MessageEntityUrl, types.MessageEntityTextUrl)
            ) or (
                isinstance(
                    entity, (types.MessageEntityMention, types.MessageEntityMentionName)
                )
                and self._skip_mention
            ):
                return False, message

        return True, message


class UrlMessageFilter(UpdateEntitiesParams, MessageFilter):
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
        filtered_text = utils.add_surrogate(message.message)
        filtered_entities = list[types.TypeMessageEntity]()

        for entity in message.entities or []:
            drop_entity = False
            update_pos = False

            if (
                isinstance(entity, types.MessageEntityUrl)
                and self._url_matcher.match(
                    filtered_text[entity.offset : entity.offset + entity.length]
                )
            ) or (
                isinstance(entity, types.MessageEntityMention)
                and self._match_mention(
                    filtered_text[entity.offset : entity.offset + entity.length]
                )
            ):
                filtered_text = (
                    filtered_text[: entity.offset]
                    + self._placeholder
                    + filtered_text[entity.offset + entity.length :]
                )
                entity_len_diff = len(self._placeholder) - entity.length
                update_pos = True
                drop_entity = True
            elif (
                self._filter_by_id_mention
                and isinstance(entity, types.MessageEntityMentionName)
            ) or (
                isinstance(entity, types.MessageEntityTextUrl)
                and self._url_matcher.match(entity.url)
            ):
                drop_entity = True

            if update_pos is True:
                self.update_entities_params(
                    message.entities,
                    entity.offset,
                    entity.offset + entity.length,
                    entity_len_diff,
                )

            if drop_entity is False:
                filtered_entities.append(entity)

        # Double check for URLs in text
        offset_error = 0
        for start, end in self._url_matcher.search(filtered_text):
            actual_start = start + offset_error
            actual_end = end + offset_error

            filtered_text = (
                filtered_text[:actual_start]
                + self._placeholder
                + filtered_text[actual_end:]
            )

            diff = len(self._placeholder) - (end - start)
            offset_error += diff

            self.update_entities_params(
                filtered_entities, actual_start, actual_end, diff
            )

        # Filter link preview
        if (
            isinstance(message.media, types.MessageMediaWebPage)
            and isinstance(message.media.webpage, types.WebPage)
            and self._url_matcher.match(message.media.webpage.url)
        ):
            message.media = None

        message.entities = filtered_entities
        message.message = utils.del_surrogate(filtered_text)

        return True, message

    def _match_mention(self, mention: str) -> bool:
        if self._filter_mention is not None:
            return self._filter_mention

        if self._mention_blacklist and mention not in self._mention_blacklist:
            return False

        return True


class ForwardFormatFilter(ChannelName, MessageLink, MessageFilter):
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

        from telethon.extensions import markdown as md_parser

        self._parser = md_parser

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventMessage]:
        # Skip format editing for empty album's items
        if (
            event_type is events.MessageEdited.Event
            and message.grouped_id
            and not message.message
        ):
            return True, message

        message_link = self.message_link(message)
        channel_name = self.channel_name(message)

        if not message_link or not channel_name:
            return True, message

        pre_formatted_message = self._format.format(
            channel_name=channel_name,
            message_link=message_link,
            message_text=self.MESSAGE_PLACEHOLDER,
        )
        pre_formatted_text, pre_formatted_entities = self._parser.parse(
            pre_formatted_message
        )

        message_offset = pre_formatted_text.find(self.MESSAGE_PLACEHOLDER)

        if message.entities and message_offset > 0:
            # Move message entities to start of message placeholder
            for entity in message.entities:
                entity.offset += message_offset

        if pre_formatted_entities:
            # Update entities position after message placeholder
            message_placeholder_length_diff = len(
                # Telegram offsets are calculated with surrogates
                utils.add_surrogate(message.message)
            ) - len(self.MESSAGE_PLACEHOLDER)

            for entity in pre_formatted_entities:
                if entity.offset > message_offset:
                    entity.offset += message_placeholder_length_diff

            if message.entities:
                message.entities.extend(pre_formatted_entities)
            else:
                message.entities = pre_formatted_entities

        message.message = pre_formatted_text.format(message_text=message.message)

        return True, message

    async def _process_album(
        self, album: EventAlbumMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventAlbumMessage]:
        # Process first message with non-empty text or first message
        message_idx, message_album = next(
            ((idx, message) for idx, message in enumerate(album) if message.message),
            (0, album[0]),
        )

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


class KeywordReplaceFilter(UpdateEntitiesParams, WordBoundaryRegex, MessageFilter):
    """Filter that maps keywords
    Args:
        keywords (dict[str, str]): Keywords map
    """

    def __init__(self, keywords: dict[str, str], regex: bool = False) -> None:
        self._lookup_regex = (
            re.compile(
                f'{self.BOUNDARY_REGEX}{"|".join(re.escape(k) for k in keywords)}{self.BOUNDARY_REGEX}',
                flags=re.IGNORECASE,
            )
            if not regex
            else re.compile(
                f'{self.BOUNDARY_REGEX}{"|".join(keywords.keys())}{self.BOUNDARY_REGEX}',
                flags=re.IGNORECASE,
            )
        )
        # Lower-cased keywords mapping
        self._keywords_mapping = {k.lower(): v for k, v in keywords.items()}

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventMessage]:
        if not message.message:
            return True, message

        filtered_text = utils.add_surrogate(message.message)
        filtered_entities = message.entities or []
        entities_offset_error = 0

        def repl(match: re.Match[str]) -> str:
            group = match.group()
            replacement = self._keywords_mapping.get(group.lower())

            nonlocal entities_offset_error
            match_start, match_end = match.span()
            diff = len(replacement) - (match_end - match_start)
            self.update_entities_params(
                filtered_entities,
                match_start + entities_offset_error,
                match_end + entities_offset_error,
                diff,
            )
            entities_offset_error += diff

            if group.islower():
                return replacement.lower()
            if group.istitle():
                return replacement.title()
            if group.isupper():
                return replacement.upper()
            return replacement

        filtered_text = self._lookup_regex.sub(repl, filtered_text)

        message.entities = filtered_entities
        message.message = utils.del_surrogate(filtered_text)

        return True, message


class SkipWithKeywordsFilter(WordBoundaryRegex, MessageFilter):
    """Skips message if some keyword found"""

    def __init__(self, keywords: set[str], regex: bool = False) -> None:
        self._lookup_regex = (
            re.compile(
                f'{self.BOUNDARY_REGEX}{"|".join(re.escape(k) for k in keywords)}{self.BOUNDARY_REGEX}',
                flags=re.IGNORECASE,
            )
            if not regex
            else re.compile(
                f'{self.BOUNDARY_REGEX}{"|".join(keywords)}{self.BOUNDARY_REGEX}',
                flags=re.IGNORECASE,
            )
        )

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventMessage]:
        return self._lookup_regex.search(message.message) is None, message

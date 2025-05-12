import re
from typing import Optional, Set, Type, Union

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
from .base import FilterAction, FilterResult, MessageFilter


class EmptyMessageFilter(MessageFilter):
    """Do nothing with message"""

    async def process(
        self, entity: EventEntity, event_type: Type[EventLike]
    ) -> FilterResult[EventEntity]:
        return FilterResult(FilterAction.CONTINUE, entity)

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> FilterResult[EventMessage]:
        raise NotImplementedError


class SkipAllFilter(MessageFilter):
    """Skips all messages"""

    async def process(
        self, entity: EventEntity, event_type: Type[EventLike]
    ) -> FilterResult[EventEntity]:
        return FilterResult(FilterAction.DISCARD, entity)

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> FilterResult[EventMessage]:
        raise NotImplementedError


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
    ) -> FilterResult[EventMessage]:
        if isinstance(message.media, types.MessageMediaWebPage):
            return FilterResult(FilterAction.DISCARD, message)

        for entity in message.entities or []:
            if isinstance(
                entity, (types.MessageEntityUrl, types.MessageEntityTextUrl)
            ) or (
                isinstance(
                    entity, (types.MessageEntityMention, types.MessageEntityMentionName)
                )
                and self._skip_mention
            ):
                return FilterResult(FilterAction.DISCARD, message)

        return FilterResult(FilterAction.CONTINUE, message)


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
        self._placeholder = utils.add_surrogate(placeholder)
        self._placeholder_len = len(self._placeholder)

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
    ) -> FilterResult[EventMessage]:
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
                isinstance(
                    entity, (types.MessageEntityMention, types.MessageEntityTextUrl)
                )
                and self._match_mention(
                    filtered_text[entity.offset : entity.offset + entity.length]
                )
            ):
                filtered_text = (
                    filtered_text[: entity.offset]
                    + self._placeholder
                    + filtered_text[entity.offset + entity.length :]
                )
                entity_len_diff = self._placeholder_len - entity.length
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

            diff = self._placeholder_len - (end - start)
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

        return FilterResult(FilterAction.CONTINUE, message)

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
        where `{channel_name}`, `{message_link}`, `{sender_title}`, `{sender_username}`
        and `{message_text}` are placeholders to actual incoming message values.
    """

    MESSAGE_PLACEHOLDER: str = "{message_text}"
    CHANNEL_NAME_PLACEHOLDER: str = "{channel_name}"
    MESSAGE_LINK_PLACEHOLDER: str = "{message_link}"
    SENDER_TITLE_PLACEHOLDER: str = "{sender_title}"
    SENDER_USERNAME_PLACEHOLDER: str = "{sender_username}"

    DEFAULT_FORMAT: str = (
        "{message_text}\n\nForwarded from [{channel_name}]({message_link})"
    )

    def __init__(self, format: str = DEFAULT_FORMAT) -> None:
        self._format = format

        self._request_channel_name = (
            ForwardFormatFilter.CHANNEL_NAME_PLACEHOLDER in format
        )
        self._request_message_link = (
            ForwardFormatFilter.MESSAGE_LINK_PLACEHOLDER in format
        )
        self._request_sender_title = (
            ForwardFormatFilter.SENDER_TITLE_PLACEHOLDER in format
        )
        self._request_sender_username = (
            ForwardFormatFilter.SENDER_USERNAME_PLACEHOLDER in format
        )

        from telethon.extensions import markdown as md_parser

        self._parser = md_parser

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> FilterResult[EventMessage]:
        # Skip format editing for empty album's items
        if (
            event_type is events.MessageEdited.Event
            and message.grouped_id
            and not message.message
        ):
            return FilterResult(FilterAction.CONTINUE, message)

        message_link = (
            self.message_link(message) or "" if self._request_message_link else ""
        )
        channel_name = (
            self.channel_name(message) or "" if self._request_channel_name else ""
        )

        sender_title: str = ""
        sender_username: str = ""

        if self._request_sender_title or self._request_sender_username:
            sender: Optional[
                Union[types.User, types.Channel]
            ] = await message.get_sender()

            if sender:
                if self._request_sender_title:
                    sender_title = utils.get_display_name(sender) or ""

                if self._request_sender_username:
                    sender_username = sender.username or ""

        # Fill all placeholders, except {message_text}
        pre_formatted_message = self._format.format(
            channel_name=channel_name,
            message_link=message_link,
            sender_title=sender_title,
            sender_username=sender_username,
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

        return FilterResult(FilterAction.CONTINUE, message)

    async def _process_album(
        self, album: EventAlbumMessage, event_type: Type[EventLike]
    ) -> FilterResult[EventAlbumMessage]:
        # Process first message with non-empty text or first message
        message_idx, message_album = next(
            ((idx, message) for idx, message in enumerate(album) if message.message),
            (0, album[0]),
        )

        filter_action, album[message_idx] = await self._process_message(
            message_album, event_type
        )

        return FilterResult(filter_action, album)


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

    def __init__(self, keywords: dict[str, str]) -> None:
        self._lookup_regex = {
            re.compile(
                k.removeprefix("r'").removesuffix("'")
                if k.startswith("r'")
                else f"{self.BOUNDARY_REGEX}{re.escape(k)}{self.BOUNDARY_REGEX}",
                flags=re.IGNORECASE,
            ): utils.add_surrogate(v)
            for k, v in keywords.items()
        }

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> FilterResult[EventMessage]:
        if not message.message:
            return FilterResult(FilterAction.CONTINUE, message)

        filtered_text = utils.add_surrogate(message.message)
        filtered_entities = message.entities or []
        entities_offset_error = 0

        current_replacement = None

        def repl(match: re.Match[str]) -> str:
            replacement = match.expand(current_replacement)

            full_match = match.group()

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

            if full_match.islower():
                return replacement.lower()
            if full_match.istitle():
                return replacement.title()
            if full_match.isupper():
                return replacement.upper()
            return replacement

        for k, v in self._lookup_regex.items():
            current_replacement = v
            filtered_text = k.sub(repl, filtered_text)

        message.entities = filtered_entities
        message.message = utils.del_surrogate(filtered_text)

        return FilterResult(FilterAction.CONTINUE, message)


class SkipWithKeywordsFilter(WordBoundaryRegex, MessageFilter):
    """Skips message if some keyword found

    Args:
        keywords (set[str]): Keywords set
    """

    def __init__(self, keywords: set[str]) -> None:
        self._lookup_regex = re.compile(
            "|".join(
                k.removeprefix("r'").removesuffix("'")
                if k.startswith("r'")
                else f"{self.BOUNDARY_REGEX}{re.escape(k)}{self.BOUNDARY_REGEX}"
                for k in keywords
            ),
            flags=re.IGNORECASE,
        )

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> FilterResult[EventMessage]:
        return FilterResult(
            FilterAction.CONTINUE
            if self._lookup_regex.search(message.message) is None
            else FilterAction.DISCARD,
            message,
        )


class AllowWithKeywordsFilter(SkipWithKeywordsFilter):
    """Allow message if some keyword found

    Args:
        keywords (set[str]): Keywords set
    """

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> FilterResult[EventMessage]:
        return FilterResult(
            FilterAction.CONTINUE
            if self._lookup_regex.search(message.message) is not None
            else FilterAction.DISCARD,
            message,
        )

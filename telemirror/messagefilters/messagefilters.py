import re
from typing import List, Optional, Set, Tuple

from telethon import types, utils
from telethon.extensions import markdown as md_parser

from ..hints import EventMessage
from ..misc.uri import UriGuard
from .base import MessageFilter
from .mixins import ChannelName, CopyMessage, MappedChannelName, MessageLink


class EmptyMessageFilter(MessageFilter):
    """Do nothing with message"""

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        return True, message


class SkipUrlFilter(MessageFilter):
    """Skip messages with URLs

    Args:
        skip_mention (`bool`, optional): 
            Enable skipping text mentions (@channel). Defaults to True.
    """

    def __init__(
        self: 'SkipUrlFilter',
        skip_mention: bool = True
    ) -> None:
        self._skip_mention = skip_mention

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        if message.entities:
            for e in message.entities:
                if isinstance(e, (types.MessageEntityUrl, types.MessageEntityTextUrl)) or \
                        (isinstance(e, (types.MessageEntityMention, types.MessageEntityMentionName)) and self._skip_mention):
                    return False, message

        if isinstance(message.media, types.MessageMediaWebPage):
            return False, message

        return True, message


class UrlMessageFilter(CopyMessage, MessageFilter):
    """URLs message filter

    Args:
        placeholder (`str`, optional): 
            URL placeholder. Defaults to '***'.

        filter_mention (`bool`, optional): 
            Enable filter text mentions (@channel). Defaults to True.

        blacklist (`Set[str]`, optional): 
            URLs blacklist -- remove only these URLs. Defaults to empty set.

        whitelist (`Set[str]`, optional): 
            URLs whitelist -- remove all URLs except these. 
            Will be applied after the `blacklist`. Defaults to empty set.
    """

    def __init__(
        self: 'UrlMessageFilter',
        placeholder: str = '***',
        filter_mention: bool = True,
        blacklist: Set[str] = set(),
        whitelist: Set[str] = set()
    ) -> None:
        self._placeholder = placeholder
        self._placeholder_len = len(placeholder)
        self._filter_mention = filter_mention
        self._uri_guard = UriGuard(blacklist, whitelist)

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        filtered_message = self.copy_message(message)
        # Filter message entities
        if filtered_message.entities:
            good_entities: List[types.TypeMessageEntity] = []
            offset_error = 0
            for e, entity_text in filtered_message.get_entities_text():
                e.offset += offset_error
                # Filter URLs and mentions
                if (isinstance(e, types.MessageEntityUrl) and self._uri_guard.is_should_filtered(entity_text)) \
                        or (isinstance(e, types.MessageEntityMention) and self._filter_mention):
                    filtered_message.message = filtered_message.message.replace(
                        entity_text, self._placeholder, 1)
                    offset_error += self._placeholder_len - e.length
                    continue

                # Keep only 'good' entities
                if not ((isinstance(e, types.MessageEntityTextUrl) and self._uri_guard.is_should_filtered(e.url)) or
                        (isinstance(e, types.MessageEntityMentionName) and self._filter_mention)):
                    good_entities.append(e)

            filtered_message.entities = good_entities

        # Filter link preview
        if isinstance(filtered_message.media, types.MessageMediaWebPage) and \
            isinstance(filtered_message.media.webpage, types.WebPage) and \
                self._uri_guard.is_should_filtered(filtered_message.media.webpage.url):
            filtered_message.media = None

        return True, filtered_message


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
    DEFAULT_FORMAT: str = "{message_text}\n\nForwarded from [{channel_name}]({message_link})"

    def __init__(self, format: str = DEFAULT_FORMAT) -> None:
        self._format = format

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        message_link: Optional[str] = self.message_link(message)
        channel_name: str = self.channel_name(message)

        filtered_message = self.copy_message(message)

        if channel_name and message_link:

            pre_formatted_message = self._format.format(
                channel_name=channel_name,
                message_link=message_link,
                message_text=self.MESSAGE_PLACEHOLDER
            )
            pre_formatted_text, pre_formatted_entities = md_parser.parse(
                pre_formatted_message)

            message_offset = pre_formatted_text.find(self.MESSAGE_PLACEHOLDER)

            if filtered_message.entities:
                for e in filtered_message.entities:
                    e.offset += message_offset

            if pre_formatted_entities:
                message_placeholder_length_diff = len(utils.add_surrogate(
                    message.message)) - len(self.MESSAGE_PLACEHOLDER)
                for e in pre_formatted_entities:
                    if e.offset > message_offset:
                        e.offset += message_placeholder_length_diff

                if filtered_message.entities:
                    filtered_message.entities.extend(pre_formatted_entities)
                else:
                    filtered_message.entities = pre_formatted_entities

            filtered_message.message = pre_formatted_text.format(
                message_text=filtered_message.message)

        return True, filtered_message


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


class KeywordReplaceFilter(CopyMessage, MessageFilter):
    """Filter that replaces keywords

    Args:
        keywords (dict[str, str]): Keywords map
    """

    def __init__(self, keywords: dict[str, str]) -> None:
        self._keywords = {f'\\b{k}\\b': v for k, v in keywords.items()}

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        filtered_message = self.copy_message(message)

        unparsed_text = filtered_message.text

        if unparsed_text:
            for k, v in self._keywords.items():
                unparsed_text = re.sub(
                    k, v, unparsed_text, flags=re.IGNORECASE)

            filtered_message.text = unparsed_text

        return True, filtered_message


class SkipAllFilter(MessageFilter):
    """Skips all messages
    """
    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        return False, message


class SkipWithKeywordsFilter(MessageFilter):
    """Skips message if some keyword found
    """

    def __init__(self, keywords: set[str]) -> None:
        self._regex = re.compile(
            '|'.join([f'\\b{k}\\b' for k in keywords]), flags=re.IGNORECASE)

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        if self._regex.search(message.message):
            return False, message
        return True, message

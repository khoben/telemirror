from abc import abstractmethod
from typing import List, Optional, Protocol, Set, Tuple

from telethon import types, utils
from telethon.extensions import markdown as md

from .hints import EventMessage
from .misc.message import CopyMessage, MessageLink
from .misc.uri import UriGuard


class MessageFilter(Protocol):

    @abstractmethod
    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        """Apply filter to **message**

        Args:
            message (`EventMessage`): Source message

        Returns:
            Tuple[bool, EventMessage]: 
                Indicates that the filtered message should be forwarded

                Processed message
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return self.__class__.__name__


class EmptyMessageFilter(MessageFilter):
    """Do nothing with message"""

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        return True, message


class CompositeMessageFilter(MessageFilter):
    """Composite message filter that sequentially applies the filters

    Args:
        *arg (`MessageFilter`):
            Message filters 
    """

    def __init__(self, *arg: MessageFilter) -> None:
        self._filters = list(arg)

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        for f in self._filters:
            cont, message = await f.process(message)
            if cont is False:
                return False, message
        return True, message

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}: {self._filters}'


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


class ForwardFormatFilter(MessageLink, CopyMessage, MessageFilter):
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
        channel_name: str = utils.get_display_name(message.chat)

        filtered_message = self.copy_message(message)

        if channel_name and message_link:

            pre_formatted_message = self._format.format(
                channel_name=channel_name,
                message_link=message_link,
                message_text=self.MESSAGE_PLACEHOLDER
            )
            pre_formatted_text, pre_formatted_entities = md.parse(
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


class RestrictSavingContentBypassFilter(MessageFilter):
    """Filter that bypasses `saving content restriction`

    Sample implementation:
    Download the media, upload it to the Telegram servers,
    and then change to the new uploaded media:

    ```
    if not message.media or not message.chat.noforwards:
        return message

    # Handle photos
    if isinstance(message.media, types.MessageMediaPhoto):
        client: TelegramClient = message.client
        photo: bytes = client.download_media(message=message, file=bytes)
        cloned_photo: types.TypeInputFile = client.upload_file(photo)
        message.media = cloned_photo

    # Others types...

    return message

    ```
    """

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        raise NotImplementedError

from abc import abstractmethod
from typing import List, Optional, Protocol, Set

from telethon import types, utils
from telethon.extensions import markdown as md
from urlextractor import URLExtrator

from .hints import MessageLike


class MesssageFilter(Protocol):
    @abstractmethod
    async def process(self, message: MessageLike) -> MessageLike:
        """Apply filter to **message**

        Args:
            message (`MessageLike`): Source message

        Returns:
            `MessageLike`: Filtered message
        """
        raise NotImplementedError


class EmptyMessageFilter(MesssageFilter):
    """Do nothing with message"""

    async def process(self, message: MessageLike) -> MessageLike:
        return message


class UrlMessageFilter(MesssageFilter):
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
        self._extract_url = URLExtrator(blacklist, whitelist)

    async def process(self, message: MessageLike) -> MessageLike:
        # Filter message entities
        if message.entities:
            good_entities: List[types.TypeMessageEntity] = []
            offset_error = 0
            for e, entity_text in message.get_entities_text():
                e.offset += offset_error
                # Filter URLs and mentions
                if (isinstance(e, types.MessageEntityUrl) and self._extract_url.has_urls(entity_text)) \
                        or (isinstance(e, types.MessageEntityMention) and self._filter_mention):
                    message.message = message.message.replace(
                        entity_text, self._placeholder, 1)
                    offset_error += self._placeholder_len - e.length
                    continue

                # Keep only 'good' entities
                if not ((isinstance(e, types.MessageEntityTextUrl) and self._extract_url.has_urls(e.url)) or
                        (isinstance(e, types.MessageEntityMentionName) and self._filter_mention)):
                    good_entities.append(e)

            message.entities = good_entities

        # Filter link preview
        if isinstance(message.media, types.MessageMediaWebPage) and \
            isinstance(message.media.webpage, types.WebPage) and \
                self._extract_url.has_urls(message.media.webpage.url):
            message.media = None

        return message


class RestrictSavingContentBypassFilter(MesssageFilter):
    """Filter that bypasses `saving content restriction`

    Maybe download the media, upload it to the Telegram servers,
    and then change to the new uploaded media:

    ```
    downloaded = await client.download_media(message, file=bytes)
    uploaded = await client.upload_file(downloaded)
    # set uploaded as message file
    ```
    """

    async def process(self, message: MessageLike) -> MessageLike:
        raise NotImplementedError


class CompositeMessageFilter(MesssageFilter):
    """Composite message filter that sequentially applies the filters

    Args:
        *arg (`MessageFilter`):
            Message filters 
    """

    def __init__(self, *arg: MesssageFilter) -> None:
        self._filters = list(arg)

    async def process(self, message: MessageLike) -> MessageLike:
        for f in self._filters:
            message = await f.process(message)
        return message


class ForwardFormatFilter(MesssageFilter):
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

    async def process(self, message: MessageLike) -> MessageLike:
        message_link: Optional[str] = self._message_link(message)
        channel_name: str = utils.get_display_name(message.chat)

        if channel_name and message_link:

            pre_formatted_message = self._format.format(
                channel_name=channel_name,
                message_link=message_link,
                message_text=self.MESSAGE_PLACEHOLDER
            )
            pre_formatted_text, pre_formatted_entities = md.parse(
                pre_formatted_message)

            message_offset = pre_formatted_text.find(self.MESSAGE_PLACEHOLDER)

            if message.entities:
                for e in message.entities:
                    e.offset += message_offset

            if pre_formatted_entities:
                message_placeholder_length_diff = len(utils.add_surrogate(
                    message.message)) - len(self.MESSAGE_PLACEHOLDER)
                for e in pre_formatted_entities:
                    if e.offset > message_offset:
                        e.offset += message_placeholder_length_diff

                if message.entities:
                    message.entities.extend(pre_formatted_entities)
                else:
                    message.entities = pre_formatted_entities

            message.message = pre_formatted_text.format(
                message_text=message.message)

        return message
    
    def _message_link(self, message: MessageLike) -> Optional[str]:
        """Get link to message from origin channel"""
        if not isinstance(message.peer_id, types.PeerUser):
            if hasattr(message.chat, "username") and message.chat.username:
                link = f"https://t.me/{message.chat.username}/{message.id}"
            else:
                link = f"https://t.me/c/{message.chat.id}/{message.id}"
            return link
        return None

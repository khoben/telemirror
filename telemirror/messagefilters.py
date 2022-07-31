import re
from abc import abstractmethod
from typing import List, Optional, Protocol, Set, Tuple, Union

from telethon import hints, types, utils
from urlextract import URLExtract

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
    """Url filter replaces found URLs to **placeholder**

    Args:
        placeholder (`str`, optional): 
            URL placeholder. Defaults to '***'.

        filter_mention (`bool`, optional): 
            Enable filter text mentions (@channel). Defaults to True.

        blacklist (`List[str]` | `Set[str]`, optional): 
            URLs blacklist -- remove only these URLs. Defaults to {}.

        whitelist (`List[str]` | `Set[str]`, optional): 
            URLs whitelist. Defaults to {}.
    """

    def __init__(
        self: 'UrlMessageFilter',
        placeholder: str = '***',
        filter_mention: bool = True,
        blacklist: Union[List[str], Set[str]] = {},
        whitelist: Union[List[str], Set[str]] = {}
    ) -> None:
        self._placeholder = placeholder
        self._filter_mention = filter_mention
        self._extract_url = URLExtract()
        self._extract_url.permit_list = blacklist
        if not blacklist:
            self._extract_url.ignore_list = whitelist

    async def process(self, message: MessageLike) -> MessageLike:
        # replace plain text
        message.message = self._filter_urls(message.message)
        # remove MessageEntityTextUrl
        if message.entities is not None:
            message.entities = [
                e for e in message.entities
                if not(isinstance(e, types.MessageEntityTextUrl) and self._extract_url.has_urls(e.url))
            ]
        return message

    def _filter_urls(self, text: str) -> str:
        urls = self._extract_url.find_urls(text, only_unique=True)
        for url in urls:
            text = text.replace(url, self._placeholder)

        if self._filter_mention:
            text = re.sub(r'@[\d\w]*', self._placeholder, text)

        return text


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

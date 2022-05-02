import re
from abc import abstractmethod
from typing import List, Protocol, Set, Union

from telethon import custom, types
from urlextract import URLExtract

MessageLike = Union[types.Message, custom.Message]


class MesssageFilter(Protocol):
    @abstractmethod
    def process(self, message: MessageLike) -> MessageLike:
        raise NotImplementedError


class EmptyFilter(MesssageFilter):
    def process(self, message: MessageLike) -> MessageLike:
        return message


class UrlFilter(MesssageFilter):

    def __init__(
        self: 'UrlFilter',
        placeholder: str = '***',
        blacklist: Union[List[str], Set[str]] = {},
        whitelist: Union[List[str], Set[str]] = {}
    ) -> None:
        self._placeholder = placeholder
        self._extract_url = URLExtract()
        self._extract_url.permit_list = blacklist
        if not blacklist:
            self._extract_url.ignore_list = whitelist

    def process(self, message: MessageLike) -> MessageLike:
        # replace plain text
        message.message = self._filter_urls(message.message)
        # replace UrlEntities
        if message.entities is not None:
            for urlEntity in message.entities:
                if isinstance(urlEntity, types.MessageEntityTextUrl):
                    urlEntity.url = self._filter_urls(urlEntity.url)
        return message

    def _filter_urls(self, text: str) -> str:
        urls = self._extract_url.find_urls(text, only_unique=True)
        for url in urls:
            text = text.replace(url, self._placeholder)

        text = re.sub(r'@[\d\w]*', self._placeholder, text)

        return text


class RestrictSavingContentBypassFilter(MesssageFilter):
    """
    Maybe here download media, upload to Telegram servers and then change to new uploaded media

    ```
    downloaded = await client.download_media(message, file=bytes)
    uploaded = await client.upload_file(downloaded)
    ...
    ```
    """

    def process(self, message: MessageLike) -> MessageLike:
        raise NotImplementedError


class GroupFilter(MesssageFilter):

    def __init__(self, *arg: MesssageFilter) -> None:
        self._filters = list(arg)

    def process(self, message: MessageLike) -> MessageLike:
        for f in self._filters:
            message = f.process(message)
        return message

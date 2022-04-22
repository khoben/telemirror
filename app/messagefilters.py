import re
from abc import abstractmethod
from typing import List, Protocol

from telethon import types
from urlextract import URLExtract


class MesssageFilter(Protocol):
    @abstractmethod
    def process(self, message: types.Message) -> types.Message:
        raise NotImplementedError


class EmptyFilter(MesssageFilter):
    def process(self, message: types.Message) -> types.Message:
        return message


class UrlFilter(MesssageFilter):

    def __init__(self: 'UrlFilter', placeholder: str = '***', whitelist: List[str] = None) -> None:
        self._placeholder = placeholder
        if whitelist is None:
            whitelist = []
        self._whitelist = whitelist
        self._url_extractor = URLExtract()

    def process(self, message: types.Message) -> types.Message:
        # replace plain text
        message.message = self._filter_urls(message.message)
        # replace UrlEntities
        if message.entities is not None:
            for urlEntity in message.entities:
                if isinstance(urlEntity, types.MessageEntityTextUrl):
                    urlEntity.url = self._filter_urls(urlEntity.url)
        return message

    def _filter_urls(self, text: str) -> str:
        urls = self._url_extractor.find_urls(text)
        for url in urls:
            allowed = False
            for white_listed in self._whitelist:
                if url.find(white_listed) != -1:
                    allowed = True
                    break
            if allowed is False:
                text = text.replace(url, self._placeholder)

        # @test => placeholder
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

    def process(self, message: types.Message) -> types.Message:
        raise NotImplementedError


class GroupFilter(MesssageFilter):

    def __init__(self, *arg: MesssageFilter) -> None:
        self._filters = list(arg)

    def process(self, message: types.Message) -> types.Message:
        for f in self._filters:
            message = f.process(message)
        return message

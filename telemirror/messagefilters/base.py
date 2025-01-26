from abc import abstractmethod
from enum import Enum
from typing import Generic, NamedTuple, Protocol, Type, TypeVar

from ..hints import EventAlbumMessage, EventEntity, EventLike, EventMessage

EVENT_TYPE = TypeVar("EVENT_TYPE", EventEntity, EventMessage, EventAlbumMessage)


class FilterAction(int, Enum):
    CONTINUE = 0
    """Continue processing message, send/forward at the end of the filter sequence"""
    FORCE_SEND = 1
    """Send/forward message immediately, ignore other filters in sequence"""
    DISCARD = 2
    """Discard processing message, don`t send/forward message"""


class FilterResult(NamedTuple, Generic[EVENT_TYPE]):
    action: FilterAction
    entity: EVENT_TYPE


class MessageFilter(Protocol):
    @property
    def restricted_content_allowed(self) -> bool:
        """Indicates that restricted content is allowed or not to process"""
        return False

    async def process(
        self, entity: EventEntity, event_type: Type[EventLike]
    ) -> FilterResult[EventEntity]:
        """Process **entity** with filter

        Args:
            entity (`EventEntity`): Source event entity
            event_type (`Type[EventLike]`): Type of event

        Returns:
            `FilterResult[EventEntity]`:
                Indicates that the filtered message should be forwarded

                Processed entity
        """
        if isinstance(entity, EventMessage):
            return await self._process_message(entity, event_type)

        if isinstance(entity, list):
            # Check for `EventAlbumMessage`: List of messages
            return await self._process_album(entity, event_type)

        return FilterResult(FilterAction.CONTINUE, entity)

    @abstractmethod
    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> FilterResult[EventMessage]:
        """Process single **message** with filter

        Args:
            message (`EventMessage`): Source event message
            event_type (`Type[EventLike]`): Type of event

        Returns:
            `FilterResult[EventMessage]`:
                Indicates that the filtered message should be forwarded

                Processed message
        """
        raise NotImplementedError

    async def _process_album(
        self, album: EventAlbumMessage, event_type: Type[EventLike]
    ) -> FilterResult[EventAlbumMessage]:
        """Process **album** with filter

        Args:
            album (`EventAlbumMessage`): Source event album
            event_type (`Type[EventLike]`): Type of event

        Returns:
            `FilterResult[EventAlbumMessage]`:
                Indicates that the filtered message should be forwarded

                Processed album
        """
        for idx, message in enumerate(album):
            filter_action, album[idx] = await self._process_message(message, event_type)
            match filter_action:
                case FilterAction.CONTINUE | True:
                    continue
                case FilterAction.DISCARD | False:
                    return FilterResult(FilterAction.DISCARD, album)
                case FilterAction.FORCE_SEND:
                    return FilterResult(FilterAction.FORCE_SEND, album)

        return FilterResult(FilterAction.CONTINUE, album)

    def __repr__(self) -> str:
        return self.__class__.__name__


class CompositeMessageFilter(MessageFilter):
    """Composite message filter that sequentially applies the filters

    Args:
        *arg (`MessageFilter`):
            Message filters
    """

    def __init__(self, *arg: MessageFilter) -> None:
        self._filters = list(arg)
        self._is_restricted_content_allowed = any(
            f.restricted_content_allowed for f in self._filters
        )

    @property
    def restricted_content_allowed(self) -> bool:
        return self._is_restricted_content_allowed

    async def process(
        self, entity: EventEntity, event_type: Type[EventLike]
    ) -> FilterResult[EventEntity]:
        for f in self._filters:
            filter_action, entity = await f.process(entity, event_type)
            match filter_action:
                case FilterAction.CONTINUE | True:
                    continue
                case FilterAction.DISCARD | False:
                    return FilterResult(FilterAction.DISCARD, entity)
                case FilterAction.FORCE_SEND:
                    return FilterResult(FilterAction.FORCE_SEND, entity)

        return FilterResult(FilterAction.CONTINUE, entity)

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> FilterResult[EventMessage]:
        raise NotImplementedError

    async def _process_album(
        self, album: EventAlbumMessage, event_type: Type[EventLike]
    ) -> FilterResult[EventAlbumMessage]:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: {self._filters}"

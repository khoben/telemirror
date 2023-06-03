from abc import abstractmethod
from typing import Protocol, Tuple, Type

from ..hints import EventEntity, EventLike, EventAlbumMessage, EventMessage


class MessageFilter(Protocol):
    @property
    def restricted_content_allowed(self) -> bool:
        """Indicates that restricted content is allowed or not to process"""
        return False

    async def process(
        self, entity: EventEntity, event_type: Type[EventLike]
    ) -> Tuple[bool, EventEntity]:
        """Process **entity** with filter

        Args:
            entity (`EventEntity`): Source event entity
            event_type (`Type[EventLike]`): Type of event

        Returns:
            Tuple[bool, EventEntity]:
                Indicates that the filtered message should be forwarded

                Processed entity
        """
        if isinstance(entity, EventMessage):
            return await self._process_message(entity, event_type)
        elif isinstance(entity, list):
            return await self._process_album(entity, event_type)

        return True, entity

    @abstractmethod
    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventMessage]:
        """Process **message** with filter

        Args:
            message (`EventMessage`): Source event message
            event_type (`Type[EventLike]`): Type of event

        Returns:
            Tuple[bool, EventMessage]:
                Indicates that the filtered message should be forwarded

                Processed message
        """
        raise NotImplementedError

    async def _process_album(
        self, album: EventAlbumMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventAlbumMessage]:
        """Process **album** with filter

        Args:
            album (`EventAlbumMessage`): Source event album
            event_type (`Type[EventLike]`): Type of event

        Returns:
            Tuple[bool, EventAlbumMessage]:
                Indicates that the filtered message should be forwarded

                Processed album
        """
        for idx, message in enumerate(album):
            proceed, album[idx] = await self._process_message(message, event_type)
            if proceed is False:
                return False, album

        return True, album

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
        self, message: EventEntity, event_type: Type[EventLike]
    ) -> Tuple[bool, EventEntity]:
        for f in self._filters:
            proceed, message = await f.process(message, event_type)
            if proceed is False:
                return False, message
        return True, message

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventMessage]:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: {self._filters}"

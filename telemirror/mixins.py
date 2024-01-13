from typing import List, Optional

from telethon import types, utils

from .hints import EventAlbumMessage, EventMessage


class MappedChannelName:
    def __init__(self, mapped: dict[int, str]) -> None:
        self.__mapped = mapped

    def channel_name(self, message: EventMessage) -> Optional[str]:
        """Get chat/channel display name"""
        return self.__mapped.get(message.chat_id, utils.get_display_name(message.chat))


class ChannelName:
    def channel_name(self, message: EventMessage) -> Optional[str]:
        """Get chat/channel display name"""
        return utils.get_display_name(message.chat)


class MessageLink:
    def message_link(self, message: EventMessage) -> Optional[str]:
        """Get link to message from origin channel"""
        if not isinstance(message.peer_id, types.PeerUser):
            if hasattr(message.chat, "username") and message.chat.username:
                link = f"https://t.me/{message.chat.username}/{message.id}"
            else:
                link = f"https://t.me/c/{message.chat.id}/{message.id}"
            return link
        return None


class CopyEventMessage:
    def copy_message(self, message: EventMessage) -> EventMessage:
        """Copy message via constructor:
        `message`, `entities` and `media` properties
        shouldn't be affected by changes from original message

        Args:
            message (`EventMessage`): Source message

        Returns:
            `EventMessage`: Copied message
        """
        from copy import deepcopy

        cloned = EventMessage(
            id=message.id,
            peer_id=message.peer_id,
            date=message.date,
            out=message.out,
            mentioned=message.mentioned,
            media_unread=message.media_unread,
            silent=message.silent,
            post=message.post,
            from_id=message.from_id,
            reply_to=message.reply_to,
            ttl_period=message.ttl_period,
            message=message.message,
            fwd_from=message.fwd_from,
            via_bot_id=message.via_bot_id,
            media=deepcopy(message.media),
            reply_markup=message.reply_markup,
            entities=deepcopy(message.entities),
            views=message.views,
            edit_date=message.edit_date,
            post_author=message.post_author,
            grouped_id=message.grouped_id,
            from_scheduled=message.from_scheduled,
            legacy=message.legacy,
            edit_hide=message.edit_hide,
            pinned=message.pinned,
            noforwards=message.noforwards,
            reactions=message.reactions,
            restriction_reason=message.restriction_reason,
            forwards=message.forwards,
            replies=message.replies,
            action=message.action,
        )
        cloned._chat = message._chat
        cloned._client = message._client
        return cloned

    def copy_album(self, album: EventAlbumMessage) -> EventAlbumMessage:
        """Copy album via constructor:
        `message`, `entities` and `media` properties
        shouldn't be affected by changes from original album

        Args:
            album (`EventAlbumMessage`): Source album

        Returns:
            `EventAlbumMessage`: Copied album
        """
        return [self.copy_message(message) for message in album]


class WordBoundaryRegex:
    """
    Word boundary regex
    """

    BOUNDARY_REGEX = r"\b"


class UpdateEntitiesParams:
    def update_entities_params(
        self,
        entities: List[types.TypeMessageEntity],
        start: int,
        end: int,
        diff: int,
    ) -> None:
        """In-place iterative update entities `offset` and `length`:

        `[ ] ()`: Update `offset` += `diff`

        `( [ ] )`: Update `length` += `diff`

        `( [ ) ]`: Update `length` to `( )[ ]`

        `[ ( ] )`: Update `offset` to `[ ]( )`

        `[ ( ) ]`: Update `offset` and `length` to `[( )]`
        """
        if not entities or diff == 0:
            return

        for entity in entities:
            if entity.offset >= end:
                # After
                entity.offset += diff
            elif entity.offset <= start and entity.offset + entity.length >= end:
                # Before & After
                entity.length += diff
            elif entity.offset < start and start < entity.offset + entity.length < end:
                # Before with partial overlap
                entity.length -= (entity.offset + entity.length) - start
            elif start < entity.offset < end and entity.offset + entity.length > end:
                # After with partial overlap
                entity.offset = end + diff
            elif (
                start < entity.offset < end
                and start < entity.offset + entity.length < end
            ):
                # Fully inside: resize to match entity
                entity.offset = start
                entity.length = (end - start) + diff

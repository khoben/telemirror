from typing import Optional

from telethon import types, utils

from ..hints import EventMessage


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


class CopyMessage:

    def copy_message(self, message: EventMessage) -> EventMessage:
        """Copy **message** via constructor

        Args:
            message (`EventMessage`): Source message

        Returns:
            `EventMessage`: Copy of message
        """
        copy = EventMessage(
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
            media=message.media,
            reply_markup=message.reply_markup,
            entities=message.entities,
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
            action=message.action
        )
        copy._chat = message._chat
        copy._client = message._client
        return copy

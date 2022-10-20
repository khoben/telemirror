from typing import Optional, Tuple, Union
from telethon import types, utils

from telemirror.hints import EventMessage
from telemirror.messagefilters import MessageFilter, ForwardFormatFilter
from telemirror.storage import Database

KEY_POST = 0
KEY_COMMENT = 1

class ForwardLinkMessage:

    def message_link(self, message: EventMessage) -> Optional[str]:
        """Get link to message from origin channel"""

        if message.fwd_from and isinstance(message.fwd_from.from_id, types.PeerChannel) and message.fwd_from.channel_post:
            return f"https://t.me/c/{message.fwd_from.from_id.channel_id}/{message.fwd_from.channel_post}"

        return None

class BottomLinkFilter(ForwardLinkMessage, ForwardFormatFilter):
    pass


class AllowChannelPostFilter(MessageFilter):
    """Skip if not channel post
    """

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        return self.__is_post_from_chat(message), message

    def __is_post_from_chat(self, message: EventMessage) -> bool:
        if message.from_id and isinstance(message.from_id, types.PeerChannel) and message.fwd_from \
            and isinstance(message.fwd_from.from_id, types.PeerChannel) and \
                message.from_id.channel_id == message.fwd_from.from_id.channel_id:
            return True

        return False


class UserCommentFormatFilter(MessageFilter):
    """User comment format filter for linked chat
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:

        if message.reply_to is None:
            return False, message

        if not await self._database.get_messages(message.reply_to_msg_id, message.chat_id):
            return False, message

        comment_sender: Union[Optional[types.User], Optional[types.Channel]] = await message.get_sender()

        if comment_sender:
            name = utils.get_display_name(comment_sender)

            if isinstance(comment_sender, types.User):
                if not name:
                    name = 'User'
                mention = f"[{name}](tg://user?id={comment_sender.id})"

                message.text = f'Comment from {mention}:\n\n{message.text}'
                await message.client._replace_with_mention(message.entities, 0, comment_sender.id)

            elif isinstance(comment_sender, types.Channel):
                if not name:
                    name = 'Channel'
                if comment_sender.username:
                    mention = f"[{name}](https://t.me/{comment_sender.username})"
                else:
                    mention = name
                
                message.text = f'Comment from {mention}:\n\n{message.text}'

        return True, message

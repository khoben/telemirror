from typing import Optional, Tuple, Union

from telemirror.hints import EventMessage
from telemirror.messagefilters import ForwardFormatFilter, MessageFilter
from telemirror.storage import Database, MirrorMessage
from telethon import TelegramClient, types, utils


class Target:
    def __init__(self, v: str) -> None:
        assert v.startswith('(')
        assert v.endswith(')')

        values = v[1:-1].split('|')

        assert len(values) == 1 or len(values) == 2

        self.channel, self.comments = -1, None

        if len(values) == 2:
            self.channel, self.comments = int(values[0]), int(values[1])
        else:
            self.channel = int(values[0])

    def __repr__(self) -> str:
        return f'Target(channel={self.channel}, comments={self.comments})'


class Source:
    def __init__(self, v: str) -> None:
        assert v.startswith('(')
        assert v.endswith(')')

        values = v[1:-1].split('|')

        assert len(values) == 2 or len(values) == 3

        self.channel, self.title, self.comments = -1, '', None

        if len(values) == 3:
            self.channel, self.title, self.comments = int(
                values[0]), values[1], int(values[2])
        else:
            self.channel, self.title = int(values[0]), values[1]

        self.title = self.title[1:-1]

    def __repr__(self) -> str:
        return f'Source(channel={self.channel}, title={self.title}, comments={self.comments})'


class LinkedChatFilter(MessageFilter):
    """Linked chat filter that react to channel posts and replies to them
    """

    def install_db(self, db: Database) -> None:
        self._database = db

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:

        if self.__is_post_from_chat(message):

            mirror_channel_messages = await self._database.get_messages(
                message.fwd_from.channel_post,
                utils.get_peer_id(message.fwd_from.from_id)
            )

            if mirror_channel_messages:
                for mirror_channel_message in mirror_channel_messages:

                    comment_chat, comment_id = await message.client._get_comment_data(
                        mirror_channel_message.mirror_channel, mirror_channel_message.mirror_id)

                    await self._database.insert(
                        MirrorMessage(
                            message.id,
                            utils.get_peer_id(message.peer_id),
                            comment_id,
                            utils.get_peer_id(comment_chat)
                        )
                    )

            return False, message

        elif await self.__is_reply_to_post(message):

            return True, message

        return False, message

    def __is_post_from_chat(self, message: EventMessage) -> bool:
        if message.from_id and isinstance(message.from_id, types.PeerChannel) and message.fwd_from \
                and isinstance(message.fwd_from.from_id, types.PeerChannel) \
                and message.fwd_from.channel_post \
                and message.from_id.channel_id == message.fwd_from.from_id.channel_id:
            return True
        return False

    async def __is_reply_to_post(self, message: EventMessage) -> bool:
        if message.reply_to is None or message.reply_to.reply_to_msg_id is None:
            return False

        reply_to_id: int = message.reply_to.reply_to_msg_id
        chat_id: int = utils.get_peer_id(message.peer_id)

        if await self._database.get_messages(reply_to_id, chat_id):
            return True

        return False


class UserCommentFormatFilter(MessageFilter):
    """User comment format filter for linked chat
    """

    WARNING = "These are cloned comments.\nIf you want to comment, please [click here]({link}) to go to the original channel."

    def install_db(self, db: Database) -> None:
        self._database = db

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:

        # Sometimes returns None
        comment_sender: Union[Optional[types.User], Optional[types.Channel]] = await message.get_sender()

        if comment_sender:
            name = utils.get_display_name(comment_sender)
            message_link = self.message_link(message)

            if not name:
                if isinstance(comment_sender, types.User):
                    name = 'User'
                elif isinstance(comment_sender, types.Channel):
                    name = 'Channel'

            if message_link:
                message.text = f'[{name} say]({message_link}): {message.text}'

            reply_key = self.__reply_message_key(message)

            if not await self._database.check_for_message(reply_key):

                await self._database.mark_message(reply_key)

                reply_to_id: int = message.reply_to.reply_to_msg_id
                chat_id: int = utils.get_peer_id(message.peer_id)

                client: TelegramClient = message.client
                try:
                    message_link: Optional[str] = self.message_link(message)
                    if message_link:
                        for m in await self._database.get_messages(reply_to_id, chat_id):
                            # Send cloned comments disclaimer
                            await client.send_message(m.mirror_channel, message=self.WARNING.format(link=message_link), link_preview=False, reply_to=m.mirror_id)
                finally:
                    pass

            return True, message

        return False, message

    def message_link(self, message: EventMessage) -> str:

        reply_id = message.id
        channel_id = utils.get_peer_id(message.peer_id, add_mark=False)

        if message.reply_to is None:
            return f'https://t.me/c/{channel_id}/{reply_id}'

        reply_to_id = message.reply_to_msg_id

        return f'https://t.me/c/{channel_id}/{reply_id}?thread={reply_to_id}'

    def __reply_message_key(self, message: EventMessage) -> str:
        reply_to_id = message.reply_to_msg_id
        chat_id = utils.get_peer_id(message.peer_id)

        return f'{chat_id}:{reply_to_id}'


class MappedChannelName:

    def __init__(self, mapped: dict[int, str]) -> None:
        self.__mapped = mapped

    def channel_name(self, message: EventMessage) -> Optional[str]:
        return self.__mapped.get(message.chat_id, utils.get_display_name(message.chat))


class MappedNameForwardFormat(MappedChannelName, ForwardFormatFilter):
    def __init__(self, mapped: dict[int, str], format: str) -> None:
        MappedChannelName.__init__(self, mapped)
        ForwardFormatFilter.__init__(self, format)

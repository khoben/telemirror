import logging
from typing import Dict, List, Union

from config import TargetConfig
from telethon import TelegramClient, events, utils
from telethon.extensions import markdown
from telethon.sessions import StringSession
from telethon.tl import types

from .hints import EventLike, EventMessage
from .storage import Database, MirrorMessage


class EventHandlers:

    async def on_new_message(self: 'MirrorTelegramClient', event: events.NewMessage.Event) -> None:
        """NewMessage event handler"""

        # Skip albums
        if hasattr(event, 'grouped_id') and event.grouped_id is not None:
            return

        # Skip 'restricted saving content' enabled
        if event.message.chat.noforwards:
            self._logger.warning(
                f'Forwards from channel ({event.chat_id}) with `restricted saving content` '
                f'enabled are not supported. See https://github.com/khoben/telemirror#be-careful-with-forwards-from-'
                f'channels-with-restricted-saving-content-it-may-lead-to-an-account-ban'
            )
            return

        incoming_message_link: str = self.event_message_link(event)

        self._logger.info(f'New message: {incoming_message_link}')

        incoming_chat_id: int = event.chat_id
        incoming_message: EventMessage = event.message

        try:
            outgoing_chats = self._chat_mapping.get(incoming_chat_id)
            if not outgoing_chats:
                self._logger.warning(f'No target chats for {incoming_chat_id}')
                return

            reply_to_messages: dict[int, int] = {
                m.mirror_channel: m.mirror_id
                for m in await self._database.get_messages(incoming_message.reply_to_msg_id, incoming_chat_id)
            } if incoming_message.is_reply else {}

            if isinstance(incoming_message.media, types.MessageMediaPoll):
                # Copy quiz poll as simple poll
                incoming_message.media.poll.quiz = None

            for outgoing_chat in outgoing_chats:

                config = self._target_config.get(outgoing_chat)

                proceed, filtered_message = await config.filters.process(incoming_message)

                if proceed is False:
                    self._logger.info(
                        f'Skipping message {incoming_message_link} for {outgoing_chat}')
                    continue

                outgoing_message = await self.send_message(
                    entity=outgoing_chat,
                    message=filtered_message,
                    formatting_entities=filtered_message.entities,
                    reply_to=reply_to_messages.get(outgoing_chat)
                )

                if outgoing_message:
                    await self._database.insert(MirrorMessage(original_id=filtered_message.id,
                                                              original_channel=incoming_chat_id,
                                                              mirror_id=outgoing_message.id,
                                                              mirror_channel=outgoing_chat))
        except Exception as e:
            self._logger.error(e, exc_info=True)

    async def on_album(self: 'MirrorTelegramClient', event: events.Album.Event) -> None:
        """Album event handler"""

        # Skip 'restricted saving content' enabled
        if event.messages[0].chat.noforwards:
            self._logger.warning(
                f'Forwards from channel ({event.chat_id}) with `restricted saving content` '
                f'enabled are not supported. See https://github.com/khoben/telemirror#be-careful-with-forwards-from-'
                f'channels-with-restricted-saving-content-it-may-lead-to-an-account-ban'
            )
            return

        incoming_message_link: str = self.event_message_link(event)
        self._logger.info(f'New album: {incoming_message_link}')

        incoming_album: List[EventMessage] = event.messages
        incoming_first_message: EventMessage = incoming_album[0]
        incoming_chat_id: int = event.chat_id

        try:
            outgoing_chats = self._chat_mapping.get(incoming_chat_id)
            if not outgoing_chats:
                self._logger.warning(f'No target chats for {incoming_chat_id}')
                return

            reply_to_messages: dict[int, int] = {
                m.mirror_channel: m.mirror_id
                for m in await self._database.get_messages(incoming_first_message.reply_to_msg_id, incoming_chat_id)
            } if incoming_first_message.is_reply else {}

            for outgoing_chat in outgoing_chats:
                config = self._target_config.get(outgoing_chat)

                proceed = True
                filtered = False
                filtered_album: list[EventMessage] = []

                for m in incoming_album:
                    if m.message and not filtered:
                        filtered = True
                        proceed, filtered_message = await config.filters.process(m)
                        if proceed is False:
                            break
                        filtered_album.append(filtered_message)
                    else:
                        filtered_album.append(m)

                if not filtered:
                    proceed, filtered_album[0] = await config.filters.process(filtered_album[0])

                # Apply filters to first non-empty or first message
                if proceed is False:
                    self._logger.info(
                        f'Skipping album {incoming_message_link} for {outgoing_chat}')
                    continue

                idx: list[int] = []
                files: list[types.TypeMessageMedia] = []
                captions: list[str] = []
                for incoming_message in filtered_album:
                    idx.append(incoming_message.id)
                    files.append(incoming_message.media)
                    # Pass unparsed text, since: https://github.com/LonamiWebs/Telethon/issues/3065
                    captions.append(incoming_message.text)

                outgoing_messages: list[types.Message] = await self.send_file(
                    entity=outgoing_chat,
                    caption=captions,
                    file=files,
                    reply_to=reply_to_messages.get(outgoing_chat)
                )

                # Expect non-empty list of messages
                if outgoing_messages and utils.is_list_like(outgoing_messages):
                    for message_index, outgoing_message in enumerate(outgoing_messages):
                        await self._database.insert(MirrorMessage(original_id=idx[message_index],
                                                                  original_channel=incoming_chat_id,
                                                                  mirror_id=outgoing_message.id,
                                                                  mirror_channel=outgoing_chat))

        except Exception as e:
            self._logger.error(e, exc_info=True)

    async def on_edit_message(self: 'MirrorTelegramClient', event: events.MessageEdited.Event) -> None:
        """MessageEdited event handler"""

        # Skip updates with edit_hide attribute (reactions and so on...)
        if event.message.edit_hide is True:
            return

        incoming_message: EventMessage = event.message
        incoming_chat: int = event.chat_id
        incoming_message_link: str = self.event_message_link(event)

        self._logger.info(f'Edit message: {incoming_message_link}')

        try:
            outgoing_messages = await self._database.get_messages(incoming_message.id, incoming_chat)
            if not outgoing_messages:
                self._logger.warning(
                    f'No target messages to edit for {incoming_message_link}')
                return

            for outgoing_message in outgoing_messages:
                config = self._target_config.get(
                    outgoing_message.mirror_channel)

                if config.disable_edit is True:
                    continue

                filtered_message = incoming_message

                if incoming_message.grouped_id is None or incoming_message.message:
                    _, filtered_message = await config.filters.process(incoming_message)

                await self.edit_message(
                    entity=outgoing_message.mirror_channel,
                    message=outgoing_message.mirror_id,
                    text=filtered_message.message,
                    formatting_entities=filtered_message.entities,
                    file=filtered_message.media,
                    link_preview=isinstance(
                        filtered_message.media, types.MessageMediaWebPage)
                )
        except Exception as e:
            self._logger.error(e, exc_info=True)

    async def on_deleted_message(self: 'MirrorTelegramClient', event: events.MessageDeleted.Event) -> None:
        """MessageDeleted event handler"""

        deleted_ids: List[int] = event.deleted_ids
        incoming_chat: int = event.chat_id

        self._logger.info(
            f'Delete {len(deleted_ids)} messages from {incoming_chat}')

        try:
            for deleted_id in deleted_ids:
                deleting_messages = await self._database.get_messages(deleted_id, incoming_chat)
                if not deleting_messages:
                    self._logger.warning(
                        f'No target messages for {incoming_chat} and message#{deleted_id}')
                    continue

                for deleting_message in deleting_messages:
                    try:
                        config = self._target_config.get(
                            deleting_message.mirror_channel)

                        if config.disable_delete is True:
                            continue

                        await self.delete_messages(
                            entity=deleting_message.mirror_channel,
                            message_ids=deleting_message.mirror_id
                        )
                    except Exception as e:
                        self._logger.error(e, exc_info=True)

                await self._database.delete_messages(deleted_id, incoming_chat)

        except Exception as e:
            self._logger.error(e, exc_info=True)

    def event_message_link(self: 'MirrorTelegramClient', event: EventLike) -> str:
        """Get link to event message"""

        if isinstance(event, (events.NewMessage.Event, events.MessageEdited.Event)):
            incoming_message_id: int = event.message.id
        elif isinstance(event, events.Album.Event):
            incoming_message_id: int = event.messages[0].id
        elif isinstance(event, events.MessageDeleted.Event):
            incoming_message_id: int = event.deleted_id

        return f'https://t.me/c/{utils.resolve_id(event.chat_id)[0]}/{incoming_message_id}'


class Mirroring(EventHandlers):

    def __init__(
        self: 'MirrorTelegramClient',
        target_config: Dict[int, TargetConfig],
        chat_mapping: Dict[int, List[int]],
        database: Database,
        logger: Union[str, logging.Logger] = None,
    ) -> None:
        """Configure channels mirroring

        Args:
            target_config (`Dict[int, TargetConfig]`): Targets config
            chat_mapping (`Dict[int, List[int]]`): Mapping dictionary: {source: [target1, target2...]}
            database (`Database`): Message IDs storage
            logger (`str` | `logging.Logger`, optional): Logger. Defaults to None.
        """
        self._target_config = target_config
        self._chat_mapping = chat_mapping
        self._source_chats = list(chat_mapping.keys())
        self._database = database

        if isinstance(logger, str):
            logger = logging.getLogger(logger)
        elif not isinstance(logger, logging.Logger):
            logger = logging.getLogger(__name__)

        self._logger = logger

        self.add_event_handler(self.on_new_message,
                               events.NewMessage(chats=self._source_chats))
        self.add_event_handler(
            self.on_album, events.Album(chats=self._source_chats))

        self.add_event_handler(self.on_edit_message,
                               events.MessageEdited(chats=self._source_chats))

        self.add_event_handler(self.on_deleted_message,
                               events.MessageDeleted(chats=self._source_chats))

    def printable_config(self: 'MirrorTelegramClient') -> str:
        """Get printable mirror config"""

        mirror_mapping = '\n'.join(
            [f'{f} -> {", ".join(map(str, to))}' for (f, to) in self._chat_mapping.items()])

        return (
            f'Mirror mapping: \n{ mirror_mapping }\n'
            f'Mirror targets config: { self._target_config }\n'
            f'Using database: { self._database }\n'
        )


class MirrorTelegramClient(TelegramClient, Mirroring):

    def __init__(self: 'MirrorTelegramClient', session_string: str = None, api_id: str = None, api_hash: str = None, *args, **kwargs):
        TelegramClient.__init__(self, StringSession(
            session_string), api_id, api_hash)
        Mirroring.__init__(self, *args, **kwargs)
        # Set up default parse mode as markdown
        self._parse_mode = markdown

    @TelegramClient.parse_mode.setter
    def parse_mode(self: 'TelegramClient', mode: str):
        raise NotImplementedError

    async def run(self: 'MirrorTelegramClient') -> None:
        """Start channels mirroring"""
        await self.start()
        if await self.is_user_authorized():
            me = await self.get_me()
            self._logger.info(
                f'Logged in as {utils.get_display_name(me)} ({me.phone})')
            self._logger.info(
                f'Channel mirroring has started with config:\n{self.printable_config()}')
            await self.run_until_disconnected()
        else:
            raise RuntimeError(
                "There is no authorization for the user, try restart or get a new session key (run login.py)")

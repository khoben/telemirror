import logging
from typing import Dict, List, Union

from telethon import TelegramClient, events, utils
from telethon.sessions import StringSession
from telethon.tl import custom, types

from .hints import EventLike
from .messagefilters import EmptyMessageFilter, MesssageFilter
from .storage import Database, MirrorMessage


class EventHandlers:

    async def on_new_message(self: 'MirrorTelegramClient', event: events.NewMessage.Event) -> None:
        """NewMessage event handler"""

        if hasattr(event, 'grouped_id') and event.grouped_id is not None:
            # skip if Album
            return

        incoming_message: custom.Message = event.message
        incoming_chat: int = event.chat_id
        incoming_message_link: str = self.event_message_link(event)

        self._logger.info(f'New message: {incoming_message_link}')

        try:
            outgoing_chats = self._mirror_mapping.get(incoming_chat)
            if outgoing_chats is None or len(outgoing_chats) < 1:
                self._logger.warning(f'No target chats for {incoming_chat}')
                return

            incoming_message = await self._message_filter.process(incoming_message)
            for outgoing_chat in outgoing_chats:
                if isinstance(incoming_message.media, types.MessageMediaPoll):
                    outgoing_message = await self.send_message(
                        entity=outgoing_chat,
                        file=types.InputMediaPoll(
                            poll=incoming_message.media.poll
                        )
                    )
                else:
                    outgoing_message = await self.send_message(
                        entity=outgoing_chat,
                        message=incoming_message,
                        formatting_entities=incoming_message.entities
                    )

                if outgoing_message is not None:
                    await self._database.insert(MirrorMessage(original_id=incoming_message.id,
                                                              original_channel=incoming_chat,
                                                              mirror_id=outgoing_message.id,
                                                              mirror_channel=outgoing_chat))
        except Exception as e:
            self._logger.error(e, exc_info=True)

    async def on_album(self: 'MirrorTelegramClient', event: events.Album.Event) -> None:
        """Album event handler"""

        incoming_album: List[custom.Message] = event.messages
        incoming_chat: int = event.chat_id
        incoming_album_link: str = self.event_message_link(event)

        self._logger.info(f'New album: {incoming_album_link}')

        try:
            outgoing_chats = self._mirror_mapping.get(incoming_chat)
            if outgoing_chats is None or len(outgoing_chats) < 1:
                self._logger.warning(f'No target chats for {incoming_chat}')
                return

            files = []
            captions = []
            source_message_ids = []

            for incoming_message in incoming_album:
                incoming_message = await self._message_filter.process(incoming_message)
                files.append(incoming_message.media)
                captions.append(incoming_message.message)
                source_message_ids.append(incoming_message.id)

            for outgoing_chat in outgoing_chats:
                outgoing_messages = await self.send_file(entity=outgoing_chat, caption=captions, file=files)

                if outgoing_messages is not None and len(outgoing_messages) > 1:
                    for i, outgoing_message in enumerate(outgoing_messages):
                        await self._database.insert(MirrorMessage(original_id=source_message_ids[i],
                                                                  original_channel=incoming_chat,
                                                                  mirror_id=outgoing_message.id,
                                                                  mirror_channel=outgoing_chat))
        except Exception as e:
            self._logger.error(e, exc_info=True)

    async def on_edit_message(self: 'MirrorTelegramClient', event: events.MessageEdited.Event) -> None:
        """MessageEdited event handler"""

        if event.message.edit_hide is True:
            # skip if edit_hide (reactions and so on...)
            return

        incoming_message: custom.Message = event.message
        incoming_chat: int = event.chat_id
        incoming_message_link: str = self.event_message_link(event)

        self._logger.info(f'Edit message: {incoming_message_link}')

        try:
            outgoing_messages = await self._database.get_messages(
                incoming_message.id, incoming_chat)
            if outgoing_messages is None or len(outgoing_messages) < 1:
                self._logger.warning(
                    f'No target messages to edit for {incoming_message_link}')
                return

            incoming_message = await self._message_filter.process(incoming_message)
            for outgoing_message in outgoing_messages:
                await self.edit_message(
                    entity=outgoing_message.mirror_channel,
                    message=outgoing_message.mirror_id,
                    text=incoming_message.message,
                    formatting_entities=incoming_message.entities,
                    file=incoming_message.media
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
                deleting_messages = await self._database.get_messages(
                    deleted_id, incoming_chat)
                if deleting_messages is None or len(deleting_messages) < 1:
                    self._logger.warning(
                        f'No target messages for {incoming_chat} and message#{deleted_id}')
                    continue

                await self._database.delete_messages(deleted_id, incoming_chat)

                for deleting_message in deleting_messages:
                    try:
                        await self.delete_messages(
                            entity=deleting_message.mirror_channel,
                            message_ids=deleting_message.mirror_id
                        )
                    except Exception as e:
                        self._logger.error(e, exc_info=True)

        except Exception as e:
            self._logger.error(e, exc_info=True)

    def event_message_link(self: 'EventHandlers', event: EventLike) -> str:
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
        source_chats: List[int],
        mirror_mapping: Dict[int, List[int]],
        database: Database,
        message_filter: MesssageFilter = EmptyMessageFilter(),
        disable_edit: bool = False,
        disable_delete: bool = False,
        logger: Union[str, logging.Logger] = None,
    ) -> None:
        """Configure channels mirroring

        Args:
            source_chats (`List[int]`): Source chats ID list
            mirror_mapping (`Dict[int, List[int]]`): Mapping dictionary: {source: [target1, target2...]}
            database (`Database`): Message ID storage
            message_filter (`MesssageFilter`, optional): Message filter. Defaults to `EmptyMessageFilter`.
            disable_edit (`bool`, optional): Disable mirror message editing. Defaults to `False`.
            disable_delete (`bool`, optional): Disable mirror message deleting. Defaults to `False`.
            logger (`str` | `logging.Logger`, optional): Logger. Defaults to None.
        """
        self._source_chats = source_chats
        self._database = database
        self._mirror_mapping = mirror_mapping
        self._message_filter = message_filter
        self._disable_edit = disable_edit
        self._disable_delete = disable_delete

        if isinstance(logger, str):
            logger = logging.getLogger(logger)
        elif not isinstance(logger, logging.Logger):
            logger = logging.getLogger(__name__)

        self._logger = logger

        self.add_event_handler(self.on_new_message,
                               events.NewMessage(chats=source_chats))
        self.add_event_handler(self.on_album, events.Album(chats=source_chats))

        if not disable_edit:
            self.add_event_handler(self.on_edit_message,
                                   events.MessageEdited(chats=source_chats))

        if not disable_delete:
            self.add_event_handler(self.on_deleted_message,
                                   events.MessageDeleted(chats=source_chats))

    async def run(self: 'MirrorTelegramClient') -> None:
        """Start channels mirroring"""
        await self.start()
        if await self.is_user_authorized():
            me = await self.get_me()
            self._logger.info(
                f'Logged in as {utils.get_display_name(me)} ({me.phone})')
            self._logger.info(
                f'Channel mirroring has started with config:\n{self.print_config()}')
            await self.run_until_disconnected()
        else:
            raise RuntimeError(
                "There is no authorization for the user, try restart or get a new session key (run login.py)")

    def print_config(self: 'MirrorTelegramClient') -> str:
        """Prints mirror config"""

        return f"""
        Mirror mapping: { self._mirror_mapping }
        Message deleting: { "Disabled" if self._disable_delete else "Enabled" }
        Message editing: { "Disabled" if self._disable_edit else "Enabled" }
        Installed message filter: { self._message_filter }
        Using { self._database } database
        """


class MirrorTelegramClient(TelegramClient, Mirroring):

    def __init__(self, session_string: str = None, api_id: str = None, api_hash: str = None, *args, **kwargs):
        TelegramClient.__init__(self, StringSession(
            session_string), api_id, api_hash)
        Mirroring.__init__(self, *args, **kwargs)

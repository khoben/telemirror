import logging
from typing import Dict, List, Union

from telethon import TelegramClient, errors, events, utils
from telethon.sessions import StringSession
from telethon.tl import types

from config import DirectionConfig
from telemirror.hints import EventAlbumMessage, EventLike, EventMessage
from telemirror.storage import Database, MirrorMessage


class EventProcessor:
    def __init__(
        self: "EventProcessor",
        chat_mapping: Dict[int, Dict[int, DirectionConfig]],
        database: Database,
        client: TelegramClient,
        logger: logging.Logger,
    ) -> None:
        """Message event processor

        Args:
            chat_mapping (`Dict[int, Dict[int, DirectionConfig]]`): Chats mappings
            database (`Database`): Message IDs storage
            client (`TelegramClient`): Message sender client
            logger (`logging.Logger`): Logger
        """
        self._chat_mapping = chat_mapping
        self._database = database
        self._client = client
        self._logger = logger

    @staticmethod
    def __handle_exceptions(fn):
        from functools import wraps

        @wraps(fn)
        async def wrapper(self, *args, **kw):
            try:
                return await fn(self, *args, **kw)
            except Exception as e:
                if isinstance(self, EventProcessor):
                    self._logger.error(e, exc_info=True)

        return wrapper

    @__handle_exceptions
    async def new_message(
        self: "EventProcessor", chat_id: int, message: EventMessage, message_link: str
    ):
        restricted_saving_content: bool = message.chat and message.chat.noforwards

        outgoing_chats = self._chat_mapping.get(chat_id)
        if not outgoing_chats:
            self._logger.warning(
                f"[New message]: No target chats for message {message_link}"
            )
            return

        self._logger.info(f"[New message]: {message_link}")

        reply_to_messages: dict[int, int] = (
            {
                m.mirror_channel: m.mirror_id
                for m in await self._database.get_messages(
                    message.reply_to_msg_id, chat_id
                )
            }
            if message.is_reply
            else {}
        )

        # Copy quiz poll as simple poll
        if isinstance(message.media, types.MessageMediaPoll):
            message.media.poll.quiz = None

        for outgoing_chat, config in outgoing_chats.items():
            if (
                restricted_saving_content
                and not config.filters.restricted_content_allowed
            ):
                self._logger.warning(
                    f"Forwards from channel#{chat_id} "
                    f"with `restricted saving content` "
                    f"enabled to channel#{outgoing_chat} are not supported."
                )
                continue

            filtered_message: EventMessage
            proceed, filtered_message = await config.filters.process(
                message, events.NewMessage.Event
            )

            if proceed is False:
                self._logger.info(
                    f"[New message]: Message {message_link} was skipped "
                    f"by the filter for chat#{outgoing_chat}"
                )
                continue

            outgoing_message = None
            try:
                outgoing_message = await self._client.send_message(
                    entity=outgoing_chat,
                    message=filtered_message,
                    formatting_entities=filtered_message.entities,
                    reply_to=reply_to_messages.get(outgoing_chat),
                )
            except Exception as e:
                self._logger.error(
                    f"Error while sending message to chat#{outgoing_chat}. "
                    f"{type(e).__name__}: {e}"
                )
                continue

            if outgoing_message:
                await self._database.insert(
                    MirrorMessage(
                        original_id=filtered_message.id,
                        original_channel=chat_id,
                        mirror_id=outgoing_message.id,
                        mirror_channel=outgoing_chat,
                    )
                )

    @__handle_exceptions
    async def new_album(
        self: "EventProcessor", chat_id: int, album: EventAlbumMessage, album_link: str
    ) -> None:
        incoming_first_message: EventMessage = album[0]
        restricted_saving_content: bool = (
            incoming_first_message.chat and incoming_first_message.chat.noforwards
        )

        outgoing_chats = self._chat_mapping.get(chat_id)
        if not outgoing_chats:
            self._logger.warning(f"[New album]: No target chats for chat#{chat_id}")
            return

        self._logger.info(f"[New album]: {album_link}")

        reply_to_messages: dict[int, int] = (
            {
                m.mirror_channel: m.mirror_id
                for m in await self._database.get_messages(
                    incoming_first_message.reply_to_msg_id, chat_id
                )
            }
            if incoming_first_message.is_reply
            else {}
        )

        for outgoing_chat, config in outgoing_chats.items():
            if (
                restricted_saving_content
                and not config.filters.restricted_content_allowed
            ):
                self._logger.warning(
                    f"Forwards from channel#{chat_id} with "
                    f"`restricted saving content` "
                    f"enabled to channel#{outgoing_chat} are not supported."
                )
                continue

            filtered_album: EventAlbumMessage
            proceed, filtered_album = await config.filters.process(
                album, events.Album.Event
            )

            if proceed is False:
                self._logger.info(
                    f"[New album]: Message {album_link} was skipped "
                    f"by the filter for chat#{outgoing_chat}"
                )
                continue

            idx: List[int] = []
            files: List[types.TypeMessageMedia] = []
            captions: List[str] = []
            for incoming_message in filtered_album:
                idx.append(incoming_message.id)
                files.append(incoming_message.media)
                # Pass unparsed text, since: https://github.com/LonamiWebs/Telethon/issues/3065
                captions.append(incoming_message.text)

            outgoing_messages = None
            try:
                outgoing_messages: List[types.Message] = await self._client.send_file(
                    entity=outgoing_chat,
                    caption=captions,
                    file=files,
                    reply_to=reply_to_messages.get(outgoing_chat),
                )
            except Exception as e:
                self._logger.error(
                    f"Error while sending album to chat#{outgoing_chat}. "
                    f"{type(e).__name__}: {e}"
                )
                continue

            # Expect non-empty list of messages
            if outgoing_messages and utils.is_list_like(outgoing_messages):
                await self._database.insert_batch(
                    [
                        MirrorMessage(
                            original_id=idx[message_index],
                            original_channel=chat_id,
                            mirror_id=outgoing_message.id,
                            mirror_channel=outgoing_chat,
                        )
                        for message_index, outgoing_message in enumerate(
                            outgoing_messages
                        )
                    ]
                )

    @__handle_exceptions
    async def edit_message(
        self: "EventProcessor", chat_id: int, message: EventMessage, message_link: str
    ):
        outgoing_messages = await self._database.get_messages(message.id, chat_id)
        if not outgoing_messages:
            self._logger.warning(
                f"[Edit message]: No target messages to edit for {message_link}"
            )
            return

        self._logger.info(f"[Edit message]: {message_link}")

        for outgoing_message in outgoing_messages:
            config = self._chat_mapping.get(chat_id, {}).get(
                outgoing_message.mirror_channel
            )

            if config is None:
                self._logger.warning(
                    f"[Edit message]: No direction config for "
                    f"{chat_id}->{outgoing_message.mirror_channel}"
                )
                continue

            if config.disable_edit is True:
                continue

            proceed, filtered_message = await config.filters.process(
                message, events.MessageEdited.Event
            )
            if proceed is False:
                self._logger.info(
                    f"[Edit message]: Message {message_link} was skipped "
                    f"by the filter for chat#{outgoing_message.mirror_channel}"
                )
                continue

            try:
                await self._client.edit_message(
                    entity=outgoing_message.mirror_channel,
                    message=outgoing_message.mirror_id,
                    text=filtered_message.message,
                    formatting_entities=filtered_message.entities,
                    file=filtered_message.media,
                    link_preview=isinstance(
                        filtered_message.media, types.MessageMediaWebPage
                    ),
                )
            except errors.MessageNotModifiedError:
                self._logger.warning(
                    f"Suppressed MessageNotModifiedError for message "
                    f"{outgoing_message.mirror_channel}#{outgoing_message.mirror_id}"
                )

            except Exception as e:
                self._logger.error(
                    f"Error while editing message "
                    f"{outgoing_message.mirror_channel}#{outgoing_message.mirror_id}. "
                    f"{type(e).__name__}: {e}"
                )

    @__handle_exceptions
    async def delete_message(
        self: "EventProcessor", chat_id: int, message_ids: List[int]
    ) -> None:
        deleting_messages = await self._database.get_messages_batch(
            message_ids, chat_id
        )
        if not deleting_messages:
            self._logger.warning(
                f"[Delete message]: No target messages to delete " f"for chat#{chat_id}"
            )
            return

        self._logger.info(
            f"[Delete message]: Delete {len(message_ids)} " f"messages from {chat_id}"
        )

        delete_per_channel: Dict[int, List[int]] = {}

        for deleting_message in deleting_messages:
            config = self._chat_mapping.get(chat_id, {}).get(
                deleting_message.mirror_channel
            )

            if config is None:
                self._logger.warning(
                    f"[Delete message]: No direction config for "
                    f"{chat_id}->{deleting_message.mirror_channel}"
                )
                continue

            if config.disable_delete is True:
                continue

            delete_per_channel.setdefault(deleting_message.mirror_channel, []).append(
                deleting_message.mirror_id
            )

        for channel_id, message_list in delete_per_channel.items():
            try:
                await self._client.delete_messages(
                    entity=channel_id, message_ids=message_list
                )
            except Exception as e:
                self._logger.error(
                    f"Error while deleting messages from chat#{channel_id}. "
                    f"{type(e).__name__}: {e}"
                )

        await self._database.delete_messages_batch(message_ids, chat_id)


class EventHandlers:
    def __init__(
        self: "EventHandlers",
        client: TelegramClient,
        chats: List[int],
        processor: EventProcessor,
    ) -> None:
        """Message event handler

        Args:
            client (`TelegramClient`): Message receiver client
            chats (`List[int]`): List of chats to be observed
            processor (`EventProcessor`): Event processor
        """
        client.add_event_handler(self.on_new_message, events.NewMessage(chats=chats))
        client.add_event_handler(self.on_album, events.Album(chats=chats))
        client.add_event_handler(
            self.on_edit_message, events.MessageEdited(chats=chats)
        )
        client.add_event_handler(
            self.on_deleted_message, events.MessageDeleted(chats=chats)
        )
        self._processor = processor

    def event_message_link(self: "EventHandlers", event: EventLike) -> str:
        """Get link to event message"""

        if isinstance(event, (events.NewMessage.Event, events.MessageEdited.Event)):
            incoming_message_id: int = event.message.id
        elif isinstance(event, events.Album.Event):
            incoming_message_id: int = event.messages[0].id
        elif isinstance(event, events.MessageDeleted.Event):
            incoming_message_id: int = event.deleted_id

        return (
            f"https://t.me/c/{utils.resolve_id(event.chat_id)[0]}/{incoming_message_id}"
        )

    async def on_new_message(
        self: "EventHandlers", event: events.NewMessage.Event
    ) -> None:
        """NewMessage event handler"""

        # Skip albums
        if hasattr(event, "grouped_id") and event.grouped_id is not None:
            return

        incoming_chat_id: int = event.chat_id
        incoming_message: EventMessage = event.message
        incoming_message_link: str = self.event_message_link(event)

        await self._processor.new_message(
            chat_id=incoming_chat_id,
            message=incoming_message,
            message_link=incoming_message_link,
        )

    async def on_album(self: "EventHandlers", event: events.Album.Event) -> None:
        """Album event handler"""

        incoming_chat_id: int = event.chat_id
        incoming_album: EventAlbumMessage = event.messages
        incoming_album_link: str = self.event_message_link(event)

        await self._processor.new_album(
            chat_id=incoming_chat_id,
            album=incoming_album,
            album_link=incoming_album_link,
        )

    async def on_edit_message(
        self: "EventHandlers", event: events.MessageEdited.Event
    ) -> None:
        """MessageEdited event handler"""

        # Skip updates with edit_hide attribute (reactions and so on...)
        if event.message.edit_hide is True:
            return

        incoming_chat_id: int = event.chat_id
        incoming_message: EventMessage = event.message
        incoming_message_link: str = self.event_message_link(event)

        await self._processor.edit_message(
            chat_id=incoming_chat_id,
            message=incoming_message,
            message_link=incoming_message_link,
        )

    async def on_deleted_message(
        self: "EventHandlers", event: events.MessageDeleted.Event
    ) -> None:
        """MessageDeleted event handler"""

        incoming_chat_id: int = event.chat_id
        deleted_ids: List[int] = event.deleted_ids

        await self._processor.delete_message(
            chat_id=incoming_chat_id, message_ids=deleted_ids
        )


class Mirroring:
    def __init__(
        self: "Mirroring",
        chat_mapping: Dict[int, Dict[int, DirectionConfig]],
        database: Database,
        receiver: TelegramClient,
        sender: TelegramClient,
        logger: Union[str, logging.Logger] = None,
    ) -> None:
        """Configure channels mirroring

        Args:
            chat_mapping (`Dict[int, Dict[int, DirectionConfig]]`): Chats mappings
            database (`Database`): Message IDs storage
            receiver (`TelegramClient`): Message receiver client
            sender (`TelegramClient`): Message sender client, can be same as `receiver`
            logger (`str` | `logging.Logger`, optional): Logger. Defaults to None.
        """
        self._chat_mapping = chat_mapping
        self._database = database
        self._receiver = receiver
        self._sender = sender

        # Increase album hack delay
        events.album._HACK_DELAY = 1.01

        self._handlers = EventHandlers(
            client=receiver,
            chats=list(chat_mapping.keys()),
            processor=EventProcessor(
                chat_mapping=chat_mapping,
                database=database,
                client=sender,
                logger=logger,
            ),
        )

        self._logger = logger

    async def run(self: "Mirroring") -> None:
        self._logger.info(f"Channels mirroring config:\n{self.stringify_config()}")

        if self._sender != self._receiver:
            raise RuntimeError("Different clients are not supported now")

        await self.__connect_client(self._sender)

    def stringify_config(self: "Mirroring") -> str:
        """Stringify mirror config"""
        mirror_mapping = "\n".join(
            [
                f'{f} -> {", ".join(map(lambda x: f"{x} [{to[x]}]", to))}'
                for (f, to) in self._chat_mapping.items()
            ]
        )

        return (
            f"Mirror mapping: \n{ mirror_mapping }\n"
            f"Using database: { self._database }\n"
        )

    async def __connect_client(self: "Mirroring", client: TelegramClient) -> None:
        try:
            if not client.is_connected():
                await client.connect()

            me = await client.get_me()
            if me is None:
                raise RuntimeError(
                    "There is no authorization for the user, "
                    "try restart or get a new session key (run login.py)"
                )

            self._logger.info(f"Logged in as {utils.get_display_name(me)} ({me.phone})")

            await client.run_until_disconnected()
        except (errors.UserDeactivatedBanError, errors.UserDeactivatedError):
            self._logger.critical(
                "Account banned/deactivated by Telegram. See https://github.com/lonamiwebs/telethon/issues/824"
            )
        except errors.PhoneNumberBannedError:
            self._logger.critical(
                "Phone number banned/deactivated by Telegram. See https://github.com/lonamiwebs/telethon/issues/824"
            )
        except (errors.SessionExpiredError, errors.SessionRevokedError):
            self._logger.critical(
                "The user's session has expired, try to get a new session key (run login.py)"
            )
        finally:
            await client.disconnect()


class Telemirror:
    def __init__(
        self: "Telemirror",
        api_id: str,
        api_hash: str,
        session_string: str,
        chat_mapping: Dict[int, Dict[int, DirectionConfig]],
        database: Database,
        logger: Union[str, logging.Logger] = None,
    ):
        """Telemirror

        Args:
            api_id (`str`): Telegram API id
            api_hash (`str`): Telegram API hash
            session_string (`str`): Telegram (telethon) session string
            chat_mapping (`Dict[int, Dict[int, DirectionConfig]]`): Chats mappings
            database (`Database`): Message IDs storage
            logger (`str` | `logging.Logger`, optional): Logger. Defaults to None.
        """
        # Preparation for splitting receiver and sender
        recv_client = send_client = TelegramClient(
            StringSession(session_string), api_id, api_hash
        )
        # Set up default parse mode as markdown
        recv_client.parse_mode = send_client.parse_mode = "markdown"

        if isinstance(logger, str):
            logger = logging.getLogger(logger)
        elif not isinstance(logger, logging.Logger):
            logger = logging.getLogger(__name__)

        self._logger = logger

        self._mirroring = Mirroring(
            chat_mapping=chat_mapping,
            database=database,
            receiver=recv_client,
            sender=send_client,
            logger=logger,
        )

    async def run(self: "Telemirror") -> None:
        """Start channels mirroring"""
        await self._mirroring.run()

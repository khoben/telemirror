from typing import Type

from ..hints import EventLike, EventMessage
from .base import FilterResult, MessageFilter


class RestrictSavingContentBypassFilter(MessageFilter):
    """Filter that bypasses `saving content restriction`

    Sample implementation:

    Download the media (note that the file may be large),
    upload it to the Telegram servers,
    and then change the origin media to the new uploaded media

    ```
    # If here is media and noforwards enabled
    if message.chat.noforwards and message.media:
        # Handle images
        if isinstance(message.media, types.MessageMediaPhoto):
            client: TelegramClient = message.client
            photo: bytes = await client.download_media(message=message, file=bytes)
            cloned_photo: types.TypeInputFile = await client.upload_file(photo)
            message.media = cloned_photo
        # Others media types set to None (remove from original message)...
        else:
            message.media = None

    return FilterResult(FilterAction.CONTINUE, message)
    ```
    """

    @property
    def restricted_content_allowed(self) -> bool:
        return True

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> FilterResult[EventMessage]:
        raise NotImplementedError

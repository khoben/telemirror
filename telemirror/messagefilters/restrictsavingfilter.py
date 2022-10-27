from typing import Tuple

from ..hints import EventMessage
from .base import MessageFilter


class RestrictSavingContentBypassFilter(MessageFilter):
    """Filter that bypasses `saving content restriction`

    Sample implementation:
    Download the media, upload it to the Telegram servers,
    and then change to the new uploaded media:

    ```
    if not message.media or not message.chat.noforwards:
        return message

    # Handle photos
    if isinstance(message.media, types.MessageMediaPhoto):
        client: TelegramClient = message.client
        photo: bytes = client.download_media(message=message, file=bytes)
        cloned_photo: types.TypeInputFile = client.upload_file(photo)
        message.media = cloned_photo

    # Others types...

    return message

    ```
    """

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        raise NotImplementedError

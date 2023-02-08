from typing import Tuple

from ..hints import EventMessage
from .base import MessageFilter


class RestrictSavingContentBypassFilter(MessageFilter):
    """Filter that bypasses `saving content restriction`

    Sample implementation:

    Download the media, upload it to the Telegram servers,
    and then change to the new uploaded media

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
    
    return True, message
    ```
    """

    @property
    def restricted_content_allowed(self) -> bool:
        """Indicates that restricted content is allowed or not to process"""
        return True

    async def process(self, message: EventMessage) -> Tuple[bool, EventMessage]:
        raise NotImplementedError

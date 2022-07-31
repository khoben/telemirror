from typing import Union
from telethon import events, types, custom

EventLike = Union[
    events.NewMessage.Event,
    events.MessageEdited.Event,
    events.Album.Event,
    events.MessageDeleted.Event
]

MessageLike = Union[types.Message, custom.Message]
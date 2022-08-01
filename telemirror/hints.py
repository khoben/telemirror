from typing import Union
from telethon import events, custom

EventLike = Union[
    events.NewMessage.Event,
    events.MessageEdited.Event,
    events.Album.Event,
    events.MessageDeleted.Event
]

MessageLike = custom.Message
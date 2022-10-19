from typing import Union
from telethon import events, tl

EventLike = Union[
    events.NewMessage.Event,
    events.MessageEdited.Event,
    events.Album.Event,
    events.MessageDeleted.Event
]

EventMessage = tl.patched.Message
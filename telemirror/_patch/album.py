def set_album_event_timeout(delay_sec: float):
    """Update [AlbumEvent] item timeout"""
    from telethon.events import album

    album._HACK_DELAY = delay_sec
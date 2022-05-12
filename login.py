"""
Prints telegram session string key
"""
from config import API_HASH, API_ID
from telemirror.mirroring import MirrorTelegramClient

with MirrorTelegramClient(api_id=API_ID, api_hash=API_HASH) as client:
    client.print_session_string()

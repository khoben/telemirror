from os import environ
from dotenv import load_dotenv

load_dotenv()

def str2bool(string_value):
    """Converts string representation of boolean to boolean value

    Args:
        string_value (str): String representation of boolean

    Returns:
        bool: True or False
    """
    return string_value.lower() == 'true'

# telegram app id
API_ID = environ.get('API_ID')
# telegram app hash
API_HASH = environ.get('API_HASH')

# better to use channels id
# but names also works too
CHATS = []
CHATS_DATA = environ.get('CHATS')
if CHATS_DATA is not None:
    CHATS = [int(chat) if chat[0] == '-' else chat for chat in CHATS_DATA.split(',')]

# auth session string: can be obtain by run login.py
SESSION_STRING = environ.get('SESSION_STRING')

# target channel for posting
TARGET_CHAT = environ.get('TARGET_CHAT')
if TARGET_CHAT is not None and TARGET_CHAT[0] == '-':
    TARGET_CHAT = int(TARGET_CHAT)

# remove urls from messages
REMOVE_URLS = str2bool(environ.get('REMOVE_URLS', 'False'))
REMOVE_URLS_WL = environ.get('REMOVE_URLS_WL')
REMOVE_URLS_WL_DATA = None
if REMOVE_URLS_WL is not None:
    REMOVE_URLS_WL_DATA = REMOVE_URLS_WL.split(',')

# postgres credentials
# connection string
DB_URL = environ.get('DATABASE_URL')
# or postgres credentials
DB_NAME = environ.get("DB_NAME")
DB_USER = environ.get("DB_USER")
DB_PASS = environ.get("DB_PASS")
DB_HOST = environ.get("DB_HOST")
# if connection string wasnt set then build it from credentials
if DB_URL is None:
    DB_URL = f"postgres://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

LOG_LEVEL = environ.get("LOG_LEVEL", "INFO").upper()

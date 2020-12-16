import re
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

# channels id to mirroring
CHATS = []

# channels mapping
# [source:target1,target2];[source2:...]
CM = environ.get('CHAT_MAPPING')
CHANNEL_MAPPING = {}
if CM is not None:
    matches = re.findall(
        r'\[?((?:-100\d+,?)+):((?:-100\d+,?)+)\]?', CM, re.MULTILINE)
    for match in matches:
        sources = [int(val) for val in match[0].split(',')]
        targets = [int(val) for val in match[1].split(',')]
        for source in sources:
            CHANNEL_MAPPING.setdefault(source, []).extend(targets)
    CHATS = list(CHANNEL_MAPPING.keys())

TIMEOUT_MIRRORING = float(environ.get('TIMEOUT_MIRRORING', '0.1'))
# amount messages before timeout
LIMIT_TO_WAIT = 50
# auth session string: can be obtain by run login.py
SESSION_STRING = environ.get('SESSION_STRING')

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

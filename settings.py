from os import environ
from dotenv import load_dotenv

load_dotenv()

# telegram app id
API_ID = environ['API_ID']
# telegram app hash
API_HASH = environ['API_HASH']

# better to use channels id
# but names also works too
CHATS = []
CHATS_DATA = environ.get('CHATS')
if CHATS_DATA is not None:
    CHATS.extend([i for i in CHATS_DATA.split(',') if i[0] == '@'])
    CHATS.extend([int(i) for i in CHATS_DATA.split(',') if i[0] == '-'])


# auth session string: can be obtain by run login.py
SESSION_STRING = environ['SESSION_STRING']

# target channel for posting
TARGET_CHAT = environ['TARGET_CHAT']


DB_URL = environ.get('DATABASE_URL', None)

# postgres credentials
DB_NAME = environ["DB_NAME"]
DB_USER = environ["DB_USER"]
DB_PASS = environ["DB_PASS"]
DB_HOST = environ["DB_HOST"]

# if already not setted
if DB_URL is None:
    DB_URL = f"postgres://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

from os import environ
from dotenv import load_dotenv

load_dotenv()

# telegram app id
API_ID = environ['API_ID']
# telegram app hash
API_HASH = environ['API_HASH']

# better to use channels id
# but names also works too
CHATS = (
    -1001104714255,  # @bestovduringreklama
    -1001458049012,  # @ggg111222333
    -1001253406503,  # @realbestov
)

# auth session string: can be obtain by run login.py
SESSION_STRING = environ['SESSION_STRING']

# target channel for posting
TARGET_CHAT = environ['TARGET_CHAT']

# postgres credentials
DB_NAME = environ["DB_NAME"]
DB_USER = environ["DB_USER"]
DB_PASS = environ["DB_PASS"]
DB_HOST = environ["DB_HOST"]

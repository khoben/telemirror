from os import environ
from dotenv import load_dotenv

load_dotenv()

API_ID = environ['API_ID']
API_HASH = environ['API_HASH']

CHATS = (
    '@fromzero_to_hero',
    '@ggg111222333'
)

SESSION_STRING = environ['SESSION_STRING']

TARGET_CHAT = environ['TARGET_CHAT']

# difference between ids in original channel and mirror
OFFSET = int(environ['OFFSET_MESSAGE'])

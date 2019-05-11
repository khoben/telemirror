from os import environ

API_ID = environ['API_ID']
API_HASH = environ['API_HASH']

CHATS = (
    '@fromzero_to_hero',
    '@ggg111222333'
)

SESSION_STRING = environ['SESSION_STRING']

TARGET_CHAT = '@plus400k'

# difference between ids in original channel and mirror
OFFSET = int(environ['OFFSET_MESSAGE'])

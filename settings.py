from os import environ
from dotenv import load_dotenv

load_dotenv()

API_ID = environ['API_ID']
API_HASH = environ['API_HASH']

CHATS = (
    -1001104714255, # @bestovduringreklama
    -1001458049012, # @ggg111222333
    -1001253406503, # @realbestov

)

SESSION_STRING = environ['SESSION_STRING']

TARGET_CHAT = environ['TARGET_CHAT']

# difference between ids in original channel and mirror
# OFFSET = int(environ['OFFSET_MESSAGE'])

DB_NAME = environ["DB_NAME"]
DB_USER = environ["DB_USER"]
DB_PASS = environ["DB_PASS"]
DB_HOST = environ["DB_HOST"]

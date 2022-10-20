# Telegram forwarder from channels (make channel mirrors) via Telegram Client API (telethon)

Forwards from channels with comments (with linked chat) to target channel with linked chat

User should join to source chat with comments (linked chat)

## Env variables

```bash
# Telegram app ID
API_ID=test
# Telegram app hash
API_HASH=test
# Telegram session string (telethon session, see login.py in root directory)
SESSION_STRING=test
# Source chats. Use channel linked chat id to comment cloning
SOURCE_CHATS=-1001,-1002,-1003,-1004
# Target channel with linked chat (comments enabled). Example: -100target1
TARGET_CHANNEL=-1005
# Enable keywords replacing (true or false). Defaults to true
KEYWORD_REPLACE_ENABLE=true
# Comma-separated list keywords to replace. Example: cat:dog,one:two
KEYWORD_REPLACE_MAP=cat:dog,one:two
# Enable bottom link to original post (true or false). Defaults to true
BOTTOM_LINK_ENABLE=true
# Bottom link display name. Defaults to Link
BOTTOM_LINK_DISPLAY_NAME=Link
# Disable mirror message deleting (true or false). Defaults to false
DISABLE_DELETE=false
# Disable mirror message editing (true or false). Defaults to false
DISABLE_EDIT=false
# Use an in-memory database instead of Postgres DB (true or false). Defaults to false
USE_MEMORY_DB=false
# Logging level (debug, info, warning, error or critical). Defaults to info
LOG_LEVEL=info
```

## Deploy

### Host on Heroku:

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/khoben/telemirror/tree/custom/madlifer)
# Telegram forwarder from channels (make channel mirrors) via Telegram Client API (telethon)

To comments cloning user should join to channel and linked group with comments

## Env variables

```bash
# Telegram app ID
API_ID=test
# Telegram app hash
API_HASH=test
# Telegram session string (telethon session, see login.py in root directory)
SESSION_STRING=test
# Chat mapping: [(source_id|source_title|linked_chat_id),...:(target_id|linked_chat_id)]
# 'linked_chat_id' is optional, 'source_title' must be enclosed in double quotes
CHAT_MAPPING=[(-1000000001|"Good channel"|-1000000002):(-1000000003|-1000000004),(-1000000005)];[(-1000000006|"Good channel"|-1000000007):(-1000000008|-1000000009)];
# Disable comment cloning. Defaults to false
DISABLE_COMMENT_CLONE=false
# Comma-separated list keywords to replace. Leave empty to disable. Example: cat:dog,one:two
KEYWORD_REPLACE_MAP=cat:dog,one:two
# Comma-separated list words to stop forwarding. Leave empty to disable. Example: stop,word
KEYWORD_DO_NOT_FORWARD_MAP=stop,word
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
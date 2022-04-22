# Mirroring/forwarding Telegram channel messages app via Telegram Client API (telethon)

### Functionality
1. Catching *NewMessage* and *MessageEdited* event
2. Auto forward messages as copy
3. Flexible source and target channels mapping

### Be careful with forwards from channels with [`restrict saving content`](https://telegram.org/blog/protected-content-delete-by-date-and-more) enabled, this can lead to an account ban.

## Prepare
1. [Create Telegram App](https://my.telegram.org/apps)
2. Obtain API App ID and hash
![Telegram API Credentials](/images/telegramapp.png)
3. Setup Postgres database
4. Fill [.env-example](.env-example) with your data and rename it to .env 
    1. SESSION_STRING can be obtained by running [login.py](login.py) with putted API_ID and API_HASH before.

```bash
API_ID=test # Telegram app ID
API_HASH=test # Telegram app hash
SESSION_STRING=test # Telegram session string
# Mapping between source and target channels
# Channel id can be fetched by using @messageinformationsbot telegram bot
# and it always starts with -100 prefix
# [id1, id2, id3:id4] means send messages from id1, id2, id3 to id4
# id5:id6 means send messages from id5 to id6
# [id1, id2, id3:id4];[id5:id6] semicolon means AND
CHAT_MAPPING=[-100999999,-100999999,-100999999:-1009999999];
TIMEOUT_MIRRORING=0.1 # Delay in sec between sending or editing messages
REMOVE_URLS=false   # Apply removing URLs on messages
# Remove URLs whitelist
REMOVE_URLS_WL=youtube.com,youtu.be,vk.com,twitch.tv,instagram.com
# Postgres credentials
DATABASE_URL=postgres://user:pass@host/dbname
# or
DB_NAME=test
DB_USER=test
DB_HOST=test
DB_PASS=test
# Using in-memory database like dictionary instead of Postgres DB (true or false). Default is false
USE_MEMORY_DB=false
LOG_LEVEL=INFO
```

## Deploy

### Host on Heroku:
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/khoben/telemirror)

or

1. Clone project
```
    git clone https://github.com/khoben/telemirror.git
```
2. Create new heroku app within Heroku CLI
```
    heroku create {your app name}
```
3. Add heroku remote
```
    heroku git:remote -a {your app name}
```
4. Set environment variables to your heroku app from .env by running .bash script
```
    ./.bash
```

5. Upload on heroku host
```
    git push heroku master
```

6. Start heroku app
```
    heroku ps:scale run=1
```

### On your PC:
1. Create and activate python virtual environment
```bash
python -m venv myvenv
source myvenv/Scripts/activate # linux
myvenv/Scripts/activate # windows
```
2. Install depencies
```bash
pip install -r requirements.txt
```
3. Run
```bash
python app/telemirror.py
```
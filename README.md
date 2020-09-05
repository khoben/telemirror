# Telegram channel mirroring app 

App helps mirroring newly created post from Telegram channels. We will use Telegram client API because Bot API have limited functionality. 

## Prepare
1. [Create Telegram App](https://my.telegram.org/apps)
2. Obtain API App ID and hash
![GitHub Logo](/images/telegramapp.png)
3. Setup Postgres database
4. Fill [.env-example](.env-example) with your data and rename it to .env 
    1. SESSION_STRING can be obtained by running [login.py](login.py) with putted API_ID and API_HASH before.

```bash
API_ID=test # Telegram app ID
API_HASH=test # Telegram app hash
SESSION_STRING=test # Telegram session string
TARGET_CHAT=test    # Target chat to post 
# Postgres credentials
DATABASE_URL=postgres://user:pass@host/dbname
# or
DB_NAME=test
DB_USER=test
DB_HOST=test
DB_PASS=test
```
5. Setup channel sources in .env file (CHATS)
```bash
# use channel id more stable
# it can be fetched by using @messageinformationsbot telegram bot
# channels id always starts with -100 prefix
CHATS=-1001104714255,-1001458049012,-1001253406503
# but also names usable too
CHATS=@test1,@test2,@test3
```

## Deploy
### Locally
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
python telemirror.py
```

## Heroku
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/khoben/telemirror)

or

1. Clone project
```
    git clone git@github.com:khoben/telemirror.git
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
from telethon import TelegramClient, events, utils, functions
from settings import API_HASH, API_ID, TARGET_CHAT, CHATS, SESSION_STRING
from telethon.sessions import StringSession

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)


@client.on(events.NewMessage(chats=CHATS))
async def handler_new_message(event):
    try:
        print('LOG: NEW MESSAGE.')
        print(event.message)
        await client.send_message(TARGET_CHAT, event.message)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    client.start()
    client.run_until_disconnected()

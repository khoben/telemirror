from telethon import events, utils, functions
from telethon.sync import TelegramClient
from settings import API_HASH, API_ID, TARGET_CHAT, CHATS, SESSION_STRING, OFFSET
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


@client.on(events.MessageEdited(chats=('@ggg111222333')))
async def handler_edit_message(event):
    try:
        print('LOG. EDIT MESSAGE')
        print(event.message)
        id_message_to_edit = event.message.id + OFFSET
        result = client(functions.channels.GetMessagesRequest(
            channel='@ggg111222333',
            id=[id_message_to_edit]
        ))
        print(result)
        message_to_edit = result.messages
        await client.edit_message(message_to_edit, event.message)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    client.start()
    client.run_until_disconnected()

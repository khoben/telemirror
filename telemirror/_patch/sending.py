"""
Adds repling in topics
"""

import itertools
import typing
import warnings

from telethon import TelegramClient, functions, hints, types, utils


async def send_message(
    client: "TelegramClient",
    entity: "hints.EntityLike",
    message: "hints.MessageLike" = "",
    *,
    reply_to: "typing.Union[int, types.Message]" = None,
    reply_to_topic_id: "typing.Optional[int]" = None,
    attributes: "typing.Sequence[types.TypeDocumentAttribute]" = None,
    parse_mode: typing.Optional[str] = (),
    formatting_entities: typing.Optional[typing.List[types.TypeMessageEntity]] = None,
    link_preview: bool = True,
    file: "typing.Union[hints.FileLike, typing.Sequence[hints.FileLike]]" = None,
    thumb: "hints.FileLike" = None,
    force_document: bool = False,
    clear_draft: bool = False,
    buttons: typing.Optional["hints.MarkupLike"] = None,
    silent: bool = None,
    background: bool = None,
    supports_streaming: bool = False,
    schedule: "hints.DateLike" = None,
    comment_to: "typing.Union[int, types.Message]" = None,
    nosound_video: bool = None,
) -> "types.Message":
    """
    Sends a message to the specified user, chat or channel.

    The default parse mode is the same as the official applications
    (a custom flavour of markdown). ``**bold**, `code` or __italic__``
    are available. In addition you can send ``[links](https://example.com)``
    and ``[mentions](@username)`` (or using IDs like in the Bot API:
    ``[mention](tg://user?id=123456789)``) and ``pre`` blocks with three
    backticks.

    Sending a ``/start`` command with a parameter (like ``?start=data``)
    is also done through this method. Simply send ``'/start data'`` to
    the bot.

    See also `Message.respond() <telethon.tl.custom.message.Message.respond>`
    and `Message.reply() <telethon.tl.custom.message.Message.reply>`.

    Arguments
        entity (`entity`):
            To who will it be sent.

        message (`str` | `Message <telethon.tl.custom.message.Message>`):
            The message to be sent, or another message object to resend.

            The maximum length for a message is 35,000 bytes or 4,096
            characters. Longer messages will not be sliced automatically,
            and you should slice them manually if the text to send is
            longer than said length.

        reply_to (`int` | `Message <telethon.tl.custom.message.Message>`, optional):
            Whether to reply to a message or not. If an integer is provided,
            it should be the ID of the message that it should reply to.

        reply_to_topic_id (`int`, optional):
            Reply to topic with ID

        attributes (`list`, optional):
            Optional attributes that override the inferred ones, like
            :tl:`DocumentAttributeFilename` and so on.

        parse_mode (`object`, optional):
            See the `TelegramClient.parse_mode
            <telethon.client.messageparse.MessageParseMethods.parse_mode>`
            property for allowed values. Markdown parsing will be used by
            default.

        formatting_entities (`list`, optional):
            A list of message formatting entities. When provided, the ``parse_mode`` is ignored.

        link_preview (`bool`, optional):
            Should the link preview be shown?

        file (`file`, optional):
            Sends a message with a file attached (e.g. a photo,
            video, audio or document). The ``message`` may be empty.

        thumb (`str` | `bytes` | `file`, optional):
            Optional JPEG thumbnail (for documents). **Telegram will
            ignore this parameter** unless you pass a ``.jpg`` file!
            The file must also be small in dimensions and in disk size.
            Successful thumbnails were files below 20kB and 320x320px.
            Width/height and dimensions/size ratios may be important.
            For Telegram to accept a thumbnail, you must provide the
            dimensions of the underlying media through ``attributes=``
            with :tl:`DocumentAttributesVideo` or by installing the
            optional ``hachoir`` dependency.

        force_document (`bool`, optional):
            Whether to send the given file as a document or not.

        clear_draft (`bool`, optional):
            Whether the existing draft should be cleared or not.

        buttons (`list`, `custom.Button <telethon.tl.custom.button.Button>`, :tl:`KeyboardButton`):
            The matrix (list of lists), row list or button to be shown
            after sending the message. This parameter will only work if
            you have signed in as a bot. You can also pass your own
            :tl:`ReplyMarkup` here.

            All the following limits apply together:

            * There can be 100 buttons at most (any more are ignored).
            * There can be 8 buttons per row at most (more are ignored).
            * The maximum callback data per button is 64 bytes.
            * The maximum data that can be embedded in total is just
              over 4KB, shared between inline callback data and text.

        silent (`bool`, optional):
            Whether the message should notify people in a broadcast
            channel or not. Defaults to `False`, which means it will
            notify them. Set it to `True` to alter this behaviour.

        background (`bool`, optional):
            Whether the message should be send in background.

        supports_streaming (`bool`, optional):
            Whether the sent video supports streaming or not. Note that
            Telegram only recognizes as streamable some formats like MP4,
            and others like AVI or MKV will not work. You should convert
            these to MP4 before sending if you want them to be streamable.
            Unsupported formats will result in ``VideoContentTypeError``.

        schedule (`hints.DateLike`, optional):
            If set, the message won't send immediately, and instead
            it will be scheduled to be automatically sent at a later
            time.

        comment_to (`int` | `Message <telethon.tl.custom.message.Message>`, optional):
            Similar to ``reply_to``, but replies in the linked group of a
            broadcast channel instead (effectively leaving a "comment to"
            the specified message).

            This parameter takes precedence over ``reply_to``. If there is
            no linked chat, `telethon.errors.sgIdInvalidError` is raised.

        nosound_video (`bool`, optional):
            Only applicable when sending a video file without an audio
            track. If set to ``True``, the video will be displayed in
            Telegram as a video. If set to ``False``, Telegram will attempt
            to display the video as an animated gif. (It may still display
            as a video due to other factors.) The value is ignored if set
            on non-video files. This is set to ``True`` for albums, as gifs
            cannot be sent in albums.

    Returns
        The sent `custom.Message <telethon.tl.custom.message.Message>`.

    Example
        .. code-block:: python

            # Markdown is the default
            await client.send_message('me', 'Hello **world**!')

            # Default to another parse mode
            client.parse_mode = 'html'

            await client.send_message('me', 'Some <b>bold</b> and <i>italic</i> text')
            await client.send_message('me', 'An <a href="https://example.com">URL</a>')
            # code and pre tags also work, but those break the documentation :)
            await client.send_message('me', '<a href="tg://user?id=me">Mentions</a>')

            # Explicit parse mode
            # No parse mode by default
            client.parse_mode = None

            # ...but here I want markdown
            await client.send_message('me', 'Hello, **world**!', parse_mode='md')

            # ...and here I need HTML
            await client.send_message('me', 'Hello, <i>world</i>!', parse_mode='html')

            # If you logged in as a bot account, you can send buttons
            from telethon import events, Button

            @client.on(events.CallbackQuery)
            async def callback(event):
                await event.edit('Thank you for clicking {}!'.format(event.data))

            # Single inline button
            await client.send_message(chat, 'A single button, with "clk1" as data',
                                      buttons=Button.inline('Click me', b'clk1'))

            # Matrix of inline buttons
            await client.send_message(chat, 'Pick one from this grid', buttons=[
                [Button.inline('Left'), Button.inline('Right')],
                [Button.url('Check this site!', 'https://example.com')]
            ])

            # Reply keyboard
            await client.send_message(chat, 'Welcome', buttons=[
                Button.text('Thanks!', resize=True, single_use=True),
                Button.request_phone('Send phone'),
                Button.request_location('Send location')
            ])

            # Forcing replies or clearing buttons.
            await client.send_message(chat, 'Reply to me', buttons=Button.force_reply())
            await client.send_message(chat, 'Bye Keyboard!', buttons=Button.clear())

            # Scheduling a message to be sent after 5 minutes
            from datetime import timedelta
            await client.send_message(chat, 'Hi, future!', schedule=timedelta(minutes=5))
    """
    if file is not None:
        return await send_file(
            client,
            entity,
            file,
            caption=message,
            reply_to=reply_to,
            reply_to_topic_id=reply_to_topic_id,
            attributes=attributes,
            parse_mode=parse_mode,
            force_document=force_document,
            thumb=thumb,
            buttons=buttons,
            clear_draft=clear_draft,
            silent=silent,
            schedule=schedule,
            supports_streaming=supports_streaming,
            formatting_entities=formatting_entities,
            comment_to=comment_to,
            background=background,
            nosound_video=nosound_video,
        )

    entity = await client.get_input_entity(entity)
    if comment_to is not None:
        entity, reply_to = await client._get_comment_data(entity, comment_to)
    else:
        reply_to = utils.get_message_id(reply_to)

    if isinstance(message, types.Message):
        if buttons is None:
            markup = message.reply_markup
        else:
            markup = client.build_reply_markup(buttons)

        if silent is None:
            silent = message.silent

        if message.media and not isinstance(message.media, types.MessageMediaWebPage):
            return await send_file(
                client,
                entity,
                message.media,
                caption=message.message,
                silent=silent,
                background=background,
                reply_to=reply_to,
                reply_to_topic_id=reply_to_topic_id,
                buttons=markup,
                formatting_entities=message.entities,
                parse_mode=None,  # explicitly disable parse_mode to force using even empty formatting_entities
                schedule=schedule,
            )

        request = functions.messages.SendMessageRequest(
            peer=entity,
            message=message.message or "",
            silent=silent,
            background=background,
            reply_to=None
            if reply_to is None
            else types.InputReplyToMessage(reply_to, reply_to_topic_id),
            reply_markup=markup,
            entities=message.entities,
            clear_draft=clear_draft,
            no_webpage=not isinstance(message.media, types.MessageMediaWebPage),
            schedule_date=schedule,
        )
        message = message.message
    else:
        if formatting_entities is None:
            message, formatting_entities = await client._parse_message_text(
                message, parse_mode
            )
        if not message:
            raise ValueError("The message cannot be empty unless a file is provided")

        request = functions.messages.SendMessageRequest(
            peer=entity,
            message=message,
            entities=formatting_entities,
            no_webpage=not link_preview,
            reply_to=None
            if reply_to is None
            else types.InputReplyToMessage(reply_to, reply_to_topic_id),
            clear_draft=clear_draft,
            silent=silent,
            background=background,
            reply_markup=client.build_reply_markup(buttons),
            schedule_date=schedule,
        )

    result = await client(request)
    if isinstance(result, types.UpdateShortSentMessage):
        message = types.Message(
            id=result.id,
            peer_id=await client._get_peer(entity),
            message=message,
            date=result.date,
            out=result.out,
            media=result.media,
            entities=result.entities,
            reply_markup=request.reply_markup,
            ttl_period=result.ttl_period,
            reply_to=request.reply_to,
        )
        message._finish_init(client, {}, entity)
        return message

    return client._get_response_message(request, result, entity)


async def forward_messages(
    client: "TelegramClient",
    entity: "hints.EntityLike",
    messages: "typing.Union[hints.MessageIDLike, typing.Sequence[hints.MessageIDLike]]",
    from_peer: "hints.EntityLike" = None,
    *,
    background: bool = None,
    with_my_score: bool = None,
    silent: bool = None,
    as_album: bool = None,
    schedule: "hints.DateLike" = None,
    reply_to_topic_id: "typing.Optional[int]" = None,
) -> "typing.Sequence[types.Message]":
    """
    Forwards the given messages to the specified entity.

    If you want to "forward" a message without the forward header
    (the "forwarded from" text), you should use `send_message` with
    the original message instead. This will send a copy of it.

    See also `Message.forward_to() <telethon.tl.custom.message.Message.forward_to>`.

    Arguments
        entity (`entity`):
            To which entity the message(s) will be forwarded.

        messages (`list` | `int` | `Message <telethon.tl.custom.message.Message>`):
            The message(s) to forward, or their integer IDs.

        from_peer (`entity`):
            If the given messages are integer IDs and not instances
            of the ``Message`` class, this *must* be specified in
            order for the forward to work. This parameter indicates
            the entity from which the messages should be forwarded.

        silent (`bool`, optional):
            Whether the message should notify people with sound or not.
            Defaults to `False` (send with a notification sound unless
            the person has the chat muted). Set it to `True` to alter
            this behaviour.

        background (`bool`, optional):
            Whether the message should be forwarded in background.

        with_my_score (`bool`, optional):
            Whether forwarded should contain your game score.

        as_album (`bool`, optional):
            This flag no longer has any effect.

        schedule (`hints.DateLike`, optional):
            If set, the message(s) won't forward immediately, and
            instead they will be scheduled to be automatically sent
            at a later time.

        reply_to_topic_id (`int`, optional):
            Reply to topic with ID


    Returns
        The list of forwarded `Message <telethon.tl.custom.message.Message>`,
        or a single one if a list wasn't provided as input.

        Note that if all messages are invalid (i.e. deleted) the call
        will fail with ``MessageIdInvalidError``. If only some are
        invalid, the list will have `None` instead of those messages.

    Example
        .. code-block:: python

            # a single one
            await client.forward_messages(chat, message)
            # or
            await client.forward_messages(chat, message_id, from_chat)
            # or
            await message.forward_to(chat)

            # multiple
            await client.forward_messages(chat, messages)
            # or
            await client.forward_messages(chat, message_ids, from_chat)

            # Forwarding as a copy
            await client.send_message(chat, message)
    """
    if as_album is not None:
        warnings.warn(
            "the as_album argument is deprecated and no longer has any effect"
        )

    single = not utils.is_list_like(messages)
    if single:
        messages = (messages,)

    entity = await client.get_input_entity(entity)

    if from_peer:
        from_peer = await client.get_input_entity(from_peer)
        from_peer_id = await client.get_peer_id(from_peer)
    else:
        from_peer_id = None

    def get_key(m):
        if isinstance(m, int):
            if from_peer_id is not None:
                return from_peer_id

            raise ValueError("from_peer must be given if integer IDs are used")
        elif isinstance(m, types.Message):
            return m.chat_id
        else:
            raise TypeError("Cannot forward messages of type {}".format(type(m)))

    sent = []
    for _chat_id, chunk in itertools.groupby(messages, key=get_key):
        chunk = list(chunk)
        if isinstance(chunk[0], int):
            chat = from_peer
        else:
            chat = from_peer or await client.get_input_entity(chunk[0].peer_id)
            chunk = [m.id for m in chunk]

        req = functions.messages.ForwardMessagesRequest(
            from_peer=chat,
            id=chunk,
            to_peer=entity,
            silent=silent,
            background=background,
            with_my_score=with_my_score,
            top_msg_id=reply_to_topic_id,
            schedule_date=schedule,
        )
        result = await client(req)
        sent.extend(client._get_response_message(req, result, entity))

    return sent[0] if single else sent


async def send_file(
    client: "TelegramClient",
    entity: "hints.EntityLike",
    file: "typing.Union[hints.FileLike, typing.Sequence[hints.FileLike]]",
    *,
    caption: typing.Union[str, typing.Sequence[str]] = None,
    force_document: bool = False,
    file_size: int = None,
    clear_draft: bool = False,
    progress_callback: "hints.ProgressCallback" = None,
    reply_to: "hints.MessageIDLike" = None,
    reply_to_topic_id: "typing.Optional[int]" = None,
    attributes: "typing.Sequence[types.TypeDocumentAttribute]" = None,
    thumb: "hints.FileLike" = None,
    allow_cache: bool = True,
    parse_mode: str = (),
    formatting_entities: typing.Optional[typing.List[types.TypeMessageEntity]] = None,
    voice_note: bool = False,
    video_note: bool = False,
    buttons: typing.Optional["hints.MarkupLike"] = None,
    silent: bool = None,
    background: bool = None,
    supports_streaming: bool = False,
    schedule: "hints.DateLike" = None,
    comment_to: "typing.Union[int, types.Message]" = None,
    ttl: int = None,
    nosound_video: bool = None,
    **kwargs,
) -> "types.Message":
    """
    Sends message with the given file to the specified entity.

    .. note::

        If the ``hachoir3`` package (``hachoir`` module) is installed,
        it will be used to determine metadata from audio and video files.

        If the ``pillow`` package is installed and you are sending a photo,
        it will be resized to fit within the maximum dimensions allowed
        by Telegram to avoid ``errors.PhotoInvalidDimensionsError``. This
        cannot be done if you are sending :tl:`InputFile`, however.

    Arguments
        entity (`entity`):
            Who will receive the file.

        file (`str` | `bytes` | `file` | `media`):
            The file to send, which can be one of:

            * A local file path to an in-disk file. The file name
              will be the path's base name.

            * A `bytes` byte array with the file's data to send
              (for example, by using ``text.encode('utf-8')``).
              A default file name will be used.

            * A bytes `io.IOBase` stream over the file to send
              (for example, by using ``open(file, 'rb')``).
              Its ``.name`` property will be used for the file name,
              or a default if it doesn't have one.

            * An external URL to a file over the internet. This will
              send the file as "external" media, and Telegram is the
              one that will fetch the media and send it.

            * A Bot API-like ``file_id``. You can convert previously
              sent media to file IDs for later reusing with
              `telethon.utils.pack_bot_file_id`.

            * A handle to an existing file (for example, if you sent a
              message with media before, you can use its ``message.media``
              as a file here).

            * A handle to an uploaded file (from `upload_file`).

            * A :tl:`InputMedia` instance. For example, if you want to
              send a dice use :tl:`InputMediaDice`, or if you want to
              send a contact use :tl:`InputMediaContact`.

            To send an album, you should provide a list in this parameter.

            If a list or similar is provided, the files in it will be
            sent as an album in the order in which they appear, sliced
            in chunks of 10 if more than 10 are given.

        caption (`str`, optional):
            Optional caption for the sent media message. When sending an
            album, the caption may be a list of strings, which will be
            assigned to the files pairwise.

        force_document (`bool`, optional):
            If left to `False` and the file is a path that ends with
            the extension of an image file or a video file, it will be
            sent as such. Otherwise always as a document.

        file_size (`int`, optional):
            The size of the file to be uploaded if it needs to be uploaded,
            which will be determined automatically if not specified.

            If the file size can't be determined beforehand, the entire
            file will be read in-memory to find out how large it is.

        clear_draft (`bool`, optional):
            Whether the existing draft should be cleared or not.

        progress_callback (`callable`, optional):
            A callback function accepting two parameters:
            ``(sent bytes, total)``.

        reply_to (`int` | `Message <telethon.tl.custom.message.Message>`):
            Same as `reply_to` from `send_message`.

        reply_to_topic_id (`int`, optional):
            Reply to topic with ID

        attributes (`list`, optional):
            Optional attributes that override the inferred ones, like
            :tl:`DocumentAttributeFilename` and so on.

        thumb (`str` | `bytes` | `file`, optional):
            Optional JPEG thumbnail (for documents). **Telegram will
            ignore this parameter** unless you pass a ``.jpg`` file!

            The file must also be small in dimensions and in disk size.
            Successful thumbnails were files below 20kB and 320x320px.
            Width/height and dimensions/size ratios may be important.
            For Telegram to accept a thumbnail, you must provide the
            dimensions of the underlying media through ``attributes=``
            with :tl:`DocumentAttributesVideo` or by installing the
            optional ``hachoir`` dependency.


        allow_cache (`bool`, optional):
            This parameter currently does nothing, but is kept for
            backward-compatibility (and it may get its use back in
            the future).

        parse_mode (`object`, optional):
            See the `TelegramClient.parse_mode
            <telethon.client.messageparse.MessageParseMethods.parse_mode>`
            property for allowed values. Markdown parsing will be used by
            default.

        formatting_entities (`list`, optional):
            A list of message formatting entities. When provided, the ``parse_mode`` is ignored.

        voice_note (`bool`, optional):
            If `True` the audio will be sent as a voice note.

        video_note (`bool`, optional):
            If `True` the video will be sent as a video note,
            also known as a round video message.

        buttons (`list`, `custom.Button <telethon.tl.custom.button.Button>`, :tl:`KeyboardButton`):
            The matrix (list of lists), row list or button to be shown
            after sending the message. This parameter will only work if
            you have signed in as a bot. You can also pass your own
            :tl:`ReplyMarkup` here.

        silent (`bool`, optional):
            Whether the message should notify people with sound or not.
            Defaults to `False` (send with a notification sound unless
            the person has the chat muted). Set it to `True` to alter
            this behaviour.

        background (`bool`, optional):
            Whether the message should be send in background.

        supports_streaming (`bool`, optional):
            Whether the sent video supports streaming or not. Note that
            Telegram only recognizes as streamable some formats like MP4,
            and others like AVI or MKV will not work. You should convert
            these to MP4 before sending if you want them to be streamable.
            Unsupported formats will result in ``VideoContentTypeError``.

        schedule (`hints.DateLike`, optional):
            If set, the file won't send immediately, and instead
            it will be scheduled to be automatically sent at a later
            time.

        comment_to (`int` | `Message <telethon.tl.custom.message.Message>`, optional):
            Similar to ``reply_to``, but replies in the linked group of a
            broadcast channel instead (effectively leaving a "comment to"
            the specified message).

            This parameter takes precedence over ``reply_to``. If there is
            no linked chat, `telethon.errors.sgIdInvalidError` is raised.

        ttl (`int`. optional):
            The Time-To-Live of the file (also known as "self-destruct timer"
            or "self-destructing media"). If set, files can only be viewed for
            a short period of time before they disappear from the message
            history automatically.

            The value must be at least 1 second, and at most 60 seconds,
            otherwise Telegram will ignore this parameter.

            Not all types of media can be used with this parameter, such
            as text documents, which will fail with ``TtlMediaInvalidError``.

        nosound_video (`bool`, optional):
            Only applicable when sending a video file without an audio
            track. If set to ``True``, the video will be displayed in
            Telegram as a video. If set to ``False``, Telegram will attempt
            to display the video as an animated gif. (It may still display
            as a video due to other factors.) The value is ignored if set
            on non-video files. This is set to ``True`` for albums, as gifs
            cannot be sent in albums.

    Returns
        The `Message <telethon.tl.custom.message.Message>` (or messages)
        containing the sent file, or messages if a list of them was passed.

    Example
        .. code-block:: python

            # Normal files like photos
            await client.send_file(chat, '/my/photos/me.jpg', caption="It's me!")
            # or
            await client.send_message(chat, "It's me!", file='/my/photos/me.jpg')

            # Voice notes or round videos
            await client.send_file(chat, '/my/songs/song.mp3', voice_note=True)
            await client.send_file(chat, '/my/videos/video.mp4', video_note=True)

            # Custom thumbnails
            await client.send_file(chat, '/my/documents/doc.txt', thumb='photo.jpg')

            # Only documents
            await client.send_file(chat, '/my/photos/photo.png', force_document=True)

            # Albums
            await client.send_file(chat, [
                '/my/photos/holiday1.jpg',
                '/my/photos/holiday2.jpg',
                '/my/drawings/portrait.png'
            ])

            # Printing upload progress
            def callback(current, total):
                print('Uploaded', current, 'out of', total,
                      'bytes: {:.2%}'.format(current / total))

            await client.send_file(chat, file, progress_callback=callback)

            # Dices, including dart and other future emoji
            from telethon.tl import types
            await client.send_file(chat, types.InputMediaDice(''))
            await client.send_file(chat, types.InputMediaDice('🎯'))

            # Contacts
            await client.send_file(chat, types.InputMediaContact(
                phone_number='+34 123 456 789',
                first_name='Example',
                last_name='',
                vcard=''
            ))
    """
    # TODO Properly implement allow_cache to reuse the sha256 of the file
    # i.e. `None` was used
    if not file:
        raise TypeError("Cannot use {!r} as file".format(file))

    if not caption:
        caption = ""

    entity = await client.get_input_entity(entity)
    if comment_to is not None:
        entity, reply_to = await client._get_comment_data(entity, comment_to)
    else:
        reply_to = utils.get_message_id(reply_to)

    # First check if the user passed an iterable, in which case
    # we may want to send grouped.
    if utils.is_list_like(file):
        sent_count = 0
        used_callback = (
            None
            if not progress_callback
            else (lambda s, t: progress_callback(sent_count + s, len(file)))
        )

        if utils.is_list_like(caption):
            captions = caption
        else:
            captions = [caption]

        result = []
        while file:
            result += await _send_album(
                client,
                entity,
                file[:10],
                caption=captions[:10],
                progress_callback=used_callback,
                reply_to=reply_to,
                reply_to_topic_id=reply_to_topic_id,
                parse_mode=parse_mode,
                silent=silent,
                schedule=schedule,
                supports_streaming=supports_streaming,
                clear_draft=clear_draft,
                force_document=force_document,
                background=background,
            )
            file = file[10:]
            captions = captions[10:]
            sent_count += 10

        return result

    if formatting_entities is not None:
        msg_entities = formatting_entities
    else:
        caption, msg_entities = await client._parse_message_text(caption, parse_mode)

    file_handle, media, image = await client._file_to_media(
        file,
        force_document=force_document,
        file_size=file_size,
        progress_callback=progress_callback,
        attributes=attributes,
        allow_cache=allow_cache,
        thumb=thumb,
        voice_note=voice_note,
        video_note=video_note,
        supports_streaming=supports_streaming,
        ttl=ttl,
        nosound_video=nosound_video,
    )

    # e.g. invalid cast from :tl:`MessageMediaWebPage`
    if not media:
        raise TypeError("Cannot use {!r} as file".format(file))

    markup = client.build_reply_markup(buttons)
    reply_to = (
        None
        if reply_to is None
        else types.InputReplyToMessage(reply_to, reply_to_topic_id)
    )
    request = functions.messages.SendMediaRequest(
        entity,
        media,
        reply_to=reply_to,
        message=caption,
        entities=msg_entities,
        reply_markup=markup,
        silent=silent,
        schedule_date=schedule,
        clear_draft=clear_draft,
        background=background,
    )
    return client._get_response_message(request, await client(request), entity)


async def _send_album(
    client: "TelegramClient",
    entity,
    files,
    caption="",
    progress_callback=None,
    reply_to=None,
    reply_to_topic_id=None,
    parse_mode=(),
    silent=None,
    schedule=None,
    supports_streaming=None,
    clear_draft=None,
    force_document=False,
    background=None,
    ttl=None,
):
    """Specialized version of .send_file for albums"""
    # We don't care if the user wants to avoid cache, we will use it
    # anyway. Why? The cached version will be exactly the same thing
    # we need to produce right now to send albums (uploadMedia), and
    # cache only makes a difference for documents where the user may
    # want the attributes used on them to change.
    #
    # In theory documents can be sent inside the albums but they appear
    # as different messages (not inside the album), and the logic to set
    # the attributes/avoid cache is already written in .send_file().
    entity = await client.get_input_entity(entity)
    if not utils.is_list_like(caption):
        caption = (caption,)

    captions = []
    for c in reversed(caption):  # Pop from the end (so reverse)
        captions.append(await client._parse_message_text(c or "", parse_mode))

    reply_to = utils.get_message_id(reply_to)

    used_callback = (
        None
        if not progress_callback
        # use an integer when sent matches total, to easily determine a file has been fully sent
        else (
            lambda s, t: progress_callback(
                sent_count + 1 if s == t else sent_count + s / t, len(files)
            )
        )
    )

    # Need to upload the media first, but only if they're not cached yet
    media = []
    for sent_count, file in enumerate(files):
        # Albums want :tl:`InputMedia` which, in theory, includes
        # :tl:`InputMediaUploadedPhoto`. However, using that will
        # make it `raise MediaInvalidError`, so we need to upload
        # it as media and then convert that to :tl:`InputMediaPhoto`.
        fh, fm, _ = await client._file_to_media(
            file,
            supports_streaming=supports_streaming,
            force_document=force_document,
            ttl=ttl,
            progress_callback=used_callback,
            nosound_video=True,
        )
        if isinstance(
            fm, (types.InputMediaUploadedPhoto, types.InputMediaPhotoExternal)
        ):
            r = await client(functions.messages.UploadMediaRequest(entity, media=fm))

            fm = utils.get_input_media(r.photo)
        elif isinstance(fm, types.InputMediaUploadedDocument):
            r = await client(functions.messages.UploadMediaRequest(entity, media=fm))

            fm = utils.get_input_media(
                r.document, supports_streaming=supports_streaming
            )

        if captions:
            caption, msg_entities = captions.pop()
        else:
            caption, msg_entities = "", None
        media.append(
            types.InputSingleMedia(
                fm,
                message=caption,
                entities=msg_entities,
                # random_id is autogenerated
            )
        )

    # Now we can construct the multi-media request
    request = functions.messages.SendMultiMediaRequest(
        entity,
        reply_to=None
        if reply_to is None
        else types.InputReplyToMessage(reply_to, reply_to_topic_id),
        multi_media=media,
        silent=silent,
        schedule_date=schedule,
        clear_draft=clear_draft,
        background=background,
    )
    result = await client(request)

    random_ids = [m.random_id for m in media]
    return client._get_response_message(random_ids, result, entity)

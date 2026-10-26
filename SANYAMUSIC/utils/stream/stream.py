# -----------------------------------------------
# 🔸 Friday Music Project
# 🔹 Developed & Maintained by: Stark (https://github.com/urstark)
# 📅 Copyright © 2022 – All Rights Reserved
#
# 📖 License:
# This source code is open for educational and non-commercial use ONLY.
# You are required to retain this credit in all copies or substantial portions of this file.
# Commercial use, redistribution, or removal of this notice is strictly prohibited
# without prior written permission from the author.
#
# ❤️ Made with dedication and love by urstark
# -----------------------------------------------
import os
import asyncio
from random import randint
from typing import Union
from pyrogram.types import InlineKeyboardMarkup, InputMediaPhoto
import config
from config import lyrical
from SANYAMUSIC import Carbon, YouTube, app, LOGGER
from SANYAMUSIC.core.call import SANYA
from SANYAMUSIC.misc import db
from SANYAMUSIC.utils.database import add_active_video_chat, is_active_chat
from SANYAMUSIC.utils.exceptions import AssistantErr
from SANYAMUSIC.utils.inline import aq_markup, close_markup, stream_markup
from SANYAMUSIC.utils.pastebin import SANYABin
from SANYAMUSIC.utils.stream.queue import put_queue, put_queue_index
from SANYAMUSIC.utils.formatters import time_to_seconds
from SANYAMUSIC.utils.thumbnails import get_thumb


# Lock to handle concurrent play commands in the same chat
chat_locks = {}


async def stream(
    client,
    _,
    mystic,
    user_id,
    result,
    chat_id,
    user_name,
    original_chat_id,
    video: Union[bool, str] = None,
    streamtype: Union[bool, str] = None,
    spotify: Union[bool, str] = None,
    forceplay: Union[bool, str] = None,
):
    if not result:
        return
    
    # Ensure sequential processing for this chat to avoid race conditions
    if chat_id not in chat_locks:
        chat_locks[chat_id] = asyncio.Lock()
    
    async with chat_locks[chat_id]:
        mention = f"[{user_name}](tg://user?id={user_id})"
        run = None
        if forceplay:
            await SANYA.force_stop_stream(chat_id)
        if streamtype == "playlist":
            msg = f"{_['play_19']}\n\n"
            count = 0
            for search in result:
                if int(count) == config.PLAYLIST_FETCH_LIMIT:
                    continue
                try:
                    (
                        title,
                        duration_min,
                        duration_sec,
                        thumbnail,
                        vidid,
                    ) = await YouTube.details(search, False if spotify else True)
                except:
                    continue
                if str(duration_min) == "None":
                    continue
                if duration_sec > config.DURATION_LIMIT:
                    continue
                if await is_active_chat(chat_id) and not forceplay:
                    await put_queue(
                        chat_id,
                        original_chat_id,
                        f"vid_{vidid}",
                        title,
                        duration_min,
                        user_name,
                        vidid,
                        user_id,
                        "video" if video else "audio",
                    )
                    position = len(db.get(chat_id)) - 1
                    count += 1
                    msg += f"{count}. {title[:70]}\n"
                    msg += f"{_['play_20']} {position}\n\n"
                else:
                    if not forceplay:
                        db[chat_id] = []
                    status = True if video else False
                    n = None
                    file_path = None
                    direct = False
                    try:
                        duration_sec = time_to_seconds(duration_min)
                    except:
                        duration_sec = 0

                    try:
                        try:
                            await mystic.edit_text(_["play_downloading"])
                        except:
                            pass
                        
                        n, file_path = await YouTube.stream(
                            vidid, videoid=True, video=status
                        )
                        if n != 0 and file_path:
                            direct = True
                        else:
                            file_path, direct_download = await YouTube.download(
                                vidid, mystic, videoid=True, video=status
                            )
                            if not file_path:
                                raise AssistantErr(_["play_14"])
                            direct = False
                        count += 1
                        msg += f"{count}. {title[:70]} [Now Playing]\n\n"
                    except Exception as e:
                        if not any(err in str(e).upper() for err in ["MESSAGE_NOT_MODIFIED", "MESSAGE_ID_INVALID"]):
                             LOGGER(__name__).error(f"Playback generation failed for {vidid}: {e}")
                             raise AssistantErr(_["play_14"])
                    await SANYA.join_call(
                        chat_id,
                        original_chat_id,
                        file_path,
                        video=status,
                        image=thumbnail,
                    )
                    await put_queue(
                        chat_id,
                        original_chat_id,
                        file_path if direct else f"vid_{vidid}",
                        title,
                        duration_min,
                        user_name,
                        vidid,
                        user_id,
                        "video" if video else "audio",
                        forceplay=forceplay,
                    )
                    img = await get_thumb(vidid)
                    button = stream_markup(_, chat_id)
                    try:
                        await mystic.delete()
                    except:
                        pass
                    run = await client.send_photo(
                        original_chat_id,
                        photo=img,
                        has_spoiler=True,
                        caption=_["stream_1"].format(
                            f"https://t.me/{client.me.username}?start=info_{vidid}",
                            title[:23],
                            duration_min,
                            mention,
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                    if db.get(chat_id) and len(db[chat_id]) > 0:
                        db[chat_id][0]["mystic"] = run
                        db[chat_id][0]["markup"] = "stream"
            if count == 0:
                return
            else:
                link = await SANYABin(msg)
                lines = msg.count("\n")
                if lines >= 17:
                    car = os.linesep.join(msg.split(os.linesep)[:17])
                else:
                    car = msg
                carbon = await Carbon.generate(car, randint(100, 10000000))
                upl = close_markup(_)
                try:
                    return await client.send_photo(
                        original_chat_id,
                        photo=carbon,
                        caption=_["play_21"].format(position, link),
                        reply_markup=upl,
                    )
                except:
                    return await client.send_message(
                        original_chat_id,
                        text=_["play_21"].format(position, link),
                        reply_markup=upl,
                    )
        elif streamtype == "youtube":
            link = result["link"]
            vidid = result["vidid"]
            title = (result["title"]).title()
            duration_min = result["duration_min"]
            thumbnail = result["thumb"]
            status = True if video else False
            n = None
            file_path = None
            direct = False
            try:
                duration_sec = time_to_seconds(duration_min)
            except:
                duration_sec = 0

            try:
                try:
                    await mystic.edit_text(_["play_downloading"])
                except:
                    pass
                
                    n, file_path = await YouTube.stream(
                        vidid, videoid=True, video=status
                    )
                    if n != 0 and file_path:
                        direct = True
                    else:
                        file_path, direct_download = await YouTube.download(
                            vidid, mystic, videoid=True, video=status
                        )
                        if not file_path:
                            raise AssistantErr(_["play_14"])
                        direct = False
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e):
                    LOGGER(__name__).error(f"Playback generation failed for {vidid}: {e}")
                    raise AssistantErr(_["play_14"])
            if await is_active_chat(chat_id) and not forceplay:
                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path if direct else f"vid_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                )
                position = len(db.get(chat_id)) - 1
                
                import random, string
                play_now_hash = "".join(random.choices(string.ascii_uppercase + string.digits, k=15))
                lyrical[play_now_hash] = {"streamtype": "youtube", "result": result, "video": video}
                button = aq_markup(_, chat_id, play_now_hash, user_id, "v" if video else "a", "c" if chat_id != original_chat_id else "g")
                run = await mystic.edit_text(
                    text=_["queue_4"].format(position, title[:27], duration_min, mention),
                    reply_markup=InlineKeyboardMarkup(button),
                )
            else:
                if not forceplay:
                    db[chat_id] = []
                await SANYA.join_call(
                    chat_id,
                    original_chat_id,
                    file_path,
                    video=status,
                    image=thumbnail,
                )
                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path if direct else f"vid_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                    forceplay=forceplay,
                )
                img = await get_thumb(vidid)
                button = stream_markup(_, chat_id)
                if mystic.photo:
                    run = await mystic.edit_media(
                        media=InputMediaPhoto(
                            img,
                            has_spoiler=True,
                            caption=_["stream_1"].format(
                                f"https://t.me/{client.me.username}?start=info_{vidid}",
                                title[:23],
                                duration_min,
                                mention,
                            )
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                else:
                    try:
                        run = await mystic.edit_media(
                            media=InputMediaPhoto(
                                img,
                                has_spoiler=True,
                                caption=_["stream_1"].format(
                                    f"https://t.me/{client.me.username}?start=info_{vidid}",
                                    title[:23],
                                    duration_min,
                                    mention,
                                )
                            ),
                            reply_markup=InlineKeyboardMarkup(button),
                        )
                    except:
                        try:
                            await mystic.delete()
                        except:
                            pass
                        run = await client.send_photo(
                            original_chat_id,
                            photo=img,
                            has_spoiler=True,
                            caption=_["stream_1"].format(
                                f"https://t.me/{client.me.username}?start=info_{vidid}",
                                title[:23],
                                duration_min,
                                mention,
                            ),
                            reply_markup=InlineKeyboardMarkup(button),
                        )
                if db.get(chat_id) and len(db[chat_id]) > 0:
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "stream"
        elif streamtype == "soundcloud":
            file_path = result["filepath"]
            title = result["title"]
            duration_min = result["duration_min"]
            if await is_active_chat(chat_id) and not forceplay:
                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path,
                    title,
                    duration_min,
                    user_name,
                    streamtype,
                    user_id,
                    "audio",
                )
                position = len(db.get(chat_id)) - 1
                
                import random, string
                play_now_hash = "".join(random.choices(string.ascii_uppercase + string.digits, k=15))
                lyrical[play_now_hash] = {"streamtype": "soundcloud", "result": result, "video": video}
                button = aq_markup(_, chat_id, play_now_hash, user_id, "v" if video else "a", "c" if chat_id != original_chat_id else "g")
                run = await mystic.edit_text(
                    text=_["queue_4"].format(position, title[:27], duration_min, mention),
                    reply_markup=InlineKeyboardMarkup(button),
                )
            else:
                if not forceplay:
                    db[chat_id] = []
                await SANYA.join_call(chat_id, original_chat_id, file_path, video=None)
                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path,
                    title,
                    duration_min,
                    user_name,
                    streamtype,
                    user_id,
                    "audio",
                    forceplay=forceplay,
                )
                button = stream_markup(_, chat_id)
                img = config.SOUNCLOUD_IMG_URL
                try:
                    run = await mystic.edit_media(
                        media=InputMediaPhoto(
                            img,
                            has_spoiler=True,
                            caption=_["stream_1"].format(
                                config.SUPPORT_CHAT, title[:23], duration_min, mention
                            )
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                except:
                    try:
                        await mystic.delete()
                    except:
                        pass
                    run = await client.send_photo(
                        original_chat_id,
                        photo=img,
                        has_spoiler=True,
                        caption=_["stream_1"].format(
                            config.SUPPORT_CHAT, title[:23], duration_min, mention
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                if db.get(chat_id) and len(db[chat_id]) > 0:
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"
        elif streamtype == "telegram":
            file_path = result["path"]
            link = result["link"]
            title = (result["title"]).title()
            duration_min = result["dur"]
            status = True if video else None
            if await is_active_chat(chat_id) and not forceplay:
                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path,
                    title,
                    duration_min,
                    user_name,
                    streamtype,
                    user_id,
                    "video" if video else "audio",
                )
                position = len(db.get(chat_id)) - 1
                
                import random, string
                play_now_hash = "".join(random.choices(string.ascii_uppercase + string.digits, k=15))
                lyrical[play_now_hash] = {"streamtype": "telegram", "result": result, "video": video}
                button = aq_markup(_, chat_id, play_now_hash, user_id, "v" if video else "a", "c" if chat_id != original_chat_id else "g")
                run = await mystic.edit_text(
                    text=_["queue_4"].format(position, title[:27], duration_min, mention),
                    reply_markup=InlineKeyboardMarkup(button),
                )
            else:
                if not forceplay:
                    db[chat_id] = []
                await SANYA.join_call(chat_id, original_chat_id, file_path, video=status)
                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path,
                    title,
                    duration_min,
                    user_name,
                    streamtype,
                    user_id,
                    "video" if video else "audio",
                    forceplay=forceplay,
                )
                if video:
                    await add_active_video_chat(chat_id)
                button = stream_markup(_, chat_id)
                img = config.TELEGRAM_VIDEO_URL if video else config.TELEGRAM_AUDIO_URL
                try:
                    run = await mystic.edit_media(
                        media=InputMediaPhoto(
                            img,
                            has_spoiler=True,
                            caption=_["stream_1"].format(link, title[:23], duration_min, mention)
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                except:
                    try:
                        await mystic.delete()
                    except:
                        pass
                    run = await client.send_photo(
                        original_chat_id,
                        photo=img,
                        has_spoiler=True,
                        caption=_["stream_1"].format(link, title[:23], duration_min, mention),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                if db.get(chat_id) and len(db[chat_id]) > 0:
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"
        elif streamtype == "live":
            link = result["link"]
            vidid = result["vidid"]
            title = (result["title"]).title()
            thumbnail = result["thumb"]
            duration_min = "Live Track"
            status = True if video else None
            if await is_active_chat(chat_id) and not forceplay:
                await put_queue(
                    chat_id,
                    original_chat_id,
                    f"live_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                )
                position = len(db.get(chat_id)) - 1
                
                import random, string
                play_now_hash = "".join(random.choices(string.ascii_uppercase + string.digits, k=15))
                lyrical[play_now_hash] = {"streamtype": "live", "result": result, "video": video}
                button = aq_markup(_, chat_id, play_now_hash, user_id, "v" if video else "a", "c" if chat_id != original_chat_id else "g")
                run = await mystic.edit_text(
                    text=_["queue_4"].format(position, title[:27], duration_min, mention),
                    reply_markup=InlineKeyboardMarkup(button),
                )
            else:
                if not forceplay:
                    db[chat_id] = []
                n, file_path = await YouTube.video(link)
                if n == 0:
                    raise AssistantErr(_["str_3"])
                await SANYA.join_call(
                    chat_id,
                    original_chat_id,
                    file_path,
                    video=status,
                    image=thumbnail if thumbnail else None,
                )
                await put_queue(
                    chat_id,
                    original_chat_id,
                    f"live_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                    forceplay=forceplay,
                )
                img = await get_thumb(vidid)
                button = stream_markup(_, chat_id)
                try:
                    run = await mystic.edit_media(
                        media=InputMediaPhoto(
                            img,
                            has_spoiler=True,
                            caption=_["stream_1"].format(
                                f"https://t.me/{client.me.username}?start=info_{vidid}",
                                title[:23],
                                duration_min,
                                mention,
                            )
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                except:
                    try:
                        await mystic.delete()
                    except:
                        pass
                    run = await client.send_photo(
                        original_chat_id,
                        photo=img,
                        has_spoiler=True,
                        caption=_["stream_1"].format(
                            f"https://t.me/{client.me.username}?start=info_{vidid}",
                            title[:23],
                            duration_min,
                            mention,
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                if db.get(chat_id) and len(db[chat_id]) > 0:
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"
        elif streamtype == "index":
            link = result
            title = "ɪɴᴅᴇx ᴏʀ ᴍ3ᴜ8 ʟɪɴᴋ"
            duration_min = "00:00"
            if await is_active_chat(chat_id) and not forceplay:
                await put_queue_index(
                    chat_id,
                    original_chat_id,
                    "index_url",
                    title,
                    duration_min,
                    user_name,
                    link,
                    user_id,
                    "video" if video else "audio",
                )
                position = len(db.get(chat_id)) - 1
                
                import random, string
                play_now_hash = "".join(random.choices(string.ascii_uppercase + string.digits, k=15))
                lyrical[play_now_hash] = {"streamtype": "index", "result": result, "video": video}
                button = aq_markup(_, chat_id, play_now_hash, user_id, "v" if video else "a", "c" if chat_id != original_chat_id else "g")
                await mystic.edit_text(
                    text=_["queue_4"].format(position, title[:27], duration_min, mention),
                    reply_markup=InlineKeyboardMarkup(button),
                )
            else:
                if not forceplay:
                    db[chat_id] = []
                await SANYA.join_call(
                    chat_id,
                    original_chat_id,
                    link,
                    video=True if video else None,
                )
                await put_queue_index(
                    chat_id,
                    original_chat_id,
                    "index_url",
                    title,
                    duration_min,
                    user_name,
                    link,
                    user_id,
                    "video" if video else "audio",
                    forceplay=forceplay,
                )
                button = stream_markup(_, chat_id)
                img = config.STREAM_IMG_URL
                try:
                    run = await mystic.edit_media(
                        media=InputMediaPhoto(
                            img,
                            has_spoiler=True,
                            caption=_["stream_2"].format(mention)
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                except:
                    try:
                        await mystic.delete()
                    except:
                        pass
                    run = await client.send_photo(
                        original_chat_id,
                        photo=img,
                        has_spoiler=True,
                        caption=_["stream_2"].format(mention),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                if db.get(chat_id) and len(db[chat_id]) > 0:
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"

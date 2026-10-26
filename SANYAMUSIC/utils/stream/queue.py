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
import asyncio
import time
from typing import Union
from SANYAMUSIC.misc import db
from SANYAMUSIC.utils.formatters import check_duration, seconds_to_min
from config import autoclean, time_to_seconds

async def put_queue(
    chat_id,
    original_chat_id,
    file,
    title,
    duration,
    user,
    vidid,
    user_id,
    stream,
    forceplay: Union[bool, str] = None,
):
    title = title.title()
    try:
        duration_in_seconds = time_to_seconds(duration) - 3
    except:
        duration_in_seconds = 0
    put = {
        "title": title,
        "dur": duration,
        "streamtype": stream,
        "by": user,
        "user_id": user_id,
        "chat_id": original_chat_id,
        "file": file,
        "vidid": vidid,
        "seconds": duration_in_seconds,
        "played": 0,
        "start_time": time.time(),
    }
    if forceplay:
        check = db.get(chat_id)
        if check:
            check.insert(0, put)
        else:
            db[chat_id] = []
            db[chat_id].append(put)
    else:
        db[chat_id].append(put)
    autoclean.append(file)
    asyncio.create_task(prefetch_next_track(chat_id))


async def put_queue_index(
    chat_id,
    original_chat_id,
    file,
    title,
    duration,
    user,
    vidid,
    user_id,
    stream,
    forceplay: Union[bool, str] = None,
):
    dur = 0
    duration = "ᴜʀʟ sᴛʀᴇᴀᴍ"
    put = {
        "title": title,
        "dur": duration,
        "streamtype": stream,
        "by": user,
        "user_id": user_id,
        "chat_id": original_chat_id,
        "file": file,
        "vidid": vidid,
        "seconds": dur,
        "played": 0,
        "start_time": time.time(),
    }
    if forceplay:
        check = db.get(chat_id)
        if check:
            check.insert(0, put)
        else:
            db[chat_id] = []
            db[chat_id].append(put)
    else:
        db[chat_id].append(put)
    asyncio.create_task(prefetch_next_track(chat_id))


async def prefetch_next_track(chat_id):
    from SANYAMUSIC import YouTube, LOGGER
    check = db.get(chat_id)
    if check and len(check) > 1:
        next_track = check[1]
        file_field = next_track.get("file", "")
        vidid = next_track.get("vidid")
        streamtype = next_track.get("streamtype", "")
        if isinstance(file_field, str) and "vid_" in file_field and vidid:
            try:
                # Eagerly fetch and cache details/stream URL in Redis & memory
                await YouTube.details(vidid, videoid=True)
                video = True if str(streamtype) == "video" else False
                await YouTube.stream(vidid, videoid=True, video=video)
                LOGGER(__name__).info(f"Prefetched metadata and stream URL for next track: {vidid}")
            except Exception as e:
                LOGGER(__name__).debug(f"Prefetch failed for next track {vidid}: {e}")


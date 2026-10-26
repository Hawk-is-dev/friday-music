

import os
import re
from pyrogram import filters
from pyrogram.enums import ChatAction
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAudio,
    InputMediaVideo,
    Message,
)

class InlineKeyboardBuilder(list):
    def row(self, *buttons):
        self.append(list(buttons))

from SANYAMUSIC import app, YouTube
from config import (
    BANNED_USERS,
    SONG_DOWNLOAD_DURATION,
    SONG_DOWNLOAD_DURATION_LIMIT,
)
from SANYAMUSIC.utils.database import get_cmode
from SANYAMUSIC.utils.decorators.language import language, languageCB
from SANYAMUSIC.utils.errors import capture_err, capture_callback_err
from SANYAMUSIC.utils.formatters import convert_bytes, time_to_seconds
from SANYAMUSIC.utils.inline.song import song_markup
from SANYAMUSIC.utils.security import is_safe_input

from SANYAMUSIC.utils.stream.stream import stream

SONG_COMMAND = ["song", "find", "vfind", "video"]

@app.on_message(filters.command(SONG_COMMAND) & ~BANNED_USERS)
@capture_err
@language
async def song_command(client, message: Message, lang):
    if not await is_safe_input(message):
        return await message.reply_text("⚠️ <b>Sᴇᴄᴜʀɪᴛʏ Aʟᴇʀᴛ:</b> Yᴏᴜʀ ɪɴᴘᴜᴛ ᴄᴏɴᴛᴀɪɴs ғᴏʀʙɪᴅᴅᴇɴ ᴄʜᴀʀᴀᴄᴛᴇʀs.")
    
    url = await YouTube.url(message)
    query = url or (message.text.split(None, 1)[1] if len(message.command) > 1 else None)
    
    if not query:
        # User Guide
        guide_text = (
             "**💡 Friday Music - Finder Guide**\n\n"
             "Download any media directly in this chat!\n\n"
             "**Audio Commands:**\n"
             "» `/song <name/link>`\n"
             "» `/find <name/link>`\n\n"
             "**Video Commands:**\n"
             "» `/video <name/link>`\n"
             "» `/vfind <name/link>`\n\n"
             "**Example:** `/song sahiba`"
        )
        return await message.reply_text(guide_text, quote=True)

    # Determine if user wants video
    is_video = any(c in message.command[0] for c in ["video", "vfind", "vsong"])
    
    # Status Message
    mystic = await message.reply_text("Searching...", quote=True)
    
    try:
        details, vidid = await YouTube.track(query)
        if not details:
            return await mystic.edit_text("Play result not found.")
            
        title = details["title"]
        dur_min = details["duration_min"]
        thumb = details["thumb"]
        yturl = details["link"]

        # Limit Duration
        dur_sec = time_to_seconds(dur_min)
        if dur_sec > SONG_DOWNLOAD_DURATION_LIMIT:
             return await mystic.edit_text(lang["play_4"].format(SONG_DOWNLOAD_DURATION, dur_min))

        await mystic.edit_text("Downloading...")
        
        file_path, _ = await YouTube.download(
            vidid, 
            mystic, 
            video=is_video, 
            songaudio=not is_video, 
            songvideo=is_video, 
            title=re.sub(r"\W+", " ", title)
        )
        
        if not file_path:
             return await mystic.edit_text(lang["song_10"])

        await mystic.edit_text("Uploading...")
        
        caption = f"**ᴠɪᴀ** @{client.me.username}"
        if is_video:
             await app.send_video(
                 chat_id=message.chat.id,
                 video=file_path,
                 caption=f"**{title}**\n\n**ᴠɪᴀ** @{client.me.username}",
                 reply_to_message_id=message.id
             )
        else:
             await app.send_audio(
                 chat_id=message.chat.id,
                 audio=file_path,
                 caption=caption,
                 reply_to_message_id=message.id
             )
        
        await mystic.delete()
        
        # Cleanup
        if os.path.exists(file_path):
             os.remove(file_path)

    except Exception as e:
        await mystic.edit_text(f"❌ **Error:** `{e}`")
        if 'file_path' in locals() and file_path and os.path.exists(file_path):
             os.remove(file_path)

# ───────────────────────────── CALLBACKS ───────────────────────────── #
@app.on_callback_query(filters.regex(r"song_back") & ~BANNED_USERS)
@capture_callback_err
@languageCB
async def songs_back_helper(client, cq, lang):
    _ignored, req = cq.data.split(None, 1)
    stype, vidid = req.split("|")
    await cq.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(song_markup(lang, vidid))
    )

@app.on_callback_query(filters.regex(r"song_helper") & ~BANNED_USERS)
@capture_callback_err
@languageCB
async def song_helper_cb(client, cq, lang):
    _ignored, req = cq.data.split(None, 1)
    stype, vidid = req.split("|")

    try:
        await cq.answer(lang["song_6"], show_alert=True)
    except Exception:
        pass

    try:
        formats, _yturl = await YouTube.formats(vidid)
    except Exception:
        return await cq.edit_message_text(lang["song_7"])

    kb = InlineKeyboardBuilder()             # ← was InlineKeyboard()

    seen = set()
    if stype == "audio":
        for f in formats:
            if "audio" not in f["format"] or not f["filesize"]:
                continue
            label = f["format_note"].title()
            if label in seen:
                continue
            seen.add(label)
            kb.row(
                InlineKeyboardButton(
                    text=f"{label} • {convert_bytes(f['filesize'])}",
                    callback_data=f"song_download {stype}|{f['format_id']}|{vidid}",
                )
            )
    else:
        allowed = {160, 133, 134, 135, 136, 137, 298, 299, 264, 304, 266}
        for f in formats:
            if not f["filesize"] or int(f["format_id"]) not in allowed:
                continue
            res = f["format"].split("-")[1]
            kb.row(
                InlineKeyboardButton(
                    text=f"{res} • {convert_bytes(f['filesize'])}",
                    callback_data=f"song_download {stype}|{f['format_id']}|{vidid}",
                )
            )

    kb.row(
        InlineKeyboardButton(lang["BACK_BUTTON"], callback_data=f"song_back {stype}|{vidid}"),
        InlineKeyboardButton(lang["CLOSE_BUTTON"], callback_data="close"),
    )
    # convert to native markup here
    await cq.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))

@app.on_callback_query(filters.regex(r"song_download") & ~BANNED_USERS)
@capture_callback_err
@languageCB
async def song_download_cb(client, cq, lang):
    try:
        await cq.answer("Downloading…")
    except Exception:
        pass

    _ignored, req = cq.data.split(None, 1)
    stype, fmt_id, vidid = req.split("|")
    yturl = f"https://www.youtube.com/watch?v={vidid}"
    mystic = await cq.edit_message_text(lang["song_8"])

    file_path = None
    try:
        info, _v = await YouTube.track(yturl)
        title = re.sub(r"\W+", " ", info["title"])
        thumb = await cq.message.download()
        duration_sec = time_to_seconds(info.get("duration_min")) if info.get("duration_min") else None

        if stype == "audio":
            file_path, _ = await YouTube.download(
                yturl, mystic, songaudio=True, format_id=fmt_id, title=title
            )
            await mystic.edit_text(lang["song_11"])
            await app.send_chat_action(cq.message.chat.id, ChatAction.UPLOAD_AUDIO)
            await cq.edit_message_media(
                InputMediaAudio(
                    media=file_path,
                    caption=title,
                    thumb=thumb,
                    title=title,
                    performer=info.get("uploader"),
                )
            )
        else:  # video
            file_path, _ = await YouTube.download(
                yturl, mystic, songvideo=True, format_id=fmt_id, title=title
            )
            w, h = cq.message.photo.width, cq.message.photo.height
            await mystic.edit_text(lang["song_11"])
            await app.send_chat_action(cq.message.chat.id, ChatAction.UPLOAD_VIDEO)
            await cq.edit_message_media(
                InputMediaVideo(
                    media=file_path,
                    duration=duration_sec,
                    width=w,
                    height=h,
                    thumb=thumb,
                    caption=title,
                    supports_streaming=True,
                )
            )

    except Exception as err:
        print(f"[SONG] download/upload error: {err}")
        await mystic.edit_text(lang["song_10"])
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"[SONG] cleanup failed: {e}")


@app.on_callback_query(filters.regex(r"replay_song (.*)") & ~BANNED_USERS)
@capture_callback_err
@languageCB
async def replay_song_cb(client, cq, lang):
    videoid = cq.data.split(None, 1)[1]

    await cq.answer("ʀᴇᴘʟᴀʏɪɴɢ sᴋɪᴘᴘᴇᴅ sᴏɴɢ...", show_alert=False)

    chat_id_for_stream = cq.message.chat.id
    channel = await get_cmode(chat_id_for_stream)
    if channel:
        chat_id_for_stream = channel

    user_id = cq.from_user.id
    user_name = cq.from_user.first_name

    mystic = await cq.message.reply_text(lang["play_1"])

    try:
        details, track_id = await YouTube.track(videoid, True)
    except Exception as e:
        return await mystic.edit_text(lang["play_3"] + f"\n\nError: {e}")

    if details.get("duration_min"):
        duration_sec = time_to_seconds(details["duration_min"])
        if duration_sec > SONG_DOWNLOAD_DURATION_LIMIT:
            return await mystic.edit_text(
                lang["play_6"].format(SONG_DOWNLOAD_DURATION, dur_min)
            )

    try:
        await stream(
            client,
            lang,
            mystic,
            user_id,
            details,
            chat_id_for_stream,
            user_name,
            cq.message.chat.id,
            video=None,
            streamtype="youtube",
            forceplay=True,  # Forcefully play the replayed song
        )
    except Exception as e:
        ex_type = type(e).__name__
        err = lang["general_2"].format(ex_type)
        await mystic.edit_text(err)
        return

    await mystic.delete()
    try:
        # Delete the "Song Skipped" message with the replay button
        await cq.message.delete()
    except:
        pass

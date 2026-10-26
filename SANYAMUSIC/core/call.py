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
import shlex
import time
import os
import traceback
from datetime import datetime, timedelta
from typing import Union
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types.stream import MediaStream, StreamEnded, AudioQuality, VideoQuality
from pytgcalls.exceptions import (
    CallBusy,
    NoActiveGroupCall,
    TooOldPyrogramVersion,
)

# Compatibility aliases
AlreadyJoinedError = CallBusy
TelegramServerError = TooOldPyrogramVersion

def sanitize_ffmpeg_parameters(path: str, params: str) -> str:
    if not params:
        return params
    if not isinstance(params, str):
        return params
    if str(path).startswith(("http://", "https://", "rtmp://", "rtsp://", "mms://")):
        return params
    
    try:
        words = shlex.split(params)
    except Exception:
        words = params.split()
        
    cleaned = []
    skip = False
    for i, word in enumerate(words):
        if skip:
            skip = False
            continue
        if word in ("-reconnect", "-reconnect_at_eof", "-reconnect_streamed", "-reconnect_delay_max", "-user_agent", "-headers"):
            if i + 1 < len(words):
                skip = True
            continue
        cleaned.append(word)
        
    try:
        return shlex.join(cleaned)
    except Exception:
        return " ".join(cleaned)

# Compatibility layer for pytgcalls 2.2.11
class AudioPiped:
    def __init__(self, audio_path, audio_parameters=None, additional_ffmpeg_parameters=None):
        self.audio_path = audio_path
        self.audio_parameters = audio_parameters or AudioQuality.LOW
        self.additional_ffmpeg_parameters = additional_ffmpeg_parameters
    
    def to_media_stream(self):
        cleaned_params = sanitize_ffmpeg_parameters(self.audio_path, self.additional_ffmpeg_parameters)
        return MediaStream(
            media_path=self.audio_path,
            audio_parameters=self.audio_parameters,
            ffmpeg_parameters=cleaned_params
        )

class AudioVideoPiped:
    def __init__(self, media_path, audio_parameters=None, video_parameters=None, additional_ffmpeg_parameters=None):
        self.media_path = media_path
        self.audio_parameters = audio_parameters or AudioQuality.LOW
        self.video_parameters = video_parameters or VideoQuality.SD_480p
        self.additional_ffmpeg_parameters = additional_ffmpeg_parameters
    
    def to_media_stream(self):
        cleaned_params = sanitize_ffmpeg_parameters(self.media_path, self.additional_ffmpeg_parameters)
        return MediaStream(
            media_path=self.media_path,
            audio_parameters=self.audio_parameters,
            video_parameters=self.video_parameters,
            ffmpeg_parameters=cleaned_params
        )

class LowQualityAudio:
    def __new__(cls):
        return AudioQuality.LOW

class MediumQualityVideo:
    def __new__(cls):
        return VideoQuality.SD_360p

class StreamType:
    @staticmethod
    def pulse_stream():
        return None
import config
from SANYAMUSIC import LOGGER, YouTube, app
from SANYAMUSIC.misc import db
from SANYAMUSIC.utils.database import (
    active,
    activevideo,
    add_active_chat,
    add_active_video_chat,
    get_lang,
    get_loop,
    group_assistant,
    is_autoend,
    is_autoplay_on,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
)
from SANYAMUSIC.utils.exceptions import AssistantErr
from SANYAMUSIC.utils.formatters import check_duration, seconds_to_min, speed_converter, time_to_seconds
from SANYAMUSIC.utils.inline.play import stream_markup
from SANYAMUSIC.utils.stream.autoclear import auto_clean
from SANYAMUSIC.utils.thumbnails import get_thumb
from strings import get_string

autoend = {}
counter = {}

async def _clear_(chat_id):
    if db.get(chat_id):
        for popped in db[chat_id]:
            try:
                await auto_clean(popped)
            except:
                pass
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)

class Call(PyTgCalls):
    def __init__(self):
        from SANYAMUSIC import userbot
        self.one = PyTgCalls(userbot.one, cache_duration=400) if config.STRING1 and str(config.STRING1).strip().lower() != "none" else None
        self.two = PyTgCalls(userbot.two, cache_duration=400) if config.STRING2 and str(config.STRING2).strip().lower() != "none" else None
        self.three = PyTgCalls(userbot.three, cache_duration=400) if config.STRING3 and str(config.STRING3).strip().lower() != "none" else None
        self.four = PyTgCalls(userbot.four, cache_duration=400) if config.STRING4 and str(config.STRING4).strip().lower() != "none" else None
        self.five = PyTgCalls(userbot.five, cache_duration=400) if config.STRING5 and str(config.STRING5).strip().lower() != "none" else None

    async def pause_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.pause(chat_id)
        playing = db.get(chat_id)
        if playing:
            start_time = playing[0].get("start_time")
            if start_time:
                played = time.time() - start_time
                db[chat_id][0]["played"] += int(played)
                db[chat_id][0]["start_time"] = None

    async def resume_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.resume(chat_id)
        playing = db.get(chat_id)
        if playing:
            db[chat_id][0]["start_time"] = time.time()

    async def stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            await _clear_(chat_id)
            await assistant.leave_call(chat_id)
        except:
            pass

    async def stop_stream_force(self, chat_id: int):
        try:
            if config.STRING1 and self.one:
                await self.one.leave_call(chat_id)
        except:
            pass
        try:
            if config.STRING2 and self.two:
                await self.two.leave_call(chat_id)
        except:
            pass
        try:
            if config.STRING3 and self.three:
                await self.three.leave_call(chat_id)
        except:
            pass
        try:
            if config.STRING4 and self.four:
                await self.four.leave_call(chat_id)
        except:
            pass
        try:
            if config.STRING5 and self.five:
                await self.five.leave_call(chat_id)
        except:
            pass
        try:
            await _clear_(chat_id)
        except:
            pass

    async def speedup_stream(self, chat_id: int, file_path, speed, playing):
        assistant = await group_assistant(self, chat_id)
        if str(speed) != str("1.0"):
            base = os.path.basename(file_path)
            chatdir = os.path.join(os.getcwd(), "playback", str(speed))
            if not os.path.isdir(chatdir):
                os.makedirs(chatdir)
            out = os.path.join(chatdir, base)
            if not os.path.isfile(out):
                if str(speed) == str("0.5"):
                    vs = 2.0
                if str(speed) == str("0.75"):
                    vs = 1.35
                if str(speed) == str("1.5"):
                    vs = 0.68
                if str(speed) == str("2.0"):
                    vs = 0.5
                proc = await asyncio.create_subprocess_shell(
                    cmd=(
                        "ffmpeg "
                        "-i "
                        f"{file_path} "
                        "-filter:v "
                        f"setpts={vs}*PTS "
                        "-filter:a "
                        f"atempo={speed} "
                        "-preset ultrafast "
                        "-threads 1 "
                        f"{out} -y"
                    ),
                    stdin=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
            else:
                pass
        else:
            out = file_path
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        dur = await loop.run_in_executor(None, check_duration, out)
        dur = int(dur)
        played, con_seconds = speed_converter(playing[0]["played"], speed)
        duration = seconds_to_min(dur)
        stream = (
            AudioVideoPiped(
                out,
                audio_parameters=LowQualityAudio(),
                video_parameters=MediumQualityVideo(),
                additional_ffmpeg_parameters=f"-ss {played} -to {duration}",
            )
            if playing[0]["streamtype"] == "video"
            else AudioPiped(
                out,
                audio_parameters=LowQualityAudio(),
                additional_ffmpeg_parameters=f"-ss {played} -to {duration} -threads 1",
            )
        ).to_media_stream()
        if str(db[chat_id][0]["file"]) == str(file_path):
            await assistant.play(chat_id, stream)
        else:
            raise AssistantErr("Umm")
        if str(db[chat_id][0]["file"]) == str(file_path):
            exis = (playing[0]).get("old_dur")
            if not exis:
                db[chat_id][0]["old_dur"] = db[chat_id][0]["dur"]
                db[chat_id][0]["old_second"] = db[chat_id][0]["seconds"]
            db[chat_id][0]["played"] = con_seconds
            db[chat_id][0]["start_time"] = time.time()
            db[chat_id][0]["dur"] = duration
            db[chat_id][0]["seconds"] = dur
            db[chat_id][0]["speed_path"] = out
            db[chat_id][0]["speed"] = speed

    async def force_stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            check = db.get(chat_id)
            check.pop(0)
        except:
            pass
        await remove_active_video_chat(chat_id)
        await remove_active_chat(chat_id)
        try:
            await assistant.leave_call(chat_id)
        except:
            pass

    async def skip_stream(
        self,
        chat_id: int,
        link: str,
        video: Union[bool, str] = None,
        image: Union[bool, str] = None,
    ):
        assistant = await group_assistant(self, chat_id)
        if video:
            stream = AudioVideoPiped(
                link,
                audio_parameters=LowQualityAudio(),
                video_parameters=MediumQualityVideo(),
                additional_ffmpeg_parameters="-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 1M -analyzeduration 1M -user_agent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' -threads 1"
            ).to_media_stream()
        else:
            stream = AudioPiped(
                link, 
                audio_parameters=LowQualityAudio(),
                additional_ffmpeg_parameters="-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 1M -analyzeduration 1M -user_agent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' -threads 1"
            ).to_media_stream()
        await assistant.play(
            chat_id,
            stream,
        )

    async def seek_stream(self, chat_id, file_path, to_seek, duration, mode):
        assistant = await group_assistant(self, chat_id)
        stream = (
            AudioVideoPiped(
                file_path,
                audio_parameters=LowQualityAudio(),
                video_parameters=MediumQualityVideo(),
                additional_ffmpeg_parameters=f"-ss {to_seek} -to {duration}",
            )
            if mode == "video"
            else AudioPiped(
                file_path,
                audio_parameters=LowQualityAudio(),
                additional_ffmpeg_parameters=f"-ss {to_seek} -to {duration} -threads 1",
            )
        ).to_media_stream()
        await assistant.play(chat_id, stream)

    async def stream_call(self, link):
        assistant = await group_assistant(self, config.LOGGER_ID)
        await assistant.play(
            config.LOGGER_ID,
            AudioVideoPiped(link).to_media_stream(),
        )
        await asyncio.sleep(0.2)
        await assistant.leave_call(config.LOGGER_ID)

    async def join_call(
        self,
        chat_id: int,
        original_chat_id: int,
        link,
        video: Union[bool, str] = None,
        image: Union[bool, str] = None,
    ):
        language = await get_lang(chat_id)
        _ = get_string(language)
        
        try:
            assistant = await group_assistant(self, chat_id)
            if video:
                stream = AudioVideoPiped(
                    link,
                    audio_parameters=LowQualityAudio(),
                    video_parameters=MediumQualityVideo(),
                    additional_ffmpeg_parameters="-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 1M -analyzeduration 1M -user_agent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' -threads 1"
                ).to_media_stream()
            else:
                stream = AudioPiped(
                    link, 
                    audio_parameters=LowQualityAudio(), 
                    additional_ffmpeg_parameters="-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 1M -analyzeduration 1M -user_agent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' -threads 1"
                ).to_media_stream()
            
            try:
                await assistant.play(
                    chat_id,
                    stream,
                )
            except NoActiveGroupCall:
                # Try to start the voice chat automatically if bot has admin rights
                try:
                    from pyrogram.functions.phone import CreateGroupCall
                    await app.invoke(CreateGroupCall(peer=await app.resolve_peer(chat_id)))
                    await asyncio.sleep(1.5) # Wait for Telegram to propagate the call
                    await assistant.play(chat_id, stream)
                except Exception as e:
                    LOGGER(__name__).debug(f"Auto-Start VC failed: {e}")
                    raise AssistantErr(_["call_8"])
            except CallBusy:
                raise AssistantErr(_["call_9"])
            except TooOldPyrogramVersion:
                raise AssistantErr(_["call_10"])
            except AttributeError as e:
                LOGGER(__name__).error(f"AttributeError in play: {str(e)}")
                raise AssistantErr(f"AttributeError: {str(e)}")
        except AssistantErr:
             raise
        except Exception as e:
            LOGGER(__name__).error(f"General error in join_call: {type(e).__name__}: {str(e)}")
            raise
            
        await add_active_chat(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)
            
        if db.get(chat_id):
            db[chat_id][0]["start_time"] = time.time()
            
        if await is_autoend():
            counter[chat_id] = {}
            try:
                # Use pyrogram directly to get participants count if pytgcalls fails
                chat = await assistant.mtproto_client.get_chat(chat_id)
                users = chat.members_count if hasattr(chat, "members_count") else 1
            except:
                users = 1
            
            if users <= 1:
                autoend[chat_id] = datetime.now() + timedelta(minutes=1)

    async def change_stream(self, client, chat_id):
        check = db.get(chat_id)
        if not check:
            if chat_id in active:
                active.remove(chat_id)
            if chat_id in activevideo:
                activevideo.remove(chat_id)
            try:
                return await client.leave_call(chat_id)
            except:
                return

        # --- Resiliency Check: Ensure Assistant is in Call ---
        try:
            call_state = await client.get_call(chat_id)
            if not call_state or not call_state.is_playing:
                 LOGGER(__name__).info(f"[STREAM] Assistant not playing in {chat_id}, attempting to re-sync...")
        except Exception as e:
            LOGGER(__name__).debug(f"Call state check failed for {chat_id}: {e}")

        popped = None
        loop = await get_loop(chat_id)
        try:
            if loop == 0:
                popped = check.pop(0)
            else:
                loop = loop - 1
                await set_loop(chat_id, loop)
            await auto_clean(popped)
            if not check:
                if await is_autoplay_on(chat_id):
                    try:
                        videoid = popped.get("vidid")
                        title = popped.get("title")
                        
                        # Fallback for missing title (common in direct links)
                        if videoid and not title:
                            title = str(videoid)
                            
                        if videoid:
                            results = await YouTube.recommend(title, limit=5, videoid=videoid)
                            for result in results:
                                res_id = result.get("id")
                                res_title = result.get("title", "").lower()
                                
                                main_keyword = " ".join(title.lower().split()[:2])
                                if res_id != videoid and main_keyword not in res_title:
                                    details, track_id = await YouTube.track(result["link"])
                                    if details:
                                        # Optimization: Try to get direct stream URL first
                                        try:
                                            n, direct_link = await YouTube.stream(details["vidid"], videoid=True, video=False)
                                            autoplay_file = direct_link if (n != 0 and direct_link) else f"vid_{details['vidid']}"
                                        except:
                                            autoplay_file = f"vid_{details['vidid']}"

                                        put = {
                                            "title": details["title"],
                                            "dur": details["duration_min"],
                                            "streamtype": "youtube",
                                            "by": "Autoplay",
                                            "user_id": config.BOT_ID if hasattr(config, "BOT_ID") else 0,
                                            "chat_id": popped.get("chat_id"),
                                            "file": autoplay_file,
                                            "vidid": details["vidid"],
                                            "seconds": int(time_to_seconds(details["duration_min"])),
                                            "played": 0,
                                            "start_time": time.time(),
                                        }
                                        db[chat_id].append(put)
                                        check = db[chat_id]
                                        break
                        if not check:
                            await _clear_(chat_id)
                            return await client.leave_call(chat_id)
                    except Exception as e:
                        LOGGER(__name__).error(f"Autoplay Error: {e}")
                        await _clear_(chat_id)
                        return await client.leave_call(chat_id)
                else:
                    await _clear_(chat_id)
                    return await client.leave_call(chat_id)
        except:
            try:
                await _clear_(chat_id)
                return await client.leave_call(chat_id)
            except:
                return
        else:
            queued = check[0]["file"]
            language = await get_lang(chat_id)
            _ = get_string(language)
            title = (check[0]["title"]).title()
            user = check[0]["by"]
            user_id = check[0].get("user_id")
            mention = f"[{user}](tg://user?id={user_id})" if user_id else user
            original_chat_id = check[0]["chat_id"]
            streamtype = check[0]["streamtype"]
            videoid = check[0]["vidid"]
            db[chat_id][0]["played"] = 0
            db[chat_id][0]["start_time"] = time.time()
            exis = (check[0]).get("old_dur")
            if exis:
                db[chat_id][0]["dur"] = exis
                db[chat_id][0]["seconds"] = check[0]["old_second"]
                db[chat_id][0]["speed_path"] = None
                db[chat_id][0]["speed"] = 1.0
            video = True if str(streamtype) == "video" else False

            if "live_" in queued:
                n, link = await YouTube.video(videoid, True)
                if n == 0:
                    return await app.send_message(original_chat_id, text=_["call_6"])
                
                stream = (AudioVideoPiped(link, audio_parameters=LowQualityAudio(), video_parameters=MediumQualityVideo(), additional_ffmpeg_parameters="-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 1M -analyzeduration 1M -user_agent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' -threads 1") if video 
                         else AudioPiped(link, audio_parameters=LowQualityAudio(), additional_ffmpeg_parameters="-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 1M -analyzeduration 1M -user_agent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' -threads 1")).to_media_stream()
                
                try:
                    await client.play(chat_id, stream)
                except Exception as e:
                    LOGGER(__name__).error(f"Live Playback failed for {chat_id}: {e}")
                    try:
                        await client.leave_call(chat_id)
                        await asyncio.sleep(1)
                        await client.play(chat_id, stream)
                    except:
                        return await app.send_message(original_chat_id, text=_["call_6"])

                img = await get_thumb(videoid)
                button = stream_markup(_, chat_id)
                run = await app.send_photo(
                    chat_id=original_chat_id,
                    photo=img,
                    has_spoiler=True,
                    caption=_["stream_1"].format(f"https://t.me/{app.username}?start=info_{videoid}", title[:23], check[0]["dur"], mention),
                    reply_markup=InlineKeyboardMarkup(button),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"

            elif "vid_" in queued:
                mystic = await app.send_message(original_chat_id, _["call_7"])
                n, file_path = await YouTube.stream(videoid, videoid=True, video=video)
                if n != 0 and file_path:
                    direct = True
                else:
                    try:
                        file_path, direct_download = await YouTube.download(videoid, mystic, videoid=True, video=video)
                        if not file_path:
                            return await mystic.edit_text(_["call_6"], disable_web_page_preview=True)
                        direct = False
                    except Exception as e:
                        return await mystic.edit_text(_["call_6"], disable_web_page_preview=True)
                
                stream = (AudioVideoPiped(file_path, audio_parameters=LowQualityAudio(), video_parameters=MediumQualityVideo(), additional_ffmpeg_parameters="-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 1M -analyzeduration 1M -user_agent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' -threads 1") if video 
                         else AudioPiped(file_path, audio_parameters=LowQualityAudio(), additional_ffmpeg_parameters="-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 1M -analyzeduration 1M -user_agent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' -threads 1")).to_media_stream()
                
                try:
                    await client.play(chat_id, stream)
                except Exception as e:
                    LOGGER(__name__).error(f"Vid Playback failed for {chat_id}: {e}")
                    try:
                        await client.leave_call(chat_id)
                        await asyncio.sleep(1)
                        await client.play(chat_id, stream)
                    except:
                        return await app.send_message(original_chat_id, text=_["call_6"])

                img = await get_thumb(videoid)
                button = stream_markup(_, chat_id)
                await mystic.delete()
                run = await app.send_photo(
                    chat_id=original_chat_id,
                    photo=img,
                    has_spoiler=True,
                    caption=_["stream_1"].format(f"https://t.me/{app.username}?start=info_{videoid}", title[:23], check[0]["dur"], mention),
                    reply_markup=InlineKeyboardMarkup(button),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"
            elif "index_" in queued:
                stream = (
                    AudioVideoPiped(
                        videoid,
                        audio_parameters=LowQualityAudio(),
                        video_parameters=MediumQualityVideo(),
                    ).to_media_stream()
                    if str(streamtype) == "video"
                    else AudioPiped(videoid, audio_parameters=LowQualityAudio(), additional_ffmpeg_parameters="-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 1M -analyzeduration 1M -user_agent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' -threads 1").to_media_stream()
                )
                try:
                    await client.play(chat_id, stream)
                except:
                    return await app.send_message(
                        original_chat_id,
                        text=_["call_6"],
                    )
                button = stream_markup(_, chat_id)
                run = await app.send_photo(
                    chat_id=original_chat_id,
                    photo=config.STREAM_IMG_URL,
                    caption=_["stream_2"].format(mention),
                    reply_markup=InlineKeyboardMarkup(button),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            else:
                if video:
                    stream = AudioVideoPiped(
                        queued,
                        audio_parameters=LowQualityAudio(),
                        video_parameters=MediumQualityVideo(),
                    ).to_media_stream()
                else:
                    stream = AudioPiped(
                        queued,
                        audio_parameters=LowQualityAudio(),
                        additional_ffmpeg_parameters="-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 1M -analyzeduration 1M -user_agent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' -threads 1",
                    ).to_media_stream()
                try:
                    await client.play(chat_id, stream)
                except:
                    return await app.send_message(
                        original_chat_id,
                        text=_["call_6"],
                    )
                if videoid == "telegram":
                    button = stream_markup(_, chat_id)
                    run = await app.send_photo(
                        chat_id=original_chat_id,
                        photo=config.TELEGRAM_AUDIO_URL
                        if str(streamtype) == "audio"
                        else config.TELEGRAM_VIDEO_URL,
                        caption=_["stream_1"].format(
                            config.SUPPORT_CHAT, title[:23], check[0]["dur"], mention
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"
                elif videoid == "soundcloud":
                    button = stream_markup(_, chat_id)
                    run = await app.send_photo(
                        chat_id=original_chat_id,
                        photo=config.SOUNCLOUD_IMG_URL,
                        caption=_["stream_1"].format(
                            config.SUPPORT_CHAT, title[:23], check[0]["dur"], mention
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"
                else:
                    img = await get_thumb(videoid)
                    button = stream_markup(_, chat_id)
                    run = await app.send_photo(
                        chat_id=original_chat_id,
                        photo=img,
                        has_spoiler=True,
                        caption=_["stream_1"].format(
                            f"https://t.me/{app.username}?start=info_{videoid}",
                            title[:23],
                            check[0]["dur"],
                            mention,
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "stream"

        try:
            from SANYAMUSIC.utils.stream.queue import prefetch_next_track
            asyncio.create_task(prefetch_next_track(chat_id))
        except Exception as pe:
            LOGGER(__name__).debug(f"Failed to start prefetch task: {pe}")

    async def ping(self):
        pings = []
        if config.STRING1:
            pings.append(self.one.ping)
        if config.STRING2:
            pings.append(self.two.ping)
        if config.STRING3:
            pings.append(self.three.ping)
        if config.STRING4:
            pings.append(self.four.ping)
        if config.STRING5:
            pings.append(self.five.ping)
        return str(round(sum(pings) / len(pings), 3))

    async def safe_change_stream(self, client, update):
        try:
            await self.change_stream(client, update.chat_id)
        except Exception as e:
            LOGGER(__name__).error(f"Error in safe_change_stream: {type(e).__name__}: {str(e)}")
            LOGGER(__name__).error(f"Traceback: {traceback.format_exc()}")

    async def watchdog_task(self):
        """Periodically checks for idle voice chats and system health."""
        try:
            import psutil
        except ImportError:
            psutil = None
            
        from config import AUTO_LEAVE_ASSISTANT_TIME, LOGGER_ID
        IDLE_TIMEOUT = int(AUTO_LEAVE_ASSISTANT_TIME) if AUTO_LEAVE_ASSISTANT_TIME else 900
        idle_timers = {} 
        high_cpu_count = 0
        
        while True:
            try:
                await asyncio.sleep(60)
                
                if psutil:
                    cpu = psutil.cpu_percent(interval=None)
                    ram = psutil.virtual_memory().percent
                    
                    # Check for active or orphaned ffmpeg processes
                    ffmpeg_count = 0
                    try:
                        for proc in psutil.process_iter(attrs=['name']):
                            if proc.info['name'] == 'ffmpeg':
                                ffmpeg_count += 1
                    except:
                        pass
                    
                    # Self-Healing RAM check
                    if ram > 90:
                        LOGGER(__name__).warning(f"[WATCHDOG] RAM usage critically high: {ram}%. Restarting self-healingly...")
                        try:
                            await app.send_message(LOGGER_ID, f"🚨 **SELF-HEALING RESTART**\n\n**RAM Usage:** {ram}%\nStatus: RAM exceeded 90%, restarting container...")
                        except:
                            pass
                        os._exit(1)
                        
                    # Self-Healing CPU check (Only when actively streaming OR when there are leaked ffmpeg orphans)
                    if cpu > 98 and (len(active) > 0 or ffmpeg_count > 0):
                        high_cpu_count += 1
                        if high_cpu_count >= 3: # 3 minutes of >98% CPU
                            LOGGER(__name__).warning(f"[WATCHDOG] Sustained extreme CPU load: {cpu}%. Restarting self-healingly...")
                            try:
                                await app.send_message(LOGGER_ID, f"🚨 **SELF-HEALING RESTART**\n\n**CPU Usage:** {cpu}%\nStatus: Sustained high CPU with active/leaked processes for 3 minutes, restarting container...")
                            except:
                                pass
                            os._exit(1)
                    else:
                        high_cpu_count = 0

                # --- Part 2: Auto-Leave Idle Chats ---
                for chat_id in list(active):
                    if not db.get(chat_id):
                        if chat_id not in idle_timers:
                            idle_timers[chat_id] = time.time()
                        
                        if time.time() - idle_timers[chat_id] > IDLE_TIMEOUT:
                            try:
                                assistant = await group_assistant(self, chat_id)
                                await assistant.leave_call(chat_id)
                                await _clear_(chat_id)
                                LOGGER(__name__).info(f"[WATCHDOG] Left idle chat {chat_id}")
                                if chat_id in idle_timers:
                                    del idle_timers[chat_id]
                            except:
                                continue
                    else:
                        # Watchdog: Detection of Stalled / Missing Assistant
                        try:
                            assistant = await group_assistant(self, chat_id)
                            is_active = False
                            try:
                                # PyTgCalls v2: check the 'calls' property for active sessions
                                for call_info in await assistant.calls:
                                    if call_info.chat_id == chat_id:
                                        is_active = True
                                        break
                            except:
                                is_active = True # Fail-safe: assume active
                            
                            if not is_active:
                                LOGGER(__name__).info(f"[WATCHDOG] Detected inactive chat {chat_id}, cleaning up.")
                                await self.stop_stream(chat_id)
                                continue
                        except Exception as e:
                            LOGGER(__name__).warning(f"[WATCHDOG] Error checking chat {chat_id}: {e}")

                        if chat_id in idle_timers:
                            del idle_timers[chat_id]

                # --- Part 3: Disk Cleanup (Auto-delete old downloads/playback files) ---
                downloads_dir = "downloads"
                if os.path.exists(downloads_dir):
                    now = time.time()
                    for f in os.listdir(downloads_dir):
                        fp = os.path.join(downloads_dir, f)
                        try:
                            # Auto-clean any files older than 20 minutes to save disk space
                            if os.path.isfile(fp) and (now - os.path.getmtime(fp) > 1200):
                                os.remove(fp)
                                LOGGER(__name__).info(f"[WATCHDOG] Cleaned up old downloaded file: {f}")
                        except:
                            pass

                playback_dir = "playback"
                if os.path.exists(playback_dir):
                    now = time.time()
                    for root, dirs, files in os.walk(playback_dir):
                        for f in files:
                            fp = os.path.join(root, f)
                            try:
                                # Auto-clean speedup cached files older than 20 minutes
                                if os.path.isfile(fp) and (now - os.path.getmtime(fp) > 1200):
                                    os.remove(fp)
                            except:
                                pass

            except Exception as e:
                LOGGER(__name__).error(f"Watchdog Error: {e}")
                await asyncio.sleep(10)

    async def start(self):
        LOGGER(__name__).info("Starting PyTgCalls Client...\n")
        if config.STRING1 and self.one:
            await self.one.start()
        if config.STRING2 and self.two:
            await self.two.start()
        if config.STRING3 and self.three:
            await self.three.start()
        if config.STRING4 and self.four:
            await self.four.start()
        if config.STRING5 and self.five:
            await self.five.start()

        # Start background watchdog tasks
        asyncio.create_task(self.watchdog_task())

        async def update_handler(client, update: Update):
            if not isinstance(update, StreamEnded):
                return
            asyncio.create_task(self.safe_change_stream(client, update))

        try:
            if config.STRING1 and self.one:
                self.one.on_update()(update_handler)
            if config.STRING2 and self.two:
                self.two.on_update()(update_handler)
            if config.STRING3 and self.three:
                self.three.on_update()(update_handler)
            if config.STRING4 and self.four:
                self.four.on_update()(update_handler)
            if config.STRING5 and self.five:
                self.five.on_update()(update_handler)
        except Exception as e:
            LOGGER(__name__).error(f"Error setting up decorators: {e}")


class SimpleLazyProxy:
    def __init__(self, func):
        self._func = func
    def __getattr__(self, name):
        return getattr(self._func(), name)

_SANYA = None

def get_sanya_call():
    global _SANYA
    if _SANYA is None:
        _SANYA = Call()
    return _SANYA

SANYA = SimpleLazyProxy(get_sanya_call)

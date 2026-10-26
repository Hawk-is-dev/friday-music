import os
import re
import json
import random
import asyncio
import yt_dlp
import aiofiles
import aiohttp
import traceback
from typing import Union
from urllib.parse import unquote, urljoin
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch, Video

import config
from upstash_redis import Redis
from SANYAMUSIC import LOGGER

# Initialize Redis Cache
try:
    redis_client = Redis(url=config.REDIS_URL, token=config.REDIS_TOKEN)
except Exception as e:
    LOGGER(__name__).error(f"Failed to initialize Redis: {e}")
    redis_client = None

from SANYAMUSIC.utils.database import is_on_off
from SANYAMUSIC.utils.formatters import time_to_seconds, seconds_to_min


_ENV_COOKIE_PATH = None


def _cookie_from_env():
    """Write COOKIES_TEXT (raw Netscape text) or COOKIES_B64 to a file once and return its path."""
    global _ENV_COOKIE_PATH
    if _ENV_COOKIE_PATH and os.path.exists(_ENV_COOKIE_PATH):
        return _ENV_COOKIE_PATH
    raw = (os.getenv("COOKIES_TEXT") or "").strip()
    if not raw:
        b64 = (os.getenv("COOKIES_B64") or "").strip()
        if b64:
            try:
                import base64
                raw = base64.b64decode(b64).decode("utf-8", "ignore").strip()
            except Exception:
                raw = ""
    if not raw:
        return None
    # Railway sometimes stores newlines as the two characters \n
    if "\\n" in raw and "\n" not in raw:
        raw = raw.replace("\\n", "\n").replace("\\t", "\t")
    os.makedirs("cookies", exist_ok=True)
    path = os.path.join("cookies", "env_cookies.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(raw + "\n")
    _ENV_COOKIE_PATH = path
    return path


def cookie_txt_file():
    env_path = _cookie_from_env()
    if env_path:
        return env_path

    original_cookie_path = "SANYAMUSIC/assets/cookies.txt"
    if os.path.exists(original_cookie_path):
        return original_cookie_path

    cookie_dir = os.path.join(os.getcwd(), "cookies")
    if os.path.exists(cookie_dir):
        cookies_files = [f for f in os.listdir(cookie_dir) if f.endswith(".txt") and not f.endswith("example.txt")]
        if cookies_files:
            return os.path.join(cookie_dir, random.choice(cookies_files))

    return None


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        self.cache = {} # Link cache
        self.query_cache = {} # Keyword to result cache
        self.stream_cache = {} # VideoID to Direct Stream URL cache
        
    def _sanitize_filename(self, filename: str) -> str:
        # Remove special characters that are illegal in filenames
        return re.sub(r'[\\/*?:"<>|]', "", filename).replace(" ", "_")

    async def _download_media(self, link: str, video: bool = False, title: str = None) -> str:
        media_type = "video" if video else "audio"
        ext = "mp4" if video else "m4a"

        video_id = (
            link.split("v=")[-1].split("&")[0] if "v=" in link else link.split("/")[-1].split("?")[0]
        )

        if not video_id or len(video_id) < 3:
            return None
        
        # Security: Strip dangerous characters to prevent Path Traversal
        video_id = re.sub(r'[^a-zA-Z0-9_-]', '', video_id)

        DOWNLOAD_DIR = "downloads"
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        # Use title in filename if provided, fallback to video_id
        safe_title = self._sanitize_filename(title) if title else video_id
        file_path = os.path.join(DOWNLOAD_DIR, f"{safe_title}_{video_id}.{ext}")

        if os.path.exists(file_path):
            return file_path

        try:
            if not config.API_URL or not config.API_KEY:
                LOGGER(__name__).warning("Sonic API not configured (API_URL/API_KEY missing). Falling back to direct download.")
                return None

            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            ]
            headers = {"User-Agent": random.choice(user_agents)}
            async with aiohttp.ClientSession(headers=headers) as session:
                search_url = f"{config.API_URL.rstrip('/')}/search"
                params = {"q": video_id, "type": media_type, "api_key": config.API_KEY}
                
                max_retries = 3
                for attempt in range(max_retries + 1):
                    try:
                        async with session.get(search_url, params=params, timeout=45) as resp:
                            if resp.status == 200:
                                try:
                                    data = await resp.json()
                                except Exception as je:
                                    text = await resp.text()
                                    LOGGER(__name__).error(f"[SONIC API] JSON Decode Error: {je}. Response text: {text[:200]}")
                                    return None
                                    
                                stream_url_path = data.get("stream_url")
                                if not stream_url_path:
                                     LOGGER(__name__).error(f"[SONIC API] ERROR: No stream_url in response: {data}")
                                     return None
                                     
                                # Handle both relative and absolute URLs correctly
                                if stream_url_path.startswith("http"):
                                    full_stream_url = stream_url_path
                                else:
                                    full_stream_url = urljoin(config.API_URL, stream_url_path)
                                    
                                # Increased timeout for large file downloads
                                for _ in range(30):
                                    async with session.get(full_stream_url, timeout=60) as stream_res:
                                        if stream_res.status == 200:
                                            LOGGER(__name__).info(f"[SONIC] Downloading media: {video_id} ({media_type})")
                                            async with aiofiles.open(file_path, "wb") as f:
                                                async for chunk in stream_res.content.iter_chunked(1048576): 
                                                    await f.write(chunk)
                                                    
                                            # Failsafe: If audio was requested, ensure the file is audio-only using FFmpeg
                                            if media_type == "audio":
                                                try:
                                                    temp_path = file_path + ".tmp"
                                                    os.rename(file_path, temp_path)
                                                    # -vn: skip video, -acodec aac: transcode to standard AAC format, -threads 1 for stability
                                                    proc = await asyncio.create_subprocess_shell(
                                                        f"ffmpeg -i {temp_path} -vn -acodec aac -threads 1 {file_path} -y",
                                                        stdout=asyncio.subprocess.PIPE,
                                                        stderr=asyncio.subprocess.PIPE,
                                                    )
                                                    await proc.communicate()
                                                    if os.path.exists(temp_path):
                                                        os.remove(temp_path)
                                                    LOGGER(__name__).info(f"[SONIC] Post-processed audio for {video_id}")
                                                except Exception as fe:
                                                    LOGGER(__name__).warning(f"FFmpeg post-process failed (falling back to original): {fe}")
                                                    if os.path.exists(temp_path) and not os.path.exists(file_path):
                                                        os.rename(temp_path, file_path)
                                            return file_path
                                        elif stream_res.status == 202:
                                            await asyncio.sleep(3)
                                        else:
                                            LOGGER(__name__).warning(f"[SONIC API] Stream fetch failed with status {stream_res.status}")
                                            break
                                break
                            elif resp.status == 202:
                                # Sonic API Accepted vault request; polling loop
                                LOGGER(__name__).info(f"[SONIC API] Search returned 202 Accepted for {video_id}. Polling details/stream...")
                                poll_attempts = 15
                                for p in range(poll_attempts):
                                    await asyncio.sleep(4)
                                    # Try fetching details again to check cache status
                                    details_url = f"{config.API_URL.rstrip('/')}/search"
                                    async with session.get(details_url, params=params, timeout=15) as poll_resp:
                                        if poll_resp.status == 200:
                                            poll_data = await poll_resp.json()
                                            stream_url_path = poll_data.get("stream_url")
                                            if stream_url_path:
                                                if stream_url_path.startswith("http"):
                                                    full_stream_url = stream_url_path
                                                else:
                                                    full_stream_url = urljoin(config.API_URL, stream_url_path)
                                                
                                                # Break outer loops and proceed with downloading
                                                async with session.get(full_stream_url, timeout=60) as stream_res:
                                                    if stream_res.status == 200:
                                                        async with aiofiles.open(file_path, "wb") as f:
                                                            async for chunk in stream_res.content.iter_chunked(1048576):
                                                                await f.write(chunk)
                                                        if media_type == "audio":
                                                            try:
                                                                temp_path = file_path + ".tmp"
                                                                os.rename(file_path, temp_path)
                                                                proc = await asyncio.create_subprocess_shell(
                                                                    f"ffmpeg -i {temp_path} -vn -acodec aac -threads 1 {file_path} -y",
                                                                    stdout=asyncio.subprocess.PIPE,
                                                                    stderr=asyncio.subprocess.PIPE,
                                                                )
                                                                await proc.communicate()
                                                                if os.path.exists(temp_path):
                                                                    os.remove(temp_path)
                                                            except:
                                                                if os.path.exists(temp_path) and not os.path.exists(file_path):
                                                                    os.rename(temp_path, file_path)
                                                        return file_path
                                            elif poll_data.get("cdn") == "Pending-Vault":
                                                # Still vaulting
                                                continue
                                        elif poll_resp.status != 202:
                                            break
                                break
                            elif attempt < max_retries:
                                LOGGER(__name__).warning(f"[SONIC API] Search attempt {attempt+1} failed with status {resp.status} for {video_id}. Retrying in 3s...")
                                await asyncio.sleep(3)
                            else:
                                LOGGER(__name__).warning(f"[SONIC API] Search failed with status {resp.status} for {video_id} after {max_retries+1} attempts.")
                    except Exception as e:
                         if attempt < max_retries:
                             LOGGER(__name__).warning(f"[SONIC API] Search attempt {attempt+1} raised exception: {type(e).__name__} for {video_id}. Retrying in 3s...")
                             await asyncio.sleep(3)
                         else:
                             LOGGER(__name__).error(f"[SONIC API] Search exception after {max_retries+1} attempts for {video_id}: {type(e).__name__}: {str(e)}")
                             # Fall through to fallback
                             break
            
            # --- Fallback: Download from ShrutiBots API (https://api01.shrutibots.site) ---
            LOGGER(__name__).info(f"[FALLBACK] Sonic API refused or failed. Trying ShrutiBots API for {video_id}...")
            async with aiohttp.ClientSession() as session:
                shrutibots_url = f"https://api01.shrutibots.site/download"
                shrutibots_params = {"url": video_id, "type": media_type}
                if config.SHRUTI_API_KEY:
                    shrutibots_params["api_key"] = config.SHRUTI_API_KEY
                async with session.get(shrutibots_url, params=shrutibots_params, timeout=30) as sb_resp:
                    if sb_resp.status == 200:
                        sb_data = await sb_resp.json()
                        token = sb_data.get("download_token")
                        if token:
                            direct_dl_url = f"https://api01.shrutibots.site/stream/{video_id}?type={media_type}&token={token}"
                            if config.SHRUTI_API_KEY:
                                direct_dl_url += f"&api_key={config.SHRUTI_API_KEY}"
                            async with session.get(direct_dl_url, timeout=120) as dl_resp:
                                if dl_resp.status == 200:
                                    async with aiofiles.open(file_path, "wb") as f:
                                        async for chunk in dl_resp.content.iter_chunked(1048576):
                                            await f.write(chunk)
                                    if media_type == "audio":
                                        try:
                                            temp_path = file_path + ".tmp"
                                            os.rename(file_path, temp_path)
                                            proc = await asyncio.create_subprocess_shell(
                                                f"ffmpeg -i {temp_path} -vn -acodec aac -threads 1 {file_path} -y",
                                                stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.PIPE,
                                            )
                                            await proc.communicate()
                                            if os.path.exists(temp_path):
                                                os.remove(temp_path)
                                        except:
                                            if os.path.exists(temp_path) and not os.path.exists(file_path):
                                                os.rename(temp_path, file_path)
                                    return file_path
        except Exception as e:
            LOGGER(__name__).error(f"Critical error in _download_media fallback for {video_id}: {type(e).__name__}: {str(e)}")
            LOGGER(__name__).debug(traceback.format_exc())
        return None

    def _yt_dlp_call_with_fallback(self, action, opts):
        # Node.js is installed in the Docker image; yt-dlp needs a JS runtime to read YouTube formats.
        opts.setdefault("js_runtimes", {"node": {}})
        if not opts.get("cookiefile"):
            cookie_file = cookie_txt_file()
            if cookie_file:
                opts["cookiefile"] = cookie_file
        with yt_dlp.YoutubeDL(opts) as ydl:
            return action(ydl)

    async def url(self, message: Message):
        if message.entities:
            for entity in message.entities:
                if entity.type == MessageEntityType.URL:
                    link = message.text[entity.offset : entity.offset + entity.length]
                    if re.search(self.regex, link):
                        return link
        if message.reply_to_message:
            if message.reply_to_message.entities:
                for entity in message.reply_to_message.entities:
                    if entity.type == MessageEntityType.URL:
                        link = message.reply_to_message.text[entity.offset : entity.offset + entity.length]
                        if re.search(self.regex, link):
                            return link
            if message.reply_to_message.text:
                if re.search(self.regex, message.reply_to_message.text):
                    return message.reply_to_message.text
        return None

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = f"https://www.youtube.com/watch?v={link}"
        if re.search(self.regex, link):
            return True
        return False

    async def details(self, link: str, videoid: Union[bool, str] = None, fast: bool = False):
        if not link:
            return None, None, None, None, None
            
        if videoid:
            link = f"{self.base}{link}"
        if "&" in link:
            link = link.split("&")[0]

        # --- Cache Check (In-Memory) ---
        if link in self.query_cache:
            return self.query_cache[link]

        # --- Cache Check (Redis - 3 Months) ---
        cache_key = f"bot_details:{link}"
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    data = json.loads(cached) if isinstance(cached, str) else cached
                    res = (data["title"], data["duration_min"], data["duration_sec"], data["thumbnail"], data["vidid"])
                    # Re-fill in-memory cache
                    self.query_cache[link] = res
                    if data.get("stream_url"):
                         self.stream_cache[data["vidid"]] = data["stream_url"]
                    return res
            except Exception as e:
                LOGGER(__name__).warning(f"Redis cache read failed: {e}")

        # --- Primary Action: Sonic API (Consolidated Metadata & Stream) ---
        if config.API_URL and config.API_KEY:
            try:
                async with aiohttp.ClientSession() as session:
                    search_query = link if not videoid else link.replace(self.base, "")
                    url = f"{config.API_URL.rstrip('/')}/search"
                    params = {"q": search_query, "type": "audio", "api_key": config.API_KEY}
                    
                    max_retries = 3
                    for attempt in range(max_retries + 1):
                        try:
                            async with session.get(url, params=params, timeout=30) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    if data and "id" in data:
                                        title = data.get("title", "Unknown Title")
                                        duration_min = data.get("duration", "00:00")
                                        thumbnail = data.get("thumbnail")
                                        vidid = data.get("id")
                                        duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
                                        stream_url = data.get("stream_url")
                                        
                                        # Store stream URL for zero-latency playback
                                        if stream_url and vidid:
                                            if not stream_url.startswith("http"):
                                                stream_url = urljoin(config.API_URL, stream_url)
                                            self.stream_cache[vidid] = stream_url
                                        
                                        res = (title, duration_min, duration_sec, thumbnail, vidid)
                                        self.query_cache[link] = res

                                        # Save to Redis (3 Months)
                                        if redis_client:
                                            try:
                                                cache_data = {
                                                    "title": title, "duration_min": duration_min, 
                                                    "duration_sec": duration_sec, "thumbnail": thumbnail, 
                                                    "vidid": vidid, "stream_url": stream_url
                                                }
                                                redis_client.set(cache_key, json.dumps(cache_data), ex=2592000)
                                            except Exception as exc:
                                                LOGGER(__name__).warning(f"Redis cache write failed: {exc}")
                                        
                                        return res
                                elif attempt < max_retries:
                                    LOGGER(__name__).warning(f"[SONIC API] Details search attempt {attempt+1} failed with status {resp.status} for {search_query}. Retrying in 3s...")
                                    await asyncio.sleep(3)
                        except Exception as e:
                            if attempt < max_retries:
                                LOGGER(__name__).warning(f"[SONIC API] Details search attempt {attempt+1} raised exception: {type(e).__name__} for {search_query}. Retrying in 3s...")
                                await asyncio.sleep(3)
                            else:
                                raise
            except Exception as e:
                LOGGER(__name__).warning(f"Sonic API search failed: {e}")

        # --- Fallback 1: Light Search ---
        try:
            results = VideosSearch(str(link), limit=1)
            results_data = await results.next()
            if results_data.get("result"):
                result = results_data["result"][0]
                title = result.get("title") or "Unknown Title"
                duration_min = result.get("duration") or "00:00"
                thumbnail = (result.get("thumbnails") or [{}])[0].get("url", "").split("?")[0]
                vidid = result.get("id")
                duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
                res = (title, duration_min, duration_sec, thumbnail, vidid)
                
                # Save to both caches
                self.query_cache[link] = res
                if redis_client:
                    try:
                        cache_data = {
                            "title": title, "duration_min": duration_min, 
                            "duration_sec": duration_sec, "thumbnail": thumbnail, 
                            "vidid": vidid
                        }
                        redis_client.set(cache_key, json.dumps(cache_data), ex=2592000)
                    except:
                        pass
                return res
        except:
             pass

        # --- Fallback 2: yt-dlp Metadata Extraction (Heavy but Reliable) ---
        try:
            is_url = await self.exists(link)
            search_query = link if is_url else f"ytsearch:{link}"
            
            opts = {
                "quiet": True, 
                "no_warnings": True, 
                "format": "bestaudio/best",
                "nocheckcertificate": True,
                "geo_bypass": True,
                "referer": "https://www.youtube.com/",
            }
            
            cookie_file = cookie_txt_file()
            if cookie_file:
                opts["cookiefile"] = cookie_file

            def extract(ydl):
                return ydl.extract_info(search_query, download=False)
            
            info = await asyncio.get_event_loop().run_in_executor(
                None, self._yt_dlp_call_with_fallback, extract, opts
            )
            if info:
                if "entries" in info:
                    if not info["entries"]:
                        return None, None, None, None, None
                    info = info["entries"][0]
                
                title = info.get("title")
                duration_sec = info.get("duration", 0)
                duration_min = seconds_to_min(duration_sec or 0)
                thumbnail = info.get("thumbnail")
                vidid = info.get("id")
                res = (title, duration_min, duration_sec, thumbnail, vidid)
                
                # Save to both caches
                self.query_cache[link] = res
                if redis_client:
                    try:
                        cache_data = {
                            "title": title, "duration_min": duration_min, 
                            "duration_sec": duration_sec, "thumbnail": thumbnail, 
                            "vidid": vidid
                        }
                        redis_client.set(cache_key, json.dumps(cache_data), ex=2592000)
                    except:
                        pass
                return res
        except Exception as e:
            LOGGER(__name__).error(f"Fallback extraction failed for {link}: {e}")

        return None, None, None, None, None

        return None, None, None, None, None

    async def title(self, link: str, videoid: Union[bool, str] = None):
        title, _, _, _, _ = await self.details(link, videoid)
        return title

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        _, duration, _, _, _ = await self.details(link, videoid)
        return duration

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        _, _, _, thumbnail, _ = await self.details(link, videoid)
        return thumbnail

    async def stream(self, link: str, videoid: Union[bool, str] = None, video: bool = False):
        if videoid:
            link = self.base + link
        
        video_id = (
            link.split("v=")[-1].split("&")[0] if "v=" in link else link.split("/")[-1].split("?")[0]
        )
        # Security: Strip dangerous characters
        video_id = re.sub(r'[^a-zA-Z0-9_-]', '', video_id)
        
        # --- Attempt 0: Stream Cache (In-Memory) ---
        if video_id in self.stream_cache and not video:
             return 1, self.stream_cache[video_id]

        # --- Attempt 0.5: Stream Cache (Redis - 3 Months) ---
        cache_key = f"bot_stream:{video_id}:{'video' if video else 'audio'}"
        if redis_client:
             try:
                 cached_url = redis_client.get(cache_key)
                 if cached_url:
                      return 1, cached_url
             except Exception as e:
                 LOGGER(__name__).warning(f"Redis stream cache read failed: {e}")

        # --- Primary Action: Sonic API ---
        try:
             media_type = "video" if video else "audio"
             async with aiohttp.ClientSession() as session:
                  url = f"{config.API_URL.rstrip('/')}/search"
                  params = {"q": video_id, "type": media_type, "api_key": config.API_KEY}
                  
                  max_retries = 3
                  for attempt in range(max_retries + 1):
                      try:
                          async with session.get(url, params=params, timeout=30) as resp:
                              if resp.status == 200:
                                  data = await resp.json()
                                  stream_url = data.get("stream_url")
                                  if stream_url:
                                      if not stream_url.startswith("http"):
                                          stream_url = urljoin(config.API_URL, stream_url)
                                      
                                      # Save to Redis (1 Week)
                                      if redis_client:
                                           try:
                                               redis_client.set(cache_key, stream_url, ex=2592000)
                                           except Exception as exc:
                                               LOGGER(__name__).warning(f"Redis stream cache write failed: {exc}")
                                               
                                      return 1, stream_url
                              elif attempt < max_retries:
                                  LOGGER(__name__).warning(f"[SONIC API] Stream search attempt {attempt+1} failed with status {resp.status} for {video_id}. Retrying in 3s...")
                                  await asyncio.sleep(3)
                      except Exception as e:
                          if attempt < max_retries:
                              LOGGER(__name__).warning(f"[SONIC API] Stream search attempt {attempt+1} raised exception: {type(e).__name__} for {video_id}. Retrying in 3s...")
                              await asyncio.sleep(3)
                          else:
                              raise
        except Exception as e:
             LOGGER(__name__).warning(f"Sonic API stream extraction failed: {e}")

        # --- Fallback: yt-dlp Direct Stream (Reliable but potentially subject to bot detection) ---
        try:
            ydl_opts = {
                "quiet": True,
                "format": "bestaudio[ext=m4a]/bestaudio/best" if not video else "best",
                "nocheckcertificate": True,
                "geo_bypass": True,
                "no_warnings": True,
                "extract_flat": False,
            }
            
            def extract(ydl):
                return ydl.extract_info(link, download=False)
            
            info = await asyncio.get_event_loop().run_in_executor(
                None, self._yt_dlp_call_with_fallback, extract, ydl_opts
            )
            stream_url = info.get("url")
            if stream_url:
                # Save to both caches
                self.stream_cache[video_id] = stream_url
                if redis_client:
                    try:
                        redis_client.set(cache_key, stream_url, ex=2592000)
                    except:
                        pass
                return 1, stream_url
        except Exception as e:
            LOGGER(__name__).error(f"Stream extraction finally failed for {video_id}: {e}")
            return 0, None

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        try:
            ydl_opts = {"quiet": True, "format": "best", "no_warnings": True, "nocheckcertificate": True, "geo_bypass": True}
            
            def extract(ydl):
                return ydl.extract_info(link, download=False)
            
            info = await asyncio.get_event_loop().run_in_executor(
                None, self._yt_dlp_call_with_fallback, extract, ydl_opts
            )
            return 1, info.get("url")
        except Exception as e:
            LOGGER(__name__).error(f"Video extraction failed: {e}")
            return None

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        try:
            opts = {"quiet": True, "no_warnings": True}
            def extract():
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(link, download=False)
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, extract)
            formats = []
            for f in info.get("formats", []):
                formats.append({
                    "format_id": f.get("format_id"),
                    "ext": f.get("ext"),
                    "resolution": f.get("resolution") or f.get("format_note"),
                    "filesize": f.get("filesize") or f.get("filesize_approx"),
                })
            return formats
        except:
            return []

    async def slider(self, query: str, query_type: int):
        # --- Attempt 1: VideosSearch ---
        try:
            query = str(query) if query else ""
            if not query:
                return None, None, None, None
            results = VideosSearch(query, limit=10)
            results_data = await results.next()
            if results_data.get("result") and len(results_data["result"]) > query_type:
                result = results_data["result"][query_type]
                title = result.get("title") or "Unknown Title"
                duration_min = result.get("duration") or "00:00"
                thumbnail = (result.get("thumbnails") or [{}])[0].get("url", "").split("?")[0]
                vidid = result.get("id")
                return title, duration_min, thumbnail, vidid
        except Exception as e:
            LOGGER(__name__).warning(f"VideosSearch slider failed for {query}: {e}")

        # --- Attempt 2: Vercel Search Fallback ---
        if config.VERCEL_SEARCH_URL:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{config.VERCEL_SEARCH_URL}/search", params={"q": query}) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data:
                                if isinstance(data, dict):
                                    data = [data]
                                if len(data) > query_type:
                                    result = data[query_type]
                                title = result.get("title")
                                duration_min = result.get("duration") or "00:00"
                                thumbnail = result.get("thumbnail")
                                vidid = result.get("id")
                                return title, duration_min, thumbnail, vidid
            except Exception as e:
                LOGGER(__name__).warning(f"Vercel slider fallback failed for {query}: {e}")
        return None, None, None, None

    async def download(self, vidid: str, mystic, video: bool = False, songaudio: bool = False, songvideo: bool = False, format_id: str = None, title: str = None, videoid: bool = None):
        if videoid or vidid or songaudio or songvideo:
            link = self.base + vidid if not vidid.startswith("http") else vidid
        else:
            link = vidid
        
        # For standard playback AND song/video commands, try Sonic API first
        if not format_id:
            file_path = await self._download_media(link, video=(video or songvideo), title=title)
            if file_path:
                return file_path, True
        
        # Fallback to yt-dlp download (used for song command or if API fails)
        try:
            if mystic:
                await mystic.edit_text("ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ...**")
            DOWNLOAD_DIR = "downloads"
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            output_template = os.path.join(DOWNLOAD_DIR, f"{title if title else '%(id)s'}.%(ext)s")
            
            if format_id:
                ydl_opts = {
                    "format": format_id,
                    "outtmpl": output_template,
                    "quiet": True,
                    "nocheckcertificate": True,
                    "geo_bypass": True,
                    "socket_timeout": 15,
                    "retries": 3,
                    "fragment_retries": 3,
                }
            else:
                ydl_opts = {
                    "format": "bestaudio[ext=m4a]/bestaudio/best" if not (video or songvideo) else "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "outtmpl": output_template,
                    "quiet": True,
                    "nocheckcertificate": True,
                    "geo_bypass": True,
                    "socket_timeout": 15,
                    "retries": 3,
                    "fragment_retries": 3,
                }
            
            def run_ydl(ydl):
                info = ydl.extract_info(link, download=True)
                return ydl.prepare_filename(info)
            
            file_path = await asyncio.get_event_loop().run_in_executor(
                None, self._yt_dlp_call_with_fallback, run_ydl, ydl_opts
            )
            return file_path, True
        except Exception as e:
            LOGGER(__name__).error(f"Download process finally failed for {vidid}: {e}")
            return None, False

    async def track(self, link: str, videoid: Union[bool, str] = None, fast: bool = False):
        if not link: return None, None
        if videoid: link = self.base + link
        if "v=" in link:
            # Handle standard watch links with multiple parameters
            vid_part = link.split("v=")[1].split("&")[0]
            link = f"https://www.youtube.com/watch?v={vid_part}"
        elif "&" in link:
            link = link.split("&")[0]
        
        # --- Cache Check ---
        if link in self.cache:
             cached_data = self.cache[link]
             return cached_data["details"], cached_data["vidid"]

        # Try metadata logic
        title, duration_min, duration_sec, thumbnail, vidid = await self.details(link, fast=fast)
        if title:
            details = {
                "title": title,
                "link": f"https://www.youtube.com/watch?v={vidid}",
                "vidid": vidid,
                "duration_min": duration_min,
                "thumb": thumbnail,
            }
            # Cache the result
            self.cache[link] = {"details": details, "vidid": vidid}
            
            # Limit cache size to 100 entries
            if len(self.cache) > 100:
                del self.cache[next(iter(self.cache))]
                
            return details, vidid
        
        return None, None

    async def suggestions(self, query: str, limit: int = 5):
        try:
            results = VideosSearch(query, limit=limit)
            results_data = await results.next()
            if results_data.get("result"):
                return results_data["result"]
        except:
            pass
        return []

    async def playlist(self, link, limit, videoid: Union[bool, str] = None):
        try:
            opts = {"quiet": True, "extract_flat": True, "playlist_items": f"1-{limit}"}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link, download=False)
                return [e.get("id") for e in info.get("entries", []) if e]
        except:
            return []

    async def recommend(self, query: str, limit: int = 5, videoid: str = None):
        if not query:
            query = "trending"
        
        query = str(query)
        clean_query = re.sub(r'\(.*?\)|\[.*?\]|official|video|audio|full video', '', query, flags=re.IGNORECASE).strip()
        q_lower = clean_query.lower()
        q_words = q_lower.split()
        
        from difflib import SequenceMatcher
        def similarity(a, b):
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()

        def is_duplicate(title):
            t_lower = title.lower()
            t_words = t_lower.split()
            for qw in q_words:
                for tw in t_words:
                    if similarity(qw, tw) > 0.8:
                        return True
            return False

        try:
            # --- Strategy 1: YouTube Radio (Mix) Discovery (High Fidelity) ---
            # This mimics the "People also search for" vibe by using YouTube's internal radio algo
            target_id = videoid
            if not target_id or str(target_id) == "None":
                def get_initial_id():
                    opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        return ydl.extract_info(f"ytsearch1:{clean_query}", download=False)
                info = await asyncio.get_event_loop().run_in_executor(None, get_initial_id)
                if info and "entries" in info and info["entries"]:
                    target_id = info["entries"][0].get("id")

            if target_id:
                radio_url = f"https://www.youtube.com/watch?v={target_id}&list=RD{target_id}"
                def get_radio_tracks():
                    opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "playlist_items": f"1-{limit + 10}"}
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        return ydl.extract_info(radio_url, download=False)
                
                radio_info = await asyncio.get_event_loop().run_in_executor(None, get_radio_tracks)
                if radio_info and "entries" in radio_info:
                    results = []
                    for entry in radio_info["entries"]:
                        if not entry: continue
                        title = entry.get("title")
                        eid = entry.get("id")
                        if not title or not eid or eid == target_id: continue
                        
                        if is_duplicate(title):
                            continue
                            
                        results.append({
                            "id": eid,
                            "title": title,
                            "link": f"https://www.youtube.com/watch?v={eid}",
                            "duration": entry.get("duration", "0:00")
                        })
                        if len(results) >= limit:
                            break
                    if results:
                        return results

            # --- Strategy 2: iTunes Fallback (Artist/Genre Discovery) ---
            import aiohttp
            itunes_url = f"https://itunes.apple.com/search?term={clean_query}&entity=song&limit=1"
            async with aiohttp.ClientSession() as session:
                async with session.get(itunes_url) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        itunes_res = data.get("results", [])
                        if itunes_res:
                            artist = itunes_res[0].get("artistName")
                            genre = itunes_res[0].get("primaryGenreName")
                            d_term = artist if artist else genre
                            d_url = f"https://itunes.apple.com/search?term={d_term}&entity=song&limit={limit + 20}"
                            async with session.get(d_url) as d_resp:
                                d_data = await d_resp.json(content_type=None)
                                discovered = []
                                for item in d_data.get("results", []):
                                    t = item.get("trackName")
                                    a = item.get("artistName")
                                    if not t or is_duplicate(t): continue
                                    discovered.append(f"{a} {t}")
                                    if len(discovered) >= limit: break
                                
                                if discovered:
                                    final = []
                                    for term in discovered:
                                        def search_yt():
                                            with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
                                                return ydl.extract_info(f"ytsearch1:{term}", download=False)
                                        info = await asyncio.get_event_loop().run_in_executor(None, search_yt)
                                        if info and "entries" in info and info["entries"]:
                                            e = info["entries"][0]
                                            final.append({
                                                "id": e.get("id"),
                                                "title": e.get("title"),
                                                "link": f"https://www.youtube.com/watch?v={e.get('id')}",
                                                "duration": e.get("duration", "0:00")
                                            })
                                    if final: return final

            # --- Strategy 3: YouTube Suggestions Fallback ---
            if target_id:
                info = await Video.getInfo(f"https://www.youtube.com/watch?v={target_id}")
                if info.get("suggestions"):
                    results = []
                    for s in info["suggestions"]:
                        if s.get("id") and s.get("title") and not is_duplicate(s["title"]):
                            results.append({
                                "id": s["id"],
                                "title": s["title"],
                                "link": f"https://www.youtube.com/watch?v={s['id']}",
                                "duration": s.get("duration", "0:00")
                            })
                        if len(results) >= limit: break
                    if results: return results

            # --- Strategy 4: Popular Music Fallback ---
            def extract_popular():
                with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
                    return ydl.extract_info(f"ytsearch{limit + 5}:trending music india", download=False)
            info = await asyncio.get_event_loop().run_in_executor(None, extract_popular)
            if info and "entries" in info:
                results = []
                for entry in info["entries"]:
                    if entry and entry.get("id") and entry.get("title") and not is_duplicate(entry["title"]):
                        results.append({
                            "id": entry.get("id"),
                            "title": entry.get("title"),
                            "link": f"https://www.youtube.com/watch?v={entry.get('id')}",
                            "duration": entry.get("duration", "0:00")
                        })
                    if len(results) >= limit: break
                return results

        except Exception as e:
            LOGGER(__name__).error(f"YouTube Recommend Error: {e}")
        return []

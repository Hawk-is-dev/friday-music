import asyncio
import importlib
import traceback
import os
from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall
import config

# Monkeypatch httpx to support 'proxies' argument for compatibility with libraries using old httpx API
try:
    import httpx
    orig_init = httpx.AsyncClient.__init__
    def patched_init(self, *args, **kwargs):
        if "proxies" in kwargs:
            proxies = kwargs.pop("proxies")
            if proxies and "proxy" not in kwargs:
                if isinstance(proxies, dict):
                    kwargs["proxy"] = proxies.get("all") or proxies.get("http") or proxies.get("https")
                else:
                    kwargs["proxy"] = proxies
        return orig_init(self, *args, **kwargs)
    httpx.AsyncClient.__init__ = patched_init
    
    orig_client_init = httpx.Client.__init__
    def patched_client_init(self, *args, **kwargs):
        if "proxies" in kwargs:
            proxies = kwargs.pop("proxies")
            if proxies and "proxy" not in kwargs:
                if isinstance(proxies, dict):
                    kwargs["proxy"] = proxies.get("all") or proxies.get("http") or proxies.get("https")
                else:
                    kwargs["proxy"] = proxies
        return orig_client_init(self, *args, **kwargs)
    httpx.Client.__init__ = patched_client_init
except ImportError:
    pass




async def safe_start(client, name: str):
    from pyrogram.errors import FloodWait
    from SANYAMUSIC import LOGGER
    while True:
        try:
            await client.start()
            break
        except FloodWait as e:
            LOGGER(__name__).warning(f"[{name}] FLOOD_WAIT encountered: sleeping for {e.value + 5} seconds...")
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            LOGGER(__name__).error(f"[{name}] Failed to start: {type(e).__name__}: {str(e)}")
            raise

async def init():
    from config import BANNED_USERS
    from SANYAMUSIC import LOGGER, app, userbot
    from SANYAMUSIC.core.call import SANYA
    from SANYAMUSIC.misc import sudo
    from SANYAMUSIC.plugins import ALL_MODULES
    from SANYAMUSIC.utils.database import get_banned_users, get_gbanned

    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("𝐒𝐭𝐫𝐢𝐧𝐠 𝐒𝐞𝐬𝐬𝐢𝐨𝐧 𝐍𝐨𝐭 𝐅𝐢𝐥𝐥𝐞𝐝, 𝐏𝐥𝐞𝐚𝐬𝐞 𝐅𝐢𝐥𝐥 𝐀 𝐏𝐲𝐫𝐨𝐠𝐫𝐚𝐦 𝐒𝐞𝐬𝐬𝐢𝐨𝐧")
        exit()
    await sudo()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
        LOGGER(__name__).info(f"Loaded {len(BANNED_USERS)} banned users")
    except Exception as e:
        LOGGER(__name__).error(f"Error loading banned users: {type(e).__name__}: {str(e)}")
        LOGGER(__name__).error(f"Traceback: {traceback.format_exc()}")
        raise
    
    await safe_start(app, "Bot")
    
    for all_module in ALL_MODULES:
        try:
            importlib.import_module("SANYAMUSIC.plugins." + all_module)
            # LOGGER(__name__).info(f"Loaded module: {all_module}")
        except Exception as e:
            LOGGER(__name__).error(f"Failed to load module {all_module}: {type(e).__name__}: {str(e)}")
            LOGGER(__name__).error(f"Traceback: {traceback.format_exc()}")
    LOGGER("SANYAMUSIC.plugins").info("𝐀𝐥𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬 𝐋𝐨𝐚𝐝𝐞𝐝 𝐁𝐚𝐛𝐲🥳...")
    
    try:
        await safe_start(userbot, "Userbot")
        LOGGER(__name__).info("Userbot started successfully")
    except Exception as e:
        LOGGER(__name__).error(f"Error in userbot.start(): {type(e).__name__}: {str(e)}")
        LOGGER(__name__).error(f"Traceback: {traceback.format_exc()}")
        raise
        
    try:
        await SANYA.start()
        LOGGER(__name__).info("PyTgCalls started successfully")
    except Exception as e:
        LOGGER(__name__).error(f"Error in SANYA.start(): {type(e).__name__}: {str(e)}")
        LOGGER(__name__).error(f"Traceback: {traceback.format_exc()}")
        raise
        
    LOGGER("SANYAMUSIC").info(
        "╔═════ஜ۩۞۩ஜ════╗\n  ☠︎︎𝗠𝗔𝗗𝗘 𝗕𝗬 𝗠𝗥 𝗦𝗧𝗔𝗥𝗞\n╚═════ஜ۩۞۩ஜ════╝"
    )

    await idle()
    await app.stop()
    await userbot.stop()
    LOGGER("SANYAMUSIC").info("𝗦𝗧𝗢𝗣 𝗙𝗥𝗜𝗗𝗔𝗬 𝗠𝗨𝗦𝗜𝗖🎻 𝗕𝗢𝗧..")


if __name__ == "__main__":
    import signal
    try:
        if os.name == "nt":
            # ProactorEventLoop is required for asyncio subprocesses (pipes) on Windows
            # which py-tgcalls uses for FFmpeg.
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            # Ignore some signals that cause issues on Windows
            try:
                signal.signal(signal.SIGINT, signal.SIG_DFL)
            except:
                pass
        else:
            try:
                import uvloop
                uvloop.install()
            except ImportError:
                pass
    except Exception:
        pass
    
    try:
        asyncio.run(init())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[FATAL] Crash during startup: {e}")
        traceback.print_exc()


import asyncio
import time
from pyrogram.types import InlineKeyboardMarkup
from SANYAMUSIC import app
from SANYAMUSIC.misc import db, get_played_time
from SANYAMUSIC.utils.database import get_active_chats, is_music_playing, get_lang
from SANYAMUSIC.utils.formatters import seconds_to_min
from SANYAMUSIC.utils.inline.play import stream_markup_timer
from strings import get_string

async def timer():
    while not await asyncio.sleep(10):
        active_chats = await get_active_chats()
        for chat_id in active_chats:
            try:
                if not await is_music_playing(chat_id):
                    continue
                playing = db.get(chat_id)
                if not playing:
                    continue
                
                # Get details
                mystic = playing[0].get("mystic")
                if not mystic:
                    continue
                
                dur = playing[0].get("dur")
                if not dur or dur == "Live" or ":" not in str(dur):
                    continue
                
                # Calculate played time
                played = get_played_time(chat_id)
                played_min = seconds_to_min(played)
                
                # Get language for buttons
                language = await get_lang(chat_id)
                _ = get_string(language)
                
                # Generate markup
                buttons = stream_markup_timer(_, chat_id, played_min, dur)
                
                # Update markup
                try:
                    await mystic.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
                except Exception:
                    continue
                    
            except Exception:
                continue

# Start the timer task
asyncio.create_task(timer())

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
from pyrogram.types import InlineKeyboardMarkup
from SANYAMUSIC.utils.database import get_lang
from SANYAMUSIC.utils.inline.play import song_ended_markup
from config import autoclean
from strings import get_string


async def auto_clean(popped):
    if not popped:
        return
    try:
        from SANYAMUSIC import app
        mystic = popped.get("mystic")
        if mystic:
            try:
                language = await get_lang(popped["chat_id"])
                _ = get_string(language)
                await mystic.edit_reply_markup(
                    reply_markup=InlineKeyboardMarkup(song_ended_markup(_))
                )
            except:
                pass
    except:
        pass
    try:
        rem = popped["file"]
        autoclean.remove(rem)
        count = autoclean.count(rem)
        if count == 0:
            if not any(rem.startswith(p) for p in ["vid_", "live_", "index_"]):
                try:
                    os.remove(rem)
                except:
                    pass
    except:
        pass

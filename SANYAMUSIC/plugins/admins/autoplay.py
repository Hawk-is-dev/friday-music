import random
import re
from typing import Union
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

import config
from SANYAMUSIC import app, YouTube, LOGGER
from SANYAMUSIC.utils.database import is_autoplay_on, autoplay_off, autoplay_on, get_cmode
from SANYAMUSIC.utils.decorators import AdminRightsCheck, ActualAdminCB
from SANYAMUSIC.utils.decorators.language import language, languageCB
from SANYAMUSIC.utils.inline import close_markup
from SANYAMUSIC.utils.formatters import time_to_seconds, clean_text
from SANYAMUSIC.utils.security import is_safe_input
from SANYAMUSIC.utils.throttling import check_flood
from SANYAMUSIC.utils.stream.stream import stream
from config import BANNED_USERS

# --------------------------------------------------------------------------------- #
#                                 RANDOM COLLECTIONS                                #
# --------------------------------------------------------------------------------- #

RANDOM_HINDI_QUERIES = [
    "bollywood hits", "punjabi pop", "indian indie", "hindi romantic", "sufi hits",
    "indian lo-fi", "bollywood remix", "retro hindi", "desi beats", "coke studio india",
    "indian chill", "bollywood acoustic", "trending hindi songs", "ghazals"
]

# --------------------------------------------------------------------------------- #
#                               AUTOPLAY TOGGLE LOGIC                               #
# --------------------------------------------------------------------------------- #

def autoplay_markup(_, status):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["autoplay_5"] if status else _["autoplay_4"],
                callback_data=f"autoplay_toggle|{status}"
            )
        ],
        [
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"], callback_data="close"
            )
        ]
    ]
    return InlineKeyboardMarkup(buttons)

@app.on_message(filters.command(["autoplay", "cautoplay"]) & filters.group & ~BANNED_USERS)
@AdminRightsCheck
async def autoplay_bot(cli, message: Message, _, chat_id):
    status = await is_autoplay_on(chat_id)
    state = _["autoplay_2"] if status else _["autoplay_3"]
    await message.reply_text(
        _["autoplay_1"].format(message.chat.title, state),
        reply_markup=autoplay_markup(_, status)
    )

@app.on_callback_query(filters.regex("autoplay_toggle") & ~BANNED_USERS)
@ActualAdminCB
async def autoplay_toggle_cb(cli, cb: CallbackQuery, _):
    chat_id = cb.message.chat.id
    status = cb.data.split("|")[1]
    
    if status == "True":
        await autoplay_off(chat_id)
        new_status = False
    else:
        await autoplay_on(chat_id)
        new_status = True
        
    state = _["autoplay_2"] if new_status else _["autoplay_3"]
    try:
        await cb.edit_message_text(
            _["autoplay_1"].format(cb.message.chat.title, state),
            reply_markup=autoplay_markup(_, new_status)
        )
    except:
        pass
    await cb.answer(_["admin_autoplay_on" if new_status else "admin_autoplay_off"].format(cb.from_user.first_name))

# --------------------------------------------------------------------------------- #
#                             ADVANCED SUGGESTION LOGIC                             #
# --------------------------------------------------------------------------------- #

@app.on_message(filters.command(["suggest", "suggestions", "suggests"]) & ~BANNED_USERS)
@language
async def suggest_command(client, message, _):
    if not await is_safe_input(message):
        return await message.reply_text("⚠️ <b>Sᴇᴄᴜʀɪᴛʏ Aʟᴇʀᴛ:</b> Yᴏᴜʀ ɪɴᴘᴜᴛ ᴄᴏɴᴛᴀɪɴs ғᴏʀʙɪᴅᴅᴇɴ ᴄʜᴀʀᴀᴄᴛᴇʀs.")
    
    if not await check_flood(message):
        return

    msg = await message.reply_text("<b>Aɴᴀʟʏᴢɪɴɢ ᴠɪʙᴇ ᴀɴᴅ ғɪɴᴅɪɴɢ sᴜɢɢᴇsᴛɪᴏɴs...</b>")
    
    if len(message.command) > 1:
        keyword = message.text.split(None, 1)[1]
        refresh_data = f"refresh_suggestions:{keyword}"
    else:
        keyword = random.choice(RANDOM_HINDI_QUERIES)
        refresh_data = "refresh_suggestions"

    # Use the high-fidelity recommendation engine
    try:
        recommendations = await YouTube.recommend(keyword, limit=8)
    except Exception as e:
        LOGGER(__name__).error(f"Suggestion Error: {e}")
        return await msg.edit_text(f"Could not fetch suggestions for '{keyword}'.")
    
    if not recommendations:
        return await msg.edit_text(f"No high-fidelity suggestions found for '{keyword}'.")

    buttons = []
    for item in recommendations:
        title = clean_text(item['title'])[:30]
        buttons.append([
            InlineKeyboardButton(
                text=f"{title}...",
                callback_data=f"suggest_play:{item['id']}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="Refresh", callback_data=refresh_data),
        InlineKeyboardButton(text="Close", callback_data="close")
    ])

    await msg.edit_text(
        f"<b>❍ Hɪɢʜ-Fɪᴅᴇʟɪᴛʏ Sᴜɢɢᴇsᴛɪᴏɴs</b>\n\n<b>• Bᴀsᴇᴅ ᴏɴ:</b> <i>{keyword}</i>\n<b>• Dɪsᴄᴏᴠᴇʀʏ:</b> YouTube Radio Mix",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex(r"^refresh_suggestions") & ~BANNED_USERS)
@languageCB
async def refresh_suggestions_cb(client, cb: CallbackQuery, _):
    await cb.answer("Rᴇғʀᴇsʜɪɴɢ Tᴏᴘ Vɪʙᴇs...", show_alert=False)
    
    if ":" in cb.data:
        keyword = cb.data.split(":", 1)[1]
        refresh_data = cb.data
    else:
        keyword = random.choice(RANDOM_HINDI_QUERIES)
        refresh_data = "refresh_suggestions"

    try:
        recommendations = await YouTube.recommend(keyword, limit=8)
    except:
        return await cb.answer("Error fetching recommendations.", show_alert=True)

    if not recommendations:
        return await cb.answer("No new suggestions found.", show_alert=True)

    buttons = []
    for item in recommendations:
        title = clean_text(item['title'])[:30]
        buttons.append([
            InlineKeyboardButton(
                text=f"{title}...",
                callback_data=f"suggest_play:{item['id']}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="Refresh", callback_data=refresh_data),
        InlineKeyboardButton(text="Close", callback_data="close")
    ])

    try:
        await cb.edit_message_text(
            f"<b>❍ Hɪɢʜ-Fɪᴅᴇʟɪᴛʏ Sᴜɢɢᴇsᴛɪᴏɴs</b>\n\n<b>• Bᴀsᴇᴅ ᴏɴ:</b> <i>{keyword}</i>\n<b>• Dɪsᴄᴏᴠᴇʀʏ:</b> YouTube Radio Mix",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except:
        pass

@app.on_callback_query(filters.regex(r"^suggest_play:") & ~BANNED_USERS)
@languageCB
async def suggest_play_cb(client, cb: CallbackQuery, _):
    vid_id = cb.data.split(":")[1]
    await cb.answer("Pʀᴏᴄᴇssɪɴɢ Sᴛʀᴇᴀᴍ...", show_alert=False)

    chat_id = cb.message.chat.id
    channel = await get_cmode(chat_id)
    if channel:
        chat_id = channel

    user_id = cb.from_user.id
    user_name = cb.from_user.first_name

    mystic = await cb.message.reply_text(_["play_1"])

    try:
        details, track_id = await YouTube.track(vid_id, True)
    except Exception as e:
        return await mystic.edit_text(_["play_3"] + f"\n\nError: {e}")

    # Check Duration
    if details.get("duration_min"):
        duration_sec = time_to_seconds(details["duration_min"])
        if duration_sec > config.DURATION_LIMIT:
            return await mystic.edit_text(
                _["play_6"].format(config.DURATION_LIMIT_MIN, client.me.mention)
            )

    try:
        await stream(
            client,
            _,
            mystic,
            user_id,
            details,
            chat_id,
            user_name,
            cb.message.chat.id,
            video=None,
            streamtype="youtube",
            forceplay=None,
        )
    except Exception as e:
        await mystic.edit_text(_["general_2"].format(type(e).__name__))
        return

    await mystic.delete()
    try:
        await cb.message.delete()
    except:
        pass

import random
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

import config
from SANYAMUSIC import app, YouTube, LOGGER
from SANYAMUSIC.utils.database import get_cmode
from SANYAMUSIC.utils.decorators.language import language, languageCB
from SANYAMUSIC.utils.formatters import clean_text, time_to_seconds
from SANYAMUSIC.utils.stream.stream import stream
from config import BANNED_USERS

# --------------------------------------------------------------------------------- #
#                                 TRENDING LOGIC                                    #
# --------------------------------------------------------------------------------- #

@app.on_message(filters.command(["trending", "trendings", "popular"]) & ~BANNED_USERS)
@language
async def trending_command(client, message, _):
    msg = await message.reply_text("<b>Fᴇᴛᴄʜɪɴɢ ʟᴀᴛᴇsᴛ ᴛʀᴇɴᴅɪɴɢ ᴍᴜsɪᴄ ғᴏʀ ʏᴏᴜ...</b>")
    
    try:
        # Fetch trending music (Strategy 4 in recommend)
        trending_tracks = await YouTube.recommend("trending music india", limit=10)
    except Exception as e:
        LOGGER(__name__).error(f"Trending Error: {e}")
        return await msg.edit_text("❌ Fᴀɪʟᴇᴅ ᴛᴏ ғᴇᴛᴄʜ ᴛʀᴇɴᴅɪɴɢ ᴍᴜsɪᴄ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.")
    
    if not trending_tracks:
        return await msg.edit_text("🤷 Nᴏ ᴛʀᴇɴᴅɪɴɢ ᴛʀᴀᴄᴋs ғᴏᴜɴᴅ ᴀᴛ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ.")

    buttons = []
    # Create two columns of buttons for better UI
    for i in range(0, len(trending_tracks), 2):
        row = []
        # Column 1
        track1 = trending_tracks[i]
        title1 = clean_text(track1['title'])[:25]
        row.append(InlineKeyboardButton(text=f"{title1}...", callback_data=f"trending_play:{track1['id']}"))
        
        # Column 2
        if i + 1 < len(trending_tracks):
            track2 = trending_tracks[i+1]
            title2 = clean_text(track2['title'])[:25]
            row.append(InlineKeyboardButton(text=f"{title2}...", callback_data=f"trending_play:{track2['id']}"))
        
        buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton(text="Rᴇғʀᴇsʜ", callback_data="refresh_trending"),
        InlineKeyboardButton(text="Cʟᴏsᴇ", callback_data="close")
    ])

    # We'll use a premium looking header
    header_text = (
        "<b>🔥 YᴏᴜTᴜʙᴇ Tʀᴇɴᴅɪɴɢ Mᴜsɪᴄ Cʜᴀʀᴛs</b>\n\n"
        "<i>Dɪsᴄᴏᴠᴇʀ ᴛʜᴇ ʜᴏᴛᴛᴇsᴛ ᴛʀᴀᴄᴋs ᴄᴜʀʀᴇɴᴛʟʏ ᴡᴀᴠɪɴɢ across the platform!</i>\n\n"
        "ᴄʟɪᴄᴋ ᴏɴ ᴀ sᴏɴɢ ʙᴇʟᴏᴡ ᴛᴏ sᴛᴀʀᴛ sᴛʀᴇᴀᴍɪɴɢ ɪᴛ ɪɴsᴛᴀɴᴛʟʏ ⚡"
    )

    await msg.edit_text(
        header_text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex("^refresh_trending$") & ~BANNED_USERS)
@languageCB
async def refresh_trending_cb(client, cb: CallbackQuery, _):
    await cb.answer("Fᴇᴛᴄʜɪɴɢ Nᴇᴡ Cʜᴀʀᴛs...", show_alert=False)
    
    try:
        trending_tracks = await YouTube.recommend("trending music india", limit=10)
    except:
        return await cb.answer("Error refreshing charts.", show_alert=True)

    if not trending_tracks:
        return await cb.answer("No trending tracks found.", show_alert=True)

    buttons = []
    for i in range(0, len(trending_tracks), 2):
        row = []
        track1 = trending_tracks[i]
        title1 = clean_text(track1['title'])[:25]
        row.append(InlineKeyboardButton(text=f"{title1}...", callback_data=f"trending_play:{track1['id']}"))
        
        if i + 1 < len(trending_tracks):
            track2 = trending_tracks[i+1]
            title2 = clean_text(track2['title'])[:25]
            row.append(InlineKeyboardButton(text=f"{title2}...", callback_data=f"trending_play:{track2['id']}"))
        
        buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton(text="Rᴇғʀᴇsʜ", callback_data="refresh_trending"),
        InlineKeyboardButton(text="Cʟᴏsᴇ", callback_data="close")
    ])

    header_text = (
        "<b>🔥 YᴏᴜTᴜʙᴇ Tʀᴇɴᴅɪɴɢ Mᴜsɪᴄ Cʜᴀʀᴛs</b>\n\n"
        "<i>Dɪsᴄᴏᴠᴇʀ ᴛʜᴇ ʜᴏᴛᴛᴇsᴛ ᴛʀᴀᴄᴋs ᴄᴜʀʀᴇɴᴛʟʏ ᴡᴀᴠɪɴɢ across the platform!</i>\n\n"
        "ᴄʟɪᴄᴋ ᴏɴ ᴀ sᴏɴɢ ʙᴇʟᴏᴡ ᴛᴏ sᴛᴀʀᴛ sᴛʀᴇᴀᴍɪɴɢ ɪᴛ ɪɴsᴛᴀɴᴛʟʏ ⚡"
    )

    try:
        await cb.edit_message_text(
            header_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except:
        pass

@app.on_callback_query(filters.regex(r"^trending_play:") & ~BANNED_USERS)
@languageCB
async def trending_play_cb(client, cb: CallbackQuery, _):
    vid_id = cb.data.split(":")[1]
    await cb.answer("Iɴɪᴛɪᴀᴛɪɴɢ Sᴛʀᴇᴀᴍ...", show_alert=False)

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

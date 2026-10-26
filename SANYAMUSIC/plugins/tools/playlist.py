from pyrogram import filters
from pyrogram.types import (InlineKeyboardButton, 
                            InlineKeyboardMarkup, Message, CallbackQuery)
import secrets

from SANYAMUSIC import app, YouTube, LOGGER
from SANYAMUSIC.utils.playlist_db import (
    get_playlists, get_playlist, save_playlist, 
    delete_playlist, is_playlist_exists, toggle_public,
    get_public_playlist, get_playlist_count, add_to_playlist,
    add_to_playlist_by_serial, remove_from_playlist
)
from SANYAMUSIC.utils.database import get_lang
from SANYAMUSIC.utils.decorators.language import language, languageCB
from SANYAMUSIC.utils.stream.stream import stream
from config import BANNED_USERS
import config
from strings import get_string

PLAYLIST_STATE = {}

# --- HELPER: Playlist Markups ---

def playlist_list_markup(playlists, _, is_pm=False):
    buttons = []
    # Serial numbers 1, 2, 3...
    for i, p in enumerate(playlists, 1):
        buttons.append([
            InlineKeyboardButton(text=f"{i}» {p['name']}", callback_data=f"pl_show:{p['name']}")
        ])
    
    # Add creation button
    if len(playlists) < 5:
        if is_pm:
            buttons.append([
                InlineKeyboardButton(text=_["PL_B_17"], callback_data="pl_create_new")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text=_["PL_B_17"], url=f"https://t.me/{app.username}?start=playlist_create")
            ])
        
    buttons.append([
        InlineKeyboardButton(text=_["CLOSE_BUTTON"], callback_data="close")
    ])
    return InlineKeyboardMarkup(buttons)

def playlist_songs_markup(name, songs, is_public, p_id, _, page=0):
    buttons = []
    # 12 songs per page
    limit = 12
    start = page * limit
    end = start + limit
    
    for song in songs[start:end]:
        title = song['title'][:25]
        buttons.append([
            InlineKeyboardButton(
                text=f"{title}...", 
                callback_data=f"pl_play_song:{name}:{song['vidid']}"
            )
        ])
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="Prev", callback_data=f"pl_page:{name}:{page-1}"))
    if end < len(songs):
        nav_buttons.append(InlineKeyboardButton(text="Next", callback_data=f"pl_page:{name}:{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Management Actions
    buttons.append([
        InlineKeyboardButton(text="➕ Add Songs", callback_data=f"pl_add_info:{name}"),
        InlineKeyboardButton(text="➖ Remove Songs", callback_data=f"pl_remove_list:{name}")
    ])
    
    # Bottom Layout Action buttons
    buttons.append([
        InlineKeyboardButton(text=_["PL_B_12"], callback_data=f"pl_play_all:{name}"),
        InlineKeyboardButton(text=_["PL_B_13"], callback_data=f"pl_delete_confirm:{name}")
    ])
    
    status_text = _["PL_B_14"] if is_public else _["PL_B_15"]
    buttons.append([
        InlineKeyboardButton(text=status_text, callback_data=f"pl_toggle_visibility:{name}"),
        InlineKeyboardButton(text=_["PL_B_16"], callback_data=f"pl_share:{name}")
    ])
    
    buttons.append([
        InlineKeyboardButton(text=_["BACK_BUTTON"], callback_data="pl_list_back"),
        InlineKeyboardButton(text=_["CLOSE_BUTTON"], callback_data="close")
    ])
    return InlineKeyboardMarkup(buttons)

# --- COMMANDS ---

@app.on_message(filters.command(["playlist", "pl"]) & ~BANNED_USERS)
@language
async def playlist_command(client, message: Message, _):
    user_id = message.from_user.id
    is_pm = message.chat.type == message.chat.type.PRIVATE

    if len(message.command) < 2:
        # Default: List owned playlists
        playlists = await get_playlists(user_id)
        if not playlists:
            if is_pm:
                markup = InlineKeyboardMarkup([[
                    InlineKeyboardButton(text=_["PL_B_17"], callback_data="pl_create_new")
                ]])
            else:
                markup = InlineKeyboardMarkup([[
                    InlineKeyboardButton(text=_["PL_B_17"], url=f"https://t.me/{app.username}?start=playlist_create")
                ]])
            return await message.reply_text(_["playlist_2"], reply_markup=markup)
        
        return await message.reply_text(
            _["playlist_1"],
            reply_markup=playlist_list_markup(playlists, _, is_pm)
        )

    subcommand = message.command[1].lower()

    if subcommand == "create":
        if not is_pm:
            return await message.reply_text(_["playlist_14"])
        
        if len(message.command) < 3:
            return await message.reply_text("Usᴀɢᴇ: `/playlist create <name>`")
        
        name = message.text.split(None, 2)[2].strip()
        if len(name) > 20: return await message.reply_text(_["playlist_6"])
        if await get_playlist_count(user_id) >= 5: return await message.reply_text(_["playlist_5"])
        if await is_playlist_exists(user_id, name): return await message.reply_text(_["playlist_4"])

        await save_playlist(user_id, name, [])
        await message.reply_text(_["playlist_3"].format(name))

    elif subcommand == "play":
        # Supports playing by Share ID or current user's playlist name
        if len(message.command) < 3: return await message.reply_text("Usᴀɢᴇ: `/playlist play <ID/Name>`")
        identifier = message.command[2]
        playlist = await get_public_playlist(identifier) or await get_playlist(user_id, identifier)
        if not playlist: return await message.reply_text(_["playlist_9"])
        
        songs = playlist.get("songs", [])
        if not songs: return await message.reply_text(_["playlist_11"])
        
        vidids = [s['vidid'] for s in songs]
        msg = await message.reply_text(_["playlist_15"])
        await stream(client, _, msg, user_id, vidids, message.chat.id, message.from_user.first_name, message.chat.id, video=None, streamtype="playlist")

@app.on_message(filters.command(["addsong", "add"]) & ~BANNED_USERS)
@language
async def addsong_command(client, message: Message, _):
    user_id = message.from_user.id
    if len(message.command) < 2:
        return await message.reply_text("Usage: /addsong <song_name> or /addsong <serial> <song_name>")
    
    # Check if first argument is a serial number (1-5)
    args = message.text.split(None, 2)
    serial = 1
    query_str = ""
    
    try:
        if len(args) > 1:
            first_arg = args[1]
            if first_arg.isdigit() and 1 <= int(first_arg) <= 5:
                serial = int(first_arg)
                query_str = args[2] if len(args) > 2 else ""
            else:
                query_str = message.text.split(None, 1)[1]
    except:
        return await message.reply_text("Invalid usage! Try: `/addsong Shape of You`")

    if not query_str:
        return await message.reply_text("Please provide a song name or link!")

    # Support comma separation for multiple songs
    queries = [q.strip() for q in query_str.split(",") if q.strip()]
    msg = await message.reply_text(f"Processing {len(queries)} song(s)...")
    
    added_count = 0
    failed_count = 0
    playlist_name = ""

    for query in queries:
        try:
            details, _ = await YouTube.track(query)
            if not details or isinstance(details, str):
                failed_count += 1
                continue
            
            song_data = {"title": details["title"], "vidid": details["vidid"], "duration": details["duration_min"]}
            res = await add_to_playlist_by_serial(user_id, serial, song_data)
            
            if res == "FULL":
                await msg.edit_text(f"Playlist full! Added {added_count} songs. Max 50 allowed.")
                return
            
            if res == "EXISTS":
                failed_count += 1
                continue
            
            if res:
                playlist_name = res
                added_count += 1
            else:
                failed_count += 1
        except:
            failed_count += 1
    
    if added_count > 0:
        await msg.edit_text(f"Sᴜᴄᴄᴇssғᴜʟʟʏ ᴀᴅᴅᴇᴅ {added_count} sᴏɴɢ(s) ᴛᴏ '**{playlist_name}**'!" + (f"\nFailed: {failed_count}" if failed_count > 0 else ""))
    else:
        await msg.edit_text(f"Fᴀɪʟᴇᴅ ᴛᴏ ᴀᴅᴅ sᴏɴɢs. Pʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ᴛʜᴇ sᴏɴɢ ɴᴀᴍᴇs ᴏʀ ʏᴏᴜʀ ᴘʟᴀʏʟɪsᴛ sᴇʀɪᴀʟ.")

# --- CALLBACKS ---

@app.on_callback_query(filters.regex("pl_create_new") & ~BANNED_USERS)
async def pl_create_new_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    PLAYLIST_STATE[user_id] = True
    await cb.edit_message_text("Please send a name for your new playlist:\n\n*(Max 20 characters)*")
    await cb.answer()

@app.on_message(filters.text & filters.private & ~BANNED_USERS & ~filters.command(["start"]), group=10)
async def playlist_name_receiver(client, message: Message):
    user_id = message.from_user.id
    if user_id not in PLAYLIST_STATE:
        return
    
    del PLAYLIST_STATE[user_id]
    
    if message.text.startswith("/"):
        return await message.reply_text("Cʀᴇᴀᴛɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ.")

    name = message.text.strip()
    language = await get_lang(message.chat.id)
    _ = get_string(language)

    if len(name) > 20: 
        return await message.reply_text(_["playlist_6"])
    if await get_playlist_count(user_id) >= 5: 
        return await message.reply_text(_["playlist_5"])
    if await is_playlist_exists(user_id, name): 
        return await message.reply_text(_["playlist_4"])

    await save_playlist(user_id, name, [])
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(text="Mᴀɴᴀɢᴇ Pʟᴀʏʟɪsᴛ", callback_data=f"pl_show:{name}")
    ]])
    await message.reply_text(_["playlist_3"].format(name), reply_markup=markup)

@app.on_message(filters.command(["rmsong", "rms"]) & ~BANNED_USERS)
@language
async def rmsong_command(client, message, _):
    user_id = message.from_user.id
    if len(message.command) < 3:
        return await message.reply_text("Usᴀɢᴇ: `/rmsong <serial_number> <song_name>`\nE.x: `/rmsong 1 Shape of You`")
    
    try:
        serial = int(message.command[1])
    except:
        return await message.reply_text("Pʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ sᴇʀɪᴀʟ ɴᴜᴍʙᴇʀ (1-5).")
    
    song_title = message.text.split(None, 2)[2].strip()
    playlists = await get_playlists(user_id)
    if not (0 < serial <= len(playlists)):
        return await message.reply_text(f"Pʟᴀʏʟɪsᴛ #{serial} ɴᴏᴛ ғᴏᴜɴᴅ.")
    
    name = playlists[serial-1]["name"]
    if await remove_from_playlist(user_id, name, song_title):
        await message.reply_text(f"🗑 Sᴜᴄᴄᴇssғᴜʟʟʏ ʀᴇᴍᴏᴠᴇᴅ '**{song_title[:25]}**' ғʀᴏᴍ '**{name}**'!")
    else:
        await message.reply_text(f"Sᴏɴɢ '**{song_title[:25]}**' ɴᴏᴛ ғᴏᴜɴᴅ ɪɴ '**{name}**'.")

@app.on_message(filters.command(["plplay", "playlistplay"]) & ~BANNED_USERS)
@language
async def plplay_command(client, message, _):
    if len(message.command) < 2:
        return await message.reply_text("Usᴀɢᴇ: `/plplay <Unique_ID>`\nE.x: `/plplay abcde123`")
    
    identifier = message.command[1]
    playlist = await get_public_playlist(identifier)
    if not playlist:
        return await message.reply_text(
            "❌ Pʟᴀʏʟɪsᴛ ᴡɪᴛʜ ᴛʜɪs ID ɴᴏᴛ ғᴏᴜɴᴅ ᴏʀ ɪs ᴘʀɪᴠᴀᴛᴇ!\n\n"
            "» Mᴀᴋᴇ sᴜʀᴇ ᴛʜᴇ ID ɪs ᴄᴏʀʀᴇᴄᴛ ᴀɴᴅ ᴛʜᴇ ᴏᴡɴᴇʀ ʜᴀs sᴇᴛ ᴛʜᴇ ᴘʟᴀʏʟɪsᴛ ᴛᴏ **PUBLIC**."
        )
    
    songs = playlist.get("songs", [])
    if not songs:
        return await message.reply_text("Tʜɪs ᴘʟᴀʏʟɪsᴛ ɪs ᴇᴍᴘᴛʏ!")
    
    msg = await message.reply_text(f"» Loading songs from {playlist['name']}...")
    vidids = [s['vidid'] for s in songs]
    await stream(client, _, msg, message.from_user.id, vidids, message.chat.id, message.from_user.first_name, message.chat.id, video=None, streamtype="playlist")

# --- CALLBACKS ---

@app.on_callback_query(filters.regex("^pl_add_info:") & ~BANNED_USERS)
async def pl_add_info_cb(client, cb: CallbackQuery):
    name = cb.data.split(":")[1]
    playlists = await get_playlists(cb.from_user.id)
    serial = 0
    for i, p in enumerate(playlists, 1):
        if p['name'] == name:
            serial = i
            break
    
    text = (
        f"**➕ Add Songs to {name}**\n\n"
        "To add a song, use the command below:\n"
        f"`/addsong {serial} <song_name>`\n\n"
        "Simply copy and replace '<song_name>' with your choice!"
    )
    buttons = [[InlineKeyboardButton(text="Back", callback_data=f"pl_show:{name}")]]
    await cb.answer(f"Use: /addsong {serial} <name>", show_alert=True)
    try: await cb.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except: pass

@app.on_callback_query(filters.regex("^pl_share:") & ~BANNED_USERS)
@languageCB
async def pl_share_cb(client, cb: CallbackQuery, _):
    name = cb.data.split(":")[1]
    user_id = cb.from_user.id
    playlist = await get_playlist(user_id, name)
    
    if not playlist.get("is_public"):
        return await cb.answer(_["playlist_12"], show_alert=True)
    
    p_id = playlist.get("playlist_id")
    text = (
        f"**🔗 Share Playlist: {name}**\n\n"
        f"**ID:** `{p_id}`\n\n"
        f"**Command:** `/plplay {p_id}`\n\n"
        "Others can play your collection using this ID!"
    )
    
    buttons = [
        [InlineKeyboardButton(text="📋 Copy ID", switch_inline_query_current_chat=str(p_id))],
        [InlineKeyboardButton(text="Back", callback_data=f"pl_show:{name}")]
    ]
    
    await cb.answer("Playlist Share Info Generated!", show_alert=False)
    await cb.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("^pl_remove_list:") & ~BANNED_USERS)
@languageCB
async def pl_remove_list_cb(client, cb: CallbackQuery, _):
    name = cb.data.split(":")[1]
    user_id = cb.from_user.id
    playlist = await get_playlist(user_id, name)
    songs = playlist.get("songs", [])
    
    if not songs: return await cb.answer(_["playlist_11"], show_alert=True)
    
    # Show alert with command
    playlists = await get_playlists(user_id)
    serial = 0
    for i, p in enumerate(playlists, 1):
        if p['name'] == name:
            serial = i
            break
    await cb.answer(f"Use: /rmsong {serial} <song name>", show_alert=True)
    
    buttons = []
    for i, song in enumerate(songs[:15], 1):
        buttons.append([
            InlineKeyboardButton(text=f"🗑 {song['title'][:25]}", callback_data=f"pl_remove_song:{name}:{i-1}")
        ])
    
    buttons.append([InlineKeyboardButton(text=_["BACK_BUTTON"], callback_data=f"pl_show:{name}")])
    await cb.edit_message_text(f"**🗑 Rᴇᴍᴏᴠᴇ Sᴏɴɢs ғʀᴏᴍ {name}**\n\nSᴇʟᴇᴄᴛ ᴀ sᴏɴɢ ᴛᴏ ᴅᴇʟᴇᴛᴇ:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("^pl_remove_song:") & ~BANNED_USERS)
@languageCB
async def pl_remove_song_cb(client, cb: CallbackQuery, _):
    parts = cb.data.split(":")
    name, index = parts[1], int(parts[2])
    user_id = cb.from_user.id
    
    playlist = await get_playlist(user_id, name)
    songs = playlist.get("songs", [])
    if index < len(songs):
        song_title = songs[index]['title']
        songs.pop(index)
        await save_playlist(user_id, name, songs, playlist.get("is_public", False))
        await cb.answer(f"🗑 Rᴇᴍᴏᴠᴇᴅ: {song_title[:20]}...", show_alert=False)
        return await pl_remove_list_cb(client, cb)
    
    await cb.answer("Sᴏɴɢ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)

@app.on_callback_query(filters.regex("^pl_show:") & ~BANNED_USERS)
@languageCB
async def show_playlist_cb(client, cb: CallbackQuery, _):
    name = cb.data.split(":")[1]
    user_id = cb.from_user.id
    playlist = await get_playlist(user_id, name)
    if not playlist: return await cb.answer(_["playlist_9"], show_alert=True)

    songs = playlist.get("songs", [])
    status = _["PL_B_14"] if playlist.get("is_public") else _["PL_B_15"]
    text = _["playlist_10"].format(playlist.get("playlist_id", "N/A"), name, status, len(songs))
    
    if not songs: text += f"\n\n{_['playlist_11']}"
    
    await cb.edit_message_text(text, reply_markup=playlist_songs_markup(name, songs, playlist.get("is_public"), None, _))

@app.on_callback_query(filters.regex("^pl_page:") & ~BANNED_USERS)
@languageCB
async def pl_page_cb(client, cb: CallbackQuery, _):
    parts = cb.data.split(":")
    name, page = parts[1], int(parts[2])
    user_id = cb.from_user.id
    playlist = await get_playlist(user_id, name)
    if not playlist: return await cb.answer(_["playlist_9"], show_alert=True)
    
    songs = playlist.get("songs", [])
    status = _["PL_B_14"] if playlist.get("is_public") else _["PL_B_15"]
    text = _["playlist_10"].format(playlist.get("playlist_id", "N/A"), name, status, len(songs))
    
    if not songs: text += f"\n\n{_['playlist_11']}"
    
    await cb.edit_message_text(text, reply_markup=playlist_songs_markup(name, songs, playlist.get("is_public"), None, _, page=page))

@app.on_callback_query(filters.regex("^pl_list_back") & ~BANNED_USERS)
@languageCB
async def list_back_cb(client, cb: CallbackQuery, _):
    user_id = cb.from_user.id
    playlists = await get_playlists(user_id)
    is_pm = cb.message.chat.type == cb.message.chat.type.PRIVATE
    await cb.edit_message_text(_["playlist_1"], reply_markup=playlist_list_markup(playlists, _, is_pm))

@app.on_callback_query(filters.regex("^pl_toggle_visibility:") & ~BANNED_USERS)
async def toggle_visibility_cb(client, cb: CallbackQuery):
    name = cb.data.split(":")[1]
    user_id = cb.from_user.id
    new_status = await toggle_public(user_id, name)
    await cb.answer(f"Pʟᴀʏʟɪsᴛ ɪs ɴᴏᴡ {'PUBLI☪' if new_status else 'PRIVATE'}", show_alert=False)
    await show_playlist_cb(client, cb)

@app.on_callback_query(filters.regex("^pl_play_song:") & ~BANNED_USERS)
@languageCB
async def play_playlist_song_cb(client, cb: CallbackQuery, _):
    vidid = cb.data.split(":")[2]
    user_id = cb.from_user.id
    await cb.answer("Streaming Selected Track...", show_alert=False)
    mystic = await cb.message.reply_text(_["play_1"])
    try:
        details, _ = await YouTube.track(vidid, videoid=True)
        await stream(client, _, mystic, user_id, details, cb.message.chat.id, cb.from_user.first_name, cb.message.chat.id, video=None, streamtype="youtube")
    except Exception as e: await mystic.edit_text(f"Error: {e}")

@app.on_callback_query(filters.regex("^pl_play_all:") & ~BANNED_USERS)
@languageCB
async def play_playlist_all_cb(client, cb: CallbackQuery, _):
    name = cb.data.split(":")[1]
    user_id = cb.from_user.id
    playlist = await get_playlist(user_id, name)
    songs = playlist.get("songs", [])
    if not songs: return await cb.answer(_["playlist_11"], show_alert=True)
    
    songs = playlist.get("songs", [])
    if not songs: return await cb.answer(_["playlist_11"], show_alert=True)
    
    vidids = [s['vidid'] for s in songs]
    await cb.answer("Starting Playlist...", show_alert=False)
    mystic = await cb.message.reply_text(_["playlist_15"])
    await stream(client, _, mystic, user_id, vidids, cb.message.chat.id, cb.from_user.first_name, cb.message.chat.id, video=None, streamtype="playlist")
    try: await cb.message.delete()
    except: pass

@app.on_callback_query(filters.regex("^pl_delete_confirm:") & ~BANNED_USERS)
@languageCB
async def delete_confirm_cb(client, cb: CallbackQuery, _):
    name = cb.data.split(":")[1]
    user_id = cb.from_user.id
    if await delete_playlist(user_id, name):
         await cb.answer(_["playlist_8"].format(name), show_alert=True)
         await list_back_cb(client, cb)
    else: await cb.answer(_["playlist_9"], show_alert=True)

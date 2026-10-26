
import aiohttp
from pyrogram import filters
from pyrogram.types import Message
from SANYAMUSIC import app
from config import BANNED_USERS
from SANYAMUSIC.utils.decorators.language import language

@app.on_message(filters.command(["lyrics", "lyric"]) & ~BANNED_USERS)
@language
async def lyrics_command(client, message: Message, _):
    if len(message.command) < 2:
        return await message.reply_text(_["lyrics_1"])
    
    query = message.text.split(None, 1)[1]
    mystic = await message.reply_text(_["lyrics_2"])
    
    url = f"https://lrclib.net/api/search?q={query}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return await mystic.edit_text(_["lyrics_3"].format(query))
                
                data = await response.json()
                if not data:
                    return await mystic.edit_text(_["lyrics_3"].format(query))
                
                # Take the first search result
                lyrics_data = data[0]
                lyrics = lyrics_data.get("plainLyrics") or lyrics_data.get("syncedLyrics")
                title = lyrics_data.get("name", query)
                artist = lyrics_data.get("artistName", "")
                album = lyrics_data.get("albumName", "")
                
                if not lyrics:
                    return await mystic.edit_text(_["lyrics_3"].format(query))
                
                # Format: Title - Artist (Album)
                # Lyrics
                formatted_lyrics = f"📌 **Tɪᴛʟᴇ:** {title}\n👤 **Aʀᴛɪsᴛ:** {artist}\n"
                if album:
                    formatted_lyrics += f"📀 **Aʟʙᴜᴍ:** {album}\n"
                formatted_lyrics += f"\n{lyrics}"
                
                if len(formatted_lyrics) > 4096:
                    # Message too long, Telegram limit is 4096 characters per message.
                    # Send in multiple messages.
                    for i in range(0, len(formatted_lyrics), 4096):
                        await message.reply_text(formatted_lyrics[i:i+4096])
                    return await mystic.delete()
                
                await mystic.edit_text(formatted_lyrics)
                
    except Exception as e:
        await mystic.edit_text(f"Eʀʀᴏʀ: {e}")

__help__ = """
  ❍ /lyrics <song name> *:* Fᴇᴛᴄʜᴇs ʟʏʀɪᴄs ᴏғ ᴛʜᴇ sᴘᴇᴄɪғɪᴇᴅ sᴏɴɢ.
"""

__mod_name__ = "Lʏʀɪᴄs"


import random
import aiohttp
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from SANYAMUSIC import app
from config import BANNED_USERS

@app.on_message(filters.command("wish") & ~BANNED_USERS)
async def wish_command(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("» ᴀᴅᴅ ᴡɪsʜ ʙᴀʙʏ🥀!")

    query = message.text.split(None, 1)[1]
    wish_count = random.randint(1, 100)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://nekos.best/api/v2/happy") as resp:
                if resp.status == 200:
                    api_data = await resp.json()
                    animation_url = api_data["results"][0]["url"]
                else:
                    animation_url = "https://64.media.tumblr.com/d701f53eb5681e87a957a547980371d2/tumblr_nbjmdrQyje1qa94xto1_500.gif"
    except:
        animation_url = "https://64.media.tumblr.com/d701f53eb5681e87a957a547980371d2/tumblr_nbjmdrQyje1qa94xto1_500.gif"

    wish_text = (
        f"✨ **ʜᴇʏ! {message.from_user.first_name}!**\n"
        f"✨ **ʏᴏᴜʀ ᴡɪsʜ:** {query}\n"
        f"✨ **ᴘᴏssɪʙʟᴇ ᴛᴏ:** {wish_count}%"
    )
    
    await message.reply_animation(
        animation=animation_url,
        caption=wish_text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✙ ʌᴅᴅ ϻє ✙", url=f"https://t.me/{app.username}?startgroup=true")]]
        )
    )

@app.on_message(filters.command("cute") & ~BANNED_USERS)
async def cute_command(client, message: Message):
    if not message.reply_to_message:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
    else:
        user_id = message.reply_to_message.from_user.id
        user_name = message.reply_to_message.from_user.first_name

    mention = f"[{user_name}](tg://user?id={user_id})"
    percentage = random.randint(1, 100)
    cute_text = f"👀 {mention} **{percentage}%** ᴄᴜᴛᴇ ʙᴀʙʏ🥀"
    
    gif_url = "https://64.media.tumblr.com/d701f53eb5681e87a957a547980371d2/tumblr_nbjmdrQyje1qa94xto1_500.gif"

    await message.reply_document(
        document=gif_url,
        caption=cute_text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✙ ʌᴅᴅ ϻє ✙", url=f"https://t.me/{app.username}?startgroup=true")]]
        )
    )

__help__ = """
  » /wish <query> *:* Wɪsʜᴇs sᴏᴍᴇᴛʜɪɴɢ ᴀɴᴅ sʜᴏᴡs ᴘᴏssɪʙɪʟɪᴛʏ.
  » /cute *:* Cʜᴇᴄᴋs ʜᴏᴡ ᴄᴜᴛᴇ ʏᴏᴜ ᴀʀᴇ.
"""
__mod_name__ = "Wɪsʜ/Cᴜᴛᴇ"

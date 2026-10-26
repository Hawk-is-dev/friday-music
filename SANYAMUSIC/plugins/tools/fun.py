import random
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.enums import ParseMode
from SANYAMUSIC import app as bot
import httpx
import config 

# Define missing variables locally to fix ModuleNotFoundError
SEX_IMAGES = ["https://telegra.ph/file/d30d11c4365c025c25e3e.jpg"]

command_to_category = {
    "cuddle": "cuddle",
    "cry": "cry",
    "hug": "hug",
    "kiss": "kiss",
    "bully": "bully",
    "blush": "blush",
    "smile": "smile",
    "sex": "sex",
    "slap": "slap",
    "kill": "kill",
    "happy": "happy",
    "dance": "dance",
}

async def delete_after(message: Message, delay: int = 600):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass
    
COMMAND_PREFIXES = config.COMMAND_PREFIXES
BASE_URL = config.BASE_URL

# Command handler for /hug
@bot.on_message(filters.command("hug" , prefixes=COMMAND_PREFIXES) & filters.group)
async def hug_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        msg = await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿'𝘀 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗼𝗿 𝗽𝗿𝗼𝘃𝗶ᴅ𝗲 𝗮 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲 𝘁𝗼 𝘀𝗲𝗻𝗱 𝗮 𝗵𝘂𝗴 𝗿𝗲𝗾𝘂𝗲𝘀𝘁.")
        asyncio.create_task(delete_after(msg))
        return

    user_a = message.from_user

    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        username = message.command[1]
        try:
            user_b = await client.get_users(username)
        except Exception as e:
            msg = await message.reply_text(f"𝗖𝗼𝘂𝗹𝗱 𝗻𝗼𝘁 𝗳𝗶𝗻𝗱 𝘂𝘀𝗲𝗿 {username}.")
            asyncio.create_task(delete_after(msg))
            return

    bot_id = (await client.get_me()).id
    if user_b.id == bot_id:
        msg = await message.reply_text("𝑁𝑜 𝑡ℎ𝑎𝑛𝑘𝑠, 𝐼 𝑑𝑜𝑛'𝑡 𝑛𝑒𝑒𝑑 𝑎 ℎ𝑢𝑔 𝑟𝑖𝑔ℎ𝑡 𝑛𝑜𝑤.")
        asyncio.create_task(delete_after(msg))
        return

    if user_a.id == user_b.id:
        msg = await message.reply_text("𝑌𝑜𝑢 𝑐𝑎𝑛𝑛𝑜𝑡 𝑠𝑒𝑛𝑑 𝑎 ℎ𝑢𝑔 𝑟𝑒𝑞𝑢𝑒𝑠𝑡 𝑡𝑜 𝑦𝑜𝑢𝑟𝑠𝑒𝑙𝑓.")
        asyncio.create_task(delete_after(msg))
        return

    inline_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("𝗔𝗰𝗰𝗲𝗽𝘁", callback_data=f"accept_hug:{user_a.id}:{user_b.id}"),
                InlineKeyboardButton("𝗥𝗲𝗷𝗲𝗰𝘁", callback_data=f"reject_hug:{user_a.id}:{user_b.id}")
            ]
        ]
    )

    msg = await message.reply_text(
        f"🤗 **[{user_b.first_name}](tg://user?id={user_b.id})**, **[{user_a.first_name}](tg://user?id={user_a.id})** wants to send you a hug! 🤗\n\n"
        "Will you accept the hug?",
        reply_markup=inline_keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    asyncio.create_task(delete_after(msg))

@bot.on_callback_query(filters.regex(r"^accept_hug:(\d+):(\d+)$"))
async def accept_hug_callback(client: Client, callback_query):
    data = callback_query.data.split(":")
    user_a_id = int(data[1])
    user_b_id = int(data[2])

    if callback_query.from_user.id != user_b_id:
        await callback_query.answer("𝗼𝗻𝗹𝘆 𝘁𝗵𝗲 𝗿𝗲𝗰𝗶ᴘ𝗶𝗲𝗻𝘁 𝗰𝗮𝗻 𝗮𝗰𝗰𝗲ᴘ𝘁 𝘁𝗵𝗶𝘀 𝗵𝘂𝗴 𝗿𝗲𝗾𝘂𝗲𝘀𝘁.", show_alert=True)
        return

    user_a = await client.get_users(user_a_id)
    hug_image_url = await fetch_image("hug")
    await callback_query.message.delete()

    msg = await client.send_photo(
        chat_id=callback_query.message.chat.id,
        photo=hug_image_url,
        caption=f"💞 **[{callback_query.from_user.first_name}](tg://user?id={user_b_id})** accepted the hug from **[{user_a.first_name}](tg://user?id={user_a_id})**! 💞",
        parse_mode=ParseMode.MARKDOWN
    )
    asyncio.create_task(delete_after(msg))
    await callback_query.answer("Hug accepted!")

@bot.on_callback_query(filters.regex(r"^reject_hug:(\d+):(\d+)$"))
async def reject_hug_callback(client: Client, callback_query):
    data = callback_query.data.split(":")
    user_b_id = int(data[2])

    if callback_query.from_user.id != user_b_id:
        await callback_query.answer("Only the recipient can reject this request.", show_alert=True)
        return

    await callback_query.message.delete()
    msg = await client.send_message(
        chat_id=callback_query.message.chat.id,
        text=f"💔 **[{callback_query.from_user.first_name}](tg://user?id={user_b_id})** rejected the hug... Ouch."
    )
    asyncio.create_task(delete_after(msg))
    await callback_query.answer("Request rejected.")

# Command handler for /kiss
@bot.on_message(filters.command("kiss"  , prefixes=COMMAND_PREFIXES) & filters.group)
async def kiss_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿 𝗼𝗿 𝘁𝗮𝗴 𝘁𝗵𝗲𝗺.")

    user_a = message.from_user
    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        try:
            user_b = await client.get_users(message.command[1])
        except:
            return await message.reply_text("User not found.")

    if user_b.id == (await client.get_me()).id:
        return await message.reply_text("Get lost!, I don't want a kiss from you.")

    if user_a.id == user_b.id:
        return await message.reply_text("Why are you single? You know, nowadays everyone is committed except you!")

    inline_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("𝗔𝗰𝗰𝗲𝗽𝘁", callback_data=f"accept_kiss:{user_a.id}:{user_b.id}"),
                InlineKeyboardButton("𝗥𝗲𝗷𝗲𝗰𝘁", callback_data=f"reject_kiss:{user_a.id}:{user_b.id}")
            ]
        ]
    )

    msg = await message.reply_text(
        f"💞 **[{user_b.first_name}](tg://user?id={user_b.id})** see **[{user_a.first_name}](tg://user?id={user_a.id})** wants to kiss you! 💞\n\n"
        "Will you accept the kiss?",
        reply_markup=inline_keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    asyncio.create_task(delete_after(msg))

@bot.on_callback_query(filters.regex(r"^accept_kiss:(\d+):(\d+)$"))
async def accept_kiss_callback(client: Client, cb):
    if cb.from_user.id != int(cb.data.split(":")[2]):
        return await cb.answer("Only the recipient can accept!", show_alert=True)
    
    user_a_id = int(cb.data.split(":")[1])
    user_a = await client.get_users(user_a_id)
    kiss_image_url = await fetch_image("kiss")
    await cb.message.delete()
    msg = await client.send_photo(
        chat_id=cb.message.chat.id,
        photo=kiss_image_url,
        caption=f"💓 **[{cb.from_user.first_name}](tg://user?id={cb.from_user.id})** accepted the kiss from **[{user_a.first_name}](tg://user?id={user_a_id})**! 💓",
        parse_mode=ParseMode.MARKDOWN
    )
    asyncio.create_task(delete_after(msg))
    await cb.answer("Kiss accepted!")

@bot.on_callback_query(filters.regex(r"^reject_kiss:(\d+):(\d+)$"))
async def reject_kiss_callback(client: Client, cb):
    user_a_id = int(cb.data.split(":")[1])
    user_b_id = int(cb.data.split(":")[2])
    
    if cb.from_user.id != user_b_id:
        return await cb.answer("Only the recipient can reject!", show_alert=True)
    
    user_a = await client.get_users(user_a_id)
    await cb.message.delete()
    msg = await client.send_message(
        chat_id=cb.message.chat.id,
        text=f"😒 **[{cb.from_user.first_name}](tg://user?id={user_b_id})** just rejected the kiss from **[{user_a.first_name}](tg://user?id={user_a_id})**. Better luck next time!"
    )
    asyncio.create_task(delete_after(msg))
    await cb.answer("Request rejected.")

# Command handler for /slap
@bot.on_message(filters.command("slap"  , prefixes=COMMAND_PREFIXES) & filters.group)
async def slap_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿 𝗼𝗿 𝘁𝗮𝗴 𝘁𝗵𝗲𝗺.")

    user_a = message.from_user
    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        try:
            user_b = await client.get_users(message.command[1])
        except:
            return await message.reply_text("User not found.")

    slap_image_url = await fetch_image("slap")
    msg = await client.send_photo(
        chat_id=message.chat.id,
        photo=slap_image_url,
        caption=f"👋 **[{user_a.first_name}](tg://user?id={user_a.id})** slapped **[{user_b.first_name}](tg://user?id={user_b.id})**! Ouch! 💥",
        parse_mode=ParseMode.MARKDOWN
    )
    asyncio.create_task(delete_after(msg))

# Command handler for /kill
@bot.on_message(filters.command("kill"  , prefixes=COMMAND_PREFIXES) & filters.group)
async def kill_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿 𝗼𝗿 𝘁𝗮𝗴 𝘁𝗵𝗲𝗺.")

    user_a = message.from_user
    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        try:
            user_b = await client.get_users(message.command[1])
        except:
            return await message.reply_text("User not found.")

    kill_image_url = await fetch_image("kill")
    msg = await client.send_photo(
        chat_id=message.chat.id,
        photo=kill_image_url,
        caption=f"💀 **[{user_a.first_name}](tg://user?id={user_a.id})** has killed **[{user_b.first_name}](tg://user?id={user_b.id})**! 😱",
        parse_mode=ParseMode.MARKDOWN
    )
    asyncio.create_task(delete_after(msg))

# Command handler for /sex
@bot.on_message(filters.command("sex"  , prefixes=COMMAND_PREFIXES) & filters.group)
async def sex_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿 𝗼𝗿 𝘁𝗮𝗴 𝘁𝗵𝗲𝗺.")

    user_a = message.from_user
    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        try:
            user_b = await client.get_users(message.command[1])
        except:
            return await message.reply_text("User not found.")

    if user_b.id == (await client.get_me()).id:
        return await message.reply_text("Get lost, I don't want to have sex with you.")

    inline_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("𝗔𝗰𝗰𝗲𝗽𝘁", callback_data=f"accept_sex:{user_a.id}:{user_b.id}"),
                InlineKeyboardButton("𝗥𝗲𝗷𝗲𝗰𝘁", callback_data=f"reject_sex:{user_a.id}:{user_b.id}")
            ]
        ]
    )

    msg = await message.reply_text(
        f"💞 **[{user_b.first_name}](tg://user?id={user_b.id})**, **[{user_a.first_name}](tg://user?id={user_a.id})** wants to have sex with you! 💞\n\n"
        "Will you accept?",
        reply_markup=inline_keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    asyncio.create_task(delete_after(msg))

@bot.on_callback_query(filters.regex(r"^(accept|reject)_sex:(\d+):(\d+)$"))
async def sex_callback(client: Client, cb):
    user_a_id = int(cb.data.split(":")[2])
    user_b_id = int(cb.data.split(":")[3])
    
    if cb.from_user.id != user_b_id:
        return await cb.answer("Only the recipient can decide!", show_alert=True)
    
    user_a = await client.get_users(user_a_id)
    await cb.message.delete()
    if "accept" in cb.data:
        sex_image_url = random.choice(SEX_IMAGES)
        msg = await client.send_photo(
            chat_id=cb.message.chat.id,
            photo=sex_image_url,
            caption=f"💓 **[{cb.from_user.first_name}](tg://user?id={user_b_id})** and **[{user_a.first_name}](tg://user?id={user_a_id})** just did it! What do you think, will they have a baby? 👶",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        msg = await client.send_message(
            chat_id=cb.message.chat.id, 
            text=f"❌ **[{cb.from_user.first_name}](tg://user?id={user_b_id})** rejected the sex request from **[{user_a.first_name}](tg://user?id={user_a_id})**."
        )
    asyncio.create_task(delete_after(msg))
    await cb.answer("Decision recorded.")

# --- PROPOSE / APPROACH / CRUSH ---

@bot.on_message(filters.command(["propose", "approach"], prefixes=COMMAND_PREFIXES) & filters.group)
async def propose_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text(f"𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿 𝗼𝗿 𝘁𝗮𝗴 𝘁𝗵𝗲𝗺.")

    user_a = message.from_user
    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        try:
            user_b = await client.get_users(message.command[1])
        except:
            return await message.reply_text("User not found.")

    action = "propose" if "propose" in message.command[0] else "approach"
    emoji = "💍" if action == "propose" else "🤝"
    
    inline_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("𝗔𝗰𝗰𝗲𝗽𝘁", callback_data=f"accept_social:{action}:{user_a.id}:{user_b.id}"),
                InlineKeyboardButton("𝗥𝗲𝗷𝗲𝗰𝘁", callback_data=f"reject_social:{action}:{user_a.id}:{user_b.id}")
            ]
        ]
    )

    msg = await message.reply_text(
        f"{emoji} **[{user_b.first_name}](tg://user?id={user_b.id})**, **[{user_a.first_name}](tg://user?id={user_a.id})** wants to **{action}** to you! {emoji}\n\n"
        f"Will you accept?",
        reply_markup=inline_keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    asyncio.create_task(delete_after(msg))

@bot.on_callback_query(filters.regex(r"^(accept|reject)_social:(propose|approach):(\d+):(\d+)$"))
async def social_callback(client: Client, cb):
    choice, action, user_a_id, user_b_id = cb.data.split(":")[0], cb.data.split(":")[1], int(cb.data.split(":")[2]), int(cb.data.split(":")[3])
    
    if cb.from_user.id != user_b_id:
        return await cb.answer("Only the recipient can decide!", show_alert=True)

    user_a = await client.get_users(user_a_id)
    user_b = await client.get_users(user_b_id)
    await cb.message.delete()

    if "accept" in choice:
        emoji = "💖" if action == "propose" else "✨"
        text = f"{emoji} **[{user_b.first_name}](tg://user?id={user_b.id})** accepted the **{action}** from **[{user_a.first_name}](tg://user?id={user_a_id})**! {emoji}"
    else:
        emoji = "💔"
        text = f"{emoji} **[{user_b.first_name}](tg://user?id={user_b.id})** rejected the **{action}** from **[{user_a.first_name}](tg://user?id={user_a_id})**... {emoji}"

    msg = await client.send_message(chat_id=cb.message.chat.id, text=text)
    asyncio.create_task(delete_after(msg))
    await cb.answer("Decision recorded.")

@bot.on_message(filters.command(["crush"], prefixes=COMMAND_PREFIXES) & filters.group)
async def crush_command(client: Client, message: Message):
    chat_id = message.chat.id
    users = []
    async for m in client.get_chat_members(chat_id, limit=200):
        if not m.user.is_bot and m.user.id != message.from_user.id:
            users.append(m.user)
    
    if not users:
        return await message.reply_text("Not enough members to find a crush!")

    target = random.choice(users)
    msg = await message.reply_text(
        f"💘 **[{message.from_user.first_name}](tg://user?id={message.from_user.id})**'s secret crush in this group is... **[{target.first_name}](tg://user?id={target.id})**! 🙈💞"
    )
    asyncio.create_task(delete_after(msg))

# Function to fetch the image from the API
async def fetch_image(category: str) -> str:
    url = f"{BASE_URL}/sfw/{category}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status() 
            data = response.json()
            return data.get("url", None)
    except:
        return None

# Generic handler for simple image/mood commands
mood_cmds = ["cuddle", "cry", "bully", "blush", "smile", "happy", "dance"]
@bot.on_message(filters.command(mood_cmds, prefixes=COMMAND_PREFIXES) & filters.group)
async def send_mood_image(client: Client, message: Message):
    command = message.command[0].lower()
    category = command_to_category.get(command, command)
    
    user_a = message.from_user
    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
        mention_a = f"[{user_a.first_name}](tg://user?id={user_a.id})"
        mention_b = f"[{user_b.first_name}](tg://user?id={user_b.id})"
        caption = f"✨ **{mention_a}** {command}s **{mention_b}**!"
    else:
        mention_a = f"[{user_a.first_name}](tg://user?id={user_a.id})"
        caption = f"✨ **{mention_a}** is feeling **{command}**!"

    try:
        image_url = await fetch_image(category)
        if image_url:
            msg = await message.reply_photo(
                photo=image_url, 
                caption=caption,
                parse_mode=ParseMode.MARKDOWN
            )
            asyncio.create_task(delete_after(msg))
    except:
        pass

__module__ = "𝖥𝗎𝗇"
__help__ = """**𝖴𝗌𝖾𝗋 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
Detailed Fun module documentation is available in the help menu.
"""

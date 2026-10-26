from io import BytesIO
from pyrogram import Client, filters
from pyrogram.types import Message
from SANYAMUSIC import app
from httpx import AsyncClient, Timeout
import base64
from config import LOGGER_ID

# ------------------------- CONFIGURATION -------------------------
# Use LOGGER_ID from config.py
LOG_GROUP_ID = LOGGER_ID
# -----------------------------------------------------------------

fetch = AsyncClient(
    http2=True,
    verify=False,
    headers={
        "Accept-Language": "id-ID",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edge/107.0.1418.42",
    },
    timeout=Timeout(20),
)

class QuotlyException(Exception):
    pass

async def get_message_sender_id(ctx: Message):
    if ctx.forward_date:
        if ctx.forward_sender_name:
            return 1
        elif ctx.forward_from:
            return ctx.forward_from.id
        elif ctx.forward_from_chat:
            return ctx.forward_from_chat.id
        else:
            return 1
    elif ctx.from_user:
        return ctx.from_user.id
    elif ctx.sender_chat:
        return ctx.sender_chat.id
    else:
        return 1

async def get_message_sender_name(ctx: Message):
    if ctx.forward_date:
        if ctx.forward_sender_name:
            return ctx.forward_sender_name
        elif ctx.forward_from:
            return (
                f"{ctx.forward_from.first_name} {ctx.forward_from.last_name}"
                if ctx.forward_from.last_name
                else ctx.forward_from.first_name
            )
        elif ctx.forward_from_chat:
            return ctx.forward_from_chat.title
        else:
            return ""
    elif ctx.from_user:
        if ctx.from_user.last_name:
            return f"{ctx.from_user.first_name} {ctx.from_user.last_name}"
        else:
            return ctx.from_user.first_name
    elif ctx.sender_chat:
        return ctx.sender_chat.title
    else:
        return ""

async def get_message_sender_username(ctx: Message):
    if ctx.forward_date:
        if ctx.forward_from:
            return ctx.forward_from.username or ""
        if ctx.forward_from_chat:
            return ctx.forward_from_chat.username or ""
        return ""
    if ctx.from_user:
        return ctx.from_user.username
    if ctx.sender_chat:
        return ctx.sender_chat.username
    return ""

async def get_message_sender_photo(ctx: Message):
    photo = None
    if ctx.forward_date:
        if ctx.forward_from and ctx.forward_from.photo:
            photo = ctx.forward_from.photo
        elif ctx.forward_from_chat and ctx.forward_from_chat.photo:
            photo = ctx.forward_from_chat.photo
    elif ctx.from_user and ctx.from_user.photo:
        photo = ctx.from_user.photo
    elif ctx.sender_chat and ctx.sender_chat.photo:
        photo = ctx.sender_chat.photo

    if photo:
        return {
            "small_file_id": photo.small_file_id,
            "small_photo_unique_id": photo.small_photo_unique_id,
            "big_file_id": photo.big_file_id,
            "big_photo_unique_id": photo.big_photo_unique_id,
        }
    return ""

async def get_text_or_caption(ctx: Message):
    if ctx.text:
        return ctx.text
    elif ctx.caption:
        return ctx.caption
    else:
        return ""

async def pyrogram_to_quotly(messages, is_reply):
    if not isinstance(messages, list):
        messages = [messages]
    payload = {
        "type": "quote",
        "format": "png",
        "backgroundColor": "#1b1429",
        "messages": [],
    }

    for message in messages:
        the_message_dict_to_append = {}
        if message.entities or message.caption_entities:
            entities = message.entities or message.caption_entities
            the_message_dict_to_append["entities"] = []
            for entity in entities:
                ent_dict = {
                    "type": entity.type.name.lower(),
                    "offset": entity.offset,
                    "length": entity.length,
                }
                if entity.url:
                    ent_dict["url"] = entity.url
                if entity.user:
                    ent_dict["user"] = {"id": entity.user.id}
                if entity.custom_emoji_id:
                    ent_dict["custom_emoji_id"] = entity.custom_emoji_id
                the_message_dict_to_append["entities"].append(ent_dict)
        else:
            the_message_dict_to_append["entities"] = []
            
        the_message_dict_to_append["chatId"] = await get_message_sender_id(message)
        the_message_dict_to_append["text"] = await get_text_or_caption(message)
        the_message_dict_to_append["avatar"] = True
        the_message_dict_to_append["from"] = {}
        the_message_dict_to_append["from"]["id"] = await get_message_sender_id(message)
        the_message_dict_to_append["from"]["name"] = await get_message_sender_name(message)
        the_message_dict_to_append["from"]["username"] = await get_message_sender_username(message)
        the_message_dict_to_append["from"]["type"] = message.chat.type.name.lower() if message.chat and message.chat.type else "private"
        
        if message.reply_to_message and is_reply:
            the_message_dict_to_append["replyMessage"] = {
                "name": await get_message_sender_name(message.reply_to_message),
                "text": await get_text_or_caption(message.reply_to_message),
                "chatId": await get_message_sender_id(message.reply_to_message),
            }
        else:
            the_message_dict_to_append["replyMessage"] = {}
        payload["messages"].append(the_message_dict_to_append)

    try:
        r = await fetch.post("https://bot.lyo.su/quote/generate", json=payload)
        if not r.is_error:
            res = r.json()
            if res.get("ok") and res.get("result", {}).get("image"):
                image_data = base64.b64decode(res["result"]["image"].encode("utf-8"))
                return image_data
            else:
                raise QuotlyException(res.get("error", {}).get("message", "API returned success but no image."))
        else:
            try:
                err_data = r.json()
                err_msg = err_data.get("error", {}).get("message", f"HTTP {r.status_code}")
            except:
                err_msg = f"API Service Error (HTTP {r.status_code})"
            raise QuotlyException(err_msg)
    except Exception as e:
        raise QuotlyException(str(e))

def isArgInt(txt) -> list:
    try:
        count = int(txt)
        return [True, count]
    except ValueError:
        return [False, 0]

@app.on_message(filters.command(["q", "r"]) & filters.reply)
async def msg_quotly_cmd(self: app, ctx: Message):
    is_reply = ctx.command[0].endswith("r")
    arg_idx = 1
    
    if not is_reply and len(ctx.command) > 1 and ctx.command[1].lower() == "r":
        is_reply = True
        arg_idx = 2
        
    msg = await ctx.reply_text("⚡️")
    
    try:
        messages = [ctx.reply_to_message]
        if len(ctx.command) > arg_idx:
            check_arg = isArgInt(ctx.command[arg_idx])
            if check_arg[0]:
                count = check_arg[1]
                if not (2 <= count <= 10):
                    await msg.delete()
                    return await ctx.reply_text("Invalid range (Use 2-10)")
                
                # Use get_messages (Bot safe) backwards from reply
                msg_ids = list(range(ctx.reply_to_message.id - count + 1, ctx.reply_to_message.id + 1))
                res = await self.get_messages(ctx.chat.id, msg_ids)
                messages = [m for m in (res if isinstance(res, list) else [res]) if m and not m.empty and not m.service]

        if not messages:
            await msg.delete()
            return await ctx.reply_text("No valid messages found to quote.")

        make_quotly = await pyrogram_to_quotly(messages, is_reply=is_reply)
        bio_sticker = BytesIO(make_quotly)
        bio_sticker.name = "quote_sticker.webp"
        await msg.delete()
        return await ctx.reply_sticker(bio_sticker)

    except Exception as e:
        await msg.delete()
        # 1. Log actual error for developer
        print(f"Quotly Error: {e}")
        
        # 2. Reply to user with specific error if possible
        return await ctx.reply_text(f"**Error:** `{e}`\n\n_This usually happens when the API is overloaded or the message contains unsupported elements._")


from PIL import Image
import os
from asyncio import gather
from traceback import format_exc

from pyrogram import filters
from pyrogram.errors import (
    PackShortNameInvalid,
    PeerIdInvalid,
    ShortnameOccupyFailed,
    StickerEmojiInvalid,
    StickerPngDimensions,
    StickerPngNopng,
    StickerVideoBig,
    UserIsBlocked,
    MessageNotModified,
)
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from SANYAMUSIC import app
from config import BOT_USERNAME
from SANYAMUSIC.utils.errors import capture_err

from SANYAMUSIC.utils.files import (
    get_document_from_file_id,
    resize_file_to_sticker_size,
    upload_document,
)

from SANYAMUSIC.utils.stickerset import (
    add_sticker_to_set,
    create_sticker,
    create_sticker_set,
    get_sticker_set_by_name,
)

# -----------

MAX_STICKERS = (
    120  # would be better if we could fetch this limit directly from telegram
)
SUPPORTED_TYPES = ["jpeg", "png", "webp"]
# ------------------------------------------
@app.on_message(filters.command("get_sticker"))
@capture_err
async def sticker_image(_, message: Message):
    r = message.reply_to_message

    if not r:
        return await message.reply("ʀᴇᴘʟʏ ᴛᴏ ᴀ sᴛɪᴄᴋᴇʀ.")

    if not r.sticker:
        return await message.reply("ʀᴇᴘʟʏ ᴛᴏ ᴀ sᴛɪᴄᴋᴇʀ.")

    m = await message.reply("sᴇɴᴅɪɴɢ..")
    f = await r.download(f"{r.sticker.file_unique_id}.png")

    await gather(
        *[
            message.reply_photo(f),
            message.reply_document(f),
        ]
    )

    await m.delete()
    os.remove(f)
#----------------
@app.on_message(filters.command("kang"))
@capture_err
async def kang(client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("ʀᴇᴘʟʏ ᴛᴏ ᴀ sᴛɪᴄᴋᴇʀ/ɪᴍᴀɢᴇ ᴛᴏ ᴋᴀɴɢ ɪᴛ.")
    if not message.from_user:
        return await message.reply_text(
            "ʏᴏᴜ ᴀʀᴇ ᴀɴᴏɴ ᴀᴅᴍɪɴ, ᴋᴀɴɢ sᴛɪᴄᴋᴇʀs ɪɴ ᴍʏ ᴘᴍ."
        )
    msg = await message.reply_text("ᴋᴀɴɢɪɴɢ sᴛɪᴄᴋᴇʀ..")

    # Always fetch the bot username to ensure the sticker pack suffix matches the bot token
    bot_username = (await client.get_me()).username

    # Find the proper emoji
    args = message.text.split()
    if len(args) > 1:
        sticker_emoji = str(args[1])
    elif (
        message.reply_to_message.sticker
        and message.reply_to_message.sticker.emoji
    ):
        sticker_emoji = message.reply_to_message.sticker.emoji
    else:
        sticker_emoji = "🤔"

    temp_file_path = None
    try:
        if message.reply_to_message.sticker:
            sticker_doc = await get_document_from_file_id(
                message.reply_to_message.sticker.file_id
            )
        else:
            doc = message.reply_to_message.photo or message.reply_to_message.document
            if not doc:
                return await msg.edit("ɴᴏᴘᴇ, ᴄᴀɴ'ᴛ ᴋᴀɴɢ ᴛʜᴀᴛ.")

            if doc.file_size > 10000000:
                return await msg.edit("ғɪʟᴇ sɪᴢᴇ ᴛᴏᴏ ʟᴀʀɢᴇ.")

            temp_file_path = await app.download_media(doc)
            with Image.open(temp_file_path) as img:
                image_type = img.format.lower() if img.format else "unknown"
            if image_type not in SUPPORTED_TYPES:
                return await msg.edit(f"ғᴏʀᴍᴀᴛ ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ! ({image_type})")

            try:
                temp_file_path = await resize_file_to_sticker_size(
                    temp_file_path
                )
            except OSError as e:
                await msg.edit_text("sᴏᴍᴇᴛʜɪɴɢ ᴡʀᴏɴɢ ʜᴀᴘᴘᴇɴᴇᴅ.")
                raise Exception(
                    f"sᴏᴍᴇᴛʜɪɴɢ ᴡʀᴏɴɢ ʜᴀᴘᴘᴇɴᴇᴅ ᴡʜɪʟᴇ ʀᴇsɪᴢɪɴɢ ᴛʜᴇ sᴛɪᴄᴋᴇʀ (ᴀᴛ {temp_file_path}); {e}"
                )
            sticker_doc = await upload_document(client, temp_file_path, message.chat.id)

        sticker = await create_sticker(sticker_doc, sticker_emoji)

        packnum = 1
        packname = f"k{message.from_user.id}_by_{bot_username}"
        retry = 0
        while retry < 50:
            stickerset = await get_sticker_set_by_name(client, packname)
            if not stickerset:
                title = f"{message.from_user.first_name[:20]} :: @{bot_username}"
                if packnum > 1:
                    title += f" v{packnum}"
                await create_sticker_set(
                    client,
                    message.from_user.id,
                    title,
                    packname,
                    [sticker],
                )
                break
            elif stickerset.set.count >= MAX_STICKERS:
                packnum += 1
                packname = f"k{packnum}_{message.from_user.id}_by_{bot_username}"
                retry += 1
                continue
            else:
                await add_sticker_to_set(client, stickerset, sticker)
                break
        else:
            await msg.edit("Failed to kang sticker after 50 attempts. Please contact support.")
            return

        await msg.edit(
            f"Sticker Kanged.\nEmoji: {sticker_emoji}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="View Pack", url=f"https://t.me/addstickers/{packname}")]]
            )
        )
    except (PeerIdInvalid, UserIsBlocked):
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Start", url=f"t.me/{bot_username}")]]
        )
        await msg.edit(
            "ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ sᴛᴀʀᴛ ᴀ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ ᴡɪᴛʜ ᴍᴇ.",
            reply_markup=keyboard,
        )
    except (StickerPngNopng, StickerPngDimensions):
        await msg.edit("The sticker's dimensions are invalid. It must be a 512x512 PNG.")
    except StickerVideoBig:
        await msg.edit("ᴛʜɪs ᴠɪᴅᴇᴏ sᴛɪᴄᴋᴇʀ ɪs ᴛᴏᴏ ʙɪɢ! ᴛᴇʟᴇɢʀᴀᴍ ʟɪᴍɪᴛs ᴠɪᴅᴇᴏ sᴛɪᴄᴋᴇʀs ᴛᴏ 256ᴋʙ ᴀɴᴅ 3 sᴇᴄᴏɴᴅs.")
    except StickerEmojiInvalid:
        await msg.edit(f"The emoji '{sticker_emoji}' is invalid.")
    except ShortnameOccupyFailed:
        await msg.edit(f"The pack name `{packname}` is already occupied by someone else.")
    except PackShortNameInvalid:
        await msg.edit(f"Sticker pack name invalid. Make sure the bot username is correct.\nPackname: `{packname}`")
    except OSError:
        await msg.edit("Image processing failed, the file might be corrupt or unsupported.")
    except Exception as e:
        await msg.edit("An unexpected error occurred. Please try again later.")
        # Re-raise for the decorator to log it
        raise e
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

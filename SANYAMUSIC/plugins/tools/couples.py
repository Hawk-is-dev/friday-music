
import os
import random
import asyncio
from datetime import datetime
from PIL import Image, ImageDraw, ImageOps
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.enums import ChatType, ParseMode
from telegraph import upload_file

from SANYAMUSIC import app
from SANYAMUSIC.utils.throttling import check_flood

# Constants
ASSETS_DIR = "SANYAMUSIC/assets"
BG_IMAGE = f"{ASSETS_DIR}/couples.jpg"
DEFAULT_PFP = f"{ASSETS_DIR}/upic.png"

def get_today_date():
    return datetime.now().strftime("%d/%m/%Y")

def get_tomorrow_date():
    from datetime import timedelta
    return (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")

async def get_user_info(user_id):
    try:
        user = await app.get_users(user_id)
        name = user.first_name or "User"
        mention = user.mention
        pfp_id = None
        if user.photo:
            pfp_id = user.photo.big_file_id
        return name, mention, pfp_id
    except Exception:
        return "Unknown", "Unknown", None

async def download_pfp(user_id, pfp_id, index, message_id):
    if not pfp_id:
        return DEFAULT_PFP
    
    file_path = f"downloads/pfp_{user_id}_{index}_{message_id}.png"
    try:
        if not os.path.exists("downloads"):
            os.makedirs("downloads")
        path = await app.download_media(pfp_id, file_name=file_path)
        return path
    except Exception:
        return DEFAULT_PFP

def prepare_pfp(path, size=(487, 487)):
    """Processed PFP with high-quality circular crop. Optimized for speed."""
    try:
        # Open and ensure RGBA
        img = Image.open(path).convert("RGBA")
        img = ImageOps.fit(img, size, centering=(0.5, 0.5))
        
        # Create mask with 2x supersampling for speed-quality balance
        mask_size = (size[0] * 2, size[1] * 2)
        mask = Image.new('L', mask_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + mask_size, fill=255)
        mask = mask.resize(size, Image.LANCZOS)
        
        # Apply circular crop
        output = Image.new('RGBA', size, (0, 0, 0, 0))
        output.paste(img, (0, 0), mask)
        
        return output
    except Exception as e:
        print(f"Error preparing PFP: {e}")
        return None

def generate_couples_image(p1_path, p2_path, output_path):
    # --- CONFIGURATION AREA ---
    PFP_SIZE = (487, 487)
    COORD_P1 = (73, 160)
    COORD_P2 = (734, 160)
    # --------------------------

    try:
        if not os.path.exists(BG_IMAGE):
             print(f"Error: Background asset not found at {BG_IMAGE}")
             return False

        # Load BG once
        background = Image.open(BG_IMAGE).convert("RGBA")

        # Process PFPs
        img1 = prepare_pfp(p1_path, size=PFP_SIZE)
        img2 = prepare_pfp(p2_path, size=PFP_SIZE)
        
        if img1:
            background.paste(img1, COORD_P1, img1)
        if img2:
            background.paste(img2, COORD_P2, img2)

        background.save(output_path, "PNG")
        return True
    except Exception as e:
        print(f"Error generating couples image: {e}")
        return False

def get_button():
    try:
        username = app.username if app.username else "BotUsername"
    except:
        username = "BotUsername"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text="➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ",
                url=f"https://t.me/{username}?startgroup=true",
            ),
        ],
    ])

@app.on_message(filters.command(["couples", "couple"]) & ~filters.private)
async def couples_cmd(_, message: Message):
    if not await check_flood(message):
        return
    chat_id = message.chat.id
    is_reply = message.reply_to_message is not None
    
    mystic = None
    output_file = None
    p_paths = []
    
    try:
        if is_reply:
            user_b = message.reply_to_message.from_user
            if not user_b or user_b.is_bot:
                return await message.reply_text("❌ <b>ʙᴏᴛs ᴄᴀɴ'ᴛ ʙᴇ ᴘᴀɪʀᴇᴅ.</b>")
            
            # Start generation process
            mystic = await message.reply_text("✨ **ɢᴇɴᴇʀᴀᴛɪɴɢ ʀᴀɴᴅᴏᴍ ᴄᴏᴜᴘʟᴇs...**")
            
            # Find a random user C from the group (not User B)
            members = []
            async for m in app.get_chat_members(chat_id, limit=100):
                if m.user and not m.user.is_bot and m.user.id != user_b.id:
                    members.append(m.user.id)
            
            if not members:
                return await mystic.edit_text("❌ **ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴍᴇᴍʙᴇʀs ᴛᴏ ᴍᴀᴛᴄʜ.**")
            
            c1_id = user_b.id
            c2_id = random.choice(members)
            title_text = "✨ **ᴄᴜsᴛᴏᴍ ᴍᴀᴛᴄʜ ғᴏᴜɴᴅ :**"
        else:
            mystic = await message.reply_text("✨ **ɢᴇɴᴇʀᴀᴛɪɴɢ ʀᴀɴᴅᴏᴍ ᴄᴏᴜᴘʟᴇs...**")
            members = []
            try:
                async for m in app.get_chat_members(chat_id, limit=150):
                    if m.user and not m.user.is_bot:
                        members.append(m.user.id)
            except Exception as e:
                print(f"Error fetching members: {e}")
            
            if len(members) < 2:
                return await mystic.edit_text("❌ **ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴍᴇᴍʙᴇʀs ᴛᴏ ғᴏʀᴍ ᴀ ᴄᴏᴜᴘʟᴇ.**")
            
            c1_id = random.choice(members)
            members.remove(c1_id)
            c2_id = random.choice(members)
            title_text = f"✨ **ᴛᴏᴅᴀʏ's ᴄᴏᴜᴘʟᴇ ᴏғ ᴛʜᴇ ᴅᴀʏ [{get_today_date()}] :**"

        # Fetch and Download PFPs
        n1, m1, p1_id = await get_user_info(c1_id)
        n2, m2, p2_id = await get_user_info(c2_id)
        
        p1_path = await download_pfp(c1_id, p1_id, 1, message.id)
        p2_path = await download_pfp(c2_id, p2_id, 2, message.id)
        p_paths = [p1_path, p2_path]
        
        output_file = f"downloads/couples_{chat_id}_{message.id}.png"
        
        # Generate Image in Thread
        img_success = await asyncio.to_thread(generate_couples_image, p1_path, p2_path, output_file)
        
        if not img_success:
            return await mystic.edit_text("❌ **ғᴀɪʟᴇᴅ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ᴄᴏᴜᴘʟᴇ ɪᴍᴀɢᴇ.**")

        # Upload to Telegraph in Thread (for Graph.org)
        try:
            t_link = await asyncio.to_thread(upload_file, output_file)
            img_url = f"https://graph.org{t_link[0]}"
        except Exception:
            img_url = output_file # Use local file if upload fails

        # Send result
        caption = f"{title_text}\n\n{m1} + {m2} = ❤️\n\n✨ **ɴᴇxᴛ ᴄᴏᴜᴘʟᴇs ᴡɪʟʟ ʙᴇ sᴇʟᴇᴄᴛᴇᴅ ᴏɴ {get_tomorrow_date()} !!**"
        
        await message.reply_photo(photo=img_url, caption=caption, reply_markup=get_button(), parse_mode=ParseMode.HTML)
        
        await mystic.delete()

    except Exception as e:
        print(f"Couples Error: {e}")
        if mystic:
            await mystic.edit_text(f"❌ **sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ.**\n\n`{e}`")
        else:
            await message.reply_text("❌ **ᴀɴ ᴜɴᴇxᴘᴇᴄᴛᴇᴅ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ.**")

    finally:
        # Cleanup
        if output_file and os.path.exists(output_file):
            os.remove(output_file)
        for p in p_paths:
            if p != DEFAULT_PFP and os.path.exists(p):
                os.remove(p)

__mod__ = "COUPLES"
__help__ = """
** /couples** - Get Todays Couples Of The Group In Interactive View
"""

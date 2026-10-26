import asyncio
import os
import textwrap
import shlex
from PIL import Image, ImageDraw, ImageFont
from pyrogram import filters
from pyrogram.types import Message
from SANYAMUSIC import app

@app.on_message(filters.command("mmf"))
async def mmf(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("**Reply to a photo or sticker after the /mmf command.**")

    reply = message.reply_to_message
    if not (reply.photo or reply.sticker or reply.animation or reply.document or reply.video):
        return await message.reply_text("**Reply to a photo, sticker, or video.**")

    if len(message.text.split()) < 2:
        return await message.reply_text("**Give me text after /mmf to memify.**")

    msg = await message.reply_text("**Memifying this media! ⚡️**")
    text = message.text.split(None, 1)[1]
    
    try:
        # Determine media type and download
        is_video = False
        is_animated_sticker = False
        
        if reply.sticker:
            if reply.sticker.is_video:
                is_video = True
            elif reply.sticker.is_animated:
                is_animated_sticker = True
        elif reply.animation or reply.video:
            is_video = True
        elif reply.document and reply.document.mime_type and reply.document.mime_type.startswith("video/"):
            is_video = True

        if is_animated_sticker:
            if reply.sticker.thumbs:
                file = await app.download_media(reply.sticker.thumbs[0])
            else:
                return await msg.edit("**Animated stickers (.tgs) are not supported. Try a video sticker or static media.**")
        else:
            file = await app.download_media(reply)
            
        if not file:
            return await msg.edit("**Failed to download media.**")

        if is_video:
            width, height = await get_video_dimensions(file)
            # For stickers, Telegram MANDATES 512x512
            if reply.sticker:
                width, height = 512, 512
                
            overlay = await drawText(file, text, is_video=True, width=width, height=height)
            output = f"{file}_meme.webm" if reply.sticker else f"{file}_meme.mp4"
            
            # Refined Ffmpeg command for transparency
            if reply.sticker:
                # [0:v]scale=512:512 forces correct dimensions for stickers
                # format=yuva420p is the golden standard for WebM Alpha
                cmd = (
                    f"ffmpeg -y -i \"{file}\" -i \"{overlay}\" -filter_complex "
                    f"\"[0:v]scale=512:512,format=yuva420p[bg];"
                    f"[1:v]format=yuva420p[fg];"
                    f"[bg][fg]overlay=format=auto,format=yuva420p\" "
                    f"-c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0 -metadata:s:v:0 alpha_mode=1 -b:v 512k \"{output}\""
                )
            else:
                cmd = f"ffmpeg -y -i \"{file}\" -i \"{overlay}\" -filter_complex \"overlay=0:0\" -c:v libx264 -preset ultrafast -pix_fmt yuv420p \"{output}\""
                
            process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await process.communicate()
            
            if os.path.exists(output):
                if reply.sticker:
                    await app.send_sticker(message.chat.id, sticker=output)
                else:
                    await app.send_video(message.chat.id, video=output)
                
                if os.name == "nt": await asyncio.sleep(1)
                for f in [file, overlay, output]:
                    try:
                        if os.path.exists(f): os.remove(f)
                    except: pass
                await msg.delete()
            else:
                await msg.edit("**Failed to process video animation.**")
                if os.name == "nt": await asyncio.sleep(1)
                for f in [file, overlay]:
                    try:
                        if os.path.exists(f): os.remove(f)
                    except: pass
        else:
            meme = await drawText(file, text)
            await app.send_document(message.chat.id, document=meme)
            await msg.delete()
            if os.name == "nt": await asyncio.sleep(1)
            for f in [meme, file]:
                try:
                    if os.path.exists(f): os.remove(f)
                except: pass
                
    except Exception as e:
        await msg.edit(f"**Error:** `{e}`")

async def get_video_dimensions(file_path):
    cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 \"{file_path}\""
    process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, _ = await process.communicate()
    try:
        w, h = map(int, stdout.decode().strip().split('x'))
        return w, h
    except:
        return 512, 512

async def drawText(image_path, text, is_video=False, width=None, height=None):
    if is_video:
        i_width, i_height = width, height
        img = Image.new("RGBA", (i_width, i_height), (0, 0, 0, 0))
    else:
        with Image.open(image_path) as img:
            img = img.convert("RGBA")
            i_width, i_height = img.size
    
    fnt_path = "arial.ttf" if os.name == "nt" else "./SANYAMUSIC/assets/default.ttf"
    font_size = int((i_width * 70) / 640)
    if font_size < 10: font_size = 20
    
    try:
        m_font = ImageFont.truetype(fnt_path, font_size)
    except:
        m_font = ImageFont.load_default()

    upper_text, lower_text = text.split(";", 1) if ";" in text else (text, "")
    draw = ImageDraw.Draw(img)

    def draw_styled_text(text_line, y_pos):
        _, _, w, h = draw.textbbox((0, 0), text_line, font=m_font)
        draw.text(
            ((i_width - w) / 2, y_pos),
            text_line,
            font=m_font,
            fill=(255, 255, 255),
            stroke_width=max(1, int(font_size/20)),
            stroke_fill=(0, 0, 0)
        )
        return h

    if upper_text:
        current_h = 10
        for line in textwrap.wrap(upper_text.upper(), width=15):
            h = draw_styled_text(line, current_h)
            current_h += h + 5

    if lower_text:
        lines = textwrap.wrap(lower_text.upper(), width=15)
        current_bh = i_height - 10
        for line in reversed(lines):
            _, _, w, h = draw.textbbox((0, 0), line, font=m_font)
            current_bh -= (h + 5)
            draw_styled_text(line, current_bh)

    if is_video:
        overlay_name = f"{image_path}_overlay.png"
        img.save(overlay_name)
        return overlay_name
    else:
        image_name = "memify.webp"
        img.save(image_name, "webp")
        return image_name

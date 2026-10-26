import asyncio
import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch
import config
from SANYAMUSIC import LOGGER
import random
import ssl

# Constants
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

logger = LOGGER(__name__)

# --- Layout Constants for 'thumbnails.py' Style ---
# The base image is 1280x720

THUMB_SIZE = 400
THUMB_BORDER = 20
THUMB_X = 120
THUMB_Y = 160

TEXT_X = 565
TITLE_Y = 180
META_Y = 320
BAR_Y = 380
ICONS_Y = 450

LINE_LENGTH = 580
RED_FILL_RATIO = 0.6  # 60% red fill as in thumbnails.py logic
CIRCLE_RADIUS = 10

# --- Helper Functions from 'thumbnails.py' ---

def truncate(text):
    list = text.split(" ")
    text1 = ""
    text2 = ""    
    for i in list:
        if len(text1) + len(i) < 30:        
            text1 += " " + i
        elif len(text2) + len(i) < 30:       
            text2 += " " + i

    text1 = text1.strip()
    text2 = text2.strip()     
    return [text1,text2]

def crop_center_circle(img, output_size, border, crop_scale=1.0):
    half_the_width = img.size[0] / 2
    half_the_height = img.size[1] / 2
    larger_size = int(output_size * crop_scale)
    
    # 1. Crop a large square from the center
    img = img.crop(
        (
            half_the_width - larger_size/2,
            half_the_height - larger_size/2,
            half_the_width + larger_size/2,
            half_the_height + larger_size/2
        )
    )
    
    # 2. Resize to fit the final circle size (minus border)
    img = img.resize((output_size - 2*border, output_size - 2*border))
    
    # 3. Create a white border image
    final_img = Image.new("RGBA", (output_size, output_size), "white")
    
    # 4. Create the mask for the thumbnail (inner circle)
    mask_main = Image.new("L", (output_size - 2*border, output_size - 2*border), 0)
    draw_main = ImageDraw.Draw(mask_main)
    draw_main.ellipse((0, 0, output_size - 2*border, output_size - 2*border), fill=255)
    
    # 5. Paste the thumbnail onto the white border image using the mask
    final_img.paste(img, (border, border), mask_main)
    
    # 6. Create the final mask (outer circle for transparency)
    mask_border = Image.new("L", (output_size, output_size), 0)
    draw_border = ImageDraw.Draw(mask_border)
    draw_border.ellipse((0, 0, output_size, output_size), fill=255)
    
    # 7. Composite with a fully transparent image to apply the outer circular mask
    result = Image.composite(final_img, Image.new("RGBA", final_img.size, (0, 0, 0, 0)), mask_border)
    
    return result

# The trim_to_width function from thumbnails2.py is no longer needed

async def get_thumb(videoid: str) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_v4.png")
    if os.path.exists(cache_path):
        return cache_path

    #logger.info(f"Generating thumbnail for {videoid}")
    title = thumbnail = duration = views = channel = None

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
    ]
    headers_api = {"User-Agent": random.choice(user_agents)}

    # Layer 1: Vercel Scraper (Always On)
    try:
        url = f"{config.VERCEL_SEARCH_URL}/search"
        params = {"q": videoid, "limit": 1}
        async with aiohttp.ClientSession(headers=headers_api) as session:
            async with session.get(url, params=params, timeout=5) as resp:
                if resp.status == 200:
                    data_list = await resp.json()
                    if data_list and isinstance(data_list, list):
                        data = data_list[0]
                        title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
                        thumbnail = data.get("thumbnail", config.YOUTUBE_IMG_URL)
                        duration = data.get("time")
                        views = "Unknown Views"
                        channel = "Unknown Channel"
                        # Success - return early or skip other layers
                        raise StopIteration
    except StopIteration:
        pass
    except Exception as e:
        LOGGER.warning(f"Vercel Scraper failed for thumbnail {videoid}: {e}")

    # Layer 2: VideosSearch (Secondary)
    if not title:
        try:
            results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
            results_data = await results.next()
            result_items = results_data.get("result", [])
            if result_items:
                data = result_items[0]
                title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
                thumbnail = (data.get("thumbnails") or [{}])[0].get("url", config.YOUTUBE_IMG_URL)
                duration = data.get("duration")
                views = data.get("viewCount", {}).get("short", "Unknown Views")
                channel = data.get("channel", {}).get("name", "Unknown Channel")
        except Exception as e:
            logger.warning(f"VideosSearch failed for {videoid}: {e}")

    # Layer 3: yt-dlp (Fallback)
    if not title:
        try:
            from SANYAMUSIC.platforms.Youtube import YouTubeAPI
            yt = YouTubeAPI()
            details = await yt.details(videoid, videoid=True)
            if details:
                title, duration, _, thumbnail, _ = details
                views = "Unknown Views"
                channel = "Unknown Channel"
        except Exception as ex:
            logger.error(f"Final metadata fetch failure for {videoid}: {ex}")
            title, thumbnail, duration, views, channel = "Unsupported Title", config.YOUTUBE_IMG_URL, None, "Unknown Views", "Unknown Channel"

    is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
    duration_text = "Live" if is_live else duration or "Unknown Mins"

    # Download thumbnail
    thumb_path = os.path.join(CACHE_DIR, f"thumb{videoid}.png")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.youtube.com/",
    }

    try:
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
            
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession(headers=headers) as session:
            for attempt in range(3):
                try:
                    async with session.get(thumbnail, ssl=ssl_ctx, timeout=15) as resp:
                        if resp.status == 200:
                            async with aiofiles.open(thumb_path, "wb") as f:
                                await f.write(await resp.read())
                            break
                        else:
                            logger.warning(f"Attempt {attempt+1}: Failed to download thumbnail: status {resp.status}")
                except Exception as e:
                    logger.warning(f"Attempt {attempt+1}: Error downloading thumbnail: {e}")
                
                if attempt < 2:
                    await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Final failure downloading thumbnail for {videoid}: {e}")
        return config.YOUTUBE_IMG_URL

    if not os.path.exists(thumb_path):
        logger.warning(f"Thumbnail path does not exist after download: {thumb_path}")
        return config.YOUTUBE_IMG_URL

    #logger.info(f"Starting sync_gen_thumb for {videoid}")
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, sync_gen_thumb, thumb_path, cache_path, title, duration_text, channel, views, is_live)

def sync_gen_thumb(thumb_path, cache_path, title, duration_text, channel, views, is_live):
    # Create base image
    base = Image.open(thumb_path)
    
    # Resize and blur background (BoxBlur(20) from thumbnails.py)
    bg = base.resize((1280, 720)).convert("RGBA")
    bg = bg.filter(ImageFilter.BoxBlur(20))
    bg = ImageEnhance.Brightness(bg).enhance(0.6) # Enhance(0.6) from thumbnails.py

    # Draw details
    draw = ImageDraw.Draw(bg)
    try:
        # Load fonts as per thumbnails.py
        arial_font = ImageFont.truetype("SANYAMUSIC/assets/assets/font2.ttf", 30)
        regular_font = ImageFont.truetype("SANYAMUSIC/assets/assets/font.ttf", 30)
        title_font = ImageFont.truetype("SANYAMUSIC/assets/assets/font3.ttf", 45)
    except OSError:
        arial_font = regular_font = title_font = ImageFont.load_default()

    # 1. Apply Circular Thumbnail
    youtube_thumb = Image.open(thumb_path)
    circle_thumbnail = crop_center_circle(youtube_thumb, THUMB_SIZE, THUMB_BORDER)
    bg.paste(circle_thumbnail, (THUMB_X, THUMB_Y), circle_thumbnail)

    # 2. Draw Text (White color)
    title1, title2 = truncate(title)
    
    draw.text((TEXT_X, TITLE_Y), title1, fill=(255, 255, 255), font=title_font)
    draw.text((TEXT_X, TITLE_Y + 50), title2, fill=(255, 255, 255), font=title_font) # 50px offset
    
    draw.text((TEXT_X, META_Y), f"{channel}  |  {views}", fill=(255, 255, 255), font=arial_font)

    # 3. Progress bar
    red_length = int(LINE_LENGTH * RED_FILL_RATIO)

    # Draw Red Line (width=9 from thumbnails.py)
    start_point_red = (TEXT_X, BAR_Y)
    end_point_red = (TEXT_X + red_length, BAR_Y)
    draw.line([start_point_red, end_point_red], fill="red", width=9)

    # Draw White/Gray Line (width=8 from thumbnails.py)
    start_point_white = (TEXT_X + red_length, BAR_Y)
    end_point_white = (TEXT_X + LINE_LENGTH, BAR_Y)
    draw.line([start_point_white, end_point_white], fill="white", width=8) # Used white as in thumbnails.py

    # Draw Red Circle
    circle_position = (end_point_red[0], end_point_red[1])
    draw.ellipse([circle_position[0] - CIRCLE_RADIUS, circle_position[1] - CIRCLE_RADIUS,
                  circle_position[0] + CIRCLE_RADIUS, circle_position[1] + CIRCLE_RADIUS], fill="red")

    # Draw time texts
    draw.text((TEXT_X, BAR_Y + 20), "00:00", fill=(255, 255, 255), font=arial_font) # 20px offset
    
    # Calculate X position for end time (1080 from thumbnails.py)
    end_time_x = 1080 
    draw.text((end_time_x, BAR_Y + 20), duration_text, fill=(255, 255, 255) if not is_live else "red", font=arial_font)

    # 4. Icons
    icons_path = "SANYAMUSIC/assets/assets/play_icons.png"
    if os.path.isfile(icons_path):
        ic = Image.open(icons_path)
        ic = ic.resize((LINE_LENGTH, 62)) # Resized to LINE_LENGTH (580) and 62px height
        bg.paste(ic, (TEXT_X, ICONS_Y), ic)

    # Cleanup and save
    try:
        os.remove(thumb_path)
    except OSError:
        pass

    bg.save(cache_path)
    return cache_path

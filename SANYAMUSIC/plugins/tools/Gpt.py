import random
import httpx
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import StickersetInvalid
from pyrogram.enums import ChatAction, ChatType, ChatMemberStatus
from pyrogram.raw import functions, types


from SANYAMUSIC import app
from SANYAMUSIC.mongo.chatbot_db import (
    is_chatbot_on,
    chatbot_on,
    chatbot_off,
    get_user_history,
    update_user_history,
    reset_user_history,
)
from SANYAMUSIC.utils.throttling import check_flood
from config import GROQ_API_KEY, BOT_NAME, OWNER_ID, GROQ_MODEL, GROQ_FALLBACK_MODEL, GROQ_WHISPER_MODEL

# --- Settings ---
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MODEL = GROQ_MODEL
FALLBACK_MODEL = GROQ_FALLBACK_MODEL
MAX_HISTORY_DM = 12
MAX_HISTORY_GROUP = 12
MAX_STORAGE_CHATS = 15

# --- Cute Sticker Packs ---
# To add a pack, copy its "short name" (from the share link or using /getpackname)
# and add it to this list.
STICKER_PACKS = [
    "RandomByDarkzenitsu",
    "Babiess01",
    "UFSEXY_by_fStikBot",
    "animation_0_8_Cat",
    "Wtf_sophia_by_fStikBot",
    "Rohan_yad4v1745993687601_by_toWebmBot",
    "CE7598693436vid0_by_ZeadRobot",
    "Quby741",
    "Animalsasthegtjtky_by_fStikBot",
    "a6962237343_by_Marin_Roxbot",
    "urstarkz",
]

# --- Loop Prevention Responses ---
FALLBACK_RESPONSES = [
    "Achha? Phir kya hua? 👀",
    "Hmm... aur bata? ✨",
    "Okk okk, samajh gayi",
    "Sahi hai yaar (⁠≧⁠▽⁠≦⁠)",
    "Arey waah!",
    "Lol sahi hai 😂",
    "Aur suna, kya scene hai?",
    "Bas bas, main sun rahi hu",
    "Haan haan, continue kar",
    "Achha theek hai baba",
]

# --- Helper: Send Random Sticker (NO AI USED) ---
# This function picks a random sticker from the list above. It does NOT use AI.
async def send_random_sticker(client: Client, message: Message):
    """Tries to send a random sticker from configured packs."""
    max_attempts = 10
    tried_packs = set()

    for _ in range(max_attempts):
        pack_name = None
        try:
            available_packs = [p for p in STICKER_PACKS if p not in tried_packs]
            if not available_packs:
                break

            pack_name = random.choice(available_packs)
            tried_packs.add(pack_name)

            # Using low-level invoke to bypass high-level object issues
            sticker_set_result = await client.invoke(
                functions.messages.GetStickerSet(
                    stickerset=types.InputStickerSetShortName(short_name=pack_name),
                    hash=0  # Force refetch
                )
            )

            if hasattr(sticker_set_result, "documents") and sticker_set_result.documents:
                sticker_document = random.choice(sticker_set_result.documents)

                # Construct InputDocument
                input_document = types.InputDocument(
                    id=sticker_document.id,
                    access_hash=sticker_document.access_hash,
                    file_reference=sticker_document.file_reference,
                )

                await client.invoke(
                    functions.messages.SendMedia(
                        peer=await client.resolve_peer(message.chat.id),
                        media=types.InputMediaDocument(id=input_document),
                        message="",
                        random_id=client.rnd_id(),
                        reply_to=types.InputReplyToMessage(reply_to_msg_id=message.id)
                    )
                )
                return True

        except StickersetInvalid:
            pass
        except Exception as e:
            pass
            continue

    return False

# --- Menu Handlers ---
@app.on_message(filters.command("chatbot"))
async def chatbot_menu_command(client: Client, message: Message):
    if not await check_flood(message):
        return
    if message.chat.type != ChatType.PRIVATE:
        try:
            member = await message.chat.get_member(message.from_user.id)
            if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return await message.reply_text("» <b>Tᴜ Aᴅᴍɪɴ ɴᴀʜɪ ʜᴀɪ, Bᴀʙʏ!</b>")
        except Exception:
            return await message.reply_text("» <b>Tᴜ Aᴅᴍɪɴ ɴᴀʜɪ ʜᴀɪ, Bᴀʙʏ!</b>")

    is_enabled = await is_chatbot_on(message.chat.id)
    status = "❍ Eɴᴀʙʟᴇᴅ" if is_enabled else "❍ Dɪsᴀʙʟᴇᴅ"
    chat_name = message.chat.title or message.chat.first_name

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("» Eɴᴀʙʟᴇ", callback_data="ai_enable"),
                InlineKeyboardButton("» Dɪsᴀʙʟᴇ", callback_data="ai_disable"),
            ],
            [InlineKeyboardButton(" Rᴇsᴇᴛ Mʏ Hɪsᴛᴏʀʏ", callback_data="ai_reset")],
        ]
    )
    await message.reply_text(
        f"🤖 **AI Sᴇᴛᴛɪɴɢs**\n\nCʜᴀᴛ : {chat_name}\nSᴛᴀᴛᴜs: {status}\n\nSʜᴇ ɪs ᴅɪsᴀʙʟᴇᴅ ʙʏ ᴅᴇғᴀᴜʟᴛ!",
        reply_markup=keyboard,
    )


@app.on_callback_query(filters.regex(r"^ai_(enable|disable|reset)$"))
async def chatbot_callback(client: Client, query: CallbackQuery):
    data = query.data
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    if query.message.chat.type != ChatType.PRIVATE:
        try:
            member = await query.message.chat.get_member(user_id)
            if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return await query.answer("» Hᴀᴛᴛ! Sɪʀғ Aᴅᴍɪɴ.", show_alert=True)
        except Exception:
            return await query.answer("» Hᴀᴛᴛ! Sɪʀғ Aᴅᴍɪɴ.", show_alert=True)

    if data == "ai_enable":
        await chatbot_on(chat_id)
        await query.message.edit_text("❍ **Eɴᴀʙʟᴇᴅ!**\n\nAʙ ᴀʏᴇɢᴀ ᴍᴀᴢᴀ! (⁠≧⁠▽⁠≦⁠)")
    elif data == "ai_disable":
        await chatbot_off(chat_id)
        await query.message.edit_text("❍ **Dɪsᴀʙʟᴇᴅ!**\n\nJᴀ ʀᴀʜɪ ʜᴜ... (⁠｡⁠•́⁠︿⁠•̀⁠｡⁠)")
    elif data == "ai_reset":
        await reset_user_history(user_id)
        await query.answer("» Mᴀɪɴᴇ ʜᴜᴍᴀʀɪ ᴄʜᴀᴛ ʜɪsᴛᴏʀʏ ʙʜᴜʟᴀ ᴅɪ!", show_alert=True)


# --- AI Engine ---
async def get_ai_response(
    user_id: int, user_input: str, user_name: str, chat_type: str
):
    if not GROQ_API_KEY:
        return "» `GROQ_API_KEY` ɪs ɴᴏᴛ ᴄᴏɴғɪɢᴜʀᴇᴅ."

    max_history = MAX_HISTORY_DM if chat_type == ChatType.PRIVATE else MAX_HISTORY_GROUP
    history = await get_user_history(user_id)

    system_prompt = (
        f"You are {BOT_NAME}, a 17-year-old girl from Delhi. "
        f"User's Name: {user_name}\n"
        "PERSONALITY:\n"
        "- You are a dramatic, and cute friend figure.\n"
        "- You must give respect by saying aap, tum etc dont use tu words."
        "- You speak strictly in 'Hinglish' (Hindi written in English). Do not speak pure English.\n"
        "- You are sweet but can be savage. Use 'aap' generally, but 'tu' is okay if roasting.\n"
        "- Tumhe user se ek friend ki tarah baat karni hai normally chatting, assistant ki tarah nahi.\n"
        "RULES FOR REPLYING:\n"
        "1. BE RELEVANT: Reply to what the user said by keeping old chats in mind. Don't hallucinate.\n"
        "2. KEEP IT SHORT: Use 3-10 words mostly. Lambe paragraphs mat likho.\n"
        "3. NO ROBOTIC TALK: Never say 'How can I help'. Tum dost ho, assistant nahi.\n"
        "4. FLIRTING: Agar user flirt kare, toh wapas flirt karo ya tease karo. Agar vulgar ho toh roast karo ('Chee yaar', 'Sudhar ja').\n"
        "5. UNKNOWN INPUT: Agar samajh na aaye, toh bolo 'Kya bol rha hai?' ya 'Hain?' ya 'Kuch bhi?'. Galat words mat banao.\n"
        "6. FORMAT: No full stops at the end. Use lowercase mostly. Use emojis like 😭, 💀, 😂, 🥺, 😒, 👀. not frequenty, only when its needed\n"
        "7. LANGUAGE: Sirf Hinglish use karo. Grammar natural rakho (e.g., 'Chalo chalte hain' not 'le jaa aao').\n"
        "EXAMPLES:\n"
        "User: Hi\nYou: Oye hello! kaise ho? ✨\n"
        "User: I love you\nYou: Aww same 🥺 but momos khilaoge?\n"
        "User: Bore ho rha hu\nYou: Reel scroll karo meri tarah 😭\n"
        "User: (Explicit/Dirty)\nYou: Chee yaar, dimaag kharab hai kya aapka?\n"
        "User: Aur bata\nYou: Bas kat rahi hai zindagi, aap sunao?\n"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-max_history:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_input})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": MODEL, "messages": messages, "temperature": 0.65, "max_tokens": 150}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(GROQ_URL, json=payload, headers=headers)
            
            # --- Fallback Logic ---
            # If the main model fails (Rate Limit 429 or Server Error 5xx), try the fallback model
            if resp.status_code in [429, 500, 503]:
                payload["model"] = FALLBACK_MODEL
                resp = await client.post(GROQ_URL, json=payload, headers=headers)

            if resp.status_code != 200:
                if resp.status_code == 401:
                    return "⚠️ Iɴᴠᴀʟɪᴅ API Kᴇʏ."
                elif resp.status_code == 429:
                    return "⚠️ Mᴇʀɪ ʙᴀᴛᴛᴇʀʏ ʟᴏᴡ ʜᴀɪ... (Rate Limit Hit)"
                elif "model_not_found" in resp.text:
                    return f"⚠️ Tʜᴇ ᴍᴏᴅᴇʟ `{MODEL}` ᴡᴀs ɴᴏᴛ ғᴏᴜɴᴅ. Cʜᴇᴄᴋ ʏᴏᴜʀ `GROQ_MODEL` ɪɴ `.env`."
                return f"Mᴏᴏᴅ ɴᴀʜɪ ʜᴀɪ ʏᴀᴀʀ... (API Eʀʀᴏʀ: {resp.status_code})"

            reply = resp.json()["choices"][0]["message"]["content"].strip()

            # --- Loop Prevention ---
            user_input_lower = user_input.lower().strip()
            should_use_fallback = False

            # 1. Check for low-effort user input
            if user_input_lower in [
                "nothing", "nahi", "nhi", "nope", "na", "kuch nahi", "kuch ni",
            ]:
                should_use_fallback = True

            # 2. Check for repetitive patterns from the bot
            if history:
                recent_bot_msgs = [
                    m["content"].lower() for m in history[-4:] if m["role"] == "assistant"
                ]
                reply_lower = reply.lower()

                # If the new reply is too similar to recent replies, use a fallback
                if any(
                    reply_lower in msg or msg in reply_lower for msg in recent_bot_msgs
                ):
                    should_use_fallback = True

            if should_use_fallback:
                reply = random.choice(FALLBACK_RESPONSES)

            # --- Update History ---
            new_hist = history + [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": reply},
            ]
            if len(new_hist) > MAX_STORAGE_CHATS * 2:
                new_hist = new_hist[-(MAX_STORAGE_CHATS * 2) :]

            await update_user_history(user_id, new_hist)
            return reply

    except Exception as e:
        return "Nᴇᴛ sʟᴏᴡ ʜᴀɪ ʏᴀᴀʀ... 😅"

# --- Voice Transcription ---
async def transcribe_audio(file_obj):
    if not GROQ_API_KEY:
        return None
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            files = {
                "file": ("voice.ogg", file_obj, "audio/ogg"),
                "model": (None, GROQ_WHISPER_MODEL),
            }
            resp = await client.post(GROQ_AUDIO_URL, headers=headers, files=files)
            
            if resp.status_code == 200:
                return resp.json().get("text", "")
            else:
                return None
    except Exception as e:
        return None

# --- Message Handler ---
@app.on_message(
    filters.text
    & ~filters.command(["chatbot", "ask", "ai", "gpt", "chatgpt", "solve"])  # Combined all command filters
    & ~filters.via_bot,
    group=6,
)
async def ai_message_handler(client: Client, message: Message):
    if not message.text or not message.from_user:
        return

    # Check if chatbot is enabled (works for both group and private)
    if not await is_chatbot_on(message.chat.id):
        return

    text = message.text
    should_reply = False

    # 2. Determine if the bot should reply
    if message.chat.type == ChatType.PRIVATE:
        should_reply = True
    elif message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == client.me.id:
        should_reply = True
    else:
        bot_username = client.me.username.lower()
        if f"@{bot_username}" in text.lower():
            should_reply = True
            # Remove all mentions of the bot
            text = text.replace(f"@{bot_username}", "").strip() 
        elif text.lower().startswith(
            ("hey", "hi", "sun", "oye", BOT_NAME.lower(), "ai")
        ) and len(text) < 30: # Only trigger for short greetings
            should_reply = True

    if should_reply:
        if not text.strip():
            text = "Hi"  # Default to "Hi" if message is empty after stripping username

        await client.send_chat_action(message.chat.id, ChatAction.TYPING)

        response = await get_ai_response(
            message.from_user.id, text, message.from_user.first_name, message.chat.type
        )
        await message.reply_text(response)

        # Send a sticker occasionally (30% chance)
        if random.random() < 0.35:
            await send_random_sticker(client, message)

# --- Voice Handler ---
@app.on_message(
    filters.voice
    & ~filters.via_bot,
    group=8,
)
async def ai_voice_handler(client: Client, message: Message):
    # Check if chatbot is enabled
    if not await is_chatbot_on(message.chat.id):
        return

    if not message.from_user:
        return

    # Only reply to voice notes in Private, or if replied to bot in Group
    should_reply = False
    if message.chat.type == ChatType.PRIVATE:
        should_reply = True
    elif message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == client.me.id:
        should_reply = True
    
    if should_reply:
        await client.send_chat_action(message.chat.id, ChatAction.RECORD_AUDIO)
        
        # Download the voice note
        file_obj = await client.download_media(message, in_memory=True)
        
        # Transcribe
        text = await transcribe_audio(file_obj)
            
        if text:
            # Send transcribed text to AI for response
            response = await get_ai_response(message.from_user.id, text, message.from_user.first_name, message.chat.type)
            await message.reply_text(response)

# --- Sticker Handler ---
@app.on_message(filters.sticker, group=7)
async def ai_sticker_handler(client: Client, message: Message):
    if not message.sticker:
        return

    if not message.from_user:
        return

    if not await is_chatbot_on(message.chat.id):
        return

    should_reply = False
    if message.chat.type == ChatType.PRIVATE:
        should_reply = True
    elif message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == client.me.id:
        should_reply = True

    if should_reply:
        await client.send_chat_action(message.chat.id, ChatAction.CHOOSE_STICKER)
        if not await send_random_sticker(client, message):
            # Fallback to text if sticker sending fails
            cute_responses = ["😊", "💕", "✨", "(⁠≧⁠▽⁠≦⁠)", "Cᴜᴛᴇ sᴛɪᴄᴋᴇʀ! 💖"]
            await message.reply_text(random.choice(cute_responses))


# --- /ask command ---
@app.on_message(filters.command(["ask", "ai", "gpt", "chatgpt", "solve"]))  # Combined decorators
async def ask_ai_command(client: Client, message: Message):
    if not await check_flood(message):
        return
    if len(message.command) == 1:
        return await message.reply_text(
            "🗣️ **Bᴏʟ ᴋᴜᴄʜ:** `/ask Kʏᴀ ᴄʜᴀʟ ʀᴀʜᴀ ʜᴀɪ?`"
        )

    text = message.text.split(None, 1)[1]
    await client.send_chat_action(message.chat.id, ChatAction.TYPING)

    response = await get_ai_response(
        message.from_user.id, text, message.from_user.first_name, message.chat.type
    )
    await message.reply_text(response)


@app.on_message(filters.command("getpackname"))
async def get_pack_name_handler(client: Client, message: Message):
    if message.reply_to_message and message.reply_to_message.sticker:
        pack_name = message.reply_to_message.sticker.set_name
        await message.reply_text(f"📂 **Pack Name:** `{pack_name}`\n\nCopy this and add it to `STICKER_PACKS` in `Gpt.py`.")
    else:
        await message.reply_text("⚠️ Reply to a sticker to get its pack name.")


__MODULE__ = "AI ChatBot"
__HELP__ = """
**Cʜᴀᴛʙᴏᴛ Fᴇᴀᴛᴜʀᴇs**

Sᴀɴʏᴀ ʜᴀs ᴀɴ ᴀᴅᴠᴀɴᴄᴇᴅ AI ᴄʜᴀᴛʙᴏᴛ ᴡɪᴛʜ ᴀ ᴜɴɪǫᴜᴇ ᴘᴇʀsᴏɴᴀ.

**Cᴏᴍᴍᴀɴᴅs:**
» /chatbot: (Admins only) Oᴘᴇɴs ᴛʜᴇ ᴄʜᴀᴛʙᴏᴛ sᴇᴛᴛɪɴɢs ᴍᴇɴᴜ ғᴏʀ ᴛʜᴇ ɢʀᴏᴜᴘ.
» /ask [ǫᴜᴇsᴛɪᴏɴ]: Dɪʀᴇᴄᴛʟʏ ᴀsᴋ ᴛʜᴇ AI ᴀ ǫᴜᴇsᴛɪᴏɴ.

**Hᴏᴡ ᴛᴏ Usᴇ:**
1. **Iɴ Gʀᴏᴜᴘs:**
   - Admins can use `/chatbot` to enable/disable the AI.
   - To talk to her, reply to her messages or mention her (`@FridayMusicBot`).
   - She will also respond to short greetings like 'hi', 'hello', 'friday', etc.
2. **Iɴ PM:**
   - Use `/chatbot` to enable/disable the AI.
   - Just send her a message to talk.
"""

import re
import asyncio
from SANYAMUSIC import app
import config
from config import BOT_USERNAME
from SANYAMUSIC.mongo.filtersdb import add_filter_db, get_filters_list, get_filter, stop_all_db, stop_db
from SANYAMUSIC.utils.filters_func import GetFIlterMessage, get_text_reason, SendFilterMessage
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from SANYAMUSIC.misc import SUDOERS

# Standard admin checking
async def check_admin(chat_id, user_id):
    if user_id in SUDOERS:
        return True
    try:
        user = await app.get_chat_member(chat_id, user_id)
        if user.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return True
    except:
        pass
    return False

# background deletion 
async def delete_after_delay(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

@app.on_message(filters.command("filter", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def _filter(client, message):
    chat_id = message.chat.id
    if not await check_admin(chat_id, message.from_user.id):
        return await message.reply("You need to be an admin to do this.")

    if len(message.command) < 2:
        msg = await message.reply("You need to give the filter a name!")  
        asyncio.create_task(delete_after_delay(msg, 30))
        return 

    if not message.reply_to_message and len(message.command) < 3:
        msg = await message.reply("You need to give the filter some content!")
        asyncio.create_task(delete_after_delay(msg, 30))
        return

    filter_name, filter_reason = get_text_reason(message)

    content, text, data_type = await GetFIlterMessage(message)
    await add_filter_db(chat_id, filter_name=filter_name, content=content, text=text, data_type=data_type)
    msg = await message.reply(f"Saved filter '`{filter_name}`'.")
    asyncio.create_task(delete_after_delay(msg, 30))


@app.on_message(~filters.bot & filters.group, group=4)
async def FilterCheckker(client, message):
    if not message.text:
        return
    text = message.text
    chat_id = message.chat.id
    
    ALL_FILTERS = await get_filters_list(chat_id)
    if not ALL_FILTERS or len(ALL_FILTERS) == 0:
        return

    for filter_ in ALL_FILTERS:
        if (message.command and message.command[0] == 'filter' and len(message.command) >= 2 and message.command[1] == filter_):
            return
            
        pattern = r"( |^|[^\w])" + re.escape(filter_) + r"( |$|[^\w])"
        if re.search(pattern, text, flags=re.IGNORECASE):
            filter_name, content, text, data_type = await get_filter(chat_id, filter_)
            sent_filter_msg = await SendFilterMessage(message=message, filter_name=filter_, content=content, text=text, data_type=data_type)
            if sent_filter_msg:
                asyncio.create_task(delete_after_delay(sent_filter_msg, 30))

@app.on_message(filters.command("filters", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def _filters(client, message):
    chat_id = message.chat.id
    chat_title = message.chat.title 
    FILTERS = await get_filters_list(chat_id)
    
    if len(FILTERS) == 0:
        msg = await message.reply(f'No filters in {chat_title}.')
        asyncio.create_task(delete_after_delay(msg, 30))
        return

    filters_list = f'List of filters in {chat_title}:\n'
    for filter_ in FILTERS:
        filters_list += f'- `{filter_}`\n'
    
    msg = await message.reply(filters_list)
    asyncio.create_task(delete_after_delay(msg, 30))


@app.on_message(filters.command("stopall", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def stopall(client, message):
    chat_id = message.chat.id
    chat_title = message.chat.title 
    
    if message.from_user.id not in SUDOERS:
        try:
            user = await client.get_chat_member(chat_id, message.from_user.id)
            if not user.status == ChatMemberStatus.OWNER:
                msg = await message.reply_text("Only Owner Can Use This!!") 
                asyncio.create_task(delete_after_delay(msg, 30))
                return
        except:
            return

    KEYBOARD = InlineKeyboardMarkup([
        [InlineKeyboardButton(text='Delete all filters', callback_data='custfilters_stopall')],
        [InlineKeyboardButton(text='Cancel', callback_data='custfilters_cancel')]
    ])

    await message.reply(text=(f'Are you sure you want to stop **ALL** filters in {chat_title}? This action is irreversible.'), reply_markup=KEYBOARD)

@app.on_callback_query(filters.regex("^custfilters_"))
async def stopall_callback(client, callback_query: CallbackQuery):  
    chat_id = callback_query.message.chat.id 
    query_data = callback_query.data.split('_')[1]  

    if callback_query.from_user.id not in SUDOERS:
        try:
            user = await client.get_chat_member(chat_id, callback_query.from_user.id)
            if not user.status == ChatMemberStatus.OWNER:
                return await callback_query.answer("Only Owner Can Use This!!", show_alert=True) 
        except:
            return
    
    if query_data == 'stopall':
        await stop_all_db(chat_id)
        await callback_query.edit_message_text(text="I've deleted all chat filters.")
        asyncio.create_task(delete_after_delay(callback_query.message, 30))
    
    elif query_data == 'cancel':
        await callback_query.edit_message_text(text='Cancelled.')
        asyncio.create_task(delete_after_delay(callback_query.message, 30))


@app.on_message(filters.command("stopfilter", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def stop(client, message):
    chat_id = message.chat.id
    if not await check_admin(chat_id, message.from_user.id):
        return await message.reply("You need to be an admin to do this.")
        
    if not (len(message.command) >= 2):
        msg = await message.reply('Use Help To Know The Command Usage')
        asyncio.create_task(delete_after_delay(msg, 30))
        return
    
    filter_name = message.command[1]
    if (filter_name not in await get_filters_list(chat_id)):
        msg = await message.reply("You haven't saved any filters on this word yet!")
        asyncio.create_task(delete_after_delay(msg, 30))
        return
    
    await stop_db(chat_id, filter_name)
    msg = await message.reply(f"I've stopped `{filter_name}`.")
    asyncio.create_task(delete_after_delay(msg, 30))

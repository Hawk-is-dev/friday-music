import config
from pyrogram import filters
from pyrogram.types import Message
from SANYAMUSIC import app
from SANYAMUSIC.core.call import SANYA
from SANYAMUSIC.utils.database import set_loop
from SANYAMUSIC.utils.decorators import AdminRightsCheck
from SANYAMUSIC.utils.inline import close_markup


@app.on_message(
    filters.command(["stop", "cend", "cstop", "end"], prefixes=config.COMMAND_PREFIXES) & filters.group & ~config.BANNED_USERS
)
@AdminRightsCheck
async def stop_music(cli, message: Message, _, chat_id):
    if not len(message.command) == 1:
        return
    await SANYA.stop_stream(chat_id)
    await set_loop(chat_id, 0)
    await message.reply_text(
        _["admin_5"].format(message.from_user.mention), reply_markup=close_markup(_)
    )

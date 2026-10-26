# -----------------------------------------------
# 🔸 Friday Music Project
# 🔹 Developed & Maintained by: Stark (https://github.com/urstark)
# 📅 Copyright © 2022 – All Rights Reserved
#
# 📖 License:
# This source code is open for educational and non-commercial use ONLY.
# You are required to retain this credit in all copies or substantial portions of this file.
# Commercial use, redistribution, or removal of this notice is strictly prohibited
# without prior written permission from the author.
#
# ❤️ Made with dedication and love by urstark
# -----------------------------------------------
from typing import Union
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from SANYAMUSIC import app


def help_pannel(_, start: bool = False):
    buttons = [
        [
            InlineKeyboardButton(text="ᴍᴜsɪᴄ", callback_data="help_category music"),
            InlineKeyboardButton(text="ᴍᴀɴᴀɢᴇᴍᴇɴᴛ", callback_data="help_category management"),
        ],
        [
            InlineKeyboardButton(text="ᴛᴏᴏʟs & ᴀɪ", callback_data="help_category tools"),
            InlineKeyboardButton(text="ғᴜɴ & ᴇxᴛʀᴀs", callback_data="help_category fun"),
        ],
        [
            InlineKeyboardButton(text="ʙᴏᴛ sᴇᴛᴛɪɴɢs", callback_data="help_category settings"),
        ],
    ]

    if start:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=_["BACK_BUTTON"],
                    callback_data="settings_back_helper",
                ),
            ]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=_["BACK_BUTTON"],
                    callback_data="settings_back_helper",
                ),
            ]
        )

    return InlineKeyboardMarkup(buttons)


def help_category_pannel(_, category):
    buttons = []

    if category == "music":
        buttons = [
            [
                InlineKeyboardButton(text="ᴀᴅᴍɪɴ", callback_data="help_callback hb1 music"),
                InlineKeyboardButton(text="ᴘʟᴀʏ", callback_data="help_callback hb11 music"),
            ],
            [
                InlineKeyboardButton(text="ᴄ-ᴘʟᴀʏ", callback_data="help_callback hb6 music"),
                InlineKeyboardButton(text="ᴄ-ᴀᴅᴍɪɴ", callback_data="help_callback hb33 music"),
            ],
            [
                InlineKeyboardButton(text="ʟᴏᴏᴘ", callback_data="help_callback hb8 music"),
                InlineKeyboardButton(text="sʜᴜғғʟᴇ", callback_data="help_callback hb12 music"),
            ],
            [
                InlineKeyboardButton(text="sᴇᴇᴋ", callback_data="help_callback hb13 music"),
                InlineKeyboardButton(text="sᴘᴇᴇᴅ", callback_data="help_callback hb15 music"),
            ],
            [
                InlineKeyboardButton(text="ᴅɪsᴄᴏᴠᴇʀ", callback_data="help_callback hb37 music"),
                InlineKeyboardButton(text="ᴘʟᴀʏʟɪsᴛ", callback_data="help_callback hb38 music"),
            ],
        ]
    elif category == "management":
        buttons = [
            [
                InlineKeyboardButton(text="ᴀᴄᴛɪᴏɴ", callback_data="help_callback hb21 management"),
                InlineKeyboardButton(text="ᴍᴏᴅᴇʀᴀᴛᴏʀ", callback_data="help_callback hb35 management"),
            ],
            [
                InlineKeyboardButton(text="ᴀᴜᴛʜ", callback_data="help_callback hb2 management"),
                InlineKeyboardButton(text="ɢ-sᴇᴛᴛɪɴɢs", callback_data="help_callback hb17 management"),
            ],
            [
                InlineKeyboardButton(text="ᴀᴘᴘʀᴏᴠᴇ", callback_data="help_callback hb28 management"),
                InlineKeyboardButton(text="ғɪʟᴛᴇʀs", callback_data="help_callback hb29 management"),
            ],
            [
                InlineKeyboardButton(text="ɢ-ɪɴғᴏ", callback_data="help_callback hb32 management"),
                InlineKeyboardButton(text="ʙʟ-ᴄʜᴀᴛ", callback_data="help_callback hb4 management"),
            ],
            [
                InlineKeyboardButton(text="ʙʟ-ᴜsᴇʀs", callback_data="help_callback hb5 management"),
                InlineKeyboardButton(text="ɢ-ʙᴀɴ", callback_data="help_callback hb7 management"),
            ],
        ]
    elif category == "tools":
        buttons = [
            [
                InlineKeyboardButton(text="ᴄʜᴀᴛʙᴏᴛ", callback_data="help_callback hb16 tools"),
                InlineKeyboardButton(text="ǫᴜᴏᴛʟʏ", callback_data="help_callback hb26 tools"),
            ],
            [
                InlineKeyboardButton(text="ᴅᴏᴡɴʟᴏᴀᴅ", callback_data="help_callback hb14 tools"),
                InlineKeyboardButton(text="ɪɴғᴏ", callback_data="help_callback hb20 tools"),
            ],
            [
                InlineKeyboardButton(text="ᴘɪɴɢ", callback_data="help_callback hb10 tools"),
                InlineKeyboardButton(text="ғᴏɴᴛs", callback_data="help_callback hb22 tools"),
            ],
            [
                InlineKeyboardButton(text="ᴛᴛs", callback_data="help_callback hb24 tools"),
                InlineKeyboardButton(text="sᴏɴɢ ғɪɴᴅ", callback_data="help_callback hb39 tools"),
            ],
        ]
    elif category == "fun":
        buttons = [
            [
                InlineKeyboardButton(text="ғᴜɴ", callback_data="help_callback hb25 fun"),
                InlineKeyboardButton(text="ᴄᴏᴜᴘʟᴇs", callback_data="help_callback hb30 fun"),
            ],
            [
                InlineKeyboardButton(text="ᴛʀᴜᴛʜ/ᴅᴀʀᴇ", callback_data="help_callback hb23 fun"),
                InlineKeyboardButton(text="ᴇxᴛʀᴀs", callback_data="help_callback hb36 fun"),
            ],
            [
                InlineKeyboardButton(text="sᴛɪᴄᴋᴇʀs", callback_data="help_callback hb18 fun"),
                InlineKeyboardButton(text="ᴛᴀɢs", callback_data="help_callback hb19 fun"),
            ],
        ]
    elif category == "settings":
        buttons = [
            [
                InlineKeyboardButton(text="sᴇᴛᴛɪɴɢs", callback_data="help_callback hb31 settings"),
                InlineKeyboardButton(text="ɢ-ᴄᴀsᴛ", callback_data="help_callback hb3 settings"),
            ],
            [
                InlineKeyboardButton(text="ʟᴏɢs", callback_data="help_callback hb9 settings"),
                InlineKeyboardButton(text="ʀᴇʟᴏᴀᴅ", callback_data="help_callback hb34 settings"),
            ],
            [
                InlineKeyboardButton(text="sᴜᴅᴏ", callback_data="help_callback hb27 settings"),
            ],
        ]

    buttons.append(
        [
            InlineKeyboardButton(text=_["BACK_BUTTON"], callback_data="open_help_panel"),
        ]
    )
    return InlineKeyboardMarkup(buttons)


def help_back_markup(_, category):
    upl = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=_["BACK_BUTTON"],
                    callback_data=f"help_category {category}",
                ),
            ]
        ]
    )
    return upl


def private_help_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_4"],
                url=f"https://t.me/{app.username}?start=help",
            ),
        ],
    ]
    return buttons

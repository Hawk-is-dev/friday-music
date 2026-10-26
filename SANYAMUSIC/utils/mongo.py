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
from typing import Dict, Union
from motor.motor_asyncio import AsyncIOMotorClient as MongoCli
from config import MONGO_DB_URI

mongo = MongoCli(MONGO_DB_URI)
#db = mongo.Anon
db = mongo.SANYAMUSIC

afkdb = db.afk
filtersdb = db.filters
chatbotdb = db.chatbot

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
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_DB_URI
from ..logging import LOGGER

class Mongo:
    def __init__(self):
        self._client = None
        self._db = None

    @property
    def mongodb(self):
        if self._db is None:
            LOGGER(__name__).info("Connecting to your Mongo Database...")
            try:
                # Optimized connection pooling for lower latency
                self._client = AsyncIOMotorClient(
                    MONGO_DB_URI,
                    maxPoolSize=100,
                    minPoolSize=10,
                    maxIdleTimeMS=10000,
                    connectTimeoutMS=10000,
                    serverSelectionTimeoutMS=30000
                )
                self._db = self._client.SANYAMUSIC
                LOGGER(__name__).info("Connected to your Mongo Database.")
            except Exception as e:
                LOGGER(__name__).error(f"Failed to connect to your Mongo Database: {e}")
                exit()
        return self._db

class SimpleLazyProxy:
    def __init__(self, func):
        self._func = func
    def __getattr__(self, name):
        return getattr(self._func(), name)

mongo = Mongo()
def get_mongodb():
    return mongo.mongodb

mongodb = SimpleLazyProxy(get_mongodb)

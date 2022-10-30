import os

from dotenv import load_dotenv

load_dotenv()

mongo_pass = os.getenv("MONGO_PASSWORD")
mongo_user = os.getenv("MONGO_USERNAME")
mongo_url = os.getenv("MONGO_URL")
mongo_url = mongo_url.format(password=mongo_pass, username=mongo_user)

from motor.motor_asyncio import AsyncIOMotorClient

from .mongo import Document

mongo = AsyncIOMotorClient(mongo_url)


class MongoDB:
    def __init__(self):
        self._database = mongo["cdn_users"]
        self.users = Document(self._database, "users")
        self.keys = Document(self._database, "keys")


db = MongoDB()

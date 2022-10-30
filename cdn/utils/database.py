import os

from dotenv import load_dotenv

load_dotenv()

mongo_pass = os.getenv("MONGO_PASSWORD")
mongo_user = os.getenv("MONGO_USERNAME")
mongo_url = os.getenv("MONGO_URL")
mongo_url = mongo_url.format(password=mongo_pass, username=mongo_user)

import motor.motor_asyncio as motor

client = motor.AsyncIOMotorClient(mongo_url)


class MongoDB:
    def __init__(self, client):
        self.client = client
        self.db = client["cdn_users"]

    async def get_user(self, id: str):
        return await self.db.users.find_one({"id": id})

    async def get_key(self, key: str):
        return await self.db.keys.find_one({"key": key})

    async def upsert_user(self, id: str, data: dict):
        return await self.db.users.update_one({"id": id}, {"$set": data}, upsert=True)

    async def upsert_key(self, key: str, data: dict):
        return await self.db.keys.update_one({"key": key}, {"$set": data}, upsert=True)

    async def delete_key(self, key: str):
        return await self.db.keys.delete_one({"key": key})

    async def delete_user(self, id: str):
        return await self.db.users.delete_one({"id": id})


db = MongoDB(client)

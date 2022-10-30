import asyncio
import os

from aiobotocore.session import get_session
from dotenv import load_dotenv
from requests import session

load_dotenv()


BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID")


async def main():
    session = get_session()
    print(AWS_ACCESS_KEY_ID)
    print(AWS_SECRET_ACCESS_KEY)
    async with session.create_client(
        "s3",
        "auto",
        endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    ) as client:
        response = await client.list_buckets()
        print(response)


asyncio.run(main())

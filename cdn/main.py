import os

from dotenv import load_dotenv

load_dotenv()

ACCESS_KEY_ID = os.getenv("ACCESS_KEY_ID")
SECRET_ACCESS_KEY = os.getenv("SECRET_ACCESS_KEY")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")

# https://developers.cloudflare.com/r2/examples/boto3/

import boto3

s3 = boto3.resource(
    "s3",
    "auto",
    endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=SECRET_ACCESS_KEY,
)

print("BUCKETS")
for bucket in s3.buckets.all():
    print(bucket.name)

bucket = s3.Bucket("mooshi-rpi-bucket")

print("Objects:")
for object in bucket.objects.all():
    print("- " + object.key)

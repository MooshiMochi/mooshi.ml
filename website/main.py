import os
from base64 import b64encode
from json import dumps as JSON_ENCODER
from typing import Optional

import uvicorn
from aiobotocore.session import get_session
from aiohttp import ClientSession
from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from utils.checks import isUserAuthorized, parse_user_form_cookie

load_dotenv()

_PORT = int(os.getenv("PORT"))
_HOST = os.getenv("HOST")

API_ENDPOINT = "https://discord.com/api/v10"
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID")

if os.name == "nt":
    _HOST = "192.168.0.11"
    REDIRECT_URI = f"http://{_HOST}:{_PORT}/auth/handshake"
    DISCORD_REDIRECT_URI = f"https://discord.com/api/oauth2/authorize?client_id=1035273148448379021&redirect_uri=http%3A%2F%2F{_HOST}%3A80%2Fauth%2Fhandshake&response_type=code&scope=identify"
    BASE_URL = f"https://cdn.mooshi.ml"

else:
    _HOST = "https://cdn.mooshi.ml"
    REDIRECT_URI = f"{_HOST}/auth/handshake"
    DISCORD_REDIRECT_URI = "https://discord.com/api/oauth2/authorize?client_id=1035273148448379021&redirect_uri=https%3A%2F%2Fcdn.mooshi.ml%2Fauth%2Fhandshake&response_type=code&scope=identify"
    BASE_URL = _HOST


class APIWrapper(FastAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.session: ClientSession = None
        self.boto_session = get_session()


app = APIWrapper()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static/templates")


@app.on_event("startup")
async def app_startup():
    app.session = ClientSession()
    logger.info("Started session")


@app.on_event("shutdown")
async def app_shutdown():
    await app.session.close()
    logger.info("Closed session")


async def exchange_code(code: str) -> Optional[str]:
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with app.session.post(
        "https://discord.com/api/oauth2/token", data=data, headers=headers
    ) as response:
        data = await response.json()
        logger.debug(f"Got response from discord: {data}")
        if data.get("error") or data.get("message"):
            logger.error(data)
            return None
        return data.get("access_token", data)


async def get_user(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    async with app.session.get(
        f"{API_ENDPOINT}/users/@me", headers=headers
    ) as response:
        data = await response.json()
        return data


@app.get("/auth/login")
async def login(request: Request, response: Response) -> None:
    if not isUserAuthorized(request.cookies):
        return RedirectResponse(DISCORD_REDIRECT_URI, 303)
    else:
        return RedirectResponse("/", 303)


@app.get("/auth/logout")
async def logout(request: Request, response: Response) -> None:
    if not isUserAuthorized(request.cookies):
        return Response("You do not have access to this page", 403)
    response = RedirectResponse("/", 303)
    response.delete_cookie("user")
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, response: Response) -> None:
    logger.debug(f"Authorized: {isUserAuthorized(request.cookies)}")
    if not isUserAuthorized(request.cookies):
        return templates.TemplateResponse("login.html", {"request": request})
    else:
        response = templates.TemplateResponse("index.html", {"request": request})
        response.set_cookie("user", request.cookies.get("user"))
        return response


@app.get("/clear_cookies")
async def cookie_clear(request: Request):
    response = RedirectResponse("/", 303)
    response.delete_cookie("user")
    return response


@app.get("/auth/handshake")
async def handshake(request: Request, response: Response):
    if code := request.query_params.get("code"):
        access_token = await exchange_code(code)
        print(access_token)
    else:  # gon be evil and keep redirecting them to discord's oauth2 page until they approve ;)
        return RedirectResponse(
            DISCORD_REDIRECT_URI,
            303,
        )

    user = await get_user(access_token)
    print(user)
    response = RedirectResponse("/", 303)
    response.set_cookie(
        "user",
        b64encode(JSON_ENCODER(user).encode("utf-8")).decode("utf-8"),
        httponly=True,
    )
    return response


async def upload_file_to_cdn(folder: str, file: File) -> str:
    try:
        async with app.boto_session.create_client(
            "s3",
            region_name="auto",
            endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
        ) as client:
            await client.put_object(
                Bucket=BUCKET_NAME,
                Key=f"{folder}/{file.filename}",
                Body=await file.read(),
            )
            return "https://cdn.mooshi.ml/" + f"{folder}/{file.filename}"
    except Exception as e:
        logger.error(e)
        return f"Something went wrong!: {e}"


async def delete_file_from_cdn(folder: str, filename: str) -> str | bool:
    try:
        async with app.boto_session.create_client(
            "s3",
            region_name="auto",
            endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
        ) as client:
            await client.delete_object(
                Bucket=BUCKET_NAME,
                Key=f"{folder}/{filename}",
            )
            return True
    except Exception as e:
        logger.error(e)
        return f"Something went wrong!: {e}"


async def get_stored_files(folder: str) -> list[str] | None:
    try:
        async with app.boto_session.create_client(
            "s3",
            region_name="auto",
            endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
        ) as client:
            response = await client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=folder)
            if response.get("Contents"):
                return [
                    f"https://cdn.mooshi.ml/{obj.get('Key')}"
                    for obj in response.get("Contents")
                ]
            else:
                return None
    except Exception as e:
        logger.error(e)
        return None


@app.post("/upload")
async def upload(request: Request, file: UploadFile) -> None:

    if not request.cookies.get("user"):
        return Response("This endpoint requires valid authentication", 401)
    if not isUserAuthorized(request.cookies):
        return Response("You do not have access to this page", 401)

    user = parse_user_form_cookie(request.cookies)
    folder = user.get("id")
    if not folder:
        return Response("You do not have access to this page", 401)

    if not file:
        return Response("No file param was provided", 400)

    resp = await upload_file_to_cdn(folder, file)
    return {"message": resp}


@app.delete("/delete")
async def delete(request: Request, filename: str) -> None:
    if not request.cookies.get("user"):
        return Response("This endpoint requires valid authentication", 401)
    if not isUserAuthorized(request.cookies):
        return Response("You do not have access to this page", 401)

    user = parse_user_form_cookie(request.cookies)
    folder = user.get("id")
    if not folder:
        return Response("You do not have access to this page", 401)

    if not filename:
        return Response("No file param was provided", 400)

    resp = await delete_file_from_cdn(folder, filename)
    if not isinstance(resp, str):
        return {"message": "File deleted successfully"}
    return {"error": resp}


@app.get("/files")
async def get_files(request: Request) -> None:
    if not request.cookies.get("user"):
        return Response("This endpoint requires valid authentication", 401)
    if not isUserAuthorized(request.cookies):
        return Response("You do not have access to this page", 401)

    user = parse_user_form_cookie(request.cookies)
    folder = user.get("id")
    if not folder:
        return Response("You do not have access to this page", 401)

    folder_url = f"{BASE_URL}/{folder}"
    try:
        return {"message": folder_url, "files": await get_stored_files(folder)}
    except Exception as e:
        return {"message": f"Something went wrong!: {e}"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=_HOST, port=_PORT, reload=True)

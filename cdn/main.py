import os
from base64 import b64encode
from json import dumps as JSON_ENCODER
from typing import Optional

import aiofiles
import uvicorn
from aiohttp import ClientSession
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from utils.checks import isMooshi, isUserAuthorized, parse_user_form_cookie
from utils.database import db

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

BASE_URL = f"https://cdn.mooshi.ml"

if os.name == "nt":
    _HOST = "192.168.0.11"
    REDIRECT_URI = f"http://{_HOST}:{_PORT}/auth/handshake"
    DISCORD_REDIRECT_URI = f"https://discord.com/api/oauth2/authorize?client_id=1035273148448379021&redirect_uri=http%3A%2F%2F{_HOST}%3A8080%2Fauth%2Fhandshake&response_type=code&scope=identify"
    BASE_URL = f"http://{_HOST}:{_PORT}"

else:
    REDIRECT_URI = f"{BASE_URL}/auth/handshake"
    DISCORD_REDIRECT_URI = "https://discord.com/api/oauth2/authorize?client_id=1035273148448379021&redirect_uri=https%3A%2F%2Fcdn.mooshi.ml%2Fauth%2Fhandshake&response_type=code&scope=identify"

if not os.path.exists("content"):
    os.mkdir("content")


class APIWrapper(FastAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.session: ClientSession = None


app = APIWrapper()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/content", StaticFiles(directory="content"), name="content")
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
        # logger.debug(f"Got response from discord: {data}")
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
async def login(request: Request) -> None:
    if not await isUserAuthorized(request.cookies):
        return RedirectResponse(DISCORD_REDIRECT_URI, 303)
    else:
        return RedirectResponse("/", 303)


@app.get("/auth/logout")
async def logout(request: Request) -> None:
    if not await isUserAuthorized(request.cookies):
        return JSONResponse({"error": "You do not have access to this page"}, 403)
    response = RedirectResponse("/", 303)
    response.delete_cookie("user")
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> None:
    logger.debug(f"Authorized: {await isUserAuthorized(request.cookies)}")
    if not await isUserAuthorized(request.cookies):
        return templates.TemplateResponse("login.html", {"request": request})
    else:
        if isMooshi(request.cookies):
            response = templates.TemplateResponse("admin.html", {"request": request})
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
async def handshake(request: Request):
    if code := request.query_params.get("code"):
        access_token = await exchange_code(code)
        print(access_token)
    else:  # gon be evil and keep redirecting them to discord's oauth2 page until they approve ;)
        return RedirectResponse(
            DISCORD_REDIRECT_URI,
            303,
        )

    user = await get_user(access_token)
    response = RedirectResponse("/", 303)
    response.set_cookie(
        "user",
        b64encode(JSON_ENCODER(user).encode("utf-8")).decode("utf-8"),
        httponly=True,
    )
    db_user = await db.users.get_by_id(user.get("id", "girthychode69420"))
    if db_user:
        user["_id"] = user.get("id", "0")
        await db.users.upsert(user)
    return response


@app.post("/upload")
async def upload(request: Request, file: UploadFile) -> None:

    if not request.cookies.get("user"):
        return JSONResponse(
            {"error": "This endpoint requires valid authentication"}, 401
        )
    if not await isUserAuthorized(request.cookies):
        return JSONResponse({"error": "You do not have access to this page"}, 401)

    user = parse_user_form_cookie(request.cookies)
    folder = user.get("id")
    if not folder:
        return JSONResponse({"error": "You do not have access to this page"}, 401)

    if not file:
        return JSONResponse({"error": "No file param was provided"}, 400)

    if not os.path.exists(f"content/{folder}"):
        os.makedirs(f"content/{folder}")

    async with aiofiles.open(f"content/{folder}/{file.filename}", "wb+") as f:
        await f.write(file.file.read())

    return {"message": f"https://cdn.mooshi.ml/content/{folder}/{file.filename}"}


@app.delete("/delete")
async def delete(
    request: Request, filename: Optional[str] = None, user_id: Optional[str] = None
) -> None:
    logger.info(f"Filename: {filename} User: {user_id}")
    if not request.cookies.get("user"):
        return JSONResponse(
            {"error": "This endpoint requires valid authentication"}, 401
        )
    if not await isUserAuthorized(request.cookies):
        return JSONResponse({"error": "You do not have access to this page"}, 401)

    user = parse_user_form_cookie(request.cookies)
    folder = user.get("id")
    if not folder:
        return JSONResponse({"error": "You do not have access to this page"}, 401)

    if not filename and not user_id:
        return JSONResponse({"error": "No filename or user_id param was provided"}, 400)

    if filename:
        if not os.path.exists(f"content/{folder}"):
            os.makedirs(f"content/{folder}")

        if not os.path.exists(f"content/{folder}/{filename}"):
            return {"error": "File does not exist"}

        os.remove(f"content/{folder}/{filename}")

        return {"message": "File deleted successfully"}

    elif user_id:
        user_data = await db.users.get_by_id(user_id)
        if not user_data:
            return {"error": "User does not have access to the database."}
        else:
            user_data = await db.users.delete_by_id(user_id)
            return {"message": "User deleted successfully", "data": user_data}

    else:
        # can only provide one param at a time
        return JSONResponse({"error": "You can only provide one param at a time"}, 400)


@app.get("/users")
async def get_users(request: Request) -> None:
    if not request.cookies.get("user"):
        return JSONResponse(
            {"error": "This endpoint requires valid authentication"}, 401
        )
    if not isMooshi(request.cookies):
        return JSONResponse({"error": "You do not have access to this page"}, 401)

    users = await db.users.get_all()
    # logger.debug(f"Returning: {users}")
    return JSONResponse({"users": users}, 200)


@app.post("/add_user")
async def add_user(request: Request, user_id: Optional[str]) -> None:
    if not request.cookies.get("user"):
        return JSONResponse(
            {"error": "This endpoint requires valid authentication"}, 401
        )
    if not isMooshi(request.cookies):
        return JSONResponse({"error": "You do not have access to this page"}, 401)

    if not user_id:
        return JSONResponse({"error": "No user_id param was provided"}, 400)

    user_data = await db.users.get_by_id(user_id)
    if not user_data:
        await db.users.upsert({"_id": user_id})
        return {"message": "User added successfully"}
    else:
        return {"error": "User is already in the database."}


@app.get("/files")
async def get_files(request: Request) -> None:
    if not request.cookies.get("user"):
        return JSONResponse(
            {"error": "This endpoint requires valid authentication"}, 401
        )
    if not await isUserAuthorized(request.cookies):
        return JSONResponse({"error": "You do not have access to this page"}, 401)

    user = parse_user_form_cookie(request.cookies)
    folder = user.get("id")
    if not folder:
        return JSONResponse({"error": "You do not have access to this page"}, 401)

    folder_url = f"{BASE_URL}/{folder}"

    if not os.path.exists(f"content/{folder}"):
        os.makedirs(f"content/{folder}")

    try:
        return {
            "message": folder_url,
            "files": [
                f"{BASE_URL}/content/{folder}/{x}"
                for x in os.listdir(f"content/{folder}")
            ],
        }
    except Exception as e:
        return {"message": f"Something went wrong!: {e}"}


if __name__ == "__main__":
    logger.info("Starting server")
    logger.info(f"Attempting to run on {_HOST}:{_PORT}")
    logger.info(f"Host type: {type(_HOST)} | Port type: {type(_PORT)}")
    if os.name == "nt":
        uvicorn.run("main:app", host=_HOST, port=_PORT, reload=True)
    else:
        uvicorn.run(app, host=_HOST, port=_PORT)

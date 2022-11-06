from __future__ import annotations

import asyncio
import os
from base64 import b64encode
from typing import Any

import aiohttp
from dotenv import load_dotenv, set_key
from fastapi import FastAPI, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from logger import init_logging
from loguru import logger
from manager import ConnectionManager
from uvicorn import Config, Server

load_dotenv()
init_logging()

try:
    from ujson import dumps as JSON_ENCODER
    from ujson import loads as JSON_DECODER
except ImportError:
    from json import dumps as JSON_ENCODER
    from json import loads as JSON_DECODER


with open("config.json", "r") as f:
    API_CONFIG = JSON_DECODER(f.read())

API_VERSION = API_CONFIG.get("version", "v1")

BASE_API_URL = f"/{API_VERSION}"
# logger: Logger = getLogger("api")


_CLIENT_ID = os.getenv("sp_client_id")
_CLIENT_SECRET = os.getenv("sp_client_secret")
_REDIRECT_URI = os.getenv("sp_redirect_uri")
_SCOPES = [x.strip() for x in os.getenv("sp_scopes").split(",")]
_ACCESS_TOKENS = {}

_ACTIVE_API_TOKENS = [x.strip() for x in os.getenv("api_keys").split(",")]
_MASTER_API_KEY = os.getenv("master_api_key")

_HOST = os.getenv("api_host")
_PORT = os.getenv("api_port")

_CREDS = b64encode(f"{_CLIENT_ID}:{_CLIENT_SECRET}".encode()).decode()
_HEADERS = {
    "Authorization": f"Basic {_CREDS}",
    "Content-Type": "application/x-www-form-urlencoded",
}


def _check_config():
    global _PORT
    for key in [
        _CLIENT_ID,
        _CLIENT_SECRET,
        _REDIRECT_URI,
        _SCOPES,
        _MASTER_API_KEY,
        _ACTIVE_API_TOKENS,
        _HOST,
        _PORT,
    ]:
        if key is None:
            raise ValueError(f"Missing config value for {key=}".split("=")[0])

    if not isinstance(_ACTIVE_API_TOKENS, list):
        raise ValueError(f"{_ACTIVE_API_TOKENS=} must be a list")

    if not isinstance(_SCOPES, list):
        raise ValueError(f"{_SCOPES=} must be a list of strings")

    if not isinstance(_MASTER_API_KEY, str):
        raise ValueError(f"{_MASTER_API_KEY=} must be a str")

    if not _PORT.isdigit():
        raise ValueError(f"{_PORT=} must be a number")
    else:
        _PORT = int(_PORT)

    if not isinstance(_HOST, str):
        raise ValueError(f"{_HOST=} must be a str")


class APIWrapper(FastAPI):
    def __init__(self, manager: ConnectionManager, *args, **kwargs):
        self._data: dict[Any, Any] = {}
        self._data["access_tokens"] = kwargs.pop("access_tokens", {})

        self.manager: ConnectionManager = manager
        self.session: aiohttp.ClientSession = None
        super().__init__(*args, **kwargs)

    def store(self, key, value):
        self._data[key] = value

    def fetch(self, key, default=None, /):
        return self._data.get(key, default)

    def delete(self, key):
        if key in self._data:
            del self._data[key]


_check_config()

_SCOPES = " ".join(_SCOPES)

manager = ConnectionManager()
manager._active_keys = set(_ACTIVE_API_TOKENS)

app: APIWrapper = APIWrapper(
    manager,
    access_tokens=_ACCESS_TOKENS,
    docs_url=None,
    redoc_url=f"{BASE_API_URL}/docs",
)


@app.on_event("startup")
async def app_startup():
    app.session = aiohttp.ClientSession()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("shutdown")
async def app_shutdown():
    await app.session.close()


@app.get("/")
async def index():
    return "Hello World"


@app.get(
    f"{BASE_API_URL}/spotify",
    description="Redirects to Spotify's OAuth2 login page",
    tags=["Spotify"],
)
async def spotify(state: int, playlist_name: str, client_id: int):
    existing_tokens = app.fetch("access_tokens")
    existing_tokens[state] = {"playlist_name": playlist_name, "client_id": client_id}
    app.store("access_tokens", existing_tokens)

    if not app.manager.get_ws(client_id):
        return PlainTextResponse(
            "Client is not connected to the websocket server. Please try again in 5 minutes! If the issue persists, contact a server administrator.",
            status_code=400,
        )
    url = f"https://accounts.spotify.com/authorize?client_id={_CLIENT_ID}&response_type=code&redirect_uri={_REDIRECT_URI}&scope={_SCOPES}&state={state}"
    return RedirectResponse(
        url=url,
        status_code=303,
    )


@app.post(f"{BASE_API_URL}/invalidate", description="Invalidates a token")
async def invalidate_key(master: str, key: str):
    tokens = app.fetch("access_tokens")

    if key not in tokens:
        return PlainTextResponse("Key not found", status_code=404)

    elif master != _MASTER_API_KEY:
        return PlainTextResponse("Invalid master API key", status_code=401)

    tokens = [k for k in tokens if k != key]

    set_key(".env", "api_keys", ", ".join(tokens))
    app.store("access_tokens", tokens)
    return PlainTextResponse("API key invalidated")


@app.get(f"{BASE_API_URL}/new_key")
async def new_key(master: str):
    if master != _MASTER_API_KEY:
        return PlainTextResponse("Invalid master API key", status_code=401)
    new_key = os.urandom(16).hex()
    _ACTIVE_API_TOKENS.append(new_key)
    set_key(".env", "api_keys", ", ".join(_ACTIVE_API_TOKENS))
    return PlainTextResponse(new_key)


@app.get("/routes")
async def routes():
    hidden_routes = [
        "/openapi.json",
        "/docs",
        # "/docs/oauth2-redirect",
        "/",
        "/ws",
        "/api/v1",
    ]
    return PlainTextResponse(
        "• " + "\n• ".join([x.path for x in app.routes if x.path not in hidden_routes])
    )


@app.get(f"{BASE_API_URL}/")
async def index():
    return RedirectResponse(url=f"{BASE_API_URL}/docs", status_code=303)


@app.get("/auth/handshake")
async def handshake(request: Request):
    return {"request": request}


@app.get(f"{BASE_API_URL}/spotify/authorized")
async def authorized(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    try:
        state = int(state)
    except ValueError:
        return PlainTextResponse("Invalid state", status_code=400)

    async with app.session.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "authorization_code",
            "redirect_uri": _REDIRECT_URI,
            "code": code,
            "scope": _SCOPES,
            "state": state,
        },
        headers=_HEADERS,
    ) as response:
        data = await response.json()
        if data.get("error"):
            return data

        data["state"] = state
        data["op"] = 6

    tokens = app.fetch("access_tokens")

    destination_client_id = tokens.get(state, {}).get("client_id", None)

    tokens[state] = data | tokens[state]

    app.store("access_tokens", tokens)

    json_data = tokens.pop(state, {})
    if client := app.manager.get_ws(destination_client_id):
        await client.send_json(json_data)
        return PlainTextResponse(
            f"Authorized, you can close this tab now.\nPlease wait about 10 seconds before running '/playlist load {json_data['playlist_name']}'."
        )
    else:
        return PlainTextResponse(
            "Client not connected. Please contact a server admin.", status_code=400
        )


@app.websocket("/ws/{client_id}")
async def websocket(websocket: WebSocket, client_id: int):
    logger.debug(f"Client #{client_id} connected")
    headers = websocket.headers
    if "Authorization" not in headers:
        await websocket.close(401, "No Authorization header provided")
        return

    if websocket.headers.get("Authorization") not in _ACTIVE_API_TOKENS:
        await websocket.close(401, "Invalid API key")
        return

    await websocket.accept()

    setattr(websocket, "id", client_id)
    await app.manager._handler(websocket)


@app.post("/cdn/upload")
async def upload_file(file: UploadFile):
    if file.content_type not in ["image/jpeg", "image/png"]:
        return PlainTextResponse("Invalid file type", status_code=400)
    file_name = file.filename
    file_path = f"{_CDN_PATH}/{file_name}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return PlainTextResponse(f"File uploaded to {_CDN_URL}/{file_name}")


if __name__ == "__main__":

    async def main():
        uvicorn_config = Config(app=app, host=_HOST, port=_PORT)
        uvicorn_server = Server(config=uvicorn_config)

        logger.info("Starting API server...")

        logger.debug("API started!")
        await uvicorn_server.serve()

    # asyncio.run(main())

    import uvicorn

    uvicorn.run("main:app", host=_HOST, port=_PORT, reload=False)

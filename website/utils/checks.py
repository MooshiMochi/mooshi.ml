from base64 import b64decode, b64encode
from json import loads as JSON_DECODER

from const import AUTHORIZED_IDS
from loguru import logger

from .database import db


def isUserAuthorized(cookie: dict) -> bool:
    user = cookie.get("user", None)
    # logger.debug(f"Raw user: {user}")
    if not user:
        return False
    decoded_user = b64decode(user.encode("utf-8")).decode("utf-8")
    # logger.debug(f"Decoded user: {decoded_user}")
    if isinstance(decoded_user, str):
        try:
            decoded_user = JSON_DECODER(decoded_user)
        except Exception as e:
            logger.error(e)
            return False
    if not isinstance(decoded_user, dict):
        return False
    if decoded_user.get("id") in AUTHORIZED_IDS:
        return True
    return False


def parse_user_form_cookie(cookie: str) -> dict:
    user = cookie.get("user", None)
    if not user:
        return {}

    decoded_user = b64decode(user.encode("utf-8")).decode("utf-8")

    if isinstance(decoded_user, str):
        try:
            decoded_user = JSON_DECODER(decoded_user)
        except Exception as e:
            logger.error(e)
            return {}
    elif not isinstance(decoded_user, dict):
        return {}

    return decoded_user


async def isKeyAuthorized(key: str) -> bool:
    return (await db.get_key(key)) is not None


def userHasFlags(id: str, flag: int) -> bool:
    ...

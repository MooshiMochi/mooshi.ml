from base64 import b64decode
from json import loads as JSON_DECODER

from loguru import logger

from .database import db


async def isUserAuthorized(cookie: dict) -> bool:
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
    if resp := await db.users.get_by_id(decoded_user.get("id", "abracadabra")):
        # logger.debug(f"DB response: {resp}")
        return True

    return False


def isMooshi(cookie: dict) -> bool:
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
    if decoded_user.get("id") == "383287544336613385":
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


async def isKeyAuthorized(user_id: str, key: str) -> bool:
    return (await db.keys.get_by_id(user_id)) == key


def userHasFlags(id: str, flag: int) -> bool:
    ...

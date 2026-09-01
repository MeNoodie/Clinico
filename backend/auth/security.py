"""Password and JWT helpers used by the authentication API."""

from datetime import datetime, timedelta, timezone
import os

from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv


load_dotenv()
# PBKDF2 avoids the bcrypt 4.x/passlib compatibility issue while retaining
# salted, slow password hashes suitable for account credentials.
PASSWORD_CONTEXT = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))


def _secret_key() -> str:
    secret = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY or SECRET_KEY must be set before using authentication")
    return secret


def hash_password(password: str) -> str:
    return PASSWORD_CONTEXT.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return PASSWORD_CONTEXT.verify(password, password_hash)


def create_access_token(user_id: int | str | dict | None = None, data: dict | None = None) -> str:
    payload: dict = {}
    if isinstance(user_id, dict):
        payload.update(user_id)
    elif data is not None:
        payload.update(data)

    if "sub" not in payload:
        if user_id is not None and not isinstance(user_id, dict):
            payload["sub"] = str(user_id)
        else:
            raise ValueError("user_id or sub claim must be provided to create_access_token")
    else:
        payload["sub"] = str(payload["sub"])

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["exp"] = expires_at
    return jwt.encode(payload, _secret_key(), algorithm=ALGORITHM)


def decode_token_payload(token: str) -> dict:
    try:
        return jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def decode_access_token(token: str) -> int:
    payload = decode_token_payload(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise ValueError("Token subject is missing")
    try:
        return int(user_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("User ID subject must be numeric") from exc

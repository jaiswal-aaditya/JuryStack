import hashlib
import secrets

from pwdlib import PasswordHash

PASSWORD_HASHER = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$TOqQQT8n45N+FhxOXUh5Sg$"
    "/zhEgVBSnMNGyFJuhEj6/0prrYP/KdnGdF+0+ogKaG8"
)


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    return PASSWORD_HASHER.verify(password, encoded_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

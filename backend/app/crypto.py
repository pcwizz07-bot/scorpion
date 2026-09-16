import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def imsi_encrypt(imsi: str, key: str | None = None) -> bytes:
    fernet = Fernet((key or settings.CRYPTO_KEY).encode())
    return fernet.encrypt(imsi.encode())


def imsi_decrypt(token: bytes, key: str | None = None) -> str:
    fernet = Fernet((key or settings.CRYPTO_KEY).encode())
    return fernet.decrypt(token).decode()


def imsi_hash(imsi: str, pepper: str | None = None) -> str:
    return hashlib.sha256((imsi + (pepper or settings.CRYPTO_KEY)).encode()).hexdigest()


def mask_imsi(imsi: str) -> str:
    return f"{imsi[:6]}***{imsi[-2:]}"

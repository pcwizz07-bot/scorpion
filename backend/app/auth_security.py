"""Authentication primitives: PBKDF2 password hashing, TOTP (RFC 6238),
opaque session tokens. All stdlib — no new dependencies.
"""
import base64
import hashlib
import hmac
import os
import secrets
import struct
import time

PBKDF2_ITERATIONS = 200_000
SESSION_TTL_SECONDS = 24 * 3600  # field sessions last a day
TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt, hex_digest = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
        return hmac.compare_digest(digest.hex(), hex_digest)
    except (ValueError, TypeError):
        return False


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def totp_uri(secret: str, username: str) -> str:
    return f"otpauth://totp/Scorpion:{username}?secret={secret}&issuer=Scorpion"


def _totp_code_at(secret: str, ts: int) -> str:
    key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8))
    counter = struct.pack(">Q", ts // TOTP_STEP_SECONDS)
    digest = hmac.new(key, counter, hashlib.sha1).digest()
    off = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[off : off + 4])[0] & 0x7FFFFFFF) % (10**TOTP_DIGITS)
    return str(code).zfill(TOTP_DIGITS)


def verify_totp(secret: str, code: str) -> bool:
    code = code.strip()
    if not code.isdigit() or len(code) != TOTP_DIGITS:
        return False
    now = int(time.time())
    # Accept the current step plus one step either side for clock drift.
    return any(
        hmac.compare_digest(_totp_code_at(secret, now + delta * TOTP_STEP_SECONDS), code)
        for delta in (-1, 0, 1)
    )


def issue_session_token() -> tuple[str, str]:
    token = secrets.token_hex(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
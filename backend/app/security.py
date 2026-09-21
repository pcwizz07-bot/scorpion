import hashlib

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Device


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_provisioning_token(
    x_provisioning_token: str | None = Header(default=None),
    x_device_token: str | None = Header(default=None),
) -> None:
    if x_provisioning_token and x_provisioning_token == settings.PROVISIONING_TOKEN:
        return
    if x_device_token:
        # A recognizable credential was supplied, just not one with enough privilege.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


def require_device_token(
    x_device_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Device:
    if not x_device_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    device = db.query(Device).filter(Device.device_token_hash == hash_token(x_device_token)).one_or_none()
    if device is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    return device


def require_device_or_provisioning_token(
    x_device_token: str | None = Header(default=None),
    x_provisioning_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> str:
    """Return the privilege level of the caller: "provisioning" or "device".

    Provisioning (admin) logins may read full IMSI values; device (capture node)
    logins may only read masked values.
    """
    if x_provisioning_token and x_provisioning_token == settings.PROVISIONING_TOKEN:
        return "provisioning"
    if x_device_token:
        device = db.query(Device).filter(Device.device_token_hash == hash_token(x_device_token)).one_or_none()
        if device is not None:
            return "device"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

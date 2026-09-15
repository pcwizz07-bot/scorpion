import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Alert, Device
from app.schemas import DeviceOut, DeviceRegisterRequest, DeviceRegisterResponse
from app.security import hash_token, require_device_or_provisioning_token, require_device_token, require_provisioning_token

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/register", response_model=DeviceRegisterResponse)
def register_device(
    body: DeviceRegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(require_provisioning_token),
) -> DeviceRegisterResponse:
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)

    existing = db.query(Device).filter(Device.name == body.name).one_or_none()
    if existing is not None:
        existing.lat = body.lat
        existing.lng = body.lng
        existing.altitude = body.altitude
        existing.firmware_version = body.firmware_version
        existing.status = "online"
        existing.last_seen = now
        existing.device_token_hash = token_hash
        db.commit()
        db.refresh(existing)
        response.status_code = status.HTTP_200_OK
        return DeviceRegisterResponse(device_id=str(existing.id), device_token=token)

    device = Device(
        name=body.name,
        lat=body.lat,
        lng=body.lng,
        altitude=body.altitude,
        firmware_version=body.firmware_version,
        status="online",
        last_seen=now,
        device_token_hash=token_hash,
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    db.add(
        Alert(
            device_id=device.id,
            type="new_device",
            severity="info",
            title=f"New device registered: {device.name}",
            message=f"Device {device.name} registered at {device.lat}, {device.lng}",
        )
    )
    db.commit()

    response.status_code = status.HTTP_201_CREATED
    return DeviceRegisterResponse(device_id=str(device.id), device_token=token)


@router.post("/{device_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
def heartbeat(
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    device: Device = Depends(require_device_token),
) -> None:
    if device.id != device_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    device.last_seen = datetime.now(timezone.utc)
    device.status = "online"
    db.commit()
    return None


@router.get("", response_model=list[DeviceOut])
def list_devices(
    db: Session = Depends(get_db),
    _: None = Depends(require_device_or_provisioning_token),
) -> list[DeviceOut]:
    devices = db.query(Device).order_by(Device.created_at.desc()).all()
    return [
        DeviceOut(
            id=str(d.id),
            name=d.name,
            lat=d.lat,
            lng=d.lng,
            status=d.status,
            last_seen=d.last_seen,
        )
        for d in devices
    ]

import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.crypto import imsi_decrypt, imsi_encrypt, imsi_hash, mask_imsi
from app.db import get_db
from app.models import Alert, Device, ImsiObservation, TrackedImsi
from app.schemas import ObservationOut, ObservationsBatchRequest, ObservationsBatchResponse
from app.security import require_device_or_provisioning_token, require_device_token

router = APIRouter(prefix="/observations", tags=["observations"])

IMSI_RE = re.compile(r"^\d{5,20}$")


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ObservationsBatchResponse)
def create_observations(
    body: ObservationsBatchRequest,
    db: Session = Depends(get_db),
    device: Device = Depends(require_device_token),
) -> ObservationsBatchResponse:
    created = 0
    duplicates = 0

    for item in body.observations:
        imsi = item.imsi.replace(" ", "").strip()
        if not IMSI_RE.match(imsi):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="invalid imsi")

        h = imsi_hash(imsi)
        observed_at = item.observed_at or datetime.now(timezone.utc)
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)

        latest = (
            db.query(ImsiObservation)
            .filter(ImsiObservation.device_id == device.id, ImsiObservation.imsi_hash == h)
            .order_by(ImsiObservation.observed_at.desc())
            .first()
        )
        if latest is not None and abs((observed_at - latest.observed_at).total_seconds()) <= settings.DEDUP_WINDOW_SECONDS:
            duplicates += 1
            continue

        encrypted = imsi_encrypt(imsi)
        db.add(
            ImsiObservation(
                device_id=device.id,
                imsi_encrypted=encrypted,
                imsi_hash=h,
                mcc=item.mcc,
                mnc=item.mnc,
                lac=item.lac,
                cell_id=item.cell_id,
                country=item.country,
                brand=item.brand,
                operator=item.operator,
                signal_dbm=item.signal_dbm,
                snr_db=item.snr_db,
                arfcn=item.arfcn,
                frequency=item.frequency,
                tmsi1=item.tmsi1,
                tmsi2=item.tmsi2,
                observed_at=observed_at,
            )
        )

        now = datetime.now(timezone.utc)
        tracked = db.query(TrackedImsi).filter(TrackedImsi.imsi_hash == h).one_or_none()
        if tracked is None:
            db.add(
                TrackedImsi(
                    imsi_hash=h,
                    imsi_encrypted=encrypted,
                    first_seen=now,
                    last_seen=now,
                )
            )
            db.add(
                Alert(
                    imsi_hash=h,
                    device_id=device.id,
                    type="new_device",
                    severity="info" if item.country else "warning",
                    title=f"New IMSI detected: {imsi[:8]}...",
                    message=(
                        f"IMSI from {item.country} ({item.brand}) detected"
                        if item.country
                        else "IMSI of unknown origin detected"
                    ),
                )
            )
        else:
            tracked.last_seen = now
            tracked.is_active = True

        created += 1

    db.commit()
    return ObservationsBatchResponse(created=created, duplicates=duplicates)


@router.get("", response_model=list[ObservationOut])
def list_observations(
    limit: int = 50,
    device_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_device_or_provisioning_token),
) -> list[ObservationOut]:
    query = db.query(ImsiObservation)
    if device_id is not None:
        query = query.filter(ImsiObservation.device_id == device_id)
    rows = query.order_by(ImsiObservation.observed_at.desc()).limit(limit).all()
    return [
        ObservationOut(
            id=row.id,
            device_id=str(row.device_id),
            imsi_masked=mask_imsi(imsi_decrypt(row.imsi_encrypted)),
            mcc=row.mcc,
            mnc=row.mnc,
            lac=row.lac,
            cell_id=row.cell_id,
            country=row.country,
            brand=row.brand,
            operator=row.operator,
            ts=row.observed_at,
        )
        for row in rows
    ]

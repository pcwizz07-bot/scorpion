import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Device, PresenceEvent
from app.schemas import PresenceEventOut, PresenceEventsBatchRequest, PresenceEventsBatchResponse
from app.security import require_device_or_provisioning_token, require_device_token

router = APIRouter(prefix="/presence", tags=["presence"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PresenceEventsBatchResponse)
def create_presence_events(
    body: PresenceEventsBatchRequest,
    db: Session = Depends(get_db),
    device: Device = Depends(require_device_token),
) -> PresenceEventsBatchResponse:
    created = 0
    duplicates = 0

    for item in body.events:
        observed_at = item.observed_at or datetime.now(timezone.utc)
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)

        latest = (
            db.query(PresenceEvent)
            .filter(
                PresenceEvent.device_id == device.id,
                PresenceEvent.kind == item.kind,
                PresenceEvent.tmsi_old == item.tmsi_old,
                PresenceEvent.tmsi_new == item.tmsi_new,
            )
            .order_by(PresenceEvent.observed_at.desc())
            .first()
        )
        if latest is not None and abs((observed_at - latest.observed_at).total_seconds()) <= settings.DEDUP_WINDOW_SECONDS:
            duplicates += 1
            continue

        db.add(
            PresenceEvent(
                device_id=device.id,
                kind=item.kind,
                tmsi_old=item.tmsi_old,
                tmsi_new=item.tmsi_new,
                lac=item.lac,
                cell_id=item.cell_id,
                chan=item.chan,
                signal_dbm=item.signal_dbm,
                observed_at=observed_at,
            )
        )
        created += 1

    db.commit()
    return PresenceEventsBatchResponse(created=created, duplicates=duplicates)


@router.get("", response_model=list[PresenceEventOut])
def list_presence_events(
    limit: int = 50,
    device_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_device_or_provisioning_token),
) -> list[PresenceEventOut]:
    query = db.query(PresenceEvent)
    if device_id is not None:
        query = query.filter(PresenceEvent.device_id == device_id)
    rows = query.order_by(PresenceEvent.observed_at.desc()).limit(limit).all()
    return [
        PresenceEventOut(
            id=row.id,
            device_id=str(row.device_id),
            kind=row.kind,
            tmsi_old=row.tmsi_old,
            tmsi_new=row.tmsi_new,
            lac=row.lac,
            cell_id=row.cell_id,
            chan=row.chan,
            signal_dbm=row.signal_dbm,
            observed_at=row.observed_at,
        )
        for row in rows
    ]

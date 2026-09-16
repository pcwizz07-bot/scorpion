from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Alert, Device, ImsiObservation, TrackedImsi
from app.schemas import StatsOut
from app.security import require_device_or_provisioning_token

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats(
    db: Session = Depends(get_db),
    _: None = Depends(require_device_or_provisioning_token),
) -> StatsOut:
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    return StatsOut(
        devices_total=db.query(func.count(Device.id)).scalar() or 0,
        devices_online=db.query(func.count(Device.id)).filter(Device.status == "online").scalar() or 0,
        observations_total=db.query(func.count(ImsiObservation.id)).scalar() or 0,
        observations_last_24h=(
            db.query(func.count(ImsiObservation.id))
            .filter(ImsiObservation.observed_at >= since_24h)
            .scalar()
            or 0
        ),
        unique_imsis=db.query(func.count(TrackedImsi.id)).scalar() or 0,
        tracked_active=db.query(func.count(TrackedImsi.id)).filter(TrackedImsi.is_active.is_(True)).scalar() or 0,
        alerts_total=db.query(func.count(Alert.id)).scalar() or 0,
        alerts_open=db.query(func.count(Alert.id)).filter(Alert.resolved.is_(False)).scalar() or 0,
    )

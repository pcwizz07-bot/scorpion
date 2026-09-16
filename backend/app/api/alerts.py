from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crypto import imsi_decrypt, mask_imsi
from app.db import get_db
from app.models import Alert, TrackedImsi
from app.schemas import AlertOut
from app.security import require_device_or_provisioning_token

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: None = Depends(require_device_or_provisioning_token),
) -> list[AlertOut]:
    rows = db.query(Alert).order_by(Alert.created_at.desc()).limit(limit).all()

    result = []
    for row in rows:
        imsi_masked = None
        if row.imsi_hash is not None:
            tracked = db.query(TrackedImsi).filter(TrackedImsi.imsi_hash == row.imsi_hash).one_or_none()
            if tracked is not None:
                imsi_masked = mask_imsi(imsi_decrypt(tracked.imsi_encrypted))
        result.append(
            AlertOut(
                id=row.id,
                device_id=str(row.device_id) if row.device_id else None,
                imsi_masked=imsi_masked,
                title=row.title,
                severity=row.severity,
                message=row.message,
                created_at=row.created_at,
            )
        )
    return result

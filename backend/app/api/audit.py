from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuditLog
from app.schemas import AuditLogOut
from app.security import require_provisioning_token

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: None = Depends(require_provisioning_token),
) -> list[AuditLogOut]:
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        AuditLogOut(id=row.id, action=row.action, detail=row.detail, created_at=row.created_at)
        for row in rows
    ]

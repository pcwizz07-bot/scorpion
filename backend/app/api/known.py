"""Known-identity registry: label captures and rule out own devices.

Stores only the value hash (never plaintext IMSI/IMEI). Write is
provisioning-only; reads allow device tokens too so the portal can filter.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crypto import imsi_hash
from app.db import get_db
from app.models import KnownIdentity
from app.schemas import KnownIdentityIn, KnownIdentityOut
from app.security import require_device_or_provisioning_token, require_provisioning_token

router = APIRouter(prefix="/known", tags=["known"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=KnownIdentityOut)
def create_known_identity(
    body: KnownIdentityIn,
    db: Session = Depends(get_db),
    _: None = Depends(require_provisioning_token),
) -> KnownIdentityOut:
    value = body.value.replace(" ", "").strip()
    h = imsi_hash(value)
    row = db.query(KnownIdentity).filter(KnownIdentity.value_hash == h).one_or_none()
    if row is None:
        row = KnownIdentity(value_hash=h, kind=body.kind, label=body.label, is_own=body.is_own)
        db.add(row)
    else:
        row.kind = body.kind
        row.label = body.label
        row.is_own = body.is_own
    db.commit()
    return KnownIdentityOut(id=row.id, kind=row.kind, label=row.label, is_own=row.is_own, created_at=row.created_at)


@router.get("", response_model=list[KnownIdentityOut])
def list_known_identities(
    db: Session = Depends(get_db),
    _: str = Depends(require_device_or_provisioning_token),
) -> list[KnownIdentityOut]:
    rows = db.query(KnownIdentity).order_by(KnownIdentity.created_at.desc()).limit(200).all()
    return [
        KnownIdentityOut(id=row.id, kind=row.kind, label=row.label, is_own=row.is_own, created_at=row.created_at)
        for row in rows
    ]


@router.delete("/{identity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_known_identity(
    identity_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_provisioning_token),
) -> None:
    row = db.query(KnownIdentity).filter(KnownIdentity.id == identity_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    db.delete(row)
    db.commit()
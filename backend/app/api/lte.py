"""LTE ingest: cell sightings (LTE-Cell-Scanner/Tracker) and captured identities (LTESniffer).

Pattern mirrors the GSM observations: identities are Fernet-encrypted at rest
(value_encrypted), hashed for lookup, masked in every read, and the decrypted
value is returned only to provisioning-token (admin) clients.
"""
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.crypto import imsi_decrypt, imsi_encrypt, imsi_hash, mask_imsi
from app.db import get_db
from app.models import Device, LteCell, LteIdentity
from app.schemas import (
    LteCellOut,
    LteCellsBatchRequest,
    LteCellsBatchResponse,
    LteIdentitiesBatchRequest,
    LteIdentitiesBatchResponse,
    LteIdentityOut,
)
from app.security import require_device_or_provisioning_token, require_device_token

router = APIRouter(prefix="/lte", tags=["lte"])

VALUE_RE = re.compile(r"^\d{5,20}$")


@router.post("/cells", status_code=status.HTTP_201_CREATED, response_model=LteCellsBatchResponse)
def create_lte_cells(
    body: LteCellsBatchRequest,
    db: Session = Depends(get_db),
    device: Device = Depends(require_device_token),
) -> LteCellsBatchResponse:
    created = 0
    for item in body.cells:
        observed_at = item.observed_at or datetime.now(timezone.utc)
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        db.add(
            LteCell(
                device_id=device.id,
                pci=item.pci,
                tac=item.tac,
                band=item.band,
                earfcn=item.earfcn,
                freq_mhz=item.freq_mhz,
                plmn=item.plmn,
                signal_dbm=item.signal_dbm,
                observed_at=observed_at,
            )
        )
        created += 1
    db.commit()
    return LteCellsBatchResponse(created=created)


@router.get("/cells", response_model=list[LteCellOut])
def list_lte_cells(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: str = Depends(require_device_or_provisioning_token),
) -> list[LteCellOut]:
    rows = (
        db.query(LteCell, Device.name)
        .join(Device, LteCell.device_id == Device.id)
        .order_by(LteCell.observed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        LteCellOut(
            id=row.id,
            device_id=str(row.device_id),
            device_name=device_name,
            pci=row.pci,
            tac=row.tac,
            band=row.band,
            earfcn=row.earfcn,
            freq_mhz=row.freq_mhz,
            plmn=row.plmn,
            signal_dbm=row.signal_dbm,
            observed_at=row.observed_at,
        )
        for row, device_name in rows
    ]


@router.post("/identities", status_code=status.HTTP_201_CREATED, response_model=LteIdentitiesBatchResponse)
def create_lte_identities(
    body: LteIdentitiesBatchRequest,
    db: Session = Depends(get_db),
    device: Device = Depends(require_device_token),
) -> LteIdentitiesBatchResponse:
    created = 0
    duplicates = 0
    for item in body.identities:
        value = item.value.replace(" ", "").strip()
        if not VALUE_RE.match(value):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="invalid value")

        h = imsi_hash(value)
        observed_at = item.observed_at or datetime.now(timezone.utc)
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)

        latest = (
            db.query(LteIdentity)
            .filter(
                LteIdentity.device_id == device.id,
                LteIdentity.kind == item.kind,
                LteIdentity.value_hash == h,
            )
            .order_by(LteIdentity.observed_at.desc())
            .first()
        )
        if latest is not None and abs((observed_at - latest.observed_at).total_seconds()) <= settings.DEDUP_WINDOW_SECONDS:
            duplicates += 1
            continue

        db.add(
            LteIdentity(
                device_id=device.id,
                kind=item.kind,
                value_encrypted=imsi_encrypt(value),
                value_hash=h,
                s_tmsi=item.s_tmsi,
                pci=item.pci,
                tac=item.tac,
                earfcn=item.earfcn,
                band=item.band,
                plmn=item.plmn,
                observed_at=observed_at,
            )
        )
        created += 1
    db.commit()
    return LteIdentitiesBatchResponse(created=created, duplicates=duplicates)


@router.get("/identities", response_model=list[LteIdentityOut])
def list_lte_identities(
    limit: int = 50,
    db: Session = Depends(get_db),
    privilege: str = Depends(require_device_or_provisioning_token),
) -> list[LteIdentityOut]:
    privileged = privilege == "provisioning"
    rows = (
        db.query(LteIdentity, Device.name)
        .join(Device, LteIdentity.device_id == Device.id)
        .order_by(LteIdentity.observed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        LteIdentityOut(
            id=row.id,
            device_id=str(row.device_id),
            device_name=device_name,
            kind=row.kind,
            value_masked=mask_imsi(plain),
            value=plain if privileged else None,
            s_tmsi=row.s_tmsi,
            pci=row.pci,
            tac=row.tac,
            earfcn=row.earfcn,
            band=row.band,
            plmn=row.plmn,
            observed_at=row.observed_at,
        )
        for row, device_name, plain in (
            (row, device_name, imsi_decrypt(row.value_encrypted)) for row, device_name in rows
        )
    ]
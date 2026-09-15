import uuid
from datetime import datetime, timedelta, timezone

from app.cli import retention
from app.crypto import imsi_encrypt, imsi_hash
from app.models import AuditLog, ImsiObservation

FAKE_IMSI = "123456789012345"


def _make_observation(device_id: uuid.UUID, days_old: int) -> ImsiObservation:
    return ImsiObservation(
        device_id=device_id,
        imsi_encrypted=imsi_encrypt(FAKE_IMSI),
        imsi_hash=imsi_hash(FAKE_IMSI),
        observed_at=datetime.now(timezone.utc) - timedelta(days=days_old),
    )


def test_retention_dry_run_reports_count_without_deleting(registered_device, db_session, capsys):
    device_id = uuid.UUID(registered_device["device_id"])
    db_session.add(_make_observation(device_id, days_old=40))
    db_session.add(_make_observation(device_id, days_old=1))
    db_session.commit()

    retention(keep_days=30, purge=False)

    captured = capsys.readouterr()
    assert "1" in captured.out
    assert db_session.query(ImsiObservation).count() == 2


def test_retention_purge_deletes_only_old_rows_and_writes_audit(registered_device, db_session):
    device_id = uuid.UUID(registered_device["device_id"])
    db_session.add(_make_observation(device_id, days_old=40))
    db_session.add(_make_observation(device_id, days_old=1))
    db_session.commit()

    retention(keep_days=30, purge=True)

    db_session.expire_all()
    remaining = db_session.query(ImsiObservation).all()
    assert len(remaining) == 1

    audit = db_session.query(AuditLog).filter(AuditLog.actor == "retention").one()
    assert audit.action == "purge_observations"

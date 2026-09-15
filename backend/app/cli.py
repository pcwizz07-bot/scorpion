import argparse
from datetime import datetime, timedelta, timezone

from app.audit import write_audit
from app.db import SessionLocal
from app.models import ImsiObservation


def retention(keep_days: int, purge: bool) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    db = SessionLocal()
    try:
        query = db.query(ImsiObservation).filter(ImsiObservation.observed_at < cutoff)
        count = query.count()
        if not purge:
            print(f"[dry-run] {count} observation(s) older than {keep_days} day(s) would be purged")
            return
        query.delete(synchronize_session=False)
        db.commit()
        write_audit(
            db,
            actor="retention",
            action="purge_observations",
            resource_type="imsi_observations",
            detail={"keep_days": keep_days, "deleted": count},
        )
        print(f"purged {count} observation(s) older than {keep_days} day(s)")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    retention_parser = subparsers.add_parser("retention")
    retention_parser.add_argument("--keep-days", type=int, required=True)
    retention_parser.add_argument("--purge", action="store_true")

    args = parser.parse_args()
    if args.command == "retention":
        retention(args.keep_days, args.purge)


if __name__ == "__main__":
    main()

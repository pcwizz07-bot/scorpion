import argparse
import secrets
from datetime import datetime, timedelta, timezone

from app.audit import write_audit
from app.auth_security import generate_totp_secret, hash_password, totp_uri
from app.db import SessionLocal
from app.models import ImsiObservation, User


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


def create_admin(username: str) -> None:
    """Create/replace an admin user. Prints the one-time password + TOTP provisioning."""
    password = secrets.token_urlsafe(12)
    totp_secret = generate_totp_secret()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).one_or_none()
        if user is None:
            user = User(username=username, password_hash=hash_password(password), totp_secret=totp_secret)
            db.add(user)
        else:
            user.password_hash = hash_password(password)
            user.totp_secret = totp_secret
        db.commit()
    finally:
        db.close()
    print(f"username:  {username}")
    print(f"password:  {password}   (one-time, change it later)")
    print(f"TOTP add:  {totp_uri(totp_secret, username)}")
    print(f"TOTP code: {totp_secret}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    retention_parser = subparsers.add_parser("retention")
    retention_parser.add_argument("--keep-days", type=int, required=True)
    retention_parser.add_argument("--purge", action="store_true")

    admin_parser = subparsers.add_parser("create-admin")
    admin_parser.add_argument("username")

    args = parser.parse_args()
    if args.command == "retention":
        retention(args.keep_days, args.purge)
    elif args.command == "create-admin":
        create_admin(args.username)


if __name__ == "__main__":
    main()

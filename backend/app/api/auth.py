"""Login / logout / session status. Sessions grant provisioning privilege."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.auth_security import (
    SESSION_TTL_SECONDS,
    hash_session_token,
    hash_password,
    issue_session_token,
    verify_password,
    verify_totp,
)
from app.db import get_db
from app.models import AuthSession, User
from app.schemas import AuthStatusResponse, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    db: DbSession = Depends(get_db),
) -> LoginResponse:
    user = db.query(User).filter(User.username == body.username).one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    if not verify_totp(user.totp_secret, body.totp_code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid 2FA code")

    token, token_hash = issue_session_token()
    now = datetime.now(timezone.utc)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(seconds=SESSION_TTL_SECONDS),
        )
    )
    user.last_login_at = now
    db.commit()
    return LoginResponse(token=token, expires_at=now + timedelta(seconds=SESSION_TTL_SECONDS), username=user.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    db: DbSession = Depends(get_db),
    x_provisioning_token: str | None = Header(default=None),
) -> None:
    if x_provisioning_token:
        db.query(AuthSession).filter(
            AuthSession.token_hash == hash_session_token(x_provisioning_token)
        ).delete()
        db.commit()


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(
    db: DbSession = Depends(get_db),
    x_provisioning_token: str | None = Header(default=None),
) -> AuthStatusResponse:
    session = _lookup_session(db, x_provisioning_token)
    if session is None:
        return AuthStatusResponse(authenticated=False)
    return AuthStatusResponse(authenticated=True, username=session[1])


def _lookup_session(db: DbSession, token: str | None) -> tuple[AuthSession, str] | None:
    if not token:
        return None
    session = (
        db.query(AuthSession, User.username)
        .join(User, AuthSession.user_id == User.id)
        .filter(AuthSession.token_hash == hash_session_token(token))
        .one_or_none()
    )
    if session is None:
        return None
    row, username = session
    if row.expires_at < datetime.now(timezone.utc):
        return None
    row.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return row, username
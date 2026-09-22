import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    lat: Mapped[float] = mapped_column(Double, nullable=False)
    lng: Mapped[float] = mapped_column(Double, nullable=False)
    altitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="online")
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    firmware_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImsiObservation(Base):
    __tablename__ = "imsi_observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    imsi_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    imsi_hash: Mapped[str] = mapped_column(Text, nullable=False)
    mcc: Mapped[str | None] = mapped_column(Text, nullable=True)
    mnc: Mapped[str | None] = mapped_column(Text, nullable=True)
    lac: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cell_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator: Mapped[str | None] = mapped_column(Text, nullable=True)
    signal_dbm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snr_db: Mapped[int | None] = mapped_column(Integer, nullable=True)
    arfcn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frequency: Mapped[float | None] = mapped_column(Double, nullable=True)
    tmsi1: Mapped[str | None] = mapped_column(Text, nullable=True)
    tmsi2: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_imsi_observations_imsi_hash", "imsi_hash"),
        Index("ix_imsi_observations_device_id_observed_at", "device_id", "observed_at"),
        Index("ix_imsi_observations_observed_at", "observed_at"),
    )


class TrackedImsi(Base):
    __tablename__ = "tracked_imsis"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    imsi_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    imsi_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(Text, nullable=True, server_default="low")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class PresenceEvent(Base):
    __tablename__ = "presence_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    tmsi_old: Mapped[str | None] = mapped_column(Text, nullable=True)
    tmsi_new: Mapped[str | None] = mapped_column(Text, nullable=True)
    lac: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cell_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chan: Mapped[str | None] = mapped_column(Text, nullable=True)
    signal_dbm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_presence_events_device_id_observed_at", "device_id", "observed_at"),
        Index("ix_presence_events_tmsi_old", "tmsi_old"),
        Index("ix_presence_events_tmsi_new", "tmsi_new"),
    )


class LteCell(Base):
    __tablename__ = "lte_cells"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    pci: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tac: Mapped[int | None] = mapped_column(Integer, nullable=True)
    band: Mapped[int | None] = mapped_column(Integer, nullable=True)
    earfcn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    freq_mhz: Mapped[float | None] = mapped_column(Double, nullable=True)
    plmn: Mapped[str | None] = mapped_column(Text, nullable=True)  # "MCC-MNC"
    signal_dbm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_lte_cells_device_id_observed_at", "device_id", "observed_at"),
        Index("ix_lte_cells_observed_at", "observed_at"),
        Index("ix_lte_cells_pci", "pci"),
    )


class LteIdentity(Base):
    __tablename__ = "lte_identities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # imsi | imei | imeisv
    value_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    value_hash: Mapped[str] = mapped_column(Text, nullable=False)
    s_tmsi: Mapped[str | None] = mapped_column(Text, nullable=True)
    pci: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tac: Mapped[int | None] = mapped_column(Integer, nullable=True)
    earfcn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    band: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plmn: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_lte_identities_value_hash", "value_hash"),
        Index("ix_lte_identities_device_id_observed_at", "device_id", "observed_at"),
        Index("ix_lte_identities_observed_at", "observed_at"),
    )


class KnownIdentity(Base):
    """Label registry to sort captures and rule out own devices.

    Only the value hash is stored (never the plaintext IMSI/IMEI). Marking an
    IMSI as 'own' lets the portal hide it and focus on unknown devices.
    """

    __tablename__ = "known_identities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    value_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # imsi | imei | imeisv
    label: Mapped[str] = mapped_column(Text, nullable=False)
    is_own: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    totp_secret: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    imsi_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False, server_default="info")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_resolved", "resolved"),
        Index("ix_alerts_created_at", "created_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

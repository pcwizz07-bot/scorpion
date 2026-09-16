from datetime import datetime

from pydantic import BaseModel, Field


class DeviceRegisterRequest(BaseModel):
    name: str
    lat: float
    lng: float
    altitude: float | None = None
    firmware_version: str | None = None


class DeviceRegisterResponse(BaseModel):
    device_id: str
    device_token: str


class DeviceOut(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    status: str
    last_seen: datetime


class ObservationIn(BaseModel):
    imsi: str
    mcc: str | None = None
    mnc: str | None = None
    lac: int | None = None
    cell_id: int | None = None
    country: str | None = None
    brand: str | None = None
    operator: str | None = None
    signal_dbm: int | None = None
    snr_db: int | None = None
    arfcn: int | None = None
    frequency: float | None = None
    tmsi1: str | None = None
    tmsi2: str | None = None
    observed_at: datetime | None = None


class ObservationsBatchRequest(BaseModel):
    observations: list[ObservationIn] = Field(max_length=200)


class ObservationsBatchResponse(BaseModel):
    created: int
    duplicates: int


class ObservationOut(BaseModel):
    id: int
    device_id: str
    device_name: str | None
    imsi_masked: str
    mcc: str | None
    mnc: str | None
    lac: int | None
    cell_id: int | None
    country: str | None
    brand: str | None
    operator: str | None
    signal_dbm: int | None
    observed_at: datetime


class AlertOut(BaseModel):
    id: int
    device_id: str | None
    imsi_masked: str | None
    type: str
    severity: str
    title: str
    message: str | None
    resolved: bool
    created_at: datetime


class StatsOut(BaseModel):
    devices_total: int
    devices_online: int
    observations_total: int
    observations_last_24h: int
    unique_imsis: int
    tracked_active: int
    alerts_total: int
    alerts_open: int


class AuditLogOut(BaseModel):
    id: int
    action: str
    detail: dict | None
    created_at: datetime

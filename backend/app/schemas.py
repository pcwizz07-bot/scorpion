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

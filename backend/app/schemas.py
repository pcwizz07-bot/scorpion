from datetime import datetime
from typing import Literal

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
    # Full decrypted IMSI. Only populated for provisioning-token (admin) reads;
    # device-token reads get None so capture nodes never see raw subscriber IDs.
    imsi: str | None = None
    mcc: str | None
    mnc: str | None
    lac: int | None
    cell_id: int | None
    country: str | None
    brand: str | None
    operator: str | None
    signal_dbm: int | None
    tmsi1: str | None = None
    tmsi2: str | None = None
    observed_at: datetime


class LteCellIn(BaseModel):
    # pci is null for energy-only (rtl_power) detections, where only the
    # carrier frequency/power is known without coherent PCI decoding.
    pci: int | None = None
    tac: int | None = None
    band: int | None = None
    earfcn: int | None = None
    freq_mhz: float | None = None
    plmn: str | None = None
    signal_dbm: int | None = None
    observed_at: datetime | None = None


class LteCellsBatchRequest(BaseModel):
    cells: list[LteCellIn] = Field(max_length=200)


class LteCellsBatchResponse(BaseModel):
    created: int


class LteCellOut(BaseModel):
    id: int
    device_id: str
    device_name: str | None
    pci: int | None
    tac: int | None
    band: int | None
    earfcn: int | None
    freq_mhz: float | None
    plmn: str | None
    signal_dbm: int | None
    observed_at: datetime


class LteIdentityIn(BaseModel):
    kind: Literal["imsi", "imei", "imeisv"]
    value: str
    s_tmsi: str | None = None
    pci: int | None = None
    tac: int | None = None
    earfcn: int | None = None
    band: int | None = None
    plmn: str | None = None
    observed_at: datetime | None = None


class LteIdentitiesBatchRequest(BaseModel):
    identities: list[LteIdentityIn] = Field(max_length=200)


class LteIdentitiesBatchResponse(BaseModel):
    created: int
    duplicates: int


class LteIdentityOut(BaseModel):
    id: int
    device_id: str
    device_name: str | None
    kind: str
    value_masked: str
    # Full decrypted value. Only populated for provisioning-token (admin) reads;
    # device-token reads get None like observations.
    value: str | None = None
    s_tmsi: str | None
    pci: int | None
    tac: int | None
    earfcn: int | None
    band: int | None
    plmn: str | None
    observed_at: datetime


class PresenceEventIn(BaseModel):
    kind: Literal["plu", "attach", "page", "reauth"]
    tmsi_old: str | None = None
    tmsi_new: str | None = None
    lac: int | None = None
    cell_id: int | None = None
    chan: str | None = None
    signal_dbm: int | None = None
    observed_at: datetime | None = None


class PresenceEventsBatchRequest(BaseModel):
    events: list[PresenceEventIn] = Field(max_length=200)


class PresenceEventsBatchResponse(BaseModel):
    created: int
    duplicates: int


class PresenceEventOut(BaseModel):
    id: int
    device_id: str
    kind: str
    tmsi_old: str | None
    tmsi_new: str | None
    lac: int | None
    cell_id: int | None
    chan: str | None
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

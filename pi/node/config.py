"""Load /etc/scorpion/agent.conf JSON + env overrides, with defaults."""
import json
import os
from dataclasses import dataclass, field

DEFAULT_CONFIG_PATH = "/etc/scorpion/agent.conf"
DEFAULT_SCAN_FREQUENCIES_MHZ = [947.0, 935.2, 940.0]


@dataclass
class Config:
    device_name: str = "Pi-Unknown"
    lat: float = 0.0
    lng: float = 0.0
    server_url: str = "http://localhost:8000"
    scan_frequencies_mhz: list = field(default_factory=lambda: list(DEFAULT_SCAN_FREQUENCIES_MHZ))
    heartbeat_interval_s: int = 60
    scan_interval_s: int = 600
    spool_dir: str = "/var/lib/scorpion"
    state_file: str = "/var/lib/scorpion/state.json"
    capture_txt: str = "/tmp/imsi-output.txt"
    gnss_enabled: bool = False
    gnss_serial: str = "/dev/ttyUSB2"
    gnss_baud: int = 115200
    provisioning_token: str | None = None


def load_config(config_path: str = DEFAULT_CONFIG_PATH, env: dict | None = None) -> Config:
    env = os.environ if env is None else env
    cfg = Config()

    if os.path.isfile(config_path):
        with open(config_path) as f:
            data = json.load(f)
        for key in cfg.__dataclass_fields__:
            if key in data:
                setattr(cfg, key, data[key])

    if "SCORPION_STATE_DIR" in env:
        cfg.spool_dir = env["SCORPION_STATE_DIR"]
        cfg.state_file = os.path.join(cfg.spool_dir, "state.json")

    if "SCORPION_DEVICE_NAME" in env:
        cfg.device_name = env["SCORPION_DEVICE_NAME"]
    if "SCORPION_LAT" in env:
        cfg.lat = float(env["SCORPION_LAT"])
    if "SCORPION_LNG" in env:
        cfg.lng = float(env["SCORPION_LNG"])
    if "SCORPION_SERVER_URL" in env:
        cfg.server_url = env["SCORPION_SERVER_URL"]
    if "SCORPION_PROVISIONING_TOKEN" in env:
        cfg.provisioning_token = env["SCORPION_PROVISIONING_TOKEN"]

    return cfg

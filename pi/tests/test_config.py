import json
import os

from pi.node.config import DEFAULT_SCAN_FREQUENCIES_MHZ, load_config


def test_defaults_when_no_file_and_no_env(tmp_path):
    missing = tmp_path / "agent.conf"
    cfg = load_config(config_path=str(missing), env={})

    assert cfg.device_name == "Pi-Unknown"
    assert cfg.lat == 0.0
    assert cfg.lng == 0.0
    assert cfg.server_url == "http://localhost:8000"
    assert cfg.scan_frequencies_mhz == DEFAULT_SCAN_FREQUENCIES_MHZ
    assert cfg.heartbeat_interval_s == 60
    assert cfg.scan_interval_s == 600
    assert cfg.spool_dir == "/var/lib/scorpion"
    assert cfg.state_file == "/var/lib/scorpion/state.json"
    assert cfg.capture_txt == "/tmp/imsi-output.txt"
    assert cfg.gnss_enabled is False
    assert cfg.gnss_serial == "/dev/ttyUSB2"
    assert cfg.gnss_baud == 115200
    assert cfg.presence_enabled is True
    assert cfg.presence_txt == "/tmp/presence-output.txt"
    assert cfg.presence_iface == "lo"
    assert cfg.provisioning_token is None


def test_loads_values_from_file(tmp_path):
    conf = tmp_path / "agent.conf"
    conf.write_text(
        json.dumps(
            {
                "device_name": "Pi-1-North",
                "lat": -25.7461,
                "lng": 28.1881,
                "server_url": "http://10.14.13.250:8000",
                "scan_frequencies_mhz": [947.0, 935.2],
                "heartbeat_interval_s": 30,
                "scan_interval_s": 300,
                "spool_dir": "/var/lib/scorpion2",
                "state_file": "/var/lib/scorpion2/state.json",
                "capture_txt": "/tmp/other.txt",
                "gnss_enabled": True,
                "gnss_serial": "/dev/ttyUSB0",
                "gnss_baud": 9600,
            }
        )
    )

    cfg = load_config(config_path=str(conf), env={})

    assert cfg.device_name == "Pi-1-North"
    assert cfg.lat == -25.7461
    assert cfg.lng == 28.1881
    assert cfg.server_url == "http://10.14.13.250:8000"
    assert cfg.scan_frequencies_mhz == [947.0, 935.2]
    assert cfg.heartbeat_interval_s == 30
    assert cfg.scan_interval_s == 300
    assert cfg.spool_dir == "/var/lib/scorpion2"
    assert cfg.state_file == "/var/lib/scorpion2/state.json"
    assert cfg.capture_txt == "/tmp/other.txt"
    assert cfg.gnss_enabled is True
    assert cfg.gnss_serial == "/dev/ttyUSB0"
    assert cfg.gnss_baud == 9600


def test_env_overrides_file(tmp_path):
    conf = tmp_path / "agent.conf"
    conf.write_text(json.dumps({"device_name": "Pi-File", "lat": 1.0, "lng": 2.0,
                                 "server_url": "http://file:8000"}))
    env = {
        "SCORPION_DEVICE_NAME": "Pi-Env",
        "SCORPION_LAT": "-1.5",
        "SCORPION_LNG": "3.5",
        "SCORPION_SERVER_URL": "http://env:8000",
    }

    cfg = load_config(config_path=str(conf), env=env)

    assert cfg.device_name == "Pi-Env"
    assert cfg.lat == -1.5
    assert cfg.lng == 3.5
    assert cfg.server_url == "http://env:8000"


def test_provisioning_token_only_from_env_never_from_file(tmp_path):
    conf = tmp_path / "agent.conf"
    conf.write_text(json.dumps({"device_name": "Pi-1"}))
    env = {"SCORPION_PROVISIONING_TOKEN": "secret-token"}

    cfg = load_config(config_path=str(conf), env=env)

    assert cfg.provisioning_token == "secret-token"
    assert "provisioning_token" not in json.loads(conf.read_text())


def test_state_dir_env_override_moves_spool_and_state_file(tmp_path):
    conf = tmp_path / "agent.conf"
    conf.write_text(json.dumps({}))
    env = {"SCORPION_STATE_DIR": "/custom/state"}

    cfg = load_config(config_path=str(conf), env=env)

    assert cfg.spool_dir == "/custom/state"
    assert cfg.state_file == "/custom/state/state.json"

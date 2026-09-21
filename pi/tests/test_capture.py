import os
import subprocess

import pytest

from pi.node import capture
from pi.node.capture import TailReader, capture_new_observations, parse_line
from pi.node.spool import Spool

# Real simple_IMSI-catcher --txt header (scanner writes stamp, tmsi1, tmsi2, imsi, ...).
HEADER = "stamp, tmsi1, tmsi2, imsi, imsicountry, imsibrand, imsioperator, mcc, mnc, lac, cell\n"


def test_parse_line_returns_observation_for_valid_csv_line():
    line = "2026-01-01T00:00:00,0x1234abcd,0x5678ef01,111222333444555,ZA,Vodacom,Vodacom,655,01,1,1"

    obs = parse_line(line)

    assert obs["imsi"] == "111222333444555"
    assert obs["country"] == "ZA"
    assert obs["brand"] == "Vodacom"
    assert obs["operator"] == "Vodacom"
    assert obs["mcc"] == "655"
    assert obs["mnc"] == "01"


def test_parse_line_captures_tmsi_chain():
    line = "2026-01-01T00:00:00,0x1234abcd,0x5678ef01,111222333444555,ZA,Vodacom,Vodacom,655,01,1,1"

    obs = parse_line(line)
    assert obs is not None

    assert obs["tmsi1"] == "0x1234abcd"
    assert obs["tmsi2"] == "0x5678ef01"


def test_parse_line_tmsi_empty_becomes_none():
    line = "2026-01-01T00:00:00,,,111222333444555,ZA,Vodacom,Vodacom,655,01,1,1"

    obs = parse_line(line)
    assert obs is not None

    assert obs["tmsi1"] is None
    assert obs["tmsi2"] is None


def test_parse_line_strips_spaces_in_imsi():
    line = "2026-01-01T00:00:00,0x1234abcd,0x5678ef01, 111 222 333 444 555 ,ZA,Vodacom,Vodacom,655,01,1,1"

    obs = parse_line(line)

    assert obs["imsi"] == "111222333444555"


def test_parse_line_skips_header_line():
    assert parse_line("stamp, tmsi1, tmsi2, imsi, imsicountry, imsibrand, imsioperator, mcc, mnc, lac, cell") is None


def test_parse_line_skips_blank_line():
    assert parse_line("") is None
    assert parse_line("   ") is None


def test_parse_line_rejects_imsi_too_short():
    line = "2026-01-01T00:00:00,0x1234abcd,0x5678ef01,1234,ZA,Vodacom,Vodacom,655,01,1,1"

    assert parse_line(line) is None


def test_parse_line_rejects_non_digit_imsi():
    line = "2026-01-01T00:00:00,0x1234abcd,0x5678ef01,11122abc3444555,ZA,Vodacom,Vodacom,655,01,1,1"

    assert parse_line(line) is None


def test_parse_line_rejects_too_few_fields():
    assert parse_line("only,three,fields") is None


def test_tail_reader_returns_only_new_lines(tmp_path):
    path = tmp_path / "imsi.txt"
    path.write_text(HEADER)
    reader = TailReader(str(path))
    reader.read_new_lines()  # consume header

    with open(path, "a") as f:
        f.write("2026-01-01T00:00:00,123,1,111222333444555,ZA,Vodacom,Vodacom,655,01,1,1\n")

    lines = reader.read_new_lines()

    assert len(lines) == 1
    assert lines[0].endswith("1,1")


def test_tail_reader_does_not_consume_partial_last_line(tmp_path):
    path = tmp_path / "imsi.txt"
    path.write_text(HEADER)
    reader = TailReader(str(path))
    reader.read_new_lines()

    with open(path, "a") as f:
        f.write("2026-01-01T00:00:00,123,1,111222333444555")  # no trailing newline yet

    lines = reader.read_new_lines()
    assert lines == []

    with open(path, "a") as f:
        f.write(",ZA,Vodacom,Vodacom,655,01,1,1\n")

    lines = reader.read_new_lines()
    assert len(lines) == 1


def test_tail_reader_resets_offset_on_truncation(tmp_path):
    path = tmp_path / "imsi.txt"
    path.write_text(
        HEADER
        + "2026-01-01T00:00:00,123,1,111222333444555,ZA,Vodacom,Vodacom,655,01,1,1\n"
        + "2026-01-01T00:00:01,123,1,222333444555666,ZA,Vodacom,Vodacom,655,01,1,1\n"
    )
    reader = TailReader(str(path))
    reader.read_new_lines()  # offset now points past both rows

    # File truncated back to just a new (shorter) header + one row.
    path.write_text(HEADER + "2026-01-01T00:00:00,123,1,999888777666555,ZA,MTN,MTN,655,02,1,1\n")

    lines = reader.read_new_lines()

    # Offset reset to 0 on truncation, so the whole (shorter) new file is read again.
    assert any("999888777666555" in line for line in lines)


def test_capture_new_observations_pushes_parsed_lines_to_spool(tmp_path):
    path = tmp_path / "imsi.txt"
    path.write_text(HEADER + "2026-01-01T00:00:00,123,1,111222333444555,ZA,Vodacom,Vodacom,655,01,1,1\n")
    reader = TailReader(str(path))
    spool = Spool(str(tmp_path / "spool.db"))

    count = capture_new_observations(reader, spool, device_name="Pi-1")

    assert count == 1
    pending = spool.pending()
    assert pending[0]["observation"]["imsi"] == "111222333444555"
    assert pending[0]["observation"]["device_name"] == "Pi-1"
    assert "observed_at" in pending[0]["observation"]


def test_capture_new_observations_includes_gnss_fix_when_available(tmp_path):
    path = tmp_path / "imsi.txt"
    path.write_text(HEADER + "2026-01-01T00:00:00,123,1,111222333444555,ZA,Vodacom,Vodacom,655,01,1,1\n")
    reader = TailReader(str(path))
    spool = Spool(str(tmp_path / "spool.db"))

    count = capture_new_observations(
        reader, spool, device_name="Pi-1", get_fix=lambda: {"lat": -25.1, "lng": 28.2}
    )

    assert count == 1
    obs = spool.pending()[0]["observation"]
    assert obs["lat"] == -25.1
    assert obs["lng"] == 28.2


def test_capture_new_observations_skips_invalid_lines(tmp_path):
    path = tmp_path / "imsi.txt"
    path.write_text(HEADER + "garbage line\n")
    reader = TailReader(str(path))
    spool = Spool(str(tmp_path / "spool.db"))

    count = capture_new_observations(reader, spool, device_name="Pi-1")

    assert count == 0
    assert spool.pending() == []


def test_start_imsi_catcher_launches_with_script_dir_as_cwd(monkeypatch, tmp_path):
    captured = {}

    def fake_open(path, mode):
        return open(tmp_path / "catcher.log", mode)

    def fake_popen(args, **kwargs):
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(capture, "open", fake_open, raising=False)
    monkeypatch.setattr(capture.subprocess, "Popen", fake_popen)

    capture.start_imsi_catcher("/tmp/imsi.txt")

    assert captured["kwargs"]["cwd"] == os.path.dirname(capture.IMSI_CATCHER_PATH)


def test_start_imsi_catcher_redirects_output_to_log_file(monkeypatch, tmp_path):
    captured = {}
    log_file = tmp_path / "catcher.log"

    def fake_open(path, mode):
        captured["open_path"] = path
        captured["open_mode"] = mode
        return open(log_file, mode)

    def fake_popen(args, **kwargs):
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(capture, "open", fake_open, raising=False)
    monkeypatch.setattr(capture.subprocess, "Popen", fake_popen)

    capture.start_imsi_catcher("/tmp/imsi.txt")

    assert captured["open_path"] == capture.CATCHER_LOG_PATH
    assert captured["open_mode"] == "ab"
    assert captured["kwargs"]["stdout"] is not None
    assert captured["kwargs"]["stdout"] != subprocess.DEVNULL
    assert captured["kwargs"]["stderr"] == subprocess.STDOUT


def test_start_grgsm_livemon_redirects_output_to_log_file(monkeypatch, tmp_path):
    captured = {}
    log_file = tmp_path / "livemon.log"

    def fake_open(path, mode):
        captured["open_path"] = path
        captured["open_mode"] = mode
        return open(log_file, mode)

    def fake_popen(args, **kwargs):
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(capture, "open", fake_open, raising=False)
    monkeypatch.setattr(capture.subprocess, "Popen", fake_popen)

    capture.start_grgsm_livemon(942.4)

    assert captured["open_path"] == capture.LIVEMON_LOG_PATH
    assert captured["open_mode"] == "ab"
    assert captured["kwargs"]["stdout"] is not None
    assert captured["kwargs"]["stdout"] != subprocess.DEVNULL
    assert captured["kwargs"]["stderr"] == subprocess.STDOUT


def test_scan_rtl_power_returns_strongest_bin_in_mhz():
    # rtl_power csv row: date, time, hz_low, hz_high, hz_step, num_samples, db...
    row = "2026-01-01, 00:00:00, 935000000, 935300000, 100000, 3, -30.0, -10.0, -25.0"

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout=row + "\n", stderr="")

    freq = capture.scan_rtl_power(run=fake_run)

    # Strongest sample is index 1 (-10.0 dB) -> 935000000 + 1*100000 = 935100000 Hz
    assert freq == pytest.approx(935.1)


def test_scan_rtl_power_returns_none_when_command_errors():
    def fake_run(args, **kwargs):
        raise OSError("rtl_power not found")

    assert capture.scan_rtl_power(run=fake_run) is None


def test_scan_rtl_power_returns_none_on_empty_output():
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    assert capture.scan_rtl_power(run=fake_run) is None


def test_find_best_frequency_falls_back_to_rtl_power_when_scanner_decodes_no_cells():
    def fake_run(args, **kwargs):
        if args[0] == "timeout":
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[0] == "rtl_power":
            row = "2026-01-01, 00:00:00, 935000000, 935300000, 100000, 2, -40.0, -5.0"
            return subprocess.CompletedProcess(args, 0, stdout=row + "\n", stderr="")
        raise AssertionError(f"unexpected command: {args}")

    freq = capture.find_best_frequency([943.0], run=fake_run)

    assert freq == pytest.approx(935.1)


def test_find_best_frequency_uses_default_when_scanner_and_fallback_both_empty():
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    freq = capture.find_best_frequency([943.0], run=fake_run)

    assert freq == 943.0


def test_find_best_frequency_skips_rtl_power_fallback_when_scanner_finds_cells():
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args[0])
        if args[0] == "timeout":
            return subprocess.CompletedProcess(
                args, 0, stdout="ARFCN: 42, Freq: 942.4M, Pwr: -30\n", stderr=""
            )
        raise AssertionError("rtl_power fallback should not run when cells were decoded")

    freq = capture.find_best_frequency([943.0], run=fake_run)

    assert freq == 942.4
    assert calls == ["timeout"]

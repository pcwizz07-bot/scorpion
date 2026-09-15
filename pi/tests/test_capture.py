from pi.node.capture import TailReader, capture_new_observations, parse_line
from pi.node.spool import Spool

HEADER = "stamp,arfcn,mcc_id,imsi,country,brand,operator,mcc,mnc,lac,cellid\n"


def test_parse_line_returns_observation_for_valid_csv_line():
    line = "2026-01-01T00:00:00,123,1,111222333444555,ZA,Vodacom,Vodacom,655,01,1,1"

    obs = parse_line(line)

    assert obs["imsi"] == "111222333444555"
    assert obs["country"] == "ZA"
    assert obs["brand"] == "Vodacom"
    assert obs["operator"] == "Vodacom"
    assert obs["mcc"] == "655"
    assert obs["mnc"] == "01"


def test_parse_line_strips_spaces_in_imsi():
    line = "2026-01-01T00:00:00,123,1, 111 222 333 444 555 ,ZA,Vodacom,Vodacom,655,01,1,1"

    obs = parse_line(line)

    assert obs["imsi"] == "111222333444555"


def test_parse_line_skips_header_line():
    assert parse_line("stamp,arfcn,mcc_id,imsi,country,brand,operator,mcc,mnc,lac,cellid") is None


def test_parse_line_skips_blank_line():
    assert parse_line("") is None
    assert parse_line("   ") is None


def test_parse_line_rejects_imsi_too_short():
    line = "2026-01-01T00:00:00,123,1,1234,ZA,Vodacom,Vodacom,655,01,1,1"

    assert parse_line(line) is None


def test_parse_line_rejects_non_digit_imsi():
    line = "2026-01-01T00:00:00,123,1,11122abc3444555,ZA,Vodacom,Vodacom,655,01,1,1"

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

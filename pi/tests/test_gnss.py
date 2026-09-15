import pytest

from pi.node.gnss import parse_gpgga


def test_parse_gpgga_returns_lat_lng_for_valid_fix():
    line = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"

    fix = parse_gpgga(line)

    assert fix["lat"] == pytest.approx(48 + 7.038 / 60)
    assert fix["lng"] == pytest.approx(11 + 31.000 / 60)


def test_parse_gpgga_applies_south_and_west_signs():
    line = "$GPGGA,123519,2544.766,S,02811.286,E,1,08,0.9,545.4,M,46.9,M,,*47"

    fix = parse_gpgga(line)

    assert fix["lat"] == pytest.approx(-(25 + 44.766 / 60))
    assert fix["lng"] == pytest.approx(28 + 11.286 / 60)


def test_parse_gpgga_returns_none_when_no_fix():
    line = "$GPGGA,123519,4807.038,N,01131.000,E,0,00,,,,,,,*66"

    assert parse_gpgga(line) is None


def test_parse_gpgga_returns_none_for_non_gpgga_line():
    assert parse_gpgga("$GPRMC,123519,A,4807.038,N*10") is None


def test_parse_gpgga_returns_none_for_malformed_line():
    assert parse_gpgga("garbage") is None

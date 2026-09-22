"""LTE scan parsers, tested against real captured CellSearch/rtl_power output."""

from pi.node.lte_scan import band_and_earfcn, parse_cellsearch, parse_rtl_power


REAL_CELLSEARCH_OUT = """LTE CellSearch v1.0.0 (release) beginning
  Search frequency range: 925-947.9 MHz
  PPM: 120
  correction: 1
Examining center frequency 925.8 MHz ...
Examining center frequency 925.9 MHz ...
Examining center frequency 926 MHz ...
  Detected a cell!
    cell ID: 25
    RX power level: -18.4395 dB
    residual frequency offset: 16890.7 Hz
Examining center frequency 926.1 MHz ...
Examining center frequency 926.2 MHz ...
"""


def test_parse_cellsearch_detection_with_frequency_context():
    cells = parse_cellsearch(REAL_CELLSEARCH_OUT)

    assert len(cells) == 1
    assert cells[0]["pci"] == 25
    assert cells[0]["freq_mhz"] == 926.0
    assert cells[0]["signal_raw"] == -18.4395


def test_parse_cellsearch_empty_on_no_detection():
    assert parse_cellsearch("Examining center frequency 925 MHz ...\n") == []


def test_parse_rtl_power_returns_strongest_frequencies():
    # Real rtl_power CSV: date,time,hz_low,hz_high,hz_step,caches,bin dbm values
    out = (
        "2026-09-21, 11:55:00, 935000000, 937000000, 200000, 0, "
        "-20.0, -15.5, -12.0, -18.0, -21.0, -19.0, -16.0, -22.0, -17.0, -20.0\n"
        "2026-09-21, 11:55:00, 937000000, 939000000, 200000, 0, "
        "-19.0, -14.0, -11.0, -17.0, -20.0, -18.0, -15.0, -21.0, -16.0, -19.0\n"
    )
    peaks = parse_rtl_power(out, top_n=2)

    assert len(peaks) == 2
    assert peaks[0] == (937.5, -11.0)
    assert peaks[1] == (935.5, -12.0)


def test_band_and_earfcn_maps_lte900_and_dcs1800():
    assert band_and_earfcn(926.0) == (8, 3460)
    assert band_and_earfcn(944.7) == (8, 3647)
    assert band_and_earfcn(1830.0) == (3, 1450)
    assert band_and_earfcn(700.0) == (None, None)
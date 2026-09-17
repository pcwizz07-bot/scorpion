import struct

from pi.node.presence import (
    GMM_ATTACH_REQUEST,
    GSMTAP_HDR_LEN,
    MM_LOC_UPD_REQUEST,
    MM_TMSI_REALLOC_CMD,
    PD_GMM,
    PD_MM,
    PD_RR,
    RR_PAGING_RESPONSE,
    TmsiChainTracker,
    capture_new_presence_events,
    decode_l3,
    extract_mobile_identity_tmsi,
    extract_udp_payload,
    format_presence_line,
    parse_gsmtap_header,
    parse_gsmtap_packet,
    parse_presence_line,
)


def _gsmtap_header(arfcn=42, timeslot=0, uplink=True, signal_dbm=-70, sub_type=0) -> bytes:
    arfcn_raw = arfcn | (0x4000 if uplink else 0)
    return struct.pack(
        "!BBBBHbbIBBBB",
        2,  # version
        GSMTAP_HDR_LEN // 4,  # hdr_len in words
        1,  # gsmtap type (UM)
        timeslot,
        arfcn_raw,
        signal_dbm,
        0,  # snr_db
        0,  # frame_number
        sub_type,
        0,  # antenna_nr
        0,  # sub_slot
        0,  # res
    )


def _lapdm(l3: bytes) -> bytes:
    return bytes([0x01, 0x03, len(l3) << 2]) + l3


def _mobile_identity_tmsi(tmsi_hex: str) -> bytes:
    tmsi_bytes = bytes.fromhex(tmsi_hex)
    return bytes([len(tmsi_bytes) + 1, 0xF4]) + tmsi_bytes


def _loc_upd_request(tmsi_hex: str, lac: int) -> bytes:
    msg = bytes([PD_MM, MM_LOC_UPD_REQUEST])
    msg += bytes([0x00])  # loc upd type + cksn
    msg += bytes([0x62, 0xF2, 0x10]) + lac.to_bytes(2, "big")  # LAI (mcc/mnc bcd + lac)
    msg += bytes([0x33])  # classmark 1
    msg += _mobile_identity_tmsi(tmsi_hex)
    return msg


def _tmsi_realloc_cmd(tmsi_hex: str, lac: int) -> bytes:
    msg = bytes([PD_MM, MM_TMSI_REALLOC_CMD])
    msg += bytes([0x62, 0xF2, 0x10]) + lac.to_bytes(2, "big")  # LAI
    msg += _mobile_identity_tmsi(tmsi_hex)
    return msg


def _paging_response(tmsi_hex: str) -> bytes:
    msg = bytes([PD_RR, RR_PAGING_RESPONSE])
    msg += bytes([0x00])  # cksn/spare
    msg += bytes([0x02, 0x20, 0x00])  # classmark 2 (len=2)
    msg += _mobile_identity_tmsi(tmsi_hex)
    return msg


def _attach_request(tmsi_hex: str) -> bytes:
    msg = bytes([PD_GMM, GMM_ATTACH_REQUEST])
    msg += bytes([0x02, 0x00, 0x00])  # MS network capability (len=2)
    msg += bytes([0x01])  # attach type + cksn
    msg += bytes([0x00, 0x00])  # DRX parameter
    msg += _mobile_identity_tmsi(tmsi_hex)
    return msg


def _packet(l3: bytes, **header_kwargs) -> bytes:
    return _gsmtap_header(**header_kwargs) + _lapdm(l3)


def test_parse_gsmtap_header_extracts_arfcn_and_uplink_flag():
    header = parse_gsmtap_header(_gsmtap_header(arfcn=99, uplink=True, timeslot=3))
    assert header["arfcn"] == 99
    assert header["uplink"] is True
    assert header["timeslot"] == 3


def test_parse_gsmtap_header_too_short_returns_none():
    assert parse_gsmtap_header(b"\x00" * 4) is None


def test_extract_mobile_identity_tmsi_decodes_tmsi_type():
    ie = _mobile_identity_tmsi("aabbccdd")[1:]
    assert extract_mobile_identity_tmsi(ie) == "aabbccdd"


def test_extract_mobile_identity_tmsi_rejects_non_tmsi_type():
    imsi_ie = bytes([0x08, 0x21, 0x43, 0x65, 0x87, 0x09])  # type=1 (IMSI)
    assert extract_mobile_identity_tmsi(imsi_ie) is None


def test_decode_l3_loc_upd_request_extracts_tmsi_and_lac():
    decoded = decode_l3(_loc_upd_request("11223344", lac=555))
    assert decoded == {"kind": "plu", "lac": 555, "tmsi_old": "11223344", "tmsi_new": None}


def test_decode_l3_tmsi_realloc_cmd_extracts_new_tmsi():
    decoded = decode_l3(_tmsi_realloc_cmd("aabbccdd", lac=555))
    assert decoded["kind"] == "reauth"
    assert decoded["tmsi_new"] == "aabbccdd"
    assert decoded["tmsi_old"] is None


def test_decode_l3_paging_response_extracts_tmsi():
    decoded = decode_l3(_paging_response("deadbeef"))
    assert decoded == {"kind": "page", "lac": None, "tmsi_old": "deadbeef", "tmsi_new": None}


def test_decode_l3_attach_request_extracts_tmsi():
    decoded = decode_l3(_attach_request("cafebabe"))
    assert decoded["kind"] == "attach"
    assert decoded["tmsi_old"] == "cafebabe"


def test_decode_l3_unknown_message_returns_none():
    assert decode_l3(bytes([PD_MM, 0x3F])) is None


def test_decode_l3_too_short_returns_none():
    assert decode_l3(b"\x05") is None


def test_tmsi_chain_tracker_chains_old_to_new_on_same_channel():
    tracker = TmsiChainTracker()
    key = (42, 0)

    plu = tracker.process(key, {"kind": "plu", "tmsi_old": "11223344", "tmsi_new": None, "lac": 555})
    assert plu["tmsi_old"] == "11223344"

    realloc = tracker.process(key, {"kind": "reauth", "tmsi_old": None, "tmsi_new": "aabbccdd", "lac": 555})
    assert realloc["tmsi_old"] == "11223344"
    assert realloc["tmsi_new"] == "aabbccdd"


def test_tmsi_chain_tracker_keeps_channels_independent():
    tracker = TmsiChainTracker()
    tracker.process((1, 0), {"kind": "plu", "tmsi_old": "11111111", "tmsi_new": None, "lac": None})

    realloc = tracker.process((2, 0), {"kind": "reauth", "tmsi_old": None, "tmsi_new": "22222222", "lac": None})

    assert realloc["tmsi_old"] is None


def test_parse_gsmtap_packet_end_to_end_chains_realloc():
    tracker = TmsiChainTracker()
    plu_packet = _packet(_loc_upd_request("11223344", lac=42), arfcn=7, timeslot=1, signal_dbm=-80)
    realloc_packet = _packet(_tmsi_realloc_cmd("aabbccdd", lac=42), arfcn=7, timeslot=1, signal_dbm=-75)

    plu_event = parse_gsmtap_packet(plu_packet, tracker)
    realloc_event = parse_gsmtap_packet(realloc_packet, tracker)

    assert plu_event["kind"] == "plu"
    assert plu_event["power"] == -80
    assert realloc_event["kind"] == "reauth"
    assert realloc_event["tmsi_old"] == "11223344"
    assert realloc_event["tmsi_new"] == "aabbccdd"


def test_format_and_parse_presence_line_roundtrip():
    event = {"kind": "reauth", "tmsi_old": "11223344", "tmsi_new": "aabbccdd", "lac": 42, "cell_id": None, "chan": 0, "power": -75}

    line = format_presence_line(event)
    parsed = parse_presence_line(line)

    assert parsed["kind"] == "reauth"
    assert parsed["tmsi_old"] == "11223344"
    assert parsed["tmsi_new"] == "aabbccdd"
    assert parsed["lac"] == 42
    assert parsed["cell_id"] is None
    assert parsed["signal_dbm"] == -75


def test_parse_presence_line_skips_header_and_blank():
    assert parse_presence_line("") is None
    assert parse_presence_line("stamp,kind,tmsi_old,tmsi_new,lac,cell_id,chan,power") is None


def test_parse_presence_line_rejects_bad_kind():
    assert parse_presence_line("2026-01-01T00:00:00,bogus,,,,,,") is None


class _FakeTailReader:
    def __init__(self, lines):
        self._lines = lines

    def read_new_lines(self):
        return self._lines


class _FakeSpool:
    def __init__(self):
        self.appended = []

    def append(self, item):
        self.appended.append(item)


def test_capture_new_presence_events_appends_parsed_lines_to_spool():
    line = format_presence_line({"kind": "page", "tmsi_old": "11223344", "tmsi_new": None, "lac": None, "cell_id": None, "chan": 0, "power": -60})
    reader = _FakeTailReader([line, "garbage"])
    spool = _FakeSpool()

    count = capture_new_presence_events(reader, spool, "Pi-1")

    assert count == 1
    assert spool.appended[0]["device_name"] == "Pi-1"
    assert spool.appended[0]["kind"] == "page"


def _eth_ipv4_udp_frame(dst_port: int, payload: bytes) -> bytes:
    eth = b"\x00" * 12 + struct.pack("!H", 0x0800)
    udp_len = 8 + len(payload)
    udp = struct.pack("!HHHH", 12345, dst_port, udp_len, 0) + payload
    total_len = 20 + udp_len
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, total_len, 0, 0, 64, 17, 0, b"\x7f\x00\x00\x01", b"\x7f\x00\x00\x01")
    return eth + ip + udp


def test_extract_udp_payload_returns_payload_for_matching_port():
    frame = _eth_ipv4_udp_frame(4729, b"hello-gsmtap")
    assert extract_udp_payload(frame, 4729) == b"hello-gsmtap"


def test_extract_udp_payload_returns_none_for_other_port():
    frame = _eth_ipv4_udp_frame(9999, b"hello")
    assert extract_udp_payload(frame, 4729) is None


def test_extract_udp_payload_returns_none_for_short_frame():
    assert extract_udp_payload(b"\x00" * 10, 4729) is None

"""GSMTAP (UDP 4729) L3 mobility-event reader: device presence + TMSI-chaining.

Sniffs passively via a raw AF_PACKET socket on loopback instead of binding
UDP 4729, so it coexists with simple_IMSI-catcher.py which already owns that
port. Decodes just enough of GSM 04.08/24.008 to pull TMSI/P-TMSI values and
LAC out of the message types we care about — not a full IE/TLV decoder.
"""
import socket
import struct
from datetime import datetime, timezone

GSMTAP_PORT = 4729
GSMTAP_HDR_LEN = 16
ARFCN_MASK = 0x0FFF
ARFCN_F_UPLINK = 0x4000

ETH_P_ALL = 0x0003
ETH_HDR_LEN = 14

PD_RR = 0x06
PD_MM = 0x05
PD_GMM = 0x08

MM_LOC_UPD_REQUEST = 0x08
MM_TMSI_REALLOC_CMD = 0x1A
RR_PAGING_RESPONSE = 0x27
GMM_ATTACH_REQUEST = 0x01
GMM_ROUTING_AREA_UPDATE_REQUEST = 0x08

KINDS = ("plu", "attach", "page", "reauth")

_KIND_BY_MESSAGE = {
    (PD_MM, MM_LOC_UPD_REQUEST): "plu",
    (PD_MM, MM_TMSI_REALLOC_CMD): "reauth",
    (PD_RR, RR_PAGING_RESPONSE): "page",
    (PD_GMM, GMM_ATTACH_REQUEST): "attach",
    (PD_GMM, GMM_ROUTING_AREA_UPDATE_REQUEST): "plu",
}


def parse_gsmtap_header(packet: bytes) -> dict | None:
    if len(packet) < GSMTAP_HDR_LEN:
        return None
    _version, hdr_len_words, _gsmtap_type, timeslot = struct.unpack_from("!BBBB", packet, 0)
    arfcn_raw, signal_dbm, _snr_db, _frame_number, sub_type, _antenna_nr, _sub_slot, _res = (
        struct.unpack_from("!HbbIBBBB", packet, 4)
    )
    return {
        "hdr_len": hdr_len_words * 4,
        "timeslot": timeslot,
        "arfcn": arfcn_raw & ARFCN_MASK,
        "uplink": bool(arfcn_raw & ARFCN_F_UPLINK),
        "signal_dbm": signal_dbm,
        "chan": sub_type,
    }


def extract_mobile_identity_tmsi(ie_value: bytes) -> str | None:
    """Decode a GSM Mobile Identity IE value; hex TMSI if type==TMSI/P-TMSI, else None."""
    if len(ie_value) < 5 or (ie_value[0] & 0x07) != 0x04:
        return None
    return ie_value[1:5].hex()


def _scan_for_tmsi(body: bytes) -> str | None:
    """Fallback scan for a TMSI mobile-identity byte (type=TMSI, odd/even+fill=0xF).

    ponytail: heuristic scan used only for Routing Area Update Request instead
    of a precise IE offset table. Upgrade to exact offsets if RAU chaining
    proves unreliable against real captures.
    """
    for i in range(len(body) - 4):
        if body[i] == 0xF4:
            return body[i + 1 : i + 5].hex()
    return None


def _decode_loc_upd_request(body: bytes) -> dict:
    lac = None
    tmsi = None
    if len(body) >= 6:
        lai = body[1:6]
        lac = int.from_bytes(lai[3:5], "big")
    if len(body) >= 8:
        id_len = body[7]
        id_val = body[8 : 8 + id_len]
        tmsi = extract_mobile_identity_tmsi(id_val)
    return {"lac": lac, "tmsi_old": tmsi, "tmsi_new": None}


def _decode_tmsi_realloc_cmd(body: bytes) -> dict:
    lac = None
    tmsi_new = None
    if len(body) >= 5:
        lai = body[0:5]
        lac = int.from_bytes(lai[3:5], "big")
    if len(body) >= 6:
        id_len = body[5]
        id_val = body[6 : 6 + id_len]
        tmsi_new = extract_mobile_identity_tmsi(id_val)
    return {"lac": lac, "tmsi_old": None, "tmsi_new": tmsi_new}


def _decode_paging_response(body: bytes) -> dict:
    tmsi = None
    if len(body) >= 2:
        cm2_len = body[1]
        idx = 2 + cm2_len
        if len(body) > idx:
            id_len = body[idx]
            id_val = body[idx + 1 : idx + 1 + id_len]
            tmsi = extract_mobile_identity_tmsi(id_val)
    return {"lac": None, "tmsi_old": tmsi, "tmsi_new": None}


def _decode_attach_request(body: bytes) -> dict:
    tmsi = None
    if len(body) >= 1:
        idx = 1 + body[0]  # MS network capability (LV)
        idx += 1  # attach type + ciphering key sequence number
        idx += 2  # DRX parameter
        if len(body) > idx:
            id_len = body[idx]
            id_val = body[idx + 1 : idx + 1 + id_len]
            tmsi = extract_mobile_identity_tmsi(id_val)
    return {"lac": None, "tmsi_old": tmsi, "tmsi_new": None}


def _decode_routing_area_update(body: bytes) -> dict:
    return {"lac": None, "tmsi_old": _scan_for_tmsi(body), "tmsi_new": None}


_DECODER_BY_MESSAGE = {
    (PD_MM, MM_LOC_UPD_REQUEST): _decode_loc_upd_request,
    (PD_MM, MM_TMSI_REALLOC_CMD): _decode_tmsi_realloc_cmd,
    (PD_RR, RR_PAGING_RESPONSE): _decode_paging_response,
    (PD_GMM, GMM_ATTACH_REQUEST): _decode_attach_request,
    (PD_GMM, GMM_ROUTING_AREA_UPDATE_REQUEST): _decode_routing_area_update,
}


def decode_l3(l3: bytes) -> dict | None:
    if len(l3) < 2:
        return None
    key = (l3[0] & 0x0F, l3[1] & 0x3F)
    kind = _KIND_BY_MESSAGE.get(key)
    if kind is None:
        return None
    return {"kind": kind, **_DECODER_BY_MESSAGE[key](l3[2:])}


class TmsiChainTracker:
    """Chains TMSI reallocation old->new by (arfcn, timeslot) radio channel.

    ponytail: correlates by channel only, not by subscriber identity; two
    reallocations racing on the same timeslot could misattribute. Upgrade to
    per-session correlation if that shows up against real captures.
    """

    def __init__(self):
        self._last_tmsi: dict = {}

    def process(self, channel_key: tuple, decoded: dict) -> dict:
        event = dict(decoded)
        if decoded["kind"] == "reauth" and decoded["tmsi_new"]:
            event["tmsi_old"] = self._last_tmsi.get(channel_key)
            self._last_tmsi[channel_key] = decoded["tmsi_new"]
        elif decoded["tmsi_old"]:
            self._last_tmsi[channel_key] = decoded["tmsi_old"]
        return event


def parse_gsmtap_packet(packet: bytes, tracker: TmsiChainTracker) -> dict | None:
    header = parse_gsmtap_header(packet)
    if header is None:
        return None
    l2 = packet[header["hdr_len"] :]
    if len(l2) < 3:
        return None
    l3 = l2[3:]  # skip short LAPDm header (address, control, length indicator)
    decoded = decode_l3(l3)
    if decoded is None:
        return None
    event = tracker.process((header["arfcn"], header["timeslot"]), decoded)
    event["chan"] = header["chan"]
    event["power"] = header["signal_dbm"]
    return event


def format_presence_line(event: dict) -> str:
    def s(key):
        val = event.get(key)
        return "" if val is None else str(val)

    return ",".join(
        [
            datetime.now(timezone.utc).isoformat(),
            event["kind"],
            s("tmsi_old"),
            s("tmsi_new"),
            s("lac"),
            s("cell_id"),
            s("chan"),
            s("power"),
        ]
    )


def parse_presence_line(line: str) -> dict | None:
    line = line.strip()
    if not line or line.startswith("stamp"):
        return None
    parts = line.split(",")
    if len(parts) != 8:
        return None
    stamp, kind, tmsi_old, tmsi_new, lac, cell_id, chan, power = parts
    if kind not in KINDS:
        return None
    return {
        "observed_at": stamp,
        "kind": kind,
        "tmsi_old": tmsi_old or None,
        "tmsi_new": tmsi_new or None,
        "lac": int(lac) if lac else None,
        "cell_id": int(cell_id) if cell_id else None,
        "chan": chan or None,
        "signal_dbm": int(power) if power else None,
    }


def capture_new_presence_events(tail_reader, spool, device_name: str) -> int:
    count = 0
    for raw_line in tail_reader.read_new_lines():
        parsed = parse_presence_line(raw_line)
        if parsed is None:
            continue
        event = dict(parsed)
        event["device_name"] = device_name
        spool.append(event)
        count += 1
    return count


def extract_udp_payload(frame: bytes, port: int) -> bytes | None:
    """Pull the UDP payload for `port` out of a raw Ethernet+IPv4+UDP frame."""
    if len(frame) < ETH_HDR_LEN + 20 + 8:
        return None
    eth_type = struct.unpack_from("!H", frame, 12)[0]
    if eth_type != 0x0800:  # IPv4
        return None
    ip_offset = ETH_HDR_LEN
    ihl = (frame[ip_offset] & 0x0F) * 4
    if frame[ip_offset + 9] != 17:  # UDP
        return None
    udp_offset = ip_offset + ihl
    if struct.unpack_from("!H", frame, udp_offset + 2)[0] != port:
        return None
    udp_len = struct.unpack_from("!H", frame, udp_offset + 4)[0]
    return frame[udp_offset + 8 : udp_offset + udp_len]


def run_presence_listener(output_path: str, iface: str = "lo", port: int = GSMTAP_PORT, stop_event=None) -> None:
    """Sniff GSMTAP off `iface` and append decoded presence events to `output_path`.

    Runs until `stop_event` is set (or forever if None) - meant for a daemon thread.
    Requires CAP_NET_RAW (the agent already runs as root for grgsm/livemon).
    """
    tracker = TmsiChainTracker()
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    sock.bind((iface, 0))
    sock.settimeout(1.0)
    try:
        while stop_event is None or not stop_event.is_set():
            try:
                frame, _addr = sock.recvfrom(65535)
            except socket.timeout:
                continue
            payload = extract_udp_payload(frame, port)
            if payload is None:
                continue
            event = parse_gsmtap_packet(payload, tracker)
            if event is None:
                continue
            with open(output_path, "a") as f:
                f.write(format_presence_line(event) + "\n")
    finally:
        sock.close()

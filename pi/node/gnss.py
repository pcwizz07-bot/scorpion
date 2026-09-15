"""GNSS fix via serial NMEA (SIM7600 HAT, $GPGGA sentence). Stdlib-only (termios)."""
import os
import time


def _to_decimal_degrees(raw: str, hemisphere: str) -> float:
    value = float(raw)
    degrees = int(value / 100)
    minutes = value - degrees * 100
    decimal = degrees + minutes / 60
    return -decimal if hemisphere in ("S", "W") else decimal


def parse_gpgga(line: str) -> dict | None:
    line = line.strip()
    if not line.startswith("$GPGGA"):
        return None
    fields = line.split("*")[0].split(",")
    if len(fields) < 6:
        return None
    lat_raw, lat_hemi, lng_raw, lng_hemi, fix_quality = fields[2], fields[3], fields[4], fields[5], fields[6] if len(fields) > 6 else ""
    if not lat_raw or not lng_raw or fix_quality in ("", "0"):
        return None
    try:
        lat = _to_decimal_degrees(lat_raw, lat_hemi)
        lng = _to_decimal_degrees(lng_raw, lng_hemi)
    except ValueError:
        return None
    return {"lat": lat, "lng": lng}


def get_fix(serial_path: str, baud: int, timeout_s: float = 2.0) -> dict | None:
    """Read from the GNSS serial device until a valid $GPGGA fix is seen, or timeout.

    ponytail: raw termios config (no pyserial dep per spec); revisit if we
    need flow control or non-Linux support.
    """
    try:
        import termios

        fd = os.open(serial_path, os.O_RDONLY | os.O_NOCTTY)
    except OSError:
        return None

    try:
        attrs = termios.tcgetattr(fd)
        baud_const = getattr(termios, f"B{baud}", termios.B115200)
        attrs[4] = baud_const
        attrs[5] = baud_const
        termios.tcsetattr(fd, termios.TCSANOW, attrs)

        deadline = time.monotonic() + timeout_s
        buf = b""
        while time.monotonic() < deadline:
            chunk = os.read(fd, 256)
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                raw_line, buf = buf.split(b"\n", 1)
                fix = parse_gpgga(raw_line.decode(errors="ignore"))
                if fix is not None:
                    return fix
    except OSError:
        return None
    finally:
        os.close(fd)
    return None

#!/usr/bin/env python3
"""Talk to a single BQ79616 (the SME daughter-board base device) over its UART.

Hardware (see docs/09-uart-bench-setup.md):
    USB-UART adapter (3.3 V, must support 1 Mbaud and 4000 baud, e.g. FTDI FT232R/FT232H)
      adapter TX  -> header A7 (ISO7721 INA  -> BQ79616 RX)
      adapter RX  <- header B7 (ISO7721 OUTB <- BQ79616 TX)
      adapter 3V3 -> header A8 (ISO7721 VCC2)
      adapter GND -> header A6 (ISO7721 GND2)
    Floating 12 V bench supply -> B10 (+) / A10 (-), current limit ~100 mA.

Examples:
    python bq_uart.py COM5 info            # wake, read PARTID/REV/address/OTP config
    python bq_uart.py COM5 cells           # wake, start main ADC, read VCELL1..16
    python bq_uart.py COM5 bat             # wake, start AUX ADC, read BAT pin voltage
    python bq_uart.py COM5 read 0x0500 1   # read 1 byte from PARTID
    python bq_uart.py COM5 write 0x030D 0x06

Requires: pip install pyserial
"""
import argparse
import sys
import time

from bq_crc import append_crc, frame_ok

BAUD = 1_000_000
WAKE_BAUD = 4000  # 0x00 at 4000 baud = start + 8 data bits low = 2.25 ms (tHLD_WAKE: 2-2.5 ms)
CELL_LSB_V = 190.73e-6
AUX_BAT_LSB_V = 3.05e-3

# Command INIT bytes (bit 7 = command, bits 6:4 = request type)
SINGLE_READ = 0x80
SINGLE_WRITE = 0x90
BROADCAST_READ = 0xC0
BROADCAST_WRITE = 0xD0

REG = {
    "OTP_SHADOW": 0x0000,  # 0x0000-0x0037 customer OTP / config shadow
    "DIR0_ADDR": 0x0306,
    "COMM_CTRL": 0x0308,
    "CONTROL1": 0x0309,
    "ADC_CTRL1": 0x030D,
    "ADC_CTRL3": 0x030F,
    "PARTID": 0x0500,
    "DEV_STAT": 0x052C,
    "FAULT_SUMMARY": 0x052D,
    "VCELL16_HI": 0x0568,
    "AUX_BAT_HI": 0x05B6,
    "DEV_REVID": 0x0E00,
}

PARTIDS = {0x21: "BQ79616", 0x01: "BQ79614", 0x02: "BQ79612"}

OTP_NAMES = {
    0x00: "DIR0_ADDR_OTP", 0x01: "DIR1_ADDR_OTP", 0x02: "DEV_CONF", 0x03: "ACTIVE_CELL",
    0x05: "BBVC_POSN1", 0x06: "BBVC_POSN2", 0x07: "ADC_CONF1", 0x08: "ADC_CONF2",
    0x09: "OV_THRESH", 0x0A: "UV_THRESH", 0x0B: "OTUT_THRESH", 0x0C: "UV_DISABLE1",
    0x0D: "UV_DISABLE2", 0x0E: "GPIO_CONF1", 0x0F: "GPIO_CONF2", 0x10: "GPIO_CONF3",
    0x11: "GPIO_CONF4", 0x16: "FAULT_MSK1", 0x17: "FAULT_MSK2", 0x18: "PWR_TRANSIT_CONF",
    0x19: "COMM_TIMEOUT_CONF", 0x1A: "TX_HOLD_OFF", 0x1B: "MAIN_ADC_CAL1",
    0x1C: "MAIN_ADC_CAL2", 0x1D: "AUX_ADC_CAL1", 0x1E: "AUX_ADC_CAL2",
    0x36: "CUST_CRC_HI", 0x37: "CUST_CRC_LO",
}


def build_read(dev: int, reg: int, length: int, init: int = SINGLE_READ) -> bytes:
    """Read `length` (1-128) bytes starting at `reg`."""
    if not 1 <= length <= 128:
        raise ValueError("length must be 1..128")
    body = bytes([init])
    if init == SINGLE_READ:
        body += bytes([dev])
    body += bytes([reg >> 8, reg & 0xFF, length - 1])
    return append_crc(body)


def build_write(dev: int, reg: int, data: bytes, init: int = SINGLE_WRITE) -> bytes:
    """Write 1-8 bytes starting at `reg`."""
    if not 1 <= len(data) <= 8:
        raise ValueError("data must be 1..8 bytes")
    body = bytes([init | (len(data) - 1)])
    if init == SINGLE_WRITE:
        body += bytes([dev])
    body += bytes([reg >> 8, reg & 0xFF]) + data
    return append_crc(body)


def parse_response(raw: bytes):
    """Split a byte stream into (dev, reg, data, crc_ok) tuples."""
    frames, i = [], 0
    while i < len(raw):
        n = (raw[i] & 0x7F) + 1
        end = i + 1 + 1 + 2 + n + 2
        if end > len(raw):
            break
        frame = raw[i:end]
        frames.append((frame[1], (frame[2] << 8) | frame[3], frame[4:4 + n], frame_ok(frame)))
        i = end
    return frames


def hexs(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


class BQ:
    def __init__(self, port: str, verbose: bool = False):
        import serial  # imported here so the frame helpers work without pyserial

        self.ser = serial.Serial(port, BAUD, timeout=0.05)
        self.verbose = verbose

    def wake(self):
        """WAKE ping: hold RX low for 2-2.5 ms, then allow the device to start up."""
        self.ser.reset_input_buffer()
        self.ser.baudrate = WAKE_BAUD
        self.ser.write(b"\x00")
        self.ser.flush()
        time.sleep(0.01)
        self.ser.baudrate = BAUD
        time.sleep(0.01)  # tSU(WAKE_SHUT) is ~1 ms; be generous
        self.ser.reset_input_buffer()

    def init_single(self):
        """Auto-address a lone base device as address 0 (datasheet 7.3.6.1.3.2).

        After WAKE the device only accepts broadcast writes; reads are ignored until this has run.
        """
        self.write(0x0343, bytes(8), init=BROADCAST_WRITE)        # DLL sync: OTP_ECC_DATAIN1..8 = 0
        self.write(REG["CONTROL1"], bytes([0x01]), init=BROADCAST_WRITE)  # ADDR_WR = 1
        self.write(REG["DIR0_ADDR"], bytes([0x00]), init=BROADCAST_WRITE)  # address 0
        self.write(REG["COMM_CTRL"], bytes([0x00]), init=BROADCAST_WRITE)  # base device, not top of stack
        self.xfer(build_read(0, 0x0343, 8, init=BROADCAST_READ), expect=14)  # DLL sync dummy read

    def xfer(self, frame: bytes, expect: int = 0) -> bytes:
        if self.verbose:
            print(f"  TX: {hexs(frame)}")
        self.ser.reset_input_buffer()
        self.ser.write(frame)
        self.ser.flush()
        if not expect:
            time.sleep(0.002)
            return b""
        raw = self.ser.read(expect)
        if self.verbose:
            print(f"  RX: {hexs(raw) if raw else '(nothing)'}")
        return raw

    def read(self, reg: int, length: int, dev: int = 0) -> bytes:
        raw = self.xfer(build_read(dev, reg, length), expect=length + 6)
        frames = parse_response(raw)
        if not frames:
            raise IOError(f"no response reading 0x{reg:04X} (got {len(raw)} bytes: {hexs(raw)})")
        rdev, rreg, data, ok = frames[0]
        if not ok:
            raise IOError(f"CRC error reading 0x{reg:04X}: {hexs(raw)}")
        return data

    def write(self, reg: int, data: bytes, dev: int = 0, init: int = SINGLE_WRITE):
        self.xfer(build_write(dev, reg, data, init=init))


def cmd_info(bq: BQ):
    partid = bq.read(REG["PARTID"], 1)[0]
    print(f"Device: {PARTIDS.get(partid, 'unknown')}")
    for name in ("PARTID", "DEV_REVID", "DIR0_ADDR", "COMM_CTRL", "DEV_STAT", "FAULT_SUMMARY"):
        val = bq.read(REG[name], 1)[0]
        print(f"{name:<14} 0x{REG[name]:04X} = 0x{val:02X}")
    otp = bq.read(REG["OTP_SHADOW"], 0x38)
    print("\nOTP shadow / configuration (0x0000-0x0037):")
    for addr, val in enumerate(otp):
        name = OTP_NAMES.get(addr, "")
        print(f"  0x{addr:04X} {name:<18} 0x{val:02X}")


def cmd_cells(bq: BQ):
    bq.write(REG["ADC_CTRL1"], bytes([0x06]))  # MAIN_GO | MAIN_MODE = continuous
    time.sleep(0.05)
    data = bq.read(REG["VCELL16_HI"], 32)
    cells = {16 - i: int.from_bytes(data[2 * i:2 * i + 2], "big", signed=True) for i in range(16)}
    # Node voltage VCn relative to VC0 (isolated GND) = sum of VCELL1..n. Readings outside
    # the 0-5 V differential range (or near +/-32767 counts) are out of spec and unreliable.
    node = 0.0
    rows = []
    for n in range(1, 17):
        v = cells[n] * CELL_LSB_V
        node += v
        flag = "  <- outside 0-5 V range" if not -0.3 <= v <= 5.0 else ""
        rows.append(f"VCELL{n:<2} raw {cells[n]:6d}  {v:8.4f} V   VC{n:<2} = {node:7.3f} V{flag}")
    for row in reversed(rows):
        print(row)


def cmd_bat(bq: BQ):
    bq.write(REG["ADC_CTRL3"], bytes([0x06]))  # AUX_GO | AUX_MODE = continuous
    time.sleep(0.1)
    raw = int.from_bytes(bq.read(REG["AUX_BAT_HI"], 2), "big", signed=True)  # read HI+LO together
    print(f"AUX_BAT raw {raw}  ->  BAT pin = {raw * AUX_BAT_LSB_V:.3f} V")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port")
    ap.add_argument("cmd", choices=["info", "cells", "bat", "read", "write", "wake"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--no-wake", action="store_true", help="skip the WAKE ping and auto-address")
    ap.add_argument("-v", "--verbose", action="store_true", help="print raw frames")
    a = ap.parse_args()

    bq = BQ(a.port, a.verbose)
    if not a.no_wake:
        bq.wake()
        bq.init_single()
    if a.cmd == "info":
        cmd_info(bq)
    elif a.cmd == "cells":
        cmd_cells(bq)
    elif a.cmd == "bat":
        cmd_bat(bq)
    elif a.cmd == "read":
        reg, length = int(a.args[0], 0), int(a.args[1], 0) if len(a.args) > 1 else 1
        print(hexs(bq.read(reg, length)))
    elif a.cmd == "write":
        reg = int(a.args[0], 0)
        bq.write(reg, bytes(int(x, 0) for x in a.args[1:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

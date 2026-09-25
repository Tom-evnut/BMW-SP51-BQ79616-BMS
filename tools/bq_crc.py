#!/usr/bin/env python3
"""CRC helper for the TI BQ796xx daisy-chain frame protocol.

The BQ79616 uses CRC-16-IBM (x^16 + x^15 + x^2 + 1), initial value 0xFFFF,
bit-reflected (identical to CRC-16/MODBUS). The CRC is appended low byte first.
Running the CRC over a complete frame including its CRC yields 0x0000.

Usage:
    bq_crc.py 80 00 02 0F 0B          -> prints frame with CRC appended
    bq_crc.py --check 80 00 02 0F 0B C0 29
"""
import sys


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def append_crc(frame: bytes) -> bytes:
    crc = crc16(frame)
    return frame + bytes([crc & 0xFF, crc >> 8])


def frame_ok(frame: bytes) -> bool:
    return len(frame) >= 3 and crc16(frame) == 0


def _selftest() -> None:
    # Example from BQ79616-Q1 datasheet SLUSE81F, section 7.3.6.1.1.2.1.6
    assert append_crc(bytes.fromhex("8000020F0B")) == bytes.fromhex("8000020F0BC029")
    assert frame_ok(bytes.fromhex("8000020F0BC029"))


if __name__ == "__main__":
    _selftest()
    args = sys.argv[1:]
    check = bool(args) and args[0] == "--check"
    if check:
        args = args[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    frame = bytes(int(a, 16) for a in args)
    if check:
        ok = frame_ok(frame)
        print("CRC OK" if ok else "CRC FAIL")
        sys.exit(0 if ok else 1)
    print(" ".join(f"{b:02X}" for b in append_crc(frame)))

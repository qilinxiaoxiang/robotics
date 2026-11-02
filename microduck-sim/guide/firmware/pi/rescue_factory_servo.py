"""Bring a servo back from factory settings (ID 1, 57600) over the duck's 1 Mbaud bus, on the A7Z, without opening the robot.

A servo that fell back to factory settings hears nothing at 1 Mbaud, and openrb_dual_host fixes the bus at 1 Mbaud. But
1 Mbaud bytes can draw a 57600 baud waveform: each 57600 bit lasts 17.4 us, and a UART byte at 1 Mbaud sets 10 us of the
line, with a forced 1 us start bit and 1 us stop bit. Those 1 us glitches sit under a 16x receiver's three-sample majority.
The OpenRB forwards any packet with a valid header and length without checking its CRC, so the drawing travels as the
payload of a packet to an ID nobody has; the 14 others drop it.

The servo's answers come back at 57600 and cannot be read here, so success is read back at 1 Mbaud afterwards: the missing
ID answers. The ID goes first, so the servo never shares ID 1 with the robot's own ID1, then the baud. The rest of the
settings are written at 1 Mbaud through replace_servo's normal path. Only a missing ID can be rescued, and torque stays off.

  rescue_factory_servo.py --id 2
"""
import argparse
import struct
import sys
import time

from replace_servo import ADDR_BAUD, ADDR_ID, ALL_IDS, BAUD, BAUD_1M, PORT, SETTINGS, Bus, brain_running, crc16, packet

FACTORY_ID = 1
FACTORY_BIT_US = 1e6 / 57600
FRAMES_PER_BYTE = 18  # 180 us, against 173.6 us for 10 bits: a slightly long stop bit
CARRIER_ID = 252  # no servo has it; the others ignore the packet
ADDR_LEN = 1  # both registers are one byte


def draw_byte(value):
    """18 frames (180 us) for one 8N1 byte at 57600, the first frame's start bit on the byte's falling edge.

    Every byte restarts on a frame edge, so no drift builds up, and the last glitch before an edge lies a full 10 us ahead
    of it. A glitch nearer than that would pass a receiver's start check and sync it early (the first version did).
    """
    levels = [0] + [(value >> k) & 1 for k in range(8)] + [1]
    out = bytearray()
    for frame in range(FRAMES_PER_BYTE):
        byte = 0
        for k in range(8):
            i = int((frame * 10 + 1 + k + 0.5) / FACTORY_BIT_US)  # the frame's own start bit fills its first microsecond
            if i >= len(levels) or levels[i]:
                byte |= 1 << k
        out.append(byte)
    return bytes(out)


def draw(data):
    """1 Mbaud bytes whose line levels draw data at 57600."""
    return b"".join(draw_byte(b) for b in data)


def carrier(payload):
    """A packet the OpenRB forwards whole: header, an unused ID, a length that covers the drawing."""
    head = bytes([0xFF, 0xFF, 0xFD, 0x00, CARRIER_ID]) + struct.pack("<H", len(payload) + 2)
    return head + payload + struct.pack("<H", crc16(head + payload) ^ 0xFFFF)  # a bad CRC on purpose: no servo acts on it


def write_at_57600(bus, sid, addr, value):
    inner = packet(sid, 0x03, struct.pack("<H", addr) + bytes([value]))
    bus.ser.reset_input_buffer()
    bus.ser.write(carrier(b"\xff" * 4 + draw(inner) + b"\xff" * 4))
    time.sleep(0.05)  # the EEPROM write, and the factory 500 us reply delay


def rescue(bus, target, tries=3):
    ids = bus.scan()
    missing = [i for i in ALL_IDS if i not in ids]
    if target not in missing:
        sys.exit(f"rescue: ID{target} answers at 1 Mbaud, nothing to do; on the bus: {ids}")
    if len(missing) != 1:
        sys.exit(f"rescue: IDs {missing} are missing; this needs exactly one; nothing written")
    for attempt in range(1, tries + 1):
        if target != FACTORY_ID:
            write_at_57600(bus, FACTORY_ID, ADDR_ID, target)
        write_at_57600(bus, target, ADDR_BAUD, BAUD_1M)
        time.sleep(0.2)
        if target in bus.scan():
            for addr, size, value in SETTINGS:
                if not bus.write(target, addr, size, value):
                    sys.exit(f"rescue: ID{target} answers but address {addr} did not read back {value}; rerun")
            print(f"ID{target} is back at 1 Mbaud on try {attempt}, with the robot's settings; torque off")
            return
    sys.exit(f"rescue: ID{target} still silent after {tries} tries. Either it is not at factory settings or the drawing failed")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", type=int, required=True, choices=ALL_IDS, help="the ID that went missing")
    ap.add_argument("--port", default=PORT)
    a = ap.parse_args()
    if brain_running():
        sys.exit("rescue: the brain is running and holds the bus; stop it first")
    import serial
    rescue(Bus(serial.Serial(a.port, BAUD, timeout=0)), a.id)


if __name__ == "__main__":
    main()

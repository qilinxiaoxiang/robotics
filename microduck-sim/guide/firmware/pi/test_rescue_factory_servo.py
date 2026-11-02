"""The 57600 drawing, decoded by a software model of a 16x oversampling UART (the receiver in the servo is an assumption)."""
import unittest

import rescue_factory_servo as r
from replace_servo import packet


def line_level(out):
    """The line per microsecond when the bytes leave a 1 Mbaud UART back to back."""
    return [bit for b in out for bit in [0] + [(b >> k) & 1 for k in range(8)] + [1]]


def uart_16x(line, baud=57600.0, error=0.0):
    """Start on a falling edge confirmed by majority at mid bit; each bit by the three samples at 7/16, 8/16 and 9/16."""
    bit_us = 1e6 / (baud * (1 + error))
    at = lambda t: line[int(t)] if int(t) < len(line) else 1
    vote = lambda t: at(t + bit_us * 7 / 16) + at(t + bit_us * 8 / 16) + at(t + bit_us * 9 / 16) >= 2
    out, t = bytearray(), 0.0
    while t < len(line):
        if at(t) == 1 or vote(t):  # no edge, or a start bit that does not hold
            t += bit_us / 16
            continue
        byte = 0
        for k in range(8):
            byte |= vote(t + bit_us * (k + 1)) << k
        if vote(t + bit_us * 9):  # a good stop bit; a framing error drops the byte
            out.append(byte)
        t += bit_us * 9.5
    return bytes(out)


class Drawing(unittest.TestCase):
    def test_the_packet_survives_at_every_receiver_clock_error(self):
        inner = packet(1, 0x03, b"\x07\x00\x02")
        for error in (-0.02, -0.01, 0.0, 0.01, 0.02):
            line = [1] * 40 + line_level(r.draw(inner)) + [1] * 40
            self.assertEqual(uart_16x(line, error=error), inner, f"clock error {error}")

    def test_every_byte_value_survives(self):
        data = bytes(range(256))
        self.assertEqual(uart_16x([1] * 40 + line_level(r.draw(data)) + [1] * 40), data)

    def test_the_carrier_fits_the_openrb_and_no_servo_can_act_on_it(self):
        pkt = r.carrier(r.draw(packet(1, 0x03, b"\x07\x00\x02")))
        self.assertLessEqual(len(pkt), 512)  # MAX_PKT in openrb_dual_host.ino
        self.assertEqual(pkt[:4], b"\xff\xff\xfd\x00")
        self.assertEqual(7 + int.from_bytes(pkt[5:7], "little"), len(pkt))
        self.assertEqual(pkt[4], r.CARRIER_ID)
        self.assertNotEqual(int.from_bytes(pkt[-2:], "little"), r.crc16(pkt[:-2]))


if __name__ == "__main__":
    unittest.main()

"""Watch the total servo current that flows through the OpenRB-150 ports.

The servos take the 7 V rail (XL4015 #1, set to 6.80 V) through the OpenRB's DXL ports, which ROBOTIS rates at 3 A for all ports together. This script
reads Present Current (XL330 address 126, 2 bytes, 1 mA) from IDs 1-15 with one Sync Read per cycle, prints the
running total and writes every sample to a CSV file. It only reads, so it never moves a servo; run it while the robot
stands, while you load it by hand, or while a separate script commands poses. It cannot share /dev/serial0 with the
walking controller.

Usage on the Pi:  python3 current_watch.py [--seconds 60] [--csv current.csv] [--limit-ma 3000]
Needs: pip install dynamixel-sdk
Exit code 0 when the total stayed under --limit-ma except for bursts shorter than --burst-s; 1 otherwise; 2 on a port
or read failure.
"""
import argparse
import csv
import sys
import time

from dynamixel_sdk import COMM_SUCCESS, GroupSyncRead, PacketHandler, PortHandler

IDS = range(1, 16)
ADDR_PRESENT_CURRENT = 126  # XL330, 2 bytes, signed, 1 mA


def signed16(v: int) -> int:
    return v - 65536 if v > 32767 else v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/serial0")
    ap.add_argument("--baud", type=int, default=1_000_000)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--csv", default="current.csv")
    ap.add_argument("--limit-ma", type=int, default=3000)
    ap.add_argument("--burst-s", type=float, default=1.0)
    args = ap.parse_args()

    port = PortHandler(args.port)
    packet = PacketHandler(2.0)
    if not port.openPort() or not port.setBaudRate(args.baud):
        print(f"Cannot open {args.port} at {args.baud}")
        return 2
    reader = GroupSyncRead(port, packet, ADDR_PRESENT_CURRENT, 2)
    for i in IDS:
        reader.addParam(i)

    peak_total, peak_single, over_since, longest_over, samples, failures = 0, (0, 0), None, 0.0, 0, 0
    t0 = time.monotonic()
    with open(args.csv, "w", newline="") as fh:
        out = csv.writer(fh)
        out.writerow(["t_s", "total_ma"] + [f"id{i}_ma" for i in IDS])
        while time.monotonic() - t0 < args.seconds:
            if reader.txRxPacket() != COMM_SUCCESS:
                failures += 1
                if failures > 20:
                    print("Sync Read keeps failing; check the bus with scan_bus.py")
                    return 2
                continue
            now = time.monotonic() - t0
            ma = [abs(signed16(reader.getData(i, ADDR_PRESENT_CURRENT, 2))) for i in IDS]
            total = sum(ma)
            samples += 1
            out.writerow([f"{now:.3f}", total] + ma)
            peak_total = max(peak_total, total)
            top = max(zip(ma, IDS))
            if top[0] > peak_single[0]:
                peak_single = top
            if total > args.limit_ma:
                over_since = now if over_since is None else over_since
                longest_over = max(longest_over, now - over_since)
            else:
                over_since = None
            print(f"\r{now:6.1f} s  total {total:5d} mA  peak {peak_total:5d} mA  longest over {args.limit_ma} mA: {longest_over:4.1f} s",
                  end="", flush=True)
    port.closePort()

    print(f"\n{samples} samples in {args.csv}; peak total {peak_total} mA; highest single servo ID{peak_single[1]} {peak_single[0]} mA")
    if longest_over >= args.burst_s:
        print(f"The total stayed above {args.limit_ma} mA for {longest_over:.1f} s: the OpenRB ports are past their rating. Stop and report.")
        return 1
    print(f"Under {args.limit_ma} mA apart from bursts shorter than {args.burst_s:.1f} s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

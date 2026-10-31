"""Record the XIAO's USB serial until stopped: every non-sample line (status, panic, backtrace) with the Mac time, a
note whenever the firmware clock goes backwards (a reboot), and one summary line a minute. Usage:
  ~/.venvs/touch/bin/python xiao_serial_log.py [port] > log.txt"""
import sys
import time

import serial

port = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbmodem101"
prev_ms, samples, minute = None, 0, time.time()
while True:
    try:
        s = serial.Serial(port, 115200, timeout=0.5)
    except serial.SerialException as e:
        print(time.strftime("%H:%M:%S"), "port:", e, flush=True)
        time.sleep(1.0)
        continue
    try:
        while True:
            raw = s.readline()
            now = time.strftime("%H:%M:%S")
            if not raw:
                continue
            l = raw.decode(errors="replace").rstrip()
            if l.startswith("T,"):
                samples += 1
                try:
                    ms = int(l.split(",")[1])
                except (IndexError, ValueError):
                    ms = None
                if ms is not None and prev_ms is not None and ms < prev_ms:
                    print(now, f"REBOOT: firmware clock {prev_ms} -> {ms} ms", flush=True)
                prev_ms = ms if ms is not None else prev_ms
            elif l.startswith("R,"):
                if time.time() - minute >= 60:
                    print(now, f"{samples} samples in the last minute;", l, flush=True)
                    samples, minute = 0, time.time()
            else:
                print(now, l, flush=True)
    except (serial.SerialException, OSError) as e:  # the XIAO re-enumerates after a reboot
        print(time.strftime("%H:%M:%S"), "port lost:", e, flush=True)
        s.close()
        time.sleep(0.5)

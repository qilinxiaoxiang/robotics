#!/usr/bin/python3
"""MicroDuck power V2 (PS-3): at the end of an A7Z poweroff, pulse header pin 22 high so the Pololu 2813 removes power.

Wire: A7Z header pin 22 (PL5, 3.3 V bank) -> robot-side MR30 pin 3 -> backpack MR30 pin 3 -> 1N4148 -> Pololu OFF
(100 k OFF to GND on the Pololu side). The Pololu switches off on a high OFF; the XIAO cutoff joins the same pin
through its own 1N4148.

Why header pin 22 (PL5):
  - free: the A7Z pin map in bringup/a7z/build_a7z_pages.py (USED) holds 1-7, 9-12, 17, 25, 29, 31, 34, 35, 38-40;
    8 is the debug console; 36 is I2S0-MCLK in Radxa's i2s0 overlay (bringup/a7z/sources/sun60iw2p1-i2s0-2ch.dtso).
  - 3.3 V: the Radxa schematic V1.11 page 14 names it PL5_3V3, and page 4 feeds VCC-PL from ALDO1 3.3 V. The PD pins
    (19, 21, 23, 24, 26) sit on VCC-PD = BLDO2 1.8 V: 1.8 V minus the 1N4148 drop is too little for the OFF input.
  - not a UART: PL6/PL7 (13, 15) and PM3/PM4/PM5 (33, 37, 32) carry S-UART functions and PJ24/PJ25 (16, 18) UART4;
    a UART pin idles high, which would switch the robot off at boot. PL5's functions are S-JTAG-CK, S-TWI2-SDA,
    S-SPI0-CLK, S-PWM0-3 (Radxa "40 Pin GPIO" table, guide/print/a7z-head/sources/radxa-a7z-pin-gpio.md).
  - reachable: edge row next to GND pin 20; the camera-screw blockers are at 9/10 and 31/32.
  Not verified on the board: its level during u-boot. The guide's first power-up checks that the ring stays lit
  through the A7Z boot with the wire in.

Called three ways:
  duck_power_off.py poweroff|halt|reboot|kexec   from the systemd-shutdown hook (argv[1] as systemd passes it).
                                                 Pulses only for poweroff and halt; a reboot must keep the power on.
                                                 By then every filesystem is read-only, so cutting power is safe.
  duck_power_off.py --check                      at boot (duck-power-off-check.service): finds the line, reports
                                                 whether a driver holds it and its level; exit 1 if it cannot be driven.
  duck_power_off.py --dry-run [ACTION]           prints what it would do without touching any GPIO (Mac test).

Line: by name "PL5" when the kernel names its lines, otherwise gpiochip1 offset 5 (Radxa "40 Pin GPIO": GPIOCHIP1
holds banks L and up, number = NUM + 32 * (bank - L), so PL5 = 5). DUCK_OFF_CHIP / DUCK_OFF_LINE override.
Uses python3-libgpiod (v1 or v2 API) and falls back to the gpioset command (libgpiod v1 or v2 tools).
Standard library only otherwise; runs on the read-only root at shutdown.
"""
import os
import subprocess
import sys
import time

HEADER_PIN = 22
LINE_NAME = "PL5"
DEFAULT_CHIP = "gpiochip1"
DEFAULT_OFFSET = 5
PULSE_S = 3.0            # the Pololu acts within milliseconds; still alive after this means the OFF wire is not connected
CONSUMER = "duck-power-off"
CUT_ACTIONS = ("poweroff", "halt")


def say(msg: str) -> None:
    print(f"duck-power-off: {msg}", file=sys.stderr, flush=True)


def target():
    """(chip, offset) from the environment override, or the defaults."""
    chip = os.environ.get("DUCK_OFF_CHIP", DEFAULT_CHIP)
    off = int(os.environ.get("DUCK_OFF_LINE", DEFAULT_OFFSET))
    return chip, off


def chip_path(chip: str) -> str:
    return chip if chip.startswith("/") else f"/dev/{chip}"


def load_gpiod():
    try:
        import gpiod  # noqa: F401
        return gpiod
    except ImportError:
        return None


def api_version(gpiod) -> int:
    """2 for libgpiod >= 2 (request_lines), 1 for the v1 bindings (Chip.get_line)."""
    return 2 if hasattr(gpiod, "request_lines") else 1


def find_by_name_v1(gpiod):
    try:
        line = gpiod.find_line(LINE_NAME)
    except Exception:
        return None
    if line is None:
        return None
    return line.owner().name(), line.offset()


def find_by_name_v2(gpiod):
    for entry in sorted(os.listdir("/dev")) if os.path.isdir("/dev") else []:
        if not entry.startswith("gpiochip"):
            continue
        try:
            with gpiod.Chip(f"/dev/{entry}") as c:
                off = c.line_offset_from_id(LINE_NAME)
                return entry, off
        except Exception:
            continue
    return None


def resolve(gpiod):
    """Chip and offset of the OFF line: environment override, line name, then gpiochip1 offset 5."""
    if "DUCK_OFF_CHIP" in os.environ or "DUCK_OFF_LINE" in os.environ:
        chip, off = target()
        return chip, off, "environment"
    if gpiod is not None:
        hit = find_by_name_v2(gpiod) if api_version(gpiod) == 2 else find_by_name_v1(gpiod)
        if hit:
            return hit[0], hit[1], f"line name {LINE_NAME}"
    return DEFAULT_CHIP, DEFAULT_OFFSET, "Radxa numbering (PL5 = gpiochip1 line 5)"


def pulse_v1(gpiod, chip, off, sleep=time.sleep):
    c = gpiod.Chip(chip)
    line = c.get_line(off)
    line.request(consumer=CONSUMER, type=gpiod.LINE_REQ_DIR_OUT, default_vals=[1])
    sleep(PULSE_S)
    line.set_value(0)
    line.release()


def pulse_v2(gpiod, chip, off, sleep=time.sleep):
    from gpiod.line import Direction, Value
    req = gpiod.request_lines(chip_path(chip), consumer=CONSUMER,
                              config={off: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.ACTIVE)})
    sleep(PULSE_S)
    req.set_value(off, Value.INACTIVE)
    req.release()


def gpioset_cmd(chip, off, run=subprocess.run):
    """gpioset arguments for a PULSE_S high hold, for the installed libgpiod tools version."""
    try:
        ver = run(["gpioset", "--version"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return None
    secs = int(PULSE_S)
    if "v2" in ver or " 2." in ver:
        return ["gpioset", "-c", chip, "-p", f"{secs}s", "-t", "0", f"{off}=1"]
    return ["gpioset", "--mode=time", f"--sec={secs}", chip, f"{off}=1"]


def pulse(gpiod, chip, off, run=subprocess.run, sleep=time.sleep) -> str:
    if gpiod is not None:
        (pulse_v2 if api_version(gpiod) == 2 else pulse_v1)(gpiod, chip, off, sleep)
        return f"python gpiod v{api_version(gpiod)}"
    cmd = gpioset_cmd(chip, off, run)
    if cmd is None:
        raise RuntimeError("neither python3-libgpiod nor gpioset is installed (sudo apt install gpiod python3-libgpiod)")
    run(cmd, check=True)
    return " ".join(cmd)


def check(gpiod) -> int:
    chip, off, how = resolve(gpiod)
    say(f"OFF line: header pin {HEADER_PIN}, {chip} offset {off} ({how})")
    if gpiod is None:
        cmd = gpioset_cmd(chip, off)
        if cmd is None:
            say("FAIL: neither python3-libgpiod nor gpioset is installed (sudo apt install gpiod python3-libgpiod)")
            return 1
        say(f"python3-libgpiod missing; the hook will use: {' '.join(cmd)}")
        return 0
    try:
        if api_version(gpiod) == 2:
            with gpiod.Chip(chip_path(chip)) as c:
                info = c.get_line_info(off)
                used, consumer, name = info.used, info.consumer, info.name
        else:
            line = gpiod.Chip(chip).get_line(off)
            used, consumer, name = line.is_used(), line.consumer(), line.name()
    except Exception as e:  # missing chip or offset
        say(f"FAIL: cannot open {chip} line {off}: {e}")
        return 1
    if used:
        say(f"FAIL: line {name or off} is held by '{consumer}'; a driver owns header pin {HEADER_PIN}")
        return 1
    say(f"ok: line {name or off} free; the shutdown hook can drive it")
    return 0


def main(argv) -> int:
    dry = "--dry-run" in argv
    args = [a for a in argv[1:] if a != "--dry-run"]
    if args[:1] == ["--check"]:
        if dry:
            say("dry run: would look up the OFF line and report whether it is free")
            return 0
        return check(load_gpiod())
    action = args[0] if args else "poweroff"
    if action not in CUT_ACTIONS:
        say(f"{action}: power stays on (only {' and '.join(CUT_ACTIONS)} pulse the OFF line)")
        return 0
    gpiod = None if dry else load_gpiod()
    chip, off, how = resolve(gpiod) if not dry else (*target(), "dry run")
    if dry:
        say(f"dry run: {action}: would drive {chip} line {off} (header pin {HEADER_PIN}) high for {PULSE_S:.0f} s, then low")
        return 0
    say(f"{action}: driving {chip} line {off} (header pin {HEADER_PIN}, {how}) high; the Pololu should cut power now")
    try:
        used = pulse(gpiod, chip, off)
    except Exception as e:
        say(f"FAIL: {e}; the A7Z halts but the backpack stays on: unplug the battery")
        return 0  # never block the shutdown
    say(f"still running {PULSE_S:.0f} s after the pulse ({used}): is the MR30 pin 3 wire to header pin {HEADER_PIN} connected?")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

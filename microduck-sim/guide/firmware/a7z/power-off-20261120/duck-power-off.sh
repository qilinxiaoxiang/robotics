#!/bin/sh
# systemd-shutdown hook (installed from duck-power-off.sh as /usr/lib/systemd/system-shutdown/duck-power-off).
# systemd-shutdown runs every executable in that directory after all filesystems are unmounted or read-only,
# with $1 = halt, poweroff, reboot or kexec (systemd-shutdown(8)). duck_power_off.py pulses header pin 22 for
# poweroff and halt only, so the Pololu 2813 in the backpack switches the robot off (power V2, PS-3).
# DUCK_POWER_OFF_PY lets the Mac test point at the repository copy.
exec /usr/bin/python3 "${DUCK_POWER_OFF_PY:-/usr/local/lib/duck/duck_power_off.py}" "$@"

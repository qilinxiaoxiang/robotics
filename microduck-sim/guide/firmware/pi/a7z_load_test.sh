#!/bin/bash
# A7Z brownout/thermal separation test: full CPU load with the servos untouched.
# Run on the A7Z:  ~/duck/a7z_load_test.sh [seconds]   (default 20)
# Prints boot_id, SoC temperature and CPU clock before, every second during, and after.
# If the board resets, the boot_id after power-up differs and ~/duck-logs/load_test.log
# (fsynced per line) ends mid-run; thermal.log (10 Hz service) covers the same window.
set -u
SECS=${1:-20}
LOG=~/duck-logs/load_test.log
mkdir -p ~/duck-logs
say() { echo "$(date -u +%H:%M:%S.%N | cut -c1-12) $*" | tee -a "$LOG"; sync -d "$LOG" 2>/dev/null || sync; }
temps() { for z in /sys/class/thermal/thermal_zone*/temp; do printf '%s ' "$(( $(cat "$z") / 1000 ))"; done; }
clock() { cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null | awk '{printf "%d", $1/1000}'; }
vin() {  # any PMIC input-voltage reading the kernel exposes (checked 2026-10-21); prints "-" when none
  for p in /sys/class/power_supply/*/voltage_now; do [ -r "$p" ] && printf '%s=%s ' "$(basename "$(dirname "$p")")" "$(cat "$p")"; done; echo "-"
}
say "# load test ${SECS}s boot_id $(cat /proc/sys/kernel/random/boot_id) nproc $(nproc)"
say "before: temps $(temps) MHz $(clock) vin $(vin)"
N=$(nproc)
for i in $(seq "$N"); do ( end=$((SECS + $(date +%s))); while [ "$(date +%s)" -lt "$end" ]; do :; done ) & done
for s in $(seq "$SECS"); do sleep 1; say "t=${s}s temps $(temps) MHz $(clock) vin $(vin) load $(cut -d' ' -f1 /proc/loadavg)"; done
wait
say "after: temps $(temps) MHz $(clock) vin $(vin) boot_id $(cat /proc/sys/kernel/random/boot_id)"
say "# done: same boot_id means no reset"

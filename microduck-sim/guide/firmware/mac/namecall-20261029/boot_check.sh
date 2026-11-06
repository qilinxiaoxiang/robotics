#!/bin/bash
# After a power-on: did the Mochi name response start by itself? Run on the Mac (A7Z_HOST=a7z by default):
#
#   microduck-sim/guide/firmware/mac/namecall-20261029/boot_check.sh
#
# Read-only and bounded (no whole-log parsing on the A7Z). Prints PASS when, in the current boot, the unit is
# enabled and running, systemd reported no ordering cycle, and a namecall.py child is listening.
set -uo pipefail
HOST=${A7Z_HOST:-a7z}
ssh -o ConnectTimeout=5 "$HOST" 'bash -s' <<'EOF'
echo "boot: $(uptime -s) (up $(uptime -p))"
echo "unit: enabled=$(systemctl is-enabled duck-namecall.service 2>&1) $(systemctl show duck-namecall.service -p ActiveState -p SubState -p NRestarts -p ActiveEnterTimestamp | tr '\n' ' ')"
grep -h "^After=" /etc/systemd/system/duck-namecall.service
echo "-- ordering cycles in this boot:"
cycles=$(journalctl -b --no-pager -q -t systemd 2>/dev/null | grep -i "ordering cycle" | tail -5)
echo "${cycles:-(none)}"
echo "-- boot transaction check (systemd-analyze verify default.target):"
vcycle=$(sudo -n systemd-analyze verify default.target 2>&1 | grep -i "ordering cycle" | head -3)
echo "${vcycle:-(none)}"
echo "-- who disabled/stopped it since 2026-11-02 (sudo log):"
journalctl --since 2026-11-02 --no-pager -q _COMM=sudo 2>/dev/null | grep -i -E "namecall|systemctl (disable|stop|mask)" | tail -8 || true
echo "-- processes:"
pgrep -a -f "namecall_boot.py|namecall.py" | cut -c1-160
echo "-- last supervisor records:"
tail -n 6 ~/duck-logs/namecall_boot.jsonl 2>/dev/null
ok=1
[ "$(systemctl is-enabled duck-namecall.service 2>/dev/null)" = enabled ] || ok=0
[ "$(systemctl is-active duck-namecall.service 2>/dev/null)" = active ] || ok=0
[ -z "$cycles$vcycle" ] || ok=0
pgrep -f "namecall.py --name" >/dev/null || ok=0
[ $ok = 1 ] && echo "PASS: name response started by itself in this boot" || echo "FAIL: see above"
EOF

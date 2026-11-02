#!/bin/bash
# 10 right-spin starts with a left spin after each to keep the heading, counting camera drops; the full flow if none.
cd ~/rt/microduck-sim/guide/firmware/mac
P=~/.venvs/duck-policy/bin/python
n0=$(sudo -n dmesg | grep -c "usb 1-1: USB disconnect")
drops=0
for i in 1 2 3 4 5 6 7 8 9 10; do
  timeout -s INT 8 $P -u turn_test.py --vx 0 --vtheta -0.5 --secs 1.6 > /dev/null 2>&1
  sleep 1.5
  n=$(sudo -n dmesg | grep -c "usb 1-1: USB disconnect")
  if [ "$n" != "$n0" ]; then drops=1; echo "camera dropped on right start $i"; break; fi
  timeout -s INT 8 $P -u turn_test.py --vx 0 --vtheta 0.5 --secs 1.6 > /dev/null 2>&1
  sleep 1.5
done
echo "right starts done, drops $drops, camera on bus $(lsusb | grep -c 0c45)"
[ "$drops" = 0 ] || exit 0
timeout -s INT 170 $P -u seepick.py --color orange --t2 --hsv-lo 170,50,150 --hsv-hi 18,255,255 --tries 3 > /tmp/t2run7.out 2>&1 < /dev/null
grep -v "seen x" /tmp/t2run7.out | cut -c1-170 | tail -n 45
tail -n 2 ~/duck-logs/duck_wired_log_t2c1101.jsonl | head -n 1 | python3 -c "import json,sys; r=json.loads(sys.stdin.read()); print(r['mode'],r.get('policy'),[round(x,3) for x in r['gb']],r['torque'],'neck',r['q'][11],'t',r['t'])"
echo "camera on bus $(lsusb | grep -c 0c45)"

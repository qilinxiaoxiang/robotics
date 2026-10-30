#!/bin/bash
# Play every rendered duck call of namecall's QuackBank (/tmp/namecall_calls, made by any namecall.py run with sound)
# through the head speaker while the three head microphones record, so the name spotter can be trained to ignore its
# own voice as the microphones hear it (2026-10-30: played quacks were recognised as "Mochi" and the duck answered
# itself). The robot does not move. Stops a running namecall.py first (one reader on the card). Run on the A7Z:
#   ~/rt/microduck-sim/guide/firmware/mac/namecall-20261029/record_own_quacks.sh
# Output: ~/duck-logs/own_quacks_<HHMMSS>.raw (S32_LE, 4 ch, 48 kHz) and .txt (file, start offset s in the raw).
set -u
pkill -f "^/home/radxa/.venvs/duck-policy/bin/python namecall.py" && sleep 1
[ -e /proc/asound/sndi2s0 ] || { echo "no sndi2s0 capture card"; exit 1; }
dev="hw:CARD=sndi2s0,DEV=0"
# The sunxi I2S driver silences a running capture when a playback stream STARTS (namecall.py docstring): keep one
# silent playback stream open on the default device (dmix) for the whole run, as namecall's PlaybackKeepAlive does, so
# each quack mixes into it and the microphones stay live (the first run without it recorded -140 dBFS after quack 1).
aplay -q -t raw -f S16_LE -c 2 -r 48000 /dev/zero & keep=$!
sleep 0.3
stamp=$(date +%H%M%S); raw="$HOME/duck-logs/own_quacks_$stamp.raw"; idx="$HOME/duck-logs/own_quacks_$stamp.txt"
: > "$idx"
arecord -q -D "$dev" -c 4 -r 48000 -f S32_LE -t raw "$raw" & rec=$!
t0=$(date +%s.%N); sleep 1.5
for f in /tmp/namecall_calls/*.wav; do
  echo "$(basename "$f") $(echo "$(date +%s.%N) - $t0" | bc)" >> "$idx"
  aplay -q "$f"; sleep 1.2
done
sleep 1.5; kill $rec; wait $rec 2>/dev/null; kill $keep; wait $keep 2>/dev/null
echo "recorded $(wc -l < "$idx") calls into $raw"

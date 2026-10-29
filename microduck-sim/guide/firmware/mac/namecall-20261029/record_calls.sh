#!/bin/bash
# Record the three head microphones (4-channel raw I2S0 stream) for a direction / wake-word check. The robot does not
# move. Run from the Mac:  ssh a7z '~/rt/microduck-sim/guide/firmware/mac/namecall-20261029/record_calls.sh [seconds]'
# Stops a running namecall.py first (one reader on the card). Output: ~/duck-logs/calls_<HHMMSS>.wav (S32_LE 48 kHz,
# ch0 left ear, ch1 right ear, ch2 back mic, ch3 empty; CURRENT-STATE a7z_audio_capture).
secs=${1:-60}
pkill -f "^/home/radxa/.venvs/duck-policy/bin/python namecall.py" && sleep 1
out="$HOME/duck-logs/calls_$(date +%H%M%S).wav"
dev=$(arecord -l | awk -F'[ :]' '/sndi2s0/ {print "hw:" $2 ",0"; exit}')
[ -n "$dev" ] || { echo "no sndi2s0 capture card"; exit 1; }
echo "开始录音 ${secs} 秒（$(date +%H:%M:%S)），按顺序叫 Mochi"
arecord -q -D "$dev" -c 4 -r 48000 -f S32_LE -d "$secs" "$out"
echo "录完了: $out"

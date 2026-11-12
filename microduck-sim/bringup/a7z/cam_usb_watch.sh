#!/bin/bash
# Live view: where is the U20CAM (0c45:6367) seen, on the A7Z or on this Mac?
# Prints a line whenever either status changes, plus every A7Z kernel USB event.
ssh -o LogLevel=ERROR a7z 'sudo -n journalctl -kf -n 0 -o short | grep --line-buffered -iE "usb [12]-|usb1-port|uvc|over-?current" | sed -u "s/^/  [A7Z 内核] /"' &
k=$!
trap 'kill $k 2>/dev/null' EXIT
la=""; lm=""
while true; do
  if timeout 5 ssh -o LogLevel=ERROR a7z 'lsusb | grep -q 0c45:6367'; then a="A7Z: 摄像头已识别 OK"; else a="A7Z: 未识别"; fi
  if ioreg -p IOUSB -l -w0 2>/dev/null | grep -q '"idProduct" = 25447'; then m="Mac: 摄像头已识别 OK"; else m="Mac: 未识别"; fi
  if [ "$a" != "$la" ] || [ "$m" != "$lm" ]; then echo "$(date +%H:%M:%S)  $a   |   $m"; la="$a"; lm="$m"; fi
  sleep 1
done

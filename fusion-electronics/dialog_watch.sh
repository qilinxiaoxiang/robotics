#!/bin/sh
# Print one line whenever Fusion shows a new dialog window, with a screenshot path; print
# "fusion dialogs cleared" when they go. Run it under a Monitor for the whole Fusion session.
# If Fusion's windows cannot be read (Fusion closed, no Automation access) it says so once
# instead of staying silent, since silence would read as "no dialogs".
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/lib.sh"
prev=""; blind=0
while true; do
  if [ -z "$(fusion_windows)" ]; then
    [ $blind -eq 0 ] && echo "FUSION WINDOWS UNREADABLE: Fusion not running or no System Events access; dialogs cannot be seen"
    blind=1; sleep 5; continue
  fi
  [ $blind -eq 1 ] && echo "fusion windows readable again"; blind=0
  w=$(fusion_dialog_names | sort | tr '\n' '|')
  if [ -n "$w" ] && [ "$w" != "$prev" ]; then
    echo "FUSION DIALOG: [$w] screenshot $(fusion_shot dialog)"
  elif [ -z "$w" ] && [ -n "$prev" ]; then
    echo "fusion dialogs cleared"
  fi
  prev="$w"
  sleep 2
done

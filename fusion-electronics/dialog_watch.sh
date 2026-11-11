#!/bin/sh
# Print one line whenever Fusion shows a new dialog window, with a screenshot path; print
# "fusion dialogs cleared" when they go. Run it under a Monitor for the whole Fusion session.
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/lib.sh"
prev=""
while true; do
  w=$(fusion_dialog_names | sort | tr '\n' '|')
  if [ -n "$w" ] && [ "$w" != "$prev" ]; then
    echo "FUSION DIALOG: [$w] screenshot $(fusion_shot dialog)"
  elif [ -z "$w" ] && [ -n "$prev" ]; then
    echo "fusion dialogs cleared"
  fi
  prev="$w"
  sleep 2
done

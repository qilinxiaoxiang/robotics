#!/bin/sh
# Send a Python file to the Fusion ClaudeBridge add-in (127.0.0.1:8777) and print the JSON result.
# The code runs on Fusion's main thread with `app`, `ui` and `adsk` defined.
# Guards:
#  1. Refuse EAGLE ADD commands without an exact "name@library" (a bare ADD opens a modal picker).
#  2. Refuse to run while Fusion shows any dialog; fail loudly if one appears afterwards
#     (Fusion raises assert dialogs a few seconds after the call returns).
#  3. A call stuck for more than 10 s is almost always a modal dialog: screenshot and exit 5.
# Exit codes: 0 ok, 2 bare ADD, 3 dialog before, 4 dialog after, 5 stuck.
# Screenshots go to $FUSION_SHOT_DIR (default ${TMPDIR:-/tmp}/fusion-shots).
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/lib.sh"
if grep -E "ADD +[^;'\"]*" "$1" | grep -vq '@'; then
  echo '{"ok": false, "error": "guard: ADD without name@library opens a modal picker; use exact names"}'; exit 2
fi
n=$(fusion_dialog_count)
if [ "${n:-0}" -gt 0 ]; then
  echo "{\"ok\": false, \"error\": \"guard: Fusion already shows $n dialog window(s); inspect and close before sending code\"}"; exit 3
fi
curl -s --max-time "${FX_TIMEOUT:-10}" -X POST --data-binary @"$1" http://127.0.0.1:8777/
rc=$?
if [ $rc -eq 28 ]; then
  f=$(fusion_shot stuck)
  echo; echo "{\"ok\": false, \"error\": \"guard: bridge call exceeded ${FX_TIMEOUT:-10} s; screenshot $f\"}"; exit 5
fi
sleep 3
n=$(fusion_dialog_count)
if [ "${n:-0}" -gt 0 ]; then
  f=$(fusion_shot dialog)
  echo; echo "{\"ok\": false, \"error\": \"guard: Fusion opened $n dialog window(s) during this call; screenshot $f\"}"; exit 4
fi
exit $rc

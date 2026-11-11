# Shell helpers for dialog_watch.sh. The bridge client and data commands are in fusion.py.
# Fusion's main window title contains "Autodesk Fusion"; docked palettes have fixed names.
# Every other window (including untitled ones, which report an empty name) is a dialog.
FUSION_SHOT_DIR=${FUSION_SHOT_DIR:-${TMPDIR:-/tmp}/fusion-shots}

fusion_windows() {
  osascript -e 'tell application "System Events" to tell (first process whose name is "Autodesk Fusion") to get name of every window' 2>/dev/null
}
fusion_dialog_names() {   # one line per dialog: name;subrole;WxH (to tell short-lived windows from modals)
  osascript -e 'set out to ""' \
    -e 'tell application "System Events" to tell (first process whose name is "Autodesk Fusion")' \
    -e 'repeat with w in every window' \
    -e 'set out to out & (name of w) & ";" & (subrole of w) & ";" & (item 1 of (size of w as list)) & "x" & (item 2 of (size of w as list)) & linefeed' \
    -e 'end repeat' -e 'end tell' -e 'return out' 2>/dev/null \
    | grep -v '^$' | grep -vE "^(.*Autodesk Fusion.*|BROWSER|SHEETS|TEXT COMMANDS|COMMENTS|PLACE COMPONENTS|INSPECTOR);" | sed 's/^;/<untitled>;/'
}
fusion_shot() {   # fusion_shot <tag> -> prints the screenshot path
  mkdir -p "$FUSION_SHOT_DIR"
  f="$FUSION_SHOT_DIR/$1-$(date +%H%M%S).png"
  screencapture -x "$f" 2>/dev/null && sips -Z 1400 "$f" >/dev/null 2>&1
  echo "$f"
}

# Shared shell helpers for the Fusion tools. Source with: . "$HERE/lib.sh"
# Fusion's main window title contains "Autodesk Fusion"; docked palettes have fixed names.
# Every other window (including untitled ones, which report an empty name) is a dialog.
FUSION_PALETTES='^(.*Autodesk Fusion.*|BROWSER|SHEETS|TEXT COMMANDS|COMMENTS|PLACE COMPONENTS|INSPECTOR)$'
FUSION_SHOT_DIR=${FUSION_SHOT_DIR:-${TMPDIR:-/tmp}/fusion-shots}

fusion_windows() {
  osascript -e 'tell application "System Events" to tell (first process whose name is "Autodesk Fusion") to get name of every window' 2>/dev/null
}
fusion_dialog_names() {   # one line per dialog: name;subrole;WxH (used to tell toasts from modals)
  osascript -e 'set out to ""' \
    -e 'tell application "System Events" to tell (first process whose name is "Autodesk Fusion")' \
    -e 'repeat with w in every window' \
    -e 'set out to out & (name of w) & ";" & (subrole of w) & ";" & (item 1 of (size of w as list)) & "x" & (item 2 of (size of w as list)) & linefeed' \
    -e 'end repeat' -e 'end tell' -e 'return out' 2>/dev/null \
    | grep -v '^$' | grep -vE "^(.*Autodesk Fusion.*|BROWSER|SHEETS|TEXT COMMANDS|COMMENTS|PLACE COMPONENTS|INSPECTOR);" | sed 's/^;/<untitled>;/'
}
fusion_dialog_count() {
  fusion_windows | tr ',' '\n' | sed 's/^ //' | grep -vEc "$FUSION_PALETTES"
}
fusion_shot() {   # fusion_shot <tag> -> prints the screenshot path
  mkdir -p "$FUSION_SHOT_DIR"
  f="$FUSION_SHOT_DIR/$1-$(date +%H%M%S).png"
  screencapture -x "$f" 2>/dev/null && sips -Z 1400 "$f" >/dev/null 2>&1
  echo "$f"
}
# Pressing a key needs Fusion frontmost, which steals the user's focus. Use only for the
# Upload Options dialog that uploadFile always raises; never as a generic dialog closer.
fusion_key() {
  osascript -e 'tell application "System Events" to tell (first process whose name is "Autodesk Fusion")' \
    -e 'set frontmost to true' -e 'delay 0.3' -e "key code $1" -e 'end tell'
}

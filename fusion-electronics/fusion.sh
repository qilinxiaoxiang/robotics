#!/bin/sh
# Fusion data operations through the bridge, for the folder named by FUSION_PROJECT + FUSION_PATH.
#   fusion.sh ls
#   fusion.sh rename NAME NEW
#   fusion.sh delete NAME            # electronics design (.fprj parent first, then children)
#   fusion.sh delete-folder NAME     # subfolder and every design in it
#   fusion.sh import FILE.sch [--replace]
#       Upload an EAGLE .sch as an electronics design named after the file. PASS only when no
#       Fusion "Error" window appears and NAME.fsch exists. Without --replace an existing design of
#       that name is refused; with --replace the old one is renamed aside, the new one imported,
#       and the old one deleted only after the import passed.
#   fusion.sh image NAME OUT.png [DPI]   # open the schematic, export the full sheet (off-screen)
#   fusion.sh run JOB.py             # any bridge code, with the guards of fx.sh
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/lib.sh"
TMP=${TMPDIR:-/tmp}/fusion-jobs; mkdir -p "$TMP"
job() { t="$1"; shift; python3 "$HERE/job.py" "$HERE/jobs/$t.py" "$TMP/$t.py" "$@" || exit 2; sh "$HERE/fx.sh" "$TMP/$t.py"; }
names() { job ls | python3 -c 'import sys,json; r=json.loads(sys.stdin.read().split("\n")[0]); print(r["out"] if r.get("ok") else "ERR "+r.get("error",""))'; }
cmd="$1"; shift
case "$cmd" in
  ls) job ls;;
  rename) job rename "NAME=$1" "NEW=$2";;
  delete) job delete "NAME=$1" "KIND=design";;
  delete-folder) job delete "NAME=$1" "KIND=folder";;
  run) sh "$HERE/fx.sh" "$1";;
  image) FX_TIMEOUT=60 job image "NAME=$1" "OUT=$2" "DPI=${3:-150}";;
  import)
    SCH="$1"; NAME=$(basename "$SCH" .sch); MODE="$2"
    case "$SCH" in /*) ;; *) echo "import needs an absolute path"; exit 2;; esac
    existing=$(names)
    case "$existing" in ERR*) echo "$existing"; exit 1;; esac
    case "$existing" in
      *"\"$NAME.fsch\""*)
        [ "$MODE" = "--replace" ] || { echo "FAIL: design $NAME already exists; pass --replace"; exit 6; }
        OLD="${NAME}__replaced_$(date +%Y%m%d%H%M%S)"
        job rename "NAME=$NAME" "NEW=$OLD" >/dev/null || { echo "FAIL: could not rename old $NAME"; exit 1; };;
    esac
    python3 "$HERE/job.py" "$HERE/jobs/upload.py" "$TMP/upload.py" "FILE=$SCH" "CREATE=yes" || exit 2
    curl -s --max-time 30 -X POST --data-binary @"$TMP/upload.py" http://127.0.0.1:8777/ >/dev/null &
    i=0
    while [ $i -lt 30 ]; do   # uploadFile always raises an untitled "Upload Options" dialog: confirm it
      sleep 1; i=$((i+1))
      case "$(fusion_windows)" in ,*|*", ,"*) fusion_key 36; break;; esac
    done
    i=0
    while [ $i -lt 40 ]; do
      sleep 1; i=$((i+1))
      case "$(fusion_windows)" in
        *Error*) f=$(fusion_shot import-error); fusion_key 36
                 echo "FAIL: Fusion reported an import error for $NAME (screenshot $f)"
                 [ -n "$OLD" ] && job rename "NAME=$OLD" "NEW=$NAME" >/dev/null && echo "old design restored as $NAME"
                 exit 1;;
      esac
      case "$(names)" in
        *"\"$NAME.fsch\""*)
          echo "PASS: $NAME imported"
          if [ -n "$OLD" ]; then job delete "NAME=$OLD" "KIND=design" | head -1; fi
          exit 0;;
      esac
    done
    echo "FAIL: no $NAME.fsch after 40 s and no error window seen"; exit 1;;
  *) sed -n '2,14p' "$0"; exit 2;;
esac

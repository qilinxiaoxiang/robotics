#!/bin/zsh
# Copy the drawn-pack visual manifest (sim/out/visual/flightpack-nominal.json, the sim agent's pack_visual.py output)
# and the CAD world STLs it names into the training mirror on the Mac mini, so flight_video.py can draw the pack there.
# Read-only use of the sim agent's files; nothing in sim/ is changed.
set -e
SIMROOT=/Users/xiangzheng/code/robotics/microduck-sim
VIS=extensions/flight-20261110/sim/out/visual/flightpack-nominal.json
REMOTE=code/flight-train-mirror/robotics/microduck-sim
LIST=/private/tmp/claude-501/-Users-xiangzheng-code-robotics/f1c031c9-315e-4562-8a86-dcbcac4d6fa0/scratchpad/pack_visual_files.txt
python3 - "$SIMROOT" "$VIS" "$LIST" <<'EOF'
import json, sys
from pathlib import Path
root, vis, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
d = json.loads((root / vis).read_text())
files = [vis] + sorted({p["file"] for p in d.get("visual_parts", [])})
missing = [f for f in files if not (root / f).exists()]
assert not missing, missing
Path(out).write_text("\n".join(files) + "\n")
print(f"pack visual: {len(files)} files")
EOF
rsync -a --files-from=$LIST $SIMROOT/ mac-mini:$REMOTE/

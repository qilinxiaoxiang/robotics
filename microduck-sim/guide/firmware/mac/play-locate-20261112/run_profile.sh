#!/bin/bash
# Mac mini: stance-phase profile of the tilt gap, robot 2026-11-11 and 11-02..06 against the sim replays.
cd "$(dirname "$0")"
PY="$HOME/.venvs/microduck-dyn/bin/python"
R="$HOME/duck-walks/raw"
"$PY" stance_profile.py --out prof-robot-1111.json "$R"/duck_wired_log_app1111-*.jsonl > prof-robot-1111.txt 2>&1 &
"$PY" stance_profile.py --out prof-robot-1102-06.json "$R"/duck_wired_log_app110[2-6]-*.jsonl > prof-robot-1102-06.txt 2>&1 &
"$PY" stance_profile.py --out prof-sim.json "$HOME"/duck-walks/scorecard-auto/*-walk*.seed0.ticks.jsonl > prof-sim.txt 2>&1 &
wait
"$PY" - <<'EOF'
import json
for f in ("prof-robot-1111", "prof-robot-1102-06", "prof-sim"):
    d = json.load(open(f + ".json"))
    print("==", f, d["runs"])
    for s, bins in d["profile"].items():
        print("  ", s, "pitch mean by phase", [b["pitch_mean"] for b in bins], "sd", [b["pitch_sd"] for b in bins])
        print("  ", s, "roll  mean by phase", [b["roll_mean"] for b in bins], "sd", [b["roll_sd"] for b in bins])
EOF

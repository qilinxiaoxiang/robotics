"""Round 2, check B (2026-11-18): why do the students of teacher A-999 fall in the runtime simulation where the teacher
does not? The two selection cases the students fail (ts2_pick.py: COM x +10 mm walk, walking shove 0.5 N s; 20
episodes, seeds as in selection) with one thing changed per tag.

  python3 train/ts2_bcheck.py <models dir under train/ckpt> <tag> [<tag> ...]

Tags: base | privnopack | privload | privzero   (teacher: its privileged inputs replaced, flight_eval FLIGHT_PRIV_FIX)
      nodrop | sdelay0 | adelay0                  (the ts_sep.py switches toward the training env)
      hand100 | hand250                           (student: teacher A-999 drives the first 2 s / 5 s, then released)
Result files eval/bc_<dir>_<case>_<tag>.json (existing files are reused) and one row per dir and tag in
out/ts2_bcheck.json.
"""
import json
import subprocess
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
TEACHER = "train/ckpt/ts2a999_teacher/teacher.onnx"
TAGS = {
    "base": ("", ""),
    "privnopack": ("FLIGHT_PRIV_FIX=nopack ", ""),
    "privload": ("FLIGHT_PRIV_FIX=loadonly ", ""),
    "privzero": ("FLIGHT_PRIV_FIX=zero ", ""),
    "nodrop": ("", "--drop 0"),
    "sdelay0": ("", "--sensor-delay 0"),
    "adelay0": ("", "--action-delay 0"),
    "hand100": (f"FLIGHT_HANDOVER={TEACHER}:100 ", ""),
    "hand250": (f"FLIGHT_HANDOVER={TEACHER}:250 ", ""),
}
CASES = [("comx", "comx+10", ""), ("shove", "nominal", "--shove-ns 0.5 --shove-at 8")]
models, tags = sys.argv[1], sys.argv[2:]
mini = str(TRAIN / "mini.sh")
todo = [(t, c) for t in tags for c in CASES if not (TRAIN / f"eval/bc_{models}_{c[0]}_{t}.json").exists()]
if todo:
    subprocess.run(["zsh", mini, "push"], check=True, capture_output=True)
    for i in range(0, len(todo), 6):
        cmd = "; ".join(
            f"{TAGS[t][0]}$PY train/flight_eval.py --models train/ckpt/{models} --manifest train/manifests/flightpack-{man}.json "
            f"--case walk --episodes 20 --workers 8 {flags} --extra='{('--stand-s 0 ' + TAGS[t][1]).strip()}' "
            f"--out train/eval/bc_{models}_{name}_{t}.json > /dev/null 2> train/eval/bc_{models}_{name}_{t}.err; echo done {name} {t}"
            for t, (name, man, flags) in todo[i:i + 6])
        r = subprocess.run(["zsh", mini, "run", cmd], capture_output=True, text=True)
        print(r.stdout.replace("busy\n", "").strip()[-300:].replace("\n", " "), r.stderr.strip()[-300:], flush=True)
        subprocess.run(["zsh", mini, "pull"], check=True, capture_output=True)
out_p = TRAIN / "out/ts2_bcheck.json"
out = json.loads(out_p.read_text()) if out_p.exists() else {}
for t in tags:
    row, parts = {}, []
    for name, _, _ in CASES:
        p = TRAIN / f"eval/bc_{models}_{name}_{t}.json"
        if not p.exists():
            parts.append(f"{name} missing")
            continue
        s = json.loads(p.read_text())["summary"]
        row[name] = dict(falls_of_20=s["falls"], fall_times=[round(x, 1) for x in s["fall_times"]],
                         speed=s["speed_median_upright"], file=f"eval/{p.name}")
        parts.append(f"{name} {s['falls']}/20 (speed {s['speed_median_upright']}, first falls {row[name]['fall_times'][:4]})")
    out.setdefault(models, {})[t] = row
    print(f"{models} {t}: " + "; ".join(parts), flush=True)
out_p.write_text(json.dumps(out, indent=1))

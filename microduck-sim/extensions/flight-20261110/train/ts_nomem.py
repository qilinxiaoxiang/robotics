"""No-memory control of TEACHER-STUDENT-PLAN.md section 7: a recurrent student with its state held at zero.

  python3 train/ts_nomem.py <models dir under train/ckpt> [<models dir> ...]

Per load (none, 50 %, batteries out, full pack): the acceptance walk (20 s, seeds 0..19) through style_eval.py on the
Mac mini with --hist-repeat (the stateful session passes a zero state at every policy call). Result files
eval/un_<dir>_walk_<load>.json; printed next to the same case with the state carried (eval/ua_<dir>_<case>.json).
"""
import json
import subprocess
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
LOADS = (("none", "none", "", "nopack_walk"), ("load050", "load050", "--stand-s 0", "load050_walk"),
         ("nobatt", "nobatt", "--stand-s 0", "nobatt_walk"), ("load100", "load100", "--stand-s 0", "load100_walk"))

mini = str(TRAIN / "mini.sh")
subprocess.run(["zsh", mini, "push"], check=True, capture_output=True)
for m in sys.argv[1:]:
    todo = [(n, man, ex) for n, man, ex, _ in LOADS if not (TRAIN / f"eval/un_{m}_walk_{n}.json").exists()]
    if todo:
        cmd = "; ".join(
            f"$PY train/style_eval.py --name un_{m}_walk_{n} --models train/ckpt/{m} "
            f"--manifest train/manifests/flightpack-{man}.json --case walk --episodes 20 --workers 8 --seed0 0 --hist-repeat "
            + (f"--extra='{ex}' " if ex else "") + f"--out train/eval/un_{m}_walk_{n}.json > /dev/null 2>&1; echo done {n}"
            for n, man, ex in todo)
        r = subprocess.run(["zsh", mini, "run", cmd], capture_output=True, text=True)
        print(m, r.stdout.replace("busy\n", "").strip()[-300:], flush=True)
        subprocess.run(["zsh", mini, "pull"], check=True, capture_output=True)
    for n, _, _, case in LOADS:
        z, c = TRAIN / f"eval/un_{m}_walk_{n}.json", TRAIN / f"eval/ua_{m}_{case}.json"
        zs = json.loads(z.read_text())["summary"] if z.exists() else None
        cs = json.loads(c.read_text())["summary"] if c.exists() else None
        print(f"{m} {n}: state zero falls {zs and zs['falls']}/20 at {zs and zs.get('speed_median_upright')} m/s; "
              f"state carried falls {cs and cs['falls']}/20 at {cs and cs.get('speed_median_upright')} m/s", flush=True)

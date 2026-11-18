"""Teacher gate table (TEACHER-STUDENT-PLAN.md section 6): out/teval_<name>_<load>.json -> out/ts_gate.json.
Per checkpoint and load, the intended walk alone in the teacher env (128 envs x 500 steps, training randomization):
falls per env-minute, speed along the command (m/s), torque-margin cost per second. t<iter> = teacher, c<iter> = the
one-frame control at the same iteration, start = the start policy."""
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
rows = {}
for p in sorted(OUT.glob("teval_*_*.json")):
    m = re.match(r"teval_(.+)_(full|nobatt|none)\.json", p.name)
    r = list(json.loads(p.read_text())["results"].values())[0]
    it = next(v for k, v in r.items() if k.endswith("intended"))
    rows.setdefault(m.group(1), {})[m.group(2)] = dict(falls_per_env_min=it["falls_per_env_minute"], speed=it["speed_along_cmd"],
                                                       low_cmd_speed=it.get("low_cmd_speed"),
                                                       torque_margin_per_s=round(it["terms_per_s"]["torque_margin"], 4),
                                                       reward_per_s=it["reward_per_s"])
(OUT / "ts_gate.json").write_text(json.dumps(rows, indent=1))


def key(n):
    d = re.sub(r"\D", "", n)
    return (int(d) if d else -1, n)


for n in sorted(rows, key=key):
    print(f"{n:8s}", "  ".join(f"{ld}: {v['falls_per_env_min']:.3f} falls/min, {v['speed']:.3f} m/s, tq {v['torque_margin_per_s']}"
                               for ld, v in rows[n].items()))

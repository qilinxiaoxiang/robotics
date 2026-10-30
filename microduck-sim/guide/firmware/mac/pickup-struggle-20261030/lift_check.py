"""Read a lift test from a walk_wired tick log (copied to the Mac): per 0.1 s, the hand (e), hold authority s, leg gain,
landed, leg current, the largest leg action, body gravity z and mode; plus every change of landed / mode.

  python3 lift_check.py <log.jsonl> [t_from] [t_to]
"""
import json
import sys
import time

path = sys.argv[1]
t_from = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
t_to = float(sys.argv[3]) if len(sys.argv) > 3 else 1e12
last_bucket, last_key = None, None
for line in open(path):
    try:
        r = json.loads(line)
    except ValueError:
        continue
    t = r.get("t")
    if t is None or t < t_from or t > t_to:
        continue
    h = r.get("hold") or {}
    a = r.get("action") or []
    legs = [abs(v) for i, v in enumerate(a) if i < 10]
    gb = r.get("gb") or [None] * 3
    key = (h.get("landed"), r.get("mode"), (h.get("s") or 0) > 0.5)
    bucket = int(t * 10)
    if bucket == last_bucket and key == last_key:
        continue
    last_bucket = bucket
    mark = " <-" if key != last_key else ""
    last_key = key
    print(f"{time.strftime('%H:%M:%S', time.localtime(t))}.{int(t % 1 * 100):02d} e={h.get('e')} cov={h.get('cov')} "
          f"load={h.get('load')} s={h.get('s')} kp_leg={h.get('kp_leg')} landed={h.get('landed')} "
          f"legs_ma={r.get('legs_ma')} amax={max(legs) if legs else None:.2f} gbz={gb[2]} mode={r.get('mode')}{mark}"
          if legs else
          f"{time.strftime('%H:%M:%S', time.localtime(t))}.{int(t % 1 * 100):02d} e={h.get('e')} s={h.get('s')} "
          f"kp_leg={h.get('kp_leg')} landed={h.get('landed')} legs_ma={r.get('legs_ma')} amax=- gbz={gb[2]} "
          f"mode={r.get('mode')}{mark}")

"""spk2 lateral-miss diagnosis: per-file means of the runtime-sim pickup probe at the close step (accept_seepick.py /
pk_* eval files): pad and object in the foot frame, the policy's item slots, object minus pad, goal clamp ticks per
joint, camera deliveries. python3 train/spk2diag_eval_table.py eval/pk_a.json eval/pk_b.json ..."""
import json
import statistics as st
import sys
from pathlib import Path


def m(v):
    v = [x for x in v if x is not None]
    return round(st.mean(v), 4) if v else None


def sd(v):
    v = [x for x in v if x is not None]
    return round(st.pstdev(v), 4) if len(v) > 1 else None


for f in sys.argv[1:]:
    d = json.loads(Path(f).read_text())
    rows = []
    clamp = {}
    for e in d["episodes"]:
        p = e.get("probe", {}).get("seepick", {})
        ev = p.get("events", {})
        c = ev.get("close_at") or {}
        if not c:
            continue
        rows.append(dict(held=bool(ev.get("first_holding_bit_t") is not None), fell=e.get("fell_at") is not None,
                         pad_fy=c["pad_foot_xy"][1], obj_fy=c["object_foot_xy"][1], slot_y=c["body_slots"][1],
                         slot_x=c["body_slots"][0], obj_fx=c["object_foot_xy"][0], pad_fx=c["pad_foot_xy"][0],
                         rel_y=c["object_rel_pad_xy"][1], rel_x=c["object_rel_pad_xy"][0],
                         pad_r0y=c["pad_root0_xy"][1], t=c["t_from_switch"],
                         lastvis=p["camera"].get("last_visible_from_switch_s"), vis=p["camera"].get("visible"),
                         tilt=c.get("tilt")))
        for j, n in (ev.get("goal_clamped_ticks") or {}).items():
            clamp[j] = clamp.get(j, 0) + n
    k = lambda key: m([r[key] for r in rows])  # noqa: E731
    print(f"{Path(f).stem}: n {len(rows)} held {sum(r['held'] for r in rows)} falls {sum(r['fell'] for r in rows)} | "
          f"at close (t {k('t')} s): pad foot ({k('pad_fx')}, {k('pad_fy')}) object foot ({k('obj_fx')}, {k('obj_fy')}) "
          f"slots ({k('slot_x')}, {k('slot_y')}) obj-pad ({k('rel_x')}, {k('rel_y')} sd {sd([r['rel_y'] for r in rows])}) "
          f"pad root0 y {k('pad_r0y')} (trunk drift y ~ pad root0 y - pad foot y "
          f"{m([r['pad_r0y'] - r['pad_fy'] for r in rows])}) | slot y - object foot y {m([r['slot_y'] - r['obj_fy'] for r in rows])} | "
          f"camera visible {k('vis')} last visible {k('lastvis')} s | tilt {k('tilt')}")
    print("   goal clamp ticks (sum over episodes):", dict(sorted(clamp.items(), key=lambda kv: -kv[1])))

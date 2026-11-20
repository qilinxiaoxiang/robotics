"""One line per case of a grid result: offset, pass, why not, seated pad centre and yaw, clearances."""
import json, sys
from collections import defaultdict

rows = [json.loads(l) for l in open(sys.argv[1])]
key = lambda r: (r["case"]["concept"], json.dumps(r["case"].get("params"), sort_keys=True), r["case"].get("mu_rail", .35),
                 r["case"].get("floor_mu", 1.0), r["case"]["off"][2], r["case"]["off"][0], r["case"]["off"][1], r["case"]["seed"])
rows.sort(key=key)
last = None
for r in rows:
    c = r["case"]
    head = (c["concept"], json.dumps(c.get("params"), sort_keys=True), c.get("mu_rail", .35), c.get("floor_mu", 1.0))
    if head != last:
        print("\n##", *head); last = head
    if "error" in r:
        print(c["off"], c["seed"], "ERROR", r["error"][-300:]); continue
    why = []
    for k in ("plus", "minus"):
        p = r["pads"][k]
        if not p["ok"]:
            why.append(f"{k[0]}:" + ",".join(w for w, bad in (("x", p["x_margin"] < .5), ("y", p["y_overlap_own"] < 1),
                                                         ("short", p["y_overlap_other"] > 0), ("lift", p["compression"] < 1)) if bad))
    if r["fell_before_unsit"]: why.append("fell")
    cl = r["clearance_mm"]
    if not r["rail_clear_ok"]:
        why.append("rail-touch " + " ".join(f"{ph}:{min(v['rails_legs'], v['rails_trunk']):.1f}" for ph, v in cl.items() if ph != 'after'))
    pc = r["seated_pad_centre_D"]
    print(f"off {str(c['off']):14s} s{c['seed']} {'PASS' if r['pass_'] else 'fail'}  pad c ({pc[0]:7.2f},{pc[1]:6.2f},{pc[2]:5.2f}) "
          f"yaw {r['seated_yaw_rel_deg']:6.2f}  xm {min(r['pads']['plus']['x_margin'], r['pads']['minus']['x_margin']):5.2f} "
          f" rail-leg sit/rise {min(cl['sit']['rails_legs'], cl.get('rise', cl.get('standup'))['rails_legs']):6.1f} after {cl.get('after', {}).get('rails_legs', 0):6.1f} risen {r.get('risen_at')}  {' '.join(why)}")

"""Side-by-side of a training-env trace (gap_trace.py) and a runtime trace (brain_sim_check.py --sp-trace)."""
import json, sys
HOME = [0, -0.0873, -0.4579, -0.0049, 0.4530, 0.3491, 0.3491, 0, 0, 0, 0.0873, 0.4579, 0.0049, -0.4530]
def load(p):
    rows = [json.loads(l) for l in open(p)]
    rows = [r for r in rows if "summary" not in r]
    for r in rows:
        if r.get("target") is None:
            r["target"] = [h + a for h, a in zip(HOME, r["action"])]
    return rows
tr, rt = load(sys.argv[1]), load(sys.argv[2])
k0, k1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (56, 100)
print("k | jaw tr/rt | lipup tr/rt | jawtip tr/rt | beakF tr/rt | neck q/t tr | neck q/t rt | hpitch q/t tr | hpitch q/t rt | hroll t tr/rt | contacts jaw,upper tr rt | tilt tr/rt")
for k in range(k0, min(k1, len(tr), len(rt)), 2):
    a, b = tr[k], rt[k]
    fa = a.get("head_floor_n", 0) + a.get("jaw_floor_n", 0)
    print(f"{k:3d} {a['jaw_rad']:.3f}/{b['jaw_rad']:.3f} | {a['lip_up_z']*1e3:5.1f}/{b['lip_up_z']*1e3:5.1f} | {a['jaw_tip_bottom_z']*1e3:5.1f}/{b['jaw_tip_bottom_z']*1e3:5.1f} | {fa:4.1f}/{b['beak_floor_n']:4.1f} | {a['q'][5]:.2f}/{a['target'][5]:.2f} | {b['q'][5]:.2f}/{b['target'][5]:.2f} | {a['q'][6]:.2f}/{a['target'][6]:.2f} | {b['q'][6]:.2f}/{b['target'][6]:.2f} | {a['target'][8]:+.2f}/{b['target'][8]:+.2f} | {int(a['jaw_contact'])}{int(a['upper_contact'])} {int(b['jaw_contact'])}{int(b['upper_contact'])} | {a['tilt_deg']:.1f}/{b['tilt_deg']:.1f}")

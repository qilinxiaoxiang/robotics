"""Group the sim rows (results/*.jsonl) by posture label: falls, tilt, head reached, camera numbers and which faces are
seen with IPD >= 10 px at 0.3 / 0.5 / 1.0 / 2.0 m. Prints the summary and writes results/summary.json.

  python3 summarize.py
"""
import collections
import json
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")


def rows(name):
    p = os.path.join(RES, f"{name}.jsonl")
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


def seen(cam):
    out = []
    for k, f in cam.get("faces", {}).items():
        if f["inside"] and f["ipd_ok"]:
            out.append(k)
    return out


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(st.mean(xs), 2) if xs else None


def bsc_summary(name):
    g = collections.defaultdict(list)
    for r in rows(name):
        g[r["label"]].append(r)
    out = {}
    for label, rs in g.items():
        cams = [r["camera"] for r in rs if r.get("camera")]
        heads = [r["reached_head"] for r in rs if r.get("reached_head")]
        s = dict(runs=len(rs), falls=sum(1 for r in rs if r.get("fell")), max_tilt=max((r.get("max_tilt") or 0) for r in rs),
                 window_tilt=max((r.get("window_tilt") or 0) for r in rs),
                 reached_head={k: mean([h[k] for h in heads]) for k in heads[0]} if heads else None,
                 cam_height_m=mean([c["cam_height_m"] for c in cams]), elev_deg=mean([c["elev_deg"] for c in cams]),
                 top_edge_deg=mean([c["top_edge_deg"] for c in cams]), image_roll_deg=mean([c["image_roll_deg"] for c in cams]),
                 trunk_pitch_deg=mean([c["trunk_pitch_deg"] for c in cams]),
                 highest_face_m=cams[0]["highest_face_m"] if cams else None,
                 seen=sorted(set(seen(cams[0]))) if cams else None,
                 faces={k: dict(inside=f["inside"], ipd_px=f["ipd_px"], los_up_deg=f["los_up_deg"]) for k, f in cams[0]["faces"].items()} if cams else None,
                 reached_q=next((r["reached_q"] for r in rs if r.get("reached_q")), None),
                 trunk_gb=next((r["trunk_gb"] for r in rs if r.get("trunk_gb")), None))
        if "sit" in rs[0] and rs[0]["sit"]:
            s["seated_tilt"] = max(r["sit"].get("seated_max_tilt", 0) for r in rs)
            s["seated_trunk_z"] = rs[0]["sit"].get("seated_trunk_z")
        out[label] = s
    return out


def openloop_summary(name):
    g = collections.defaultdict(list)
    for r in rows(name):
        g[r["label"]].append(r)
    out = {}
    for label, rs in g.items():
        held = [r for r in rs if r["fell_at"] is None]
        s = dict(runs=len(rs), falls=len(rs) - len(held), fell_at=[r["fell_at"] for r in rs if r["fell_at"] is not None],
                 held_dx=sorted(set(r["dx_mm"] for r in held)), fell_dx=sorted(set(r["dx_mm"] for r in rs if r["fell_at"] is not None)),
                 push_held=[r["push"] for r in held if r.get("push")], push_fell=[r["push"] for r in rs if r.get("push") and r["fell_at"] is not None],
                 end_pitch_held=[r["end_pitch"] for r in held], max_tilt_after_5s_held=max((r["max_tilt_after_5s"] for r in held), default=None),
                 end_pitch_fell=[r["end_pitch"] for r in rs if r["fell_at"] is not None][:3])
        cams = [r["camera"] for r in held if r.get("camera")]
        if cams:
            s.update(cam_height_m=mean([c["cam_height_m"] for c in cams]), elev_deg=mean([c["elev_deg"] for c in cams]),
                     top_edge_deg=mean([c["top_edge_deg"] for c in cams]), image_roll_deg=mean([c["image_roll_deg"] for c in cams]),
                     highest_face_m=cams[0]["highest_face_m"], seen=sorted(set(seen(cams[0]))),
                     faces={k: dict(inside=f["inside"], ipd_px=f["ipd_px"], los_up_deg=f["los_up_deg"]) for k, f in cams[0]["faces"].items()})
        out[label] = s
    return out


if __name__ == "__main__":
    summary = {}
    for name in ("policy_head", "walk_head", "sit", "gp"):
        s = bsc_summary(name)
        summary[name] = s
        print(f"== {name}")
        for label, v in s.items():
            print(f"  {label:<40} runs {v['runs']} falls {v['falls']} tilt {v['max_tilt']} head {v['reached_head']} trunk {v['trunk_pitch_deg']} "
                  f"cam z {v['cam_height_m']} elev {v['elev_deg']} top {v['top_edge_deg']} roll {v['image_roll_deg']} highest {v['highest_face_m']} seen {v['seen']}")
    for name in ("openloop", "openloop2", "openloop3", "openloop4"):
        s = openloop_summary(name)
        if not s:
            continue
        summary[name] = s
        print(f"== {name}")
        for label, v in s.items():
            print(f"  {label:<40} runs {v['runs']} falls {v['falls']} held dx {v['held_dx']} fell dx {v['fell_dx']} fell_at {v['fell_at'][:4]} "
                  f"end pitch held {v['end_pitch_held'][:4]} push held {v['push_held']} fell {v['push_fell']} elev {v.get('elev_deg')} z {v.get('cam_height_m')} top {v.get('top_edge_deg')} seen {v.get('seen')}")
    summary["lying"] = rows("lying")
    print("== lying")
    for r in summary["lying"]:
        print(f"  {r['label']:<30} head {r['reached_head']} cam z {r['cam_height_m']} elev {r['elev_deg']} roll {r['image_roll_deg']} seen "
              f"{[k for k, f in r['faces'].items() if f['inside'] and f['ipd_ok']]}")
    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)

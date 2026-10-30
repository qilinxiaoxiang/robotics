"""A2 acceptance, the occlusion criterion: the id is held through a 2 s occlusion (20 frames at 10 fps).

Two passes of tracker.py over a recorded frame directory. Pass 1 (clean) finds the target's dominant track id and
its median box. Pass 2 paints a grey block over that box (padded) in 20 consecutive frames starting at --at, which
is the synthetic occlusion, and this script checks that the id reported before the block equals the id reported
after it, and that no track of the query is reported inside the block (the detector really lost it).

  occlusion_test.py testdata/live_home "orange ball" --at 100 --tracker bytetrack_duck.yaml --out runs/occl_bt.json
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run(dirpath, query, out, tracker, extra):
    cmd = [PY, os.path.join(HERE, "tracker.py"), "--query", query, "--source", f"dir:{dirpath}", "--out", out,
           "--quiet", "--tracker", tracker, "--warmup", "0"] + extra
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr[-2000:])
    return [json.loads(l) for l in open(out)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("query")
    ap.add_argument("--at", type=int, default=100, help="first occluded frame (index in the sorted directory)")
    ap.add_argument("--n", type=int, default=20, help="occluded frames (20 = 2 s at 10 fps)")
    ap.add_argument("--pad", type=float, default=12.0, help="pixels of grey around the median box")
    ap.add_argument("--tracker", default="bytetrack_duck.yaml")
    ap.add_argument("--count", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--extra", default="", help="extra tracker.py arguments, e.g. '--backend yoloe'")
    a = ap.parse_args()
    extra = a.extra.split()
    if a.count:
        extra += ["--count", str(a.count)]
    q = a.query
    base = os.path.join(HERE, "runs", "occl_" + os.path.basename(a.tracker).split(".")[0])
    clean = run(a.dir, q, base + "_clean.jsonl", a.tracker, extra)
    per_frame = [[t for t in f["tracks"] if t["name"] == q] for f in clean]
    ids = [max(ts, key=lambda t: t["conf"])["id"] for ts in per_frame if ts]
    n_det = len(ids)
    ids = [i for i in ids if i >= 0]   # -1 = detection the tracker never confirmed as a track
    if not ids:
        sys.exit(f"{q!r} detected in {n_det} frames but never confirmed as a track in {a.dir}: NO TRACK")
    vals, counts = np.unique(ids, return_counts=True)
    dom = int(vals[np.argmax(counts)])
    boxes = np.array([[t["u"], t["v"], t["w"], t["h"]] for ts in per_frame for t in ts if t["id"] == dom])
    u, v, w, h = np.median(boxes, 0)
    box = (u - w / 2 - a.pad, v - h / 2 - a.pad, u + w / 2 + a.pad, v + h / 2 + a.pad)
    clean_ids = sorted(set(ids))
    print(f"clean: {len(clean)} frames, {q!r} in {len(ids)}, dominant id {dom} in {int(counts.max())} frames, "
          f"all ids {clean_ids}, median box centre ({u:.0f},{v:.0f}) size {w:.0f}x{h:.0f}")
    blank = f"{a.at},{a.n},{box[0]:.0f},{box[1]:.0f},{box[2]:.0f},{box[3]:.0f}"
    occ = run(a.dir, q, base + "_occluded.jsonl", a.tracker, extra + ["--blank", blank])
    before = [max(ts, key=lambda t: t["conf"])["id"] for ts in
              ([t for t in f["tracks"] if t["name"] == q and t["id"] >= 0] for f in occ[:a.at]) if ts]
    during_raw = [[t for t in f["tracks"] if t["name"] == q] for f in occ[a.at:a.at + a.n]]
    inside = [t for ts in during_raw for t in ts if box[0] <= t["u"] <= box[2] and box[1] <= t["v"] <= box[3]]
    after_frames = occ[a.at + a.n:]
    after = [max(ts, key=lambda t: t["conf"])["id"] for ts in
             ([t for t in f["tracks"] if t["name"] == q and t["id"] >= 0] for f in after_frames) if ts]
    id_before = before[-1] if before else None
    first_after = next((i for i, f in enumerate(after_frames) if [t for t in f["tracks"] if t["name"] == q]), None)
    id_after = after[0] if after else None
    held = id_before is not None and id_before >= 0 and id_after == id_before
    same_after = sum(1 for i in after if i == id_before)
    res = {"dir": a.dir, "query": q, "tracker": a.tracker, "extra": extra, "frames": len(occ), "occluded_from": a.at,
           "clean_frames_tracked": len(ids), "clean_frames_detected": n_det, "clean_dominant_id": dom,
           "occluded_n": a.n, "blank_box": [round(b) for b in box], "id_before": id_before, "id_after": id_after,
           "held": held, "frames_until_refound": first_after, "after_frames_with_same_id": same_after,
           "after_frames_found": len(after), "tracks_inside_blank_during": len(inside),
           "ids_before": sorted(set(before)), "ids_after": sorted(set(after))}
    print(json.dumps(res))
    print("HELD" if held else ("NO TRACK" if (id_before is None or id_before < 0) else "ID CHANGED"),
          f"(before {id_before}, after {id_after}, refound after {first_after} frames, "
          f"{len(inside)} detections inside the blank while occluded)")
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)
    sys.exit(0 if held and not inside else 1)


if __name__ == "__main__":
    main()

"""Measure the open-vocabulary detector candidates on recorded frames: per-frame latency (p50/p90, after warm-up) and
how many frames contain a detection of each query, per candidate and device. Numbers, not guesses, for ACCEPTANCE.md.

  bench.py testdata/live_home "orange ball,laundry basket,person" --out runs/bench_live.json
  bench.py testdata/bend "laundry basket" --start 150 --candidates yw-s:mps,yw-m:mps --out runs/bench_bend.json

Candidates: yw-s / yw-m / yw-l (YOLO-World v2 s/m/l), ye-s / ye-m (YOLOE-11 s/m seg, text prompts), flo-b
(Florence-2-base, open-vocabulary detection, transformers), each with :mps or :cpu.
"""
import argparse
import json
import os
import sys
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

WEIGHTS = {"yw-s": "yolov8s-worldv2.pt", "yw-m": "yolov8m-worldv2.pt", "yw-l": "yolov8l-worldv2.pt",
           "ye-s": "yoloe-11s-seg.pt", "ye-m": "yoloe-11m-seg.pt"}


def load(cand, device, queries, imgsz):
    if cand.startswith("yw"):
        from ultralytics import YOLO
        m = YOLO(os.path.join(HERE, "weights", WEIGHTS[cand]))
        m.set_classes(queries)
        return lambda img: _ul(m.predict(img, conf=0.05, imgsz=imgsz, device=device, verbose=False)[0], queries)
    if cand.startswith("ye"):
        from ultralytics import YOLOE
        m = YOLOE(os.path.join(HERE, "weights", WEIGHTS[cand]))
        m.set_classes(queries, m.get_text_pe(queries))
        return lambda img: _ul(m.predict(img, conf=0.05, imgsz=imgsz, device=device, verbose=False)[0], queries)
    if cand == "flo-b":
        from tracker import FlorenceBackend
        fb = FlorenceBackend("florence-community/Florence-2-base", queries, device, 0.0, os.path.join(HERE, "bytetrack_duck.yaml"))
        return lambda img: [(queries[int(k)], c, (x1, y1, x2, y2)) for x1, y1, x2, y2, c, k in fb.detect(img)]
    raise SystemExit(f"unknown candidate {cand}")


def _ul(r, queries):
    out = []
    for b in r.boxes:
        x1, y1, x2, y2 = b.xyxy[0].tolist()
        out.append((queries[int(b.cls)], float(b.conf), (x1, y1, x2, y2)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("queries")
    ap.add_argument("--candidates", default="yw-s:mps,yw-s:cpu,yw-m:mps,yw-l:mps,ye-s:mps,ye-m:mps")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--count", type=int, default=None)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    queries = [q.strip() for q in a.queries.split(",") if q.strip()]
    files = sorted(f for f in os.listdir(a.dir) if f.lower().endswith((".png", ".jpg")))
    files = files[a.start:None if a.count is None else a.start + a.count][::a.every]
    imgs = [cv2.imread(os.path.join(a.dir, f)) for f in files]
    results = {}
    for spec in a.candidates.split(","):
        cand, device = spec.split(":")
        t0 = time.time()
        try:
            det = load(cand, device, queries, a.imgsz)
        except Exception as e:
            results[spec] = {"error": repr(e)[:300]}
            print(f"{spec}: load failed {e!r}"[:300], flush=True)
            continue
        t_load = time.time() - t0
        lats, hits, confs = [], {q: 0 for q in queries}, {q: [] for q in queries}
        for i, img in enumerate(imgs):
            t1 = time.time()
            dets = det(img)
            dt = time.time() - t1
            if i >= a.warmup:
                lats.append(dt)
                for q in queries:
                    qd = [d for d in dets if d[0] == q]
                    if qd:
                        hits[q] += 1
                        confs[q].append(max(d[1] for d in qd))
        r = {"load_s": round(t_load, 1), "frames": len(lats),
             "ms_p50": round(1000 * float(np.percentile(lats, 50)), 1), "ms_p90": round(1000 * float(np.percentile(lats, 90)), 1),
             "ms_max": round(1000 * max(lats), 1), "fps_detector_only": round(len(lats) / sum(lats), 1),
             "hits": hits, "conf_median": {q: (round(float(np.median(c)), 3) if c else None) for q, c in confs.items()}}
        results[spec] = r
        print(f"{spec}: {json.dumps(r)}", flush=True)
    if a.out:
        with open(a.out, "w") as f:
            json.dump({"dir": a.dir, "queries": queries, "imgsz": a.imgsz, "files": len(imgs), "results": results}, f, indent=1)


if __name__ == "__main__":
    main()

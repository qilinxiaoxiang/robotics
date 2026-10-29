#!/usr/bin/env python3
"""Latency, memory and detection quality of one backend on the evidence frames (pet/see/out/frames/manifest.json).

    ~/.venvs/duck-see/bin/python pet/see/bench.py --backend yolo-world [--device cpu] [--out out/bench_<host>_<backend>.json]
    ... --random-init           architecture only, random weights: latency and memory on a machine that cannot hold the
                                weights (the Mac mini's disk), quality is not evaluated
    ... --latency-only -n 6     the first n frames, no quality bookkeeping

Quality rule (the pickup chain's use): one prompt at a time, as approach.py / seepick.py run it. For every frame and
every prompt in the set, `detect(frame, horizon)` is called with that single prompt (plus the negatives when
--negatives is given). A frame that holds the prompt's object counts as a hit when the chosen box overlaps the pasted
box with IoU >= 0.3; a frame that does not hold it counts as a false positive when anything is chosen; a chosen box
that lies mostly in the duck's own-body mask is counted separately as an own-part false positive. The horizon row is
the one approach.below_horizon would give for a level head looking down: here row 60 (the shoes and bin tops in the
real floor frame are above it).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import socket
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from pet.see.detect import BACKENDS, CONF, MODELS_DIR, OpenVocabDetector, annotate, box_in_mask  # noqa: E402

PROMPTS = ["orange block", "small ball", "keys", "remote control", "bucket"]
HORIZON = 60
IOU_HIT = 0.3


def iou(a, b):
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    ix0, iy0, ix1, iy1 = max(ax0, bx0), max(ay0, by0), min(ax0 + aw, bx0 + bw), min(ay0 + ah, by0 + bh)
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    return inter / float(aw * ah + bw * bh - inter + 1e-9)


def rss_mb():
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / (1024.0 * 1024.0) if platform.system() == "Darwin" else r / 1024.0


def random_init(backend, models_dir, device):
    """An OpenVocabDetector whose model has the architecture but random weights (no weight file needed)."""
    import torch
    det = OpenVocabDetector.__new__(OpenVocabDetector)
    det.backend, det.device, det.models_dir, det.conf = backend, device, Path(models_dir), CONF[backend]
    det.min_area, det.body_mask, det.negatives, det.imgsz = 60, None, (), 640
    det.prompts, det.last, det.last_ms = [], [], None
    import threading
    det._lock = threading.Lock()
    det._text = None
    t = time.perf_counter()
    if backend == "owlv2":
        from transformers import Owlv2Config, Owlv2ForObjectDetection, Owlv2Processor
        d = det.models_dir / "owlv2-base-patch16-ensemble"
        det._proc = Owlv2Processor.from_pretrained(d)
        det._model = Owlv2ForObjectDetection(Owlv2Config.from_pretrained(d)).to(device).eval()
    elif backend == "gdino":
        from transformers import AutoConfig, AutoProcessor, GroundingDinoForObjectDetection
        d = det.models_dir / "grounding-dino-tiny"
        det._proc = AutoProcessor.from_pretrained(d)
        det._model = GroundingDinoForObjectDetection(AutoConfig.from_pretrained(d)).to(device).eval()
    else:
        raise SystemExit("--random-init is for owlv2 / gdino; yolo-world's weights are 25 MB and always present")
    det.load_s = time.perf_counter() - t
    det.prompts = list(PROMPTS)
    return det


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", default="yolo-world", choices=BACKENDS)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--frames", default=str(HERE / "out" / "frames"))
    ap.add_argument("--models-dir", default=str(MODELS_DIR))
    ap.add_argument("--out", default=None)
    ap.add_argument("--draw", default=None, help="directory for annotated frames (one per frame and prompt that hit)")
    ap.add_argument("--negatives", default="", help="comma separated, e.g. 'robot foot'")
    ap.add_argument("--random-init", action="store_true")
    ap.add_argument("--latency-only", action="store_true")
    ap.add_argument("-n", type=int, default=None, help="use only the first n frames")
    ap.add_argument("--every", type=int, default=1, help="keep every k-th synthetic frame (all real ones stay)")
    ap.add_argument("--threads", type=int, default=None, help="torch CPU threads (default: torch's choice)")
    a = ap.parse_args()
    import torch
    if a.threads:
        torch.set_num_threads(a.threads)
    frames_dir = Path(a.frames)
    man = json.loads((frames_dir / "manifest.json").read_text())["frames"]
    if a.n:
        man = man[:a.n]
    if a.every > 1:
        synth = [f for f in man if f["kind"] != "real"][::a.every]
        man = [f for f in man if f["kind"] == "real"] + synth
    negatives = [p.strip() for p in a.negatives.split(",") if p.strip()]
    host = socket.gethostname().split(".")[0]
    rss0 = rss_mb()
    if a.random_init:
        det = random_init(a.backend, a.models_dir, a.device)
    else:
        det = OpenVocabDetector(PROMPTS, a.device, a.backend, models_dir=a.models_dir, negatives=negatives)
    rss_loaded = rss_mb()
    info = {"host": host, "machine": platform.machine(), "cpu": os.popen("sysctl -n machdep.cpu.brand_string").read().strip(),
            "python": platform.python_version(), "torch": torch.__version__, "threads": torch.get_num_threads(),
            "backend": a.backend, "device": a.device, "random_init": a.random_init, "conf": det.conf,
            "negatives": negatives, "load_s": round(det.load_s, 2), "rss_mb_before_load": round(rss0, 1),
            "rss_mb_after_load": round(rss_loaded, 1), "n_frames": len(man),
            "loadavg_start": os.getloadavg()[0], "date": time.strftime("%Y-%m-%d %H:%M:%S")}
    # warm-up on the first frame (the first call of every backend is slower: graph tracing, allocations)
    first = cv2.imread(str(frames_dir / man[0]["file"]))
    t = time.perf_counter()
    det.all(first)
    info["first_call_ms"] = round((time.perf_counter() - t) * 1000, 1)

    lat, rows = [], []
    if a.random_init or a.latency_only:
        prompts_used = [PROMPTS[0]]
        if not a.random_init:
            det.set_prompts(prompts_used + negatives)
        for f in man:
            img = cv2.imread(str(frames_dir / f["file"]))
            t = time.perf_counter()
            det.all(img)
            lat.append((time.perf_counter() - t) * 1000)
    else:
        if a.draw:
            Path(a.draw).mkdir(parents=True, exist_ok=True)
        for prompt in PROMPTS:
            det.set_prompts([prompt] + [n for n in negatives if n != prompt])
            for f in man:
                img = cv2.imread(str(frames_dir / f["file"]))
                mask = cv2.imread(str(frames_dir / f["body_mask"]), 0) if f.get("body_mask") else None
                gts = [o["bbox"] for o in f["objects"] if o["prompt"] == prompt]
                hor = HORIZON if img.shape[0] == 360 else int(HORIZON * img.shape[0] / 360)
                t = time.perf_counter()
                hit = det.detect(img, hor)
                ms = (time.perf_counter() - t) * 1000
                lat.append(ms)
                r = {"file": f["file"], "kind": f["kind"], "prompt": prompt, "has_object": bool(gts), "ms": round(ms, 1),
                     "n_dets": len(det.last), "hit": None, "outcome": None}
                if hit is not None:
                    r["hit"] = {"bbox": list(hit["bbox"]), "score": round(hit["score"], 3), "label": hit["label"]}
                    r["on_own_body"] = box_in_mask(hit["bbox"], mask)
                if gts:
                    r["iou"] = round(max(iou(hit["bbox"], g) for g in gts), 3) if hit else 0.0
                    r["outcome"] = "hit" if hit and r["iou"] >= IOU_HIT else ("wrong_box" if hit else "miss")
                else:
                    r["outcome"] = ("own_part_fp" if r.get("on_own_body") else "fp") if hit else "correct_none"
                rows.append(r)
                if a.draw and (hit is not None or gts):
                    title = f"{prompt}: {r['outcome']}" + (f" iou {r['iou']}" if gts else "")
                    cv2.imwrite(str(Path(a.draw) / f"{Path(f['file']).stem}__{prompt.replace(' ', '_')}.jpg"),
                                annotate(img, det.last, hit, hor, title))
    lat = np.array(lat)
    info.update({"latency_ms": {"median": round(float(np.median(lat)), 1), "mean": round(float(lat.mean()), 1),
                                "p90": round(float(np.percentile(lat, 90)), 1), "min": round(float(lat.min()), 1),
                                "max": round(float(lat.max()), 1), "n": int(lat.size)},
                 "fps_median": round(1000.0 / float(np.median(lat)), 2), "rss_mb_peak": round(rss_mb(), 1),
                 "loadavg_end": os.getloadavg()[0]})
    if rows:
        summ = {}
        for prompt in PROMPTS:
            rs = [r for r in rows if r["prompt"] == prompt]
            pos = [r for r in rs if r["has_object"]]
            neg = [r for r in rs if not r["has_object"]]
            summ[prompt] = {"frames_with_object": len(pos), "hits": sum(r["outcome"] == "hit" for r in pos),
                            "wrong_box": sum(r["outcome"] == "wrong_box" for r in pos),
                            "misses": sum(r["outcome"] == "miss" for r in pos), "frames_without": len(neg),
                            "false_positives": sum(r["outcome"] == "fp" for r in neg),
                            "own_part_false_positives": sum(r["outcome"] == "own_part_fp" for r in neg)}
        pos = [r for r in rows if r["has_object"]]
        neg = [r for r in rows if not r["has_object"]]
        info["quality"] = {"per_prompt": summ, "hit_rate": round(sum(r["outcome"] == "hit" for r in pos) / max(1, len(pos)), 3),
                           "n_positive": len(pos), "false_positive_rate": round(sum(r["outcome"] in ("fp", "own_part_fp") for r in neg) / max(1, len(neg)), 3),
                           "n_negative": len(neg), "own_part_false_positives": sum(r["outcome"] == "own_part_fp" for r in neg),
                           "real_frames": {f["file"]: [(r["prompt"], r["outcome"]) for r in rows if r["file"] == f["file"] and r["hit"]]
                                           for f in man if f["kind"] == "real"}}
        info["rows"] = rows
    out = Path(a.out) if a.out else HERE / "out" / f"bench_{host}_{a.backend}{'_randominit' if a.random_init else ''}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(info, indent=1))
    q = info.get("quality", {})
    print(f"{host} {a.backend}{' (random init)' if a.random_init else ''} {a.device}: load {info['load_s']} s, "
          f"first call {info['first_call_ms']} ms, median {info['latency_ms']['median']} ms ({info['fps_median']} fps), "
          f"p90 {info['latency_ms']['p90']} ms, RSS after load {info['rss_mb_after_load']} MB, peak {info['rss_mb_peak']} MB, "
          f"load avg {info['loadavg_start']:.1f} -> {info['loadavg_end']:.1f}"
          + (f"; hit rate {q['hit_rate']} ({q['n_positive']} positives), FP rate {q['false_positive_rate']} "
             f"({q['n_negative']} negatives), own-part FPs {q['own_part_false_positives']}" if q else ""))
    print("wrote", out)


if __name__ == "__main__":
    main()

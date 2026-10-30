"""Detector-only probe: what does the open-vocabulary detector see in a few recorded frames for several queries?
  probe_detect.py testdata/bend "ruler,red ruler,pink ruler,basket,laundry basket" --every 20
Prints per frame the boxes with confidence (no tracker), to pick the query word that works on this camera."""
import argparse
import os
import sys
import time

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("queries")
    ap.add_argument("--every", type=int, default=20)
    ap.add_argument("--conf", type=float, default=0.02)
    ap.add_argument("--backend", default="yoloworld", choices=["yoloworld", "yoloe"])
    ap.add_argument("--weights", default=None)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--save", default=None, help="dir for annotated pictures")
    a = ap.parse_args()
    qs = [q.strip() for q in a.queries.split(",") if q.strip()]
    if a.backend == "yoloe":
        from ultralytics import YOLOE
        m = YOLOE(a.weights or os.path.join(HERE, "weights", "yoloe-11s-seg.pt"))
        m.set_classes(qs, m.get_text_pe(qs))
    else:
        from ultralytics import YOLO
        m = YOLO(a.weights or os.path.join(HERE, "weights", "yolov8s-worldv2.pt"))
        m.set_classes(qs)
    files = sorted(f for f in os.listdir(a.dir) if f.lower().endswith((".png", ".jpg")))[::a.every]
    if a.save:
        os.makedirs(a.save, exist_ok=True)
    for f in files:
        img = cv2.imread(os.path.join(a.dir, f))
        t0 = time.time()
        r = m.predict(img, conf=a.conf, imgsz=a.imgsz, device=a.device, verbose=False)[0]
        dt = time.time() - t0
        dets = []
        for b in r.boxes:
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            dets.append(f"{qs[int(b.cls)]}:{float(b.conf):.2f}@({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f})")
        print(f"{f} {dt * 1000:.0f} ms  " + ("; ".join(dets) if dets else "-"), flush=True)
        if a.save:
            cv2.imwrite(os.path.join(a.save, f.replace(".png", ".jpg")), r.plot())


if __name__ == "__main__":
    main()

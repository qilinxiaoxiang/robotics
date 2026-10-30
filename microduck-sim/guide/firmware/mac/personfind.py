"""Person finder for the duck's eye: a frame -> the people in it as boxes, and where the person's head should be as
angles off the camera axis, so the name-call attention can follow a body up to the face (NAMECALL.md 12).

Detector: YOLOX-Tiny (Megvii, Apache-2.0; 5.06 M parameters, 6.45 GFLOPs, COCO AP 32.8 at 416), the official ONNX
export of release 0.1.1rc0,
https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_tiny.onnx
(20 219 662 bytes, sha256 427cc366d34e27ff7a03e2899b5e3671425c262ea2291f88bb942bc1cc70b0f7), COCO 80 classes, of which
only class 0 (person) is kept. Input 416 x 416 BGR 0-255 letterboxed with grey 114 at the top left (YOLOX
data_augment.preproc, no mean/std since 0.1.1); output (1, 3549, 85) = raw grid predictions over strides 8/16/32 with
objectness and class scores already through the sigmoid (YOLOX demo/ONNXRuntime/onnx_inference.py, demo_postprocess).
The file lives next to the face models in pet/identity/models/yolox/ (gitignored); pet/identity/fetch_models.sh
downloads it and checks the sha256.

Why Tiny, not Nano (2026-10-30, test_personfind.py; frames in personfind-20261030/, local only by the image ignore
rule): on the 16:54 frame of Shawn's shoes and jeans Nano's
best person score is 0.13 (below anything usable), Tiny's 0.76. A7Z, onnxruntime 1.19.2, robot brain running: Tiny
239 ms per frame at 2 threads, 365 ms at 1; Nano 87 ms. FaceFinder runs it on the same frame only when that frame
has no face, at most PERSON_HZ, inside its own serial loop, so the finder never uses more than its 2 threads.

False hits: whole-frame "people" on close blurred floor texture (the ground-pick bend frames, the lens 2-5 cm from the
wood, scores up to 0.87). A caller far enough away to look up at is never as wide as the frame, so boxes wider than
MAX_W_FRAC of it, and boxes cut by both the top and bottom edge wider than FULL_SPAN_W_FRAC, are dropped.

Angles use the same equidistant fisheye as facefind (f = 359.5 px on the 640 x 360 frame): a pixel r from the centre
is r / f rad off the axis; + right / + up as in facefind.face_angles.

Where the head is: a box whose top lies inside the frame has the head at its top, so the aim point is HEAD_FRAC of the
box height below the top edge (a standing adult's head centre is about 1/16 of the body height below the crown; the
box also cuts at the shoulders when the person is close, so a small fraction is right for both). A box that touches the
frame's top edge (within TOP_EDGE_PX) continues above the frame: the head is out of view, upward, and the caller has
to look up (top_cut True).
"""
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))   # .../robotics (or ~/rt on the A7Z)
MODEL = os.path.join(ROOT, "pet", "identity", "models", "yolox", "yolox_tiny.onnx")
MODEL_SHA256 = "427cc366d34e27ff7a03e2899b5e3671425c262ea2291f88bb942bc1cc70b0f7"
MAX_W_FRAC = 0.9      # boxes wider than this fraction of the frame are close-up texture, not a caller
FULL_SPAN_W_FRAC = 0.6  # ... and so are boxes cut by both the top and the bottom edge that are wider than this
SPAN_EDGE_PX = 8      # "cut by the edge" for that test (the detector's box edges wander a few px off the border)

F_PX = 359.5          # equidistant fisheye focal length on the 640 x 360 frame (facefind.F_PX)
INPUT = 416           # YOLOX-Nano input size
SCORE_MIN = 0.35      # objectness x person score
NMS_IOU = 0.45
MIN_H_PX = 24         # boxes shorter than this are not a caller (far away or a false hit on texture)
HEAD_FRAC = 0.06      # head centre below the box top, as a fraction of the box height
TOP_EDGE_PX = 3       # a box top at or above this row touches the frame edge: the body goes on above the frame
STRIDES = (8, 16, 32)


def nms(boxes, scores, iou=NMS_IOU):
    """Greedy non-maximum suppression; returns kept indices, best first."""
    x1, y1, x2, y2 = boxes.T
    areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size:
        i = order[0]
        keep.append(int(i))
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
        o = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        order = order[1:][o <= iou]
    return keep


def _grids(size=INPUT, strides=STRIDES):
    g, s = [], []
    for st in strides:
        n = size // st
        yv, xv = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
        g.append(np.stack((xv, yv), 2).reshape(-1, 2))
        s.append(np.full((n * n, 1), st))
    return np.concatenate(g, 0).astype(np.float32), np.concatenate(s, 0).astype(np.float32)


class PersonDetector:
    """YOLOX-Nano person boxes: detect(img_bgr) -> (n, 5) x1 y1 x2 y2 score in image pixels, best first."""

    def __init__(self, model=MODEL, threads=2, score_min=SCORE_MIN, min_h_px=MIN_H_PX, max_w_frac=MAX_W_FRAC):
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.intra_op_num_threads = int(threads)
        so.inter_op_num_threads = 1
        self.sess = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0].name
        self.score_min, self.min_h_px, self.max_w_frac = score_min, min_h_px, max_w_frac
        self.grid, self.stride = _grids()
        self.buf = np.full((INPUT, INPUT, 3), 114, np.uint8)

    def plausible(self, b, w, h):
        """A caller's box: tall enough, not frame-wide, and not a wide box cut by both the top and the bottom edge
        (close blurred texture during a bend; a body that close is under 30 cm from the lens)."""
        bw, bh = b[2] - b[0], b[3] - b[1]
        if bh < self.min_h_px or bw > self.max_w_frac * w:
            return False
        full_height = b[1] <= SPAN_EDGE_PX and b[3] >= h - SPAN_EDGE_PX
        return not (full_height and bw > FULL_SPAN_W_FRAC * w)

    def preprocess(self, img):
        import cv2
        h, w = img.shape[:2]
        r = min(INPUT / h, INPUT / w)
        nh, nw = int(round(h * r)), int(round(w * r))
        self.buf[:] = 114
        self.buf[:nh, :nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
        x = self.buf.transpose(2, 0, 1)[None].astype(np.float32)
        return x, r

    def detect(self, img):
        x, r = self.preprocess(img)
        out = self.sess.run(None, {self.inp: x})[0][0]           # (3549, 85)
        score = out[:, 4] * out[:, 5]                             # objectness x person
        m = score >= self.score_min
        if not m.any():
            return np.zeros((0, 5), np.float32)
        p, s = out[m], score[m]
        xy = (p[:, :2] + self.grid[m]) * self.stride[m]
        wh = np.exp(p[:, 2:4]) * self.stride[m]
        boxes = np.concatenate([xy - wh / 2, xy + wh / 2], 1) / r
        h, w = img.shape[:2]
        boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, w)
        boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, h)
        keep = [i for i in nms(boxes, s) if self.plausible(boxes[i], w, h)]
        return np.concatenate([boxes[keep], s[keep, None]], 1).astype(np.float32)


def person_angles(bbox, w, h, f_px=F_PX, head_frac=HEAD_FRAC, top_edge_px=TOP_EDGE_PX):
    """For a person box (x1, y1, x2, y2) in a w x h frame: dict(yaw_err, pitch_err, top_cut, height) in rad, + right,
    + up. yaw_err is the box's centre column; pitch_err the estimated head point HEAD_FRAC below the box top (when the
    top is cut by the frame edge that point is the edge itself and the head is further up)."""
    x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
    top_cut = y1 <= top_edge_px
    y_head = y1 if top_cut else y1 + head_frac * (y2 - y1)
    return dict(yaw_err=(0.5 * (x1 + x2) - 0.5 * w) / f_px, pitch_err=(0.5 * h - y_head) / f_px, top_cut=bool(top_cut),
                height=(y2 - y1) / f_px)


def people(dets, w, h):
    """Detector rows -> person dicts sorted largest first (the nearest caller), angles rounded for logging."""
    out = []
    for d in np.asarray(dets, float).reshape(-1, 5):
        a = person_angles(d, w, h)
        out.append(dict(yaw_err=round(a["yaw_err"], 4), pitch_err=round(a["pitch_err"], 4), top_cut=a["top_cut"],
                        height=round(a["height"], 4), score=round(float(d[4]), 3), box=[int(round(v)) for v in d[:4]]))
    out.sort(key=lambda p: -p["height"])
    return out


if __name__ == "__main__":
    # timing / check on saved frames: python personfind.py IMG [IMG ...] [--threads N] [--reps N]
    import argparse
    import cv2
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--model", default=MODEL)
    a = ap.parse_args()
    det = PersonDetector(a.model, threads=a.threads)
    for path in a.images:
        img = cv2.imread(path)
        if img is None:
            print(path, "unreadable")
            continue
        if img.shape[:2] != (360, 640):
            img = cv2.resize(img, (640, 360), interpolation=cv2.INTER_AREA)
        det.detect(img)                                       # warm-up
        ms = []
        for _ in range(a.reps):
            t0 = time.perf_counter()
            d = det.detect(img)
            ms.append((time.perf_counter() - t0) * 1000.0)
        print(os.path.basename(path), "ms median %.1f min %.1f max %.1f" % (np.median(ms), min(ms), max(ms)),
              people(d, img.shape[1], img.shape[0]), flush=True)

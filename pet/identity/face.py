"""Face detection, alignment and embedding with InsightFace buffalo_sc (ONNX).

buffalo_sc = SCRFD-500MF detector (det_500m.onnx) + MobileFaceNet ArcFace
recogniser (w600k_mbf.onnx, 512-d). We run the two ONNX files directly with
onnxruntime so the same code runs on the Mac and on the A7Z CPU; the
`insightface` pip package (which needs a C++ build) is not required.

Pre/post-processing follows insightface/model_zoo/scrfd.py and arcface_onnx.py
(v0.7): SCRFD input (x - 127.5) / 128 RGB at 640x640 letterbox, strides 8/16/32
with 2 anchors each; ArcFace input (x - 127.5) / 127.5 RGB 112x112 aligned to
the standard 5-point template.

Landmark order (SCRFD): 0 left eye, 1 right eye, 2 nose tip, 3 left mouth
corner, 4 right mouth corner (left/right in image coordinates).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

MODEL_DIR = Path(__file__).resolve().parent / "models" / "buffalo_sc"
DET_MODEL = MODEL_DIR / "det_500m.onnx"
REC_MODEL = MODEL_DIR / "w600k_mbf.onnx"

# Minimum inter-pupil distance in pixels for a usable recognition crop
# (2026-10-26 survey: below ~10 px MobileFaceNet embeddings collapse).
MIN_IPD_PX = 10.0

# ArcFace 112x112 reference landmarks (insightface/utils/face_align.py).
ARCFACE_DST = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)
# In the template the nose sits at this fraction of the way from the eye line
# to the mouth line; a frontal face measures about the same.
_TEMPLATE_NOSE_FRAC = (71.7366 - 51.599) / (92.2848 - 51.599)
# Nose-tip protrusion relative to the eye-to-mouth height. Used only for the
# rough pitch estimate below (anthropometric average, not calibrated).
_NOSE_DEPTH_RATIO = 0.55


@dataclass
class Face:
    bbox: np.ndarray            # x1, y1, x2, y2 in image pixels
    score: float                # detector confidence
    kps: np.ndarray             # 5x2 landmarks in image pixels
    ipd_px: float               # inter-pupil distance (eye landmarks) in px
    pitch_deg: float            # + = face seen from below (chin up vs camera)
    yaw_deg: float              # + = face turned toward image right
    usable: bool                # passes the IPD gate
    reject_reason: str = ""
    embedding: np.ndarray | None = None   # L2-normalised 512-d, None if rejected
    quality: float = 0.0        # 0..1 heuristic for memory weighting
    timings_ms: dict = field(default_factory=dict)


def estimate_pose(kps: np.ndarray) -> tuple[float, float]:
    """Rough head pitch/yaw from 5 landmarks (degrees).

    Pitch: the nose tip protrudes from the eye/mouth plane, so when the camera
    looks up at the face (or the person lifts the chin) the nose projects
    toward the eye line. With protrusion d and eye-to-mouth height H,
    nose_frac ~= frac0 - (d / H) * tan(pitch). Positive pitch = face seen
    from below, which is the MicroDuck's normal view of a standing person.

    Yaw: the nose shifts horizontally from the eye midpoint by
    d * sin(yaw); normalised by the inter-eye distance.
    This is a logging aid, not a calibrated head-pose estimator.
    """
    le, re_, nose, lm, rm = kps.astype(np.float64)
    eye_mid = (le + re_) / 2.0
    mouth_mid = (lm + rm) / 2.0
    axis = mouth_mid - eye_mid
    h = float(np.linalg.norm(axis))
    if h < 1e-6:
        return 0.0, 0.0
    u = axis / h
    frac = float(np.dot(nose - eye_mid, u)) / h
    pitch = math.degrees(math.atan2(_TEMPLATE_NOSE_FRAC - frac, _NOSE_DEPTH_RATIO))
    eye_w = float(np.linalg.norm(re_ - le))
    perp = np.array([u[1], -u[0]])  # points toward image right for an upright face
    lateral = float(np.dot(nose - eye_mid, perp)) / max(eye_w, 1e-6)
    yaw = math.degrees(math.asin(max(-1.0, min(1.0, lateral / (_NOSE_DEPTH_RATIO * h / max(eye_w, 1e-6))))))
    return pitch, yaw


def umeyama_similarity(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """2x3 similarity transform mapping src points onto dst (least squares)."""
    src = src.astype(np.float64)
    dst = dst.astype(np.float64)
    n = src.shape[0]
    mu_s, mu_d = src.mean(0), dst.mean(0)
    sc, dc = src - mu_s, dst - mu_d
    cov = dc.T @ sc / n
    u, s, vt = np.linalg.svd(cov)
    d = np.ones(2)
    if np.linalg.det(cov) < 0:
        d[-1] = -1
    r = u @ np.diag(d) @ vt
    var_s = (sc ** 2).sum() / n
    scale = (s * d).sum() / var_s
    t = mu_d - scale * r @ mu_s
    m = np.zeros((2, 3))
    m[:, :2] = scale * r
    m[:, 2] = t
    return m


def align_face(img_bgr: np.ndarray, kps: np.ndarray, size: int = 112) -> np.ndarray:
    m = umeyama_similarity(kps, ARCFACE_DST * (size / 112.0))
    return cv2.warpAffine(img_bgr, m, (size, size), borderValue=0.0)


def _distance2bbox(points, distance):
    x1 = points[:, 0] - distance[:, 0]
    y1 = points[:, 1] - distance[:, 1]
    x2 = points[:, 0] + distance[:, 2]
    y2 = points[:, 1] + distance[:, 3]
    return np.stack([x1, y1, x2, y2], axis=-1)


def _distance2kps(points, distance):
    out = []
    for i in range(0, distance.shape[1], 2):
        out.append(points[:, i % 2] + distance[:, i])
        out.append(points[:, i % 2 + 1] + distance[:, i + 1])
    return np.stack(out, axis=-1)


def _nms(dets: np.ndarray, thresh: float) -> list[int]:
    x1, y1, x2, y2, scores = dets.T
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        ovr = w * h / (areas[i] + areas[order[1:]] - w * h)
        order = order[np.where(ovr <= thresh)[0] + 1]
    return keep


class FacePipeline:
    """SCRFD-500MF detection + 5-point alignment + MobileFaceNet embedding."""

    def __init__(self, det_size: int = 640, det_thresh: float = 0.5,
                 min_ipd_px: float = MIN_IPD_PX, num_threads: int = 2,
                 providers: list[str] | None = None):
        for p in (DET_MODEL, REC_MODEL):
            if not p.exists():
                raise FileNotFoundError(f"{p} missing; run pet/identity/fetch_models.sh")
        so = ort.SessionOptions()
        so.intra_op_num_threads = num_threads
        so.log_severity_level = 3
        providers = providers or ["CPUExecutionProvider"]
        self.det = ort.InferenceSession(str(DET_MODEL), so, providers=providers)
        self.rec = ort.InferenceSession(str(REC_MODEL), so, providers=providers)
        self.det_input = self.det.get_inputs()[0].name
        self.rec_input = self.rec.get_inputs()[0].name
        self.det_size = det_size
        self.det_thresh = det_thresh
        self.min_ipd_px = min_ipd_px
        self._strides = (8, 16, 32)
        self._num_anchors = 2
        self._anchor_cache: dict = {}

    # detection ---------------------------------------------------------
    def detect(self, img_bgr: np.ndarray, max_num: int = 0) -> tuple[np.ndarray, np.ndarray]:
        s = self.det_size
        h, w = img_bgr.shape[:2]
        scale = min(s / w, s / h)
        nw, nh = int(round(w * scale)), int(round(h * scale))
        canvas = np.zeros((s, s, 3), dtype=np.uint8)
        canvas[:nh, :nw] = cv2.resize(img_bgr, (nw, nh))
        blob = cv2.dnn.blobFromImage(canvas, 1.0 / 128.0, (s, s), (127.5, 127.5, 127.5), swapRB=True)
        outs = self.det.run(None, {self.det_input: blob})
        fmc = len(self._strides)
        scores_l, boxes_l, kps_l = [], [], []
        for idx, stride in enumerate(self._strides):
            scores = outs[idx][:, 0] if outs[idx].ndim == 2 else outs[idx][0][:, 0]
            bbox_pred = (outs[idx + fmc].reshape(-1, 4)) * stride
            kps_pred = (outs[idx + fmc * 2].reshape(-1, 10)) * stride
            fh, fw = s // stride, s // stride
            key = (fh, fw, stride)
            if key not in self._anchor_cache:
                ac = np.stack(np.mgrid[:fh, :fw][::-1], axis=-1).astype(np.float32)
                ac = (ac * stride).reshape(-1, 2)
                ac = np.stack([ac] * self._num_anchors, axis=1).reshape(-1, 2)
                self._anchor_cache[key] = ac
            anchors = self._anchor_cache[key]
            pos = np.where(scores >= self.det_thresh)[0]
            boxes = _distance2bbox(anchors, bbox_pred)
            kps = _distance2kps(anchors, kps_pred).reshape(-1, 5, 2)
            scores_l.append(scores[pos])
            boxes_l.append(boxes[pos])
            kps_l.append(kps[pos])
        scores = np.concatenate(scores_l)
        if scores.size == 0:
            return np.zeros((0, 5), np.float32), np.zeros((0, 5, 2), np.float32)
        boxes = np.concatenate(boxes_l) / scale
        kps = np.concatenate(kps_l) / scale
        order = scores.argsort()[::-1]
        dets = np.hstack([boxes, scores[:, None]])[order].astype(np.float32)
        kps = kps[order]
        keep = _nms(dets, 0.4)
        dets, kps = dets[keep], kps[keep]
        if max_num and dets.shape[0] > max_num:
            area = (dets[:, 2] - dets[:, 0]) * (dets[:, 3] - dets[:, 1])
            sel = np.argsort(area)[::-1][:max_num]
            dets, kps = dets[sel], kps[sel]
        return dets, kps

    # embedding ---------------------------------------------------------
    def embed_aligned(self, crops_bgr: list[np.ndarray]) -> np.ndarray:
        blob = cv2.dnn.blobFromImages(crops_bgr, 1.0 / 127.5, (112, 112), (127.5, 127.5, 127.5), swapRB=True)
        emb = self.rec.run(None, {self.rec_input: blob})[0]
        return emb / np.linalg.norm(emb, axis=1, keepdims=True)

    def analyze(self, img_bgr: np.ndarray, max_num: int = 0) -> list[Face]:
        t0 = time.perf_counter()
        dets, kps_all = self.detect(img_bgr, max_num=max_num)
        t1 = time.perf_counter()
        faces: list[Face] = []
        crops, idx = [], []
        for d, k in zip(dets, kps_all):
            ipd = float(np.linalg.norm(k[1] - k[0]))
            pitch, yaw = estimate_pose(k)
            usable = ipd >= self.min_ipd_px
            f = Face(bbox=d[:4].copy(), score=float(d[4]), kps=k.copy(), ipd_px=ipd,
                     pitch_deg=pitch, yaw_deg=yaw, usable=usable,
                     reject_reason="" if usable else f"ipd {ipd:.1f} px < {self.min_ipd_px:.0f} px")
            faces.append(f)
            if usable:
                crops.append(align_face(img_bgr, k))
                idx.append(len(faces) - 1)
        if crops:
            embs = self.embed_aligned(crops)
            for i, e in zip(idx, embs):
                faces[i].embedding = e.astype(np.float32)
                faces[i].quality = face_quality(faces[i])
        t2 = time.perf_counter()
        for f in faces:
            f.timings_ms = {"detect": (t1 - t0) * 1e3, "embed_all": (t2 - t1) * 1e3}
        return faces


def face_quality(f: Face) -> float:
    """0..1: detector score x size factor x pose factor.

    Size saturates at 40 px IPD; pose falls off past 30 deg pitch/yaw
    (2026-10-26 survey: MobileFaceNet degrades past 15-30 deg upward pitch).
    """
    size = min(1.0, max(0.0, (f.ipd_px - MIN_IPD_PX) / (40.0 - MIN_IPD_PX)))
    pose = math.exp(-((max(0.0, abs(f.pitch_deg) - 15) / 20.0) ** 2)
                    - ((max(0.0, abs(f.yaw_deg) - 20) / 25.0) ** 2))
    return float(f.score * (0.3 + 0.7 * size) * pose)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Run face detection+embedding on images")
    ap.add_argument("images", nargs="+")
    a = ap.parse_args()
    fp = FacePipeline()
    for p in a.images:
        img = cv2.imread(p)
        faces = fp.analyze(img)
        print(f"{p}: {len(faces)} faces")
        for f in faces:
            print(f"  score={f.score:.2f} ipd={f.ipd_px:.1f}px pitch={f.pitch_deg:+.0f} "
                  f"yaw={f.yaw_deg:+.0f} usable={f.usable} q={f.quality:.2f} {f.timings_ms}")

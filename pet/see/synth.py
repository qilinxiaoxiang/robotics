#!/usr/bin/env python3
"""Build the evidence frame set in pet/see/out/frames/: the real head-camera snapshots that exist on this Mac, plus
synthetic frames made by pasting cut-outs of Shawn's own photos (the duck's orange printed parts, its feet, a bucket)
and drawn household objects onto the real floor frame. Every frame carries its provenance in manifest.json:
"real" or "synthetic", the source files, the pasted object boxes (ground truth) and the duck's own-body mask.

    ~/.venvs/duck-see/bin/python pet/see/synth.py            # writes out/frames/*.png, manifest.json, cutouts.jpg

Real snapshots (640 x 360 upright BGR as a7z_cam.py publishes them, except u20 which is the raw 1280 x 720):
  floor      concrete floor, green bin, shoes at the top        (a7z_cam --snap, 2026-10-26 session scratchpad)
  table      table top with the black USB cable                  (output/u20cam-a7z-20261026.jpg, raw 1280 x 720)
  sleeve     overexposed, a hand and a sleeve close to the lens  (same session)
  blur       motion blur, the duck's own orange hip parts at the left edge (same session)
Cut-out sources (Shawn's photos): output/shoot-20261024/hero-walk.jpg (orange hip covers, feet),
  microduck-sim/guide/firmware/mac/robot-runs-20261023-a7z/sit-headbump/photos-20261023/IMG_7104-closed-loop.jpg
  (orange ankle part, white bucket).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out" / "frames"
SCRATCH = Path("/private/tmp/claude-501/-Users-xiangzheng-code-robotics/3f6a95fd-ae2f-424f-946f-d0d0633bfb1d/scratchpad")
REAL = {   # name -> (source path, note)
    "floor": (SCRATCH / "snap_rot.jpg", "a7z_cam --snap, floor, green bin, shoes above the horizon"),
    "table": (ROOT / "output/u20cam-a7z-20261026.jpg", "raw 1280x720 camera frame, table with a black USB cable"),
    "sleeve": (SCRATCH / "snap_u20.jpg", "overexposed hand and sleeve close to the lens"),
    "blur": (SCRATCH / "web_frame.jpg", "motion blur, the duck's own orange hip covers at the left edge"),
}
HERO = ROOT / "output/shoot-20261024/hero-walk.jpg"
IMG7104 = ROOT / "microduck-sim/guide/firmware/mac/robot-runs-20261023-a7z/sit-headbump/photos-20261023/IMG_7104-closed-loop.jpg"
# cut-out rectangles (x0, y0, x1, y1) in the source pictures
CUTS = {
    "orange_hip_left": (HERO, (900, 625, 1005, 705), "orange printed hip cover (hero-walk)"),
    "orange_hip_right": (HERO, (1025, 625, 1115, 705), "orange printed hip cover (hero-walk)"),
    "foot_left": (HERO, (860, 795, 990, 910), "duck's own left foot, orange ankle + yellow sole (hero-walk)"),
    "foot_right": (HERO, (1035, 795, 1175, 910), "duck's own right foot (hero-walk)"),
    "orange_ankle": (IMG7104, (715, 935, 985, 1095), "orange printed ankle part on a yellow sole (IMG_7104)"),
    "bucket": (IMG7104, (1085, 310, 1310, 950), "white bucket, right half (IMG_7104)"),
}
# floor is seen from about 15 cm with a 120 deg lens: a 4 cm object 25 cm ahead is ~45 px wide at row ~230,
# 15 cm ahead ~80 px at row ~300. The paste height scales with the row the object's base sits on.


def grabcut(img, rect, iters=5):
    """Foreground mask of the object inside rect (soft edge), BGR cut-out and alpha."""
    x0, y0, x1, y1 = rect
    sub = img[y0:y1, x0:x1].copy()
    mask = np.zeros(sub.shape[:2], np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    m = 3
    r = (m, m, sub.shape[1] - 2 * m, sub.shape[0] - 2 * m)
    cv2.grabCut(sub, mask, r, bgd, fgd, iters, cv2.GC_INIT_WITH_RECT)
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(fg)
    if n > 2:
        k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        fg = np.where(lab == k, 255, 0).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    alpha = cv2.GaussianBlur(fg, (3, 3), 0)
    ys, xs = np.nonzero(alpha > 20)
    if xs.size == 0:
        return sub, np.full(sub.shape[:2], 255, np.uint8)
    cy0, cy1, cx0, cx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return sub[cy0:cy1, cx0:cx1], alpha[cy0:cy1, cx0:cx1]


def paste(frame, cut, alpha, base_x, base_y, height_px, shade=1.0):
    """Paste the cut-out with its bottom centre at (base_x, base_y), scaled to height_px. Returns the pasted bbox."""
    s = height_px / cut.shape[0]
    w, h = max(2, int(round(cut.shape[1] * s))), max(2, int(round(cut.shape[0] * s)))
    c = cv2.resize(cut, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) * shade
    a = cv2.resize(alpha, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255.0
    x0, y0 = int(round(base_x - w / 2)), int(round(base_y - h))
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(frame.shape[1], x0 + w), min(frame.shape[0], y0 + h)
    if X1 <= X0 or Y1 <= Y0:
        return None
    cc, aa = c[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0], a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    frame[Y0:Y1, X0:X1] = (cc * aa + frame[Y0:Y1, X0:X1].astype(np.float32) * (1 - aa)).clip(0, 255).astype(np.uint8)
    # shadow under the base
    cv2.ellipse(frame, (int(base_x), int(base_y)), (w // 2, max(2, h // 12)), 0, 0, 360, (0, 0, 0), -1)
    frame[Y0:Y1, X0:X1] = (cc * aa + frame[Y0:Y1, X0:X1].astype(np.float32) * (1 - aa)).clip(0, 255).astype(np.uint8)
    return (X0, Y0, X1 - X0, Y1 - Y0)


def draw_ball(d, colour):
    img = np.zeros((d, d, 3), np.uint8)
    alpha = np.zeros((d, d), np.uint8)
    cv2.circle(alpha, (d // 2, d // 2), d // 2 - 1, 255, -1)
    yy, xx = np.mgrid[0:d, 0:d]
    light = (1.0 - 0.6 * np.hypot(xx - d * 0.38, yy - d * 0.35) / d).clip(0.35, 1.0)
    for c in range(3):
        img[..., c] = (colour[c] * light).clip(0, 255)
    cv2.circle(img, (int(d * 0.36), int(d * 0.32)), max(1, d // 10), (255, 255, 255), -1)
    return img, alpha


def draw_remote(w, h):
    img = np.full((h, w, 3), 35, np.uint8)
    alpha = np.zeros((h, w), np.uint8)
    cv2.rectangle(alpha, (0, 0), (w - 1, h - 1), 255, -1)
    cv2.rectangle(img, (0, 0), (w - 1, h - 1), (60, 60, 60), 2)
    for i in range(3):
        for j in range(5):
            cx, cy = int(w * (0.25 + 0.25 * i)), int(h * (0.2 + 0.15 * j))
            cv2.circle(img, (cx, cy), max(2, w // 10), (120, 120, 120), -1)
    cv2.circle(img, (w // 2, int(h * 0.1)), max(2, w // 8), (0, 0, 200), -1)
    return img, alpha


def draw_keys(w, h):
    img = np.zeros((h, w, 3), np.uint8)
    alpha = np.zeros((h, w), np.uint8)
    cv2.circle(alpha, (int(w * 0.25), int(h * 0.3)), int(h * 0.25), 255, 3)
    cv2.circle(img, (int(w * 0.25), int(h * 0.3)), int(h * 0.25), (200, 200, 200), 3)
    for k, ang in enumerate((-20, 10, 40)):
        p0 = (int(w * 0.35), int(h * 0.4))
        L = int(w * 0.6)
        p1 = (int(p0[0] + L * np.cos(np.radians(ang))), int(p0[1] + L * np.sin(np.radians(ang))))
        col = (170, 170, 170) if k != 1 else (90, 160, 200)
        cv2.line(img, p0, p1, col, max(3, h // 8))
        cv2.line(alpha, p0, p1, 255, max(3, h // 8))
        cv2.circle(img, p0, max(3, h // 6), col, -1)
        cv2.circle(alpha, p0, max(3, h // 6), 255, -1)
    return img, alpha


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    manifest = {"frames": []}
    for name, (src, note) in REAL.items():
        img = cv2.imread(str(src))
        assert img is not None, src
        cv2.imwrite(str(OUT / f"real_{name}.png"), img)
        manifest["frames"].append({"file": f"real_{name}.png", "kind": "real", "source": str(src), "note": note,
                                   "shape": list(img.shape[:2]), "objects": [], "body_mask": None})
    cuts = {}
    for cname, (src, rect, note) in CUTS.items():
        img = cv2.imread(str(src))
        assert img is not None, src
        cuts[cname] = grabcut(img, rect) + (note,)
    drawn = {"ball_red": draw_ball(90, (40, 40, 220)) + ("drawn red ball",),
             "ball_tennis": draw_ball(90, (80, 230, 220)) + ("drawn tennis ball",),
             "remote": draw_remote(40, 150) + ("drawn remote control",),
             "keys": draw_keys(150, 110) + ("drawn bunch of keys",)}
    # cut-out preview sheet
    tiles = []
    for k, (c, a, note) in {**cuts, **drawn}.items():
        t = cv2.resize(cv2.cvtColor(a, cv2.COLOR_GRAY2BGR) // 2 + c // 2, (160, 160))
        cv2.putText(t, k, (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        tiles.append(t)
    while len(tiles) % 5:
        tiles.append(np.zeros((160, 160, 3), np.uint8))
    cv2.imwrite(str(OUT / "cutouts.jpg"), np.vstack([np.hstack(tiles[i:i + 5]) for i in range(0, len(tiles), 5)]))

    floor = cv2.imread(str(REAL["floor"][0]))
    H, W = floor.shape[:2]
    rng = np.random.default_rng(7)

    def body_mask_feet(frame):
        """The duck's own feet as they appear in a head-down frame: bottom corners."""
        m = np.zeros(frame.shape[:2], np.uint8)
        bl = paste(frame, *cuts["foot_left"][:2], base_x=150, base_y=H + 8, height_px=95, shade=0.92)
        br = paste(frame, *cuts["foot_right"][:2], base_x=500, base_y=H + 8, height_px=95, shade=0.92)
        for b in (bl, br):
            if b:
                x, y, w, h = b
                m[y:y + h, x:x + w] = 255
        return m

    def frame_with(objs, with_feet, name, note):
        """objs: [(cut key, prompt, base_x, base_y)]; pasted height follows the row (perspective)."""
        f = floor.copy()
        rec = {"file": name, "kind": "synthetic", "source": str(REAL["floor"][0]), "note": note,
               "shape": [H, W], "objects": [], "body_mask": None}
        for key, prompt, bx, by in objs:
            c, a, cnote = (cuts | drawn)[key]
            hp = int(np.interp(by, [150, 200, 260, 330], [22, 40, 70, 110]) * (1.0 if key != "bucket" else 1.8))
            b = paste(f, c, a, bx, by, hp, shade=0.95)
            if b:
                rec["objects"].append({"prompt": prompt, "bbox": list(b), "cutout": key, "cutout_note": cnote})
        if with_feet:
            m = body_mask_feet(f)
            mp = name.replace(".png", "_body.png")
            cv2.imwrite(str(OUT / mp), m)
            rec["body_mask"] = mp
        cv2.imwrite(str(OUT / name), f)
        manifest["frames"].append(rec)

    # orange printed part on the floor, ten placements, four with the duck's own feet in view
    places = [(320, 300), (420, 240), (210, 260), (520, 320), (120, 230), (330, 190), (450, 285), (250, 330),
              (380, 215), (560, 250)]
    for i, (bx, by) in enumerate(places):
        key = ("orange_hip_left", "orange_hip_right", "orange_ankle")[i % 3]
        frame_with([(key, "orange block", bx, by)], with_feet=(i % 3 == 0), name=f"synth_orange_{i:02d}.png",
                   note="orange printed part pasted on the real floor frame" + (", duck's own feet pasted at the "
                                                                                 "bottom" if i % 3 == 0 else ""))
    # household objects: three drawn ones and one real cut-out (bucket), each alone and once together
    singles = [("ball_red", "small ball", 300, 280), ("ball_tennis", "small ball", 400, 240),
               ("remote", "remote control", 330, 300), ("keys", "keys", 250, 290), ("bucket", "bucket", 480, 260),
               ("keys", "keys", 420, 250), ("remote", "remote control", 200, 240)]
    for i, (key, prompt, bx, by) in enumerate(singles):
        frame_with([(key, prompt, bx, by)], with_feet=(i % 2 == 1), name=f"synth_{prompt.replace(' ', '_')}_{i:02d}.png",
                   note=f"{key} pasted on the real floor frame" + (", duck's own feet in view" if i % 2 else ""))
    frame_with([("orange_hip_left", "orange block", 200, 300), ("ball_red", "small ball", 330, 250),
                ("keys", "keys", 470, 290), ("remote", "remote control", 560, 230)], with_feet=True,
               name="synth_mixed_00.png", note="four objects at once, feet in view")
    # feet only: the own-body false-positive frames (no object)
    for i in range(3):
        f = floor.copy()
        if i == 2:
            f = cv2.convertScaleAbs(f, alpha=0.8, beta=-10)
        m = body_mask_feet(f)
        cv2.imwrite(str(OUT / f"synth_feet_only_{i:02d}_body.png"), m)
        cv2.imwrite(str(OUT / f"synth_feet_only_{i:02d}.png"), f)
        manifest["frames"].append({"file": f"synth_feet_only_{i:02d}.png", "kind": "synthetic",
                                   "source": str(REAL["floor"][0]), "note": "no object, only the duck's own feet",
                                   "shape": [H, W], "objects": [], "body_mask": f"synth_feet_only_{i:02d}_body.png"})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    n_real = sum(f["kind"] == "real" for f in manifest["frames"])
    print(f"{len(manifest['frames'])} frames ({n_real} real, {len(manifest['frames']) - n_real} synthetic) in {OUT}")


if __name__ == "__main__":
    main()

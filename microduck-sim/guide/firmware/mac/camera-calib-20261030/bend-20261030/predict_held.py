"""Project the ruler into held-phase frames with a fitted parameter set and compare with the detected tick rows, to
see which ticks (mm, 5 mm, cm) the picture shows and whether their identity can be locked.

usage: python predict_held.py FIT_JSON MODEL OUT_DIR [frame ...]
Prints per frame: predicted row v and column u of every cm tick and 5 mm tick on the scale edge (y = -0.0093,
z = 1.6 mm), the predicted mm spacing in rows near the picture middle, the detected scale-edge column and the detected
tick rows from bend_ticks.json; writes OUT_DIR/pred_<frame>.png with the predicted ruler drawn over the frame.
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bendfit  # noqa: E402
import cam_calib  # noqa: E402

DEFAULT = ["f011960", "f011980", "f012010", "f012027", "f012045", "f012063", "f012080", "f012098"]


def main():
    fit_path, model, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    frames = sys.argv[4:] or DEFAULT
    os.makedirs(out_dir, exist_ok=True)
    params = json.load(open(fit_path))["models"][model]["params"] if model != "current" else {}
    kin = bendfit.BendKin()
    kin.set_params(params)
    ticks = json.load(open(os.path.join(HERE, "bend_ticks.json")))
    # frames of sweep1 live in frames/ with rows_matched.json; sweeps 2-4 in sweepN/ with their own rows_matched.json
    rows = {}
    for sweep, sub, fdir in (("sweep1", "rows_matched.json", "frames"), ("sweep2", "sweep2/rows_matched.json", "sweep2"),
                             ("sweep3", "sweep3/rows_matched.json", "sweep3"), ("sweep4", "sweep4/rows_matched.json", "sweep4")):
        for r in json.load(open(os.path.join(HERE, sub))):
            rows.setdefault(r["name"], dict(r, sweep=sweep, fdir=fdir))
    for name in frames:
        r = rows[name]
        q, gb = r["q"], r["gb"]
        tx = cam_calib.toe_x(kin, q, gb)
        pos, R = kin.camera_pose(q, gb)
        im = cv2.imread(os.path.join(HERE, r["fdir"], f"{name}.png"))
        y_edge = kin.y_edge(tx, tx, r["sweep"])
        print(f"\n{name} {r['sweep']} phase {r.get('cmd_phase', r.get('phase'))} neck {q['neck_pitch']:+.3f} head "
              f"{q['head_pitch']:+.3f} gb {gb} | cam pos {np.round(pos, 4).tolist()} toe_x {tx:.4f} y_edge {y_edge:+.4f}")
        pred = {}
        for k10 in range(0, 310):          # mm steps
            mm = k10
            uv = kin.ground_to_pixel(tx + mm / 1000, y_edge, q, gb, 640, 360, z=bendfit.BOARD)
            if uv is None:
                continue
            pred[mm] = uv
            if 0 <= uv[1] <= 360 and 0 <= uv[0] <= 700:
                long = mm % 10 == 0
                mid = mm % 5 == 0
                L = 24 if long else (14 if mid else 7)
                cv2.line(im, (int(uv[0]), int(uv[1])), (int(uv[0]) + L, int(uv[1])), (0, 255, 255), 1)
                if long:
                    cv2.putText(im, str(mm // 10), (int(uv[0]) - 22, int(uv[1]) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        vis = {mm: uv for mm, uv in pred.items() if -20 <= uv[1] <= 380 and 0 <= uv[0] <= 660}
        cm_rows = {mm // 10: (round(uv[0], 1), round(uv[1], 1)) for mm, uv in vis.items() if mm % 10 == 0}
        print("  predicted cm ticks (u, v):", cm_rows)
        mms = sorted(vis)
        if len(mms) > 2:
            sp = [vis[b][1] - vis[a][1] for a, b in zip(mms, mms[1:])]
            print(f"  predicted mm spacing along the edge: {np.round(sp[:: max(1, len(sp)//8)], 1).tolist()} px (top .. bottom order by mm)")
        det = ticks["detail"].get(name)
        if det:
            e = det["edge"]
            print("  detected edge u at v=50/180/300:", {v: round(e.get(str(v), float('nan')), 1) for v in (50, 180, 300)},
                  "| detected tick rows:", [round(p) for p in det["peaks"]])
            for v in range(0, 360, 2):
                if str(v) in e:
                    cv2.circle(im, (int(round(e[str(v)])), v), 0, (0, 255, 0), -1)
        cv2.imwrite(os.path.join(out_dir, f"pred_{name}.png"), im)


if __name__ == "__main__":
    main()

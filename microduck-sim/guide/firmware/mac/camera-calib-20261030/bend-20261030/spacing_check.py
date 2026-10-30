"""Picture-scale check of a fitted model: the mm-tick spacing the model predicts along the scale edge against the
spacing the pictures show, per read frame. A model can put two ticks at the right floor x and still be wrong about
how close the camera is to the ruler; the row spacing per mm (px/mm) at the ruler tells that directly.

usage: python spacing_check.py FIT_JSON MODEL        (MODEL = current for the mount file as it is)
Per frame: camera height over the floor and the off-vertical angle of the ray to the ruler in the model, the
predicted row of each read cm tick, the predicted px/mm between the read ticks, the detected px/mm (row difference
of the read ticks / 10 mm per cm) and the ratio detected / predicted.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bendfit  # noqa: E402

FRAMES = ["f012112", "f012116", "f091060", "f091111", "f093206", "f093294", "f093320"]


def main():
    fit_path, model = sys.argv[1], sys.argv[2]
    params = json.load(open(fit_path))["models"][model]["params"] if model != "current" else {}
    kin = bendfit.BendKin()
    kin.set_params(params)
    ticks = json.load(open(os.path.join(HERE, "bend_ticks.json")))
    by_frame = {}
    for o in ticks["obs"]:
        if o["cm"] is not None:
            by_frame.setdefault(o["frame"], []).append(o)
    ratios = []
    for name in FRAMES:
        rows = sorted(by_frame[name], key=lambda o: o["cm"])
        o0, o1 = rows[0], rows[-1]
        q, gb, sweep = o0["q"], o0["gb"], o0.get("sweep", "sweep1")
        tx = kin.toe_x(q, gb)
        ye = kin.y_edge(tx, tx, sweep)
        pos, R = kin.camera_pose(q, gb)
        pred = {}
        for o in rows:
            uv = kin.ground_to_pixel(tx + o["cm"] / 100, ye, q, gb, 640, 360, z=bendfit.BOARD)
            pred[o["cm"]] = uv
        # ray angle from vertical at the middle tick
        xm = tx + (o0["cm"] + o1["cm"]) / 200
        d = np.array([xm, ye, bendfit.BOARD]) - pos
        ang = math.degrees(math.atan2(math.hypot(d[0], d[1]), -d[2]))
        pp = abs(pred[o1["cm"]][1] - pred[o0["cm"]][1]) / (10 * (o1["cm"] - o0["cm"]))
        dp = abs(o1["v"] - o0["v"]) / (10 * (o1["cm"] - o0["cm"]))
        ratios.append(dp / pp)
        print(f"{name} {sweep} cm {o0['cm']}..{o1['cm']}: camera {pos[2]*100:.2f} cm over the floor, ray {ang:.0f} deg "
              f"off vertical, dist {np.linalg.norm(d)*100:.2f} cm | predicted rows "
              f"{ {c: round(float(uv[1])) for c, uv in pred.items()} } vs read { {o['cm']: round(o['v']) for o in rows} } | "
              f"px/mm predicted {pp:.1f} detected {dp:.1f} ratio {dp/pp:.2f}")
    print(f"mean detected/predicted px per mm: {np.mean(ratios):.2f}")


if __name__ == "__main__":
    main()

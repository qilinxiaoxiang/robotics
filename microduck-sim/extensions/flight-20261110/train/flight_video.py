"""Record one probe episode (flight_eval.episode, same flags) as an mp4 plus a key-frame png, camera following the duck.

  $PY train/flight_video.py --models <dir> --manifest <pack manifest> --case walk --seed 0 --out train/video/<name> \
      [--key-t 10] [--landing] [--shove-ns 0.5]
Writes <out>.mp4 (25 fps, 640x480) and <out>_t<key>.png. Needs an OpenGL context (run on the Mac mini or locally).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flight_eval as fe  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--case", choices=sorted(fe.CASES), required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--key-t", type=float, default=10.0)
    ap.add_argument("--landing", action="store_true")
    ap.add_argument("--shove-ns", type=float, default=0.0)
    ap.add_argument("--shove-at", type=float, default=8.0)
    ap.add_argument("--extra", default="", help="probe flags appended last, e.g. '--stand-s 0' (as in the with-pack evals)")
    a = ap.parse_args()
    import imageio
    import mujoco
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    st = dict(r=None, w=None, next_t=0.0, cam=None, key=False)

    def hook(m, d, t):
        if st["r"] is None:
            st["r"] = mujoco.Renderer(m, 480, 640)
            st["w"] = imageio.get_writer(str(out) + ".mp4", fps=25, codec="libx264", quality=8)
            cam = mujoco.MjvCamera()
            cam.type = mujoco.mjtCamera.mjCAMERA_FREE
            cam.distance, cam.azimuth, cam.elevation = 0.75, 135.0, -18.0
            st["cam"] = cam
            st["trunk"] = m.body("trunk_base").id
        if t + 1e-9 < st["next_t"]:
            return
        st["next_t"] += 0.04
        st["cam"].lookat[:] = d.xpos[st["trunk"]] * np.array([1, 1, 0]) + np.array([0, 0, 0.12])
        st["r"].update_scene(d, camera=st["cam"])
        img = st["r"].render()
        st["w"].append_data(img)
        if not st["key"] and t >= a.key_t:
            imageio.imwrite(str(out) + f"_t{a.key_t:g}.png", img)
            st["key"] = True

    fe.FRAME_HOOK = hook
    r = fe.episode((str(Path(a.models).resolve()), str(Path(a.manifest).resolve()), a.case, a.seed, a.shove_ns, a.shove_at, a.landing,
                    a.extra.split()))
    if st["w"] is not None:
        st["w"].close()
    r["video"] = str(out) + ".mp4"
    r["keyframe"] = str(out) + f"_t{a.key_t:g}.png" if st["key"] else None
    print(json.dumps(r))


if __name__ == "__main__":
    main()

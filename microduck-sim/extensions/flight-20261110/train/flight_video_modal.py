"""Render flight_video.py episodes on a Modal CPU container (software OpenGL, OSMesa): the Mac mini is saturated and the
MacBook swaps. Same layers as flight_eval_modal.py plus OSMesa.

  modal run train/flight_video_modal.py --models ckpt/fw1_1000 --manifest manifests/flightpack-nominal.json \
      --case walk --seed 0 --name fw1_1000_walk [--key-t 10] [--landing] [--extra "--stand-s 0"]
Writes train/video/<name>.mp4, <name>_t<key>.png and <name>.json (the episode record).

Container start: Modal mounts only this file at /root, so the sibling module flight_eval_modal is shipped with
add_local_python_source (2026-11-10 20:27 the first version crash-looped on ModuleNotFoundError). The image build
renders one frame of a trivial model under OSMesa, so a missing GL library fails the build, never the container
start. retries=0 and a 20-minute timeout: a failure ends the call instead of looping.
"""
import json
import sys
from pathlib import Path

import modal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flight_eval_modal as fem  # noqa: E402

GL_CHECK = ("python -c \"import mujoco, imageio, imageio_ffmpeg; m = mujoco.MjModel.from_xml_string("
            "'<mujoco><worldbody><geom size=\\'.1\\'/></worldbody></mujoco>'); d = mujoco.MjData(m); "
            "r = mujoco.Renderer(m, 48, 64); r.update_scene(d); print('osmesa render ok', r.render().shape)\"")
image = (fem.make_image(apt=("libosmesa6", "libgl1"), env={"MUJOCO_GL": "osmesa", "PYOPENGL_PLATFORM": "osmesa"},
                        check=GL_CHECK)
         .add_local_python_source("flight_eval_modal"))
app = modal.App("microduck-flight-video", image=image)


@app.function(cpu=2.0, memory=2048, timeout=1200, retries=0)
def render(models: str, manifest: str, case: str, seed: int, key_t: float, landing: bool, extra: list) -> dict:
    import subprocess
    out = "/tmp/vid"
    cmd = [sys.executable, str(fem.TRAIN / "flight_video.py"), "--models", str(fem.TRAIN / models), "--manifest",
           str(fem.TRAIN / manifest), "--case", case, "--seed", str(seed), "--out", out, "--key-t", str(key_t)]
    cmd += ["--landing"] if landing else []
    cmd += ["--extra=" + " ".join(extra)] if extra else []
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(fem.TRAIN))
    if p.returncode:
        raise RuntimeError(p.stderr[-3000:])
    rec = json.loads(p.stdout.strip().splitlines()[-1])
    files = {Path(f).name: Path(f).read_bytes() for f in (rec.get("video"), rec.get("keyframe")) if f}
    return dict(record=rec, files=files)


@app.local_entrypoint()
def main(models: str, manifest: str, case: str, name: str, seed: int = 0, key_t: float = 10.0, landing: bool = False,
         extra: str = "--stand-s 0"):
    r = render.remote(models, manifest, case, seed, key_t, landing, extra.split())
    out = fem.HERE / "video"
    out.mkdir(exist_ok=True)
    for fn, data in r["files"].items():
        (out / fn.replace("vid", name, 1)).write_bytes(data)
    rec = r["record"]
    rec["video"] = str(out / f"{name}.mp4")
    rec["keyframe"] = str(out / f"{name}_t{key_t:g}.png")
    rec.pop("per_joint_all", None)
    (out / f"{name}.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ("fell_at", "speed", "dist_x", "video", "keyframe")}))

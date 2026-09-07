"""Exercise actual dynamics, rendering, a standard environment and dataset I/O."""
import json
import subprocess
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

import mujoco
import numpy as np
import torch

from download_model import main as verify_model

ROOT = Path(__file__).resolve().parent

def main():
    verify_model()
    model = mujoco.MjModel.from_xml_path(str(ROOT / "models/robotstudio_so101/scene_box.xml"))
    data = mujoco.MjData(model)
    data.qpos[:6] = [0, -.35, .65, .8, 0, .8]
    data.ctrl[:] = data.qpos[:6]
    data.qpos[6:13] = [.22, .02, .03, 1, 0, 0, 0]
    initial = (data.qpos.copy(), data.qvel.copy(), data.ctrl.copy())
    controls = np.tile(initial[2], (20, 1)).astype(np.float32)
    controls[5:10, 0] = .3
    controls[10:, 0] = -.2
    positions, images, tips = [], [], []
    renderer = mujoco.Renderer(model, height=240, width=320)
    camera = mujoco.MjvCamera()
    camera.lookat[:] = [.12, 0, .14]
    camera.distance, camera.azimuth, camera.elevation = .85, 130, -25
    for action in controls:
        data.ctrl[:] = action
        mujoco.mj_forward(model, data)
        positions.append(data.qpos[:6].astype(np.float32).copy())
        tips.append(data.site("gripperframe").xpos.copy())
        renderer.update_scene(data, camera=camera)
        images.append(renderer.render().copy())
        mujoco.mj_step(model, data, nstep=20)
    renderer.close()
    assert np.std(images[0]) > 10, "Blank rendering"
    movement = float(np.max(np.linalg.norm(np.asarray(tips) - tips[0], axis=1)))
    assert movement > .02, "Control did not move the end effector"
    mujoco.mj_resetData(model, data)
    data.qpos[:], data.qvel[:], data.ctrl[:] = initial
    replay_error = 0.
    for action, expected in zip(controls, positions, strict=True):
        data.ctrl[:] = action
        mujoco.mj_forward(model, data)
        replay_error = max(replay_error, float(np.max(np.abs(data.qpos[:6] - expected))))
        mujoco.mj_step(model, data, nstep=20)
    assert replay_error < .001
    with tempfile.TemporaryDirectory(prefix="so101-verify-") as directory:
        source = Path(directory) / "verification-demo.npz"
        np.savez_compressed(source, state=np.asarray(positions), action=controls, images=np.asarray(images),
            initial_qpos=initial[0], initial_qvel=initial[1], initial_ctrl=initial[2], fps=10,
            task="Software verification motion; not a successful grasp demonstration")
        exported = subprocess.run([sys.executable, str(ROOT / "export_dataset.py"), str(source)],
                                  capture_output=True, text=True)
        if exported.returncode:
            raise RuntimeError(exported.stdout + exported.stderr)
        assert "Saved and read back 20 frames" in exported.stdout
    import gymnasium
    import gym_pusht  # Registers the official PushT environment.
    from lerobot.policies.act.modeling_act import ACTPolicy
    env = gymnasium.make("gym_pusht/PushT-v0", render_mode="rgb_array")
    env.reset(seed=42)
    _, reward, _, _, _ = env.step(env.action_space.sample())
    frame_shape = list(env.render().shape)
    env.close()
    report = {"verified_date": "2026-09-07", "python": sys.version.split()[0],
        "versions": {key: version(key) for key in ("lerobot", "mujoco", "torch", "gym-pusht")},
        "mps_available": torch.backends.mps.is_available(), "render_shape": [240, 320, 3],
        "end_effector_movement_m": movement, "replay_max_joint_error_rad": replay_error,
        "lerobot_dataset_written_and_read_frames": 20, "pusht_render_shape": frame_shape,
        "pusht_step_reward": float(reward), "act_policy_import": ACTPolicy.__name__,
        "limits": ["No trained policy", "No grasp success claim", "No hardware validation", "No paid service"]}
    (ROOT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()

"""Small, observable experiments for building MuJoCo intuition."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import gymnasium as gym
import imageio.v2 as imageio
import matplotlib
import mujoco
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models"
DEFAULT_ARTIFACT_DIR = ROOT / "artifacts"


def _write_video(path: Path, frames: list[np.ndarray], fps: int) -> None:
    if not frames:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(path, frames, fps=fps, quality=8)


def simulate_arm(
    mode: str,
    duration: float = 3.0,
    video_path: Path | None = None,
) -> dict[str, Any]:
    """Run the same arm passively or with a simple feedback controller."""
    if mode not in {"passive", "pd"}:
        raise ValueError(f"Unknown arm mode: {mode}")

    model = mujoco.MjModel.from_xml_path(str(MODEL_DIR / "one_joint_arm.xml"))
    data = mujoco.MjData(model)
    target = math.radians(30.0)
    data.qpos[0] = math.radians(70.0)
    mujoco.mj_forward(model, data)

    renderer = None
    frames: list[np.ndarray] = []
    if video_path is not None:
        renderer = mujoco.Renderer(model, height=480, width=640)
    render_stride = max(1, round((1 / 30) / model.opt.timestep))

    times: list[float] = []
    angles: list[float] = []
    velocities: list[float] = []
    controls: list[float] = []
    tip_heights: list[float] = []
    step = 0

    while data.time < duration:
        if mode == "pd":
            # PD means proportional-derivative: position error plus velocity damping.
            # Bias-force feedforward cancels modeled gravity instead of hiding it
            # behind a very large feedback gain.
            command = (
                12.0 * (target - data.qpos[0])
                - 3.0 * data.qvel[0]
                + data.qfrc_bias[0]
            )
            data.ctrl[0] = np.clip(command, -5.0, 5.0)
        else:
            data.ctrl[0] = 0.0

        mujoco.mj_step(model, data)
        times.append(float(data.time))
        angles.append(float(data.qpos[0]))
        velocities.append(float(data.qvel[0]))
        controls.append(float(data.ctrl[0]))
        tip_heights.append(float(data.site("tip").xpos[2]))

        if renderer is not None and step % render_stride == 0:
            renderer.update_scene(data, camera="overview")
            frames.append(renderer.render().copy())
        step += 1

    if renderer is not None:
        renderer.close()
        _write_video(video_path, frames, fps=30)

    return {
        "mode": mode,
        "target_rad": target,
        "time": np.asarray(times),
        "angle": np.asarray(angles),
        "velocity": np.asarray(velocities),
        "control": np.asarray(controls),
        "tip_height": np.asarray(tip_heights),
        "model": {
            "nq": model.nq,
            "nv": model.nv,
            "nu": model.nu,
            "timestep": float(model.opt.timestep),
        },
    }


def simulate_contact(
    duration: float = 1.5,
    video_path: Path | None = None,
) -> dict[str, Any]:
    """Drop a ball and measure when contact and contact force appear."""
    model = mujoco.MjModel.from_xml_path(str(MODEL_DIR / "ball_drop.xml"))
    data = mujoco.MjData(model)
    ball_id = model.body("ball").id

    renderer = None
    frames: list[np.ndarray] = []
    if video_path is not None:
        renderer = mujoco.Renderer(model, height=480, width=640)
    render_stride = max(1, round((1 / 30) / model.opt.timestep))

    times: list[float] = []
    heights: list[float] = []
    normal_forces: list[float] = []
    first_contact_time: float | None = None
    step = 0

    while data.time < duration:
        mujoco.mj_step(model, data)
        total_normal_force = 0.0
        for contact_index in range(data.ncon):
            contact_force = np.zeros(6, dtype=np.float64)
            mujoco.mj_contactForce(model, data, contact_index, contact_force)
            total_normal_force += max(0.0, float(contact_force[0]))
        if data.ncon and first_contact_time is None:
            first_contact_time = float(data.time)

        times.append(float(data.time))
        heights.append(float(data.xpos[ball_id, 2]))
        normal_forces.append(total_normal_force)

        if renderer is not None and step % render_stride == 0:
            renderer.update_scene(data, camera="overview")
            frames.append(renderer.render().copy())
        step += 1

    if renderer is not None:
        renderer.close()
        _write_video(video_path, frames, fps=30)

    return {
        "time": np.asarray(times),
        "height": np.asarray(heights),
        "normal_force": np.asarray(normal_forces),
        "first_contact_time": first_contact_time,
        "max_normal_force": float(np.max(normal_forces)),
    }


def run_gym_bridge(
    steps: int = 120,
    video_path: Path | None = None,
) -> dict[str, Any]:
    """Expose the observation-action-reward loop used by robot-learning code."""
    render_mode = "rgb_array" if video_path is not None else None
    env = gym.make(
        "Reacher-v5",
        render_mode=render_mode,
        width=640,
        height=480,
    )
    observation, _ = env.reset(seed=7)
    env.action_space.seed(7)
    frames: list[np.ndarray] = []
    rewards: list[float] = []

    for step in range(steps):
        # Random control is intentionally bad; it makes the policy's job visible.
        action = env.action_space.sample()
        observation, reward, terminated, truncated, _ = env.step(action)
        rewards.append(float(reward))
        if video_path is not None and step % 2 == 0:
            frames.append(env.render().copy())
        if terminated or truncated:
            observation, _ = env.reset()

    summary = {
        "environment": "Reacher-v5",
        "observation_shape": list(observation.shape),
        "action_shape": list(env.action_space.shape),
        "action_low": env.action_space.low.tolist(),
        "action_high": env.action_space.high.tolist(),
        "steps": steps,
        "total_reward": float(np.sum(rewards)),
        "mean_reward": float(np.mean(rewards)),
    }
    env.close()

    if video_path is not None:
        _write_video(video_path, frames, fps=30)
    return summary


def _plot_arm(passive: dict[str, Any], controlled: dict[str, Any], path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    axes[0].plot(passive["time"], np.degrees(passive["angle"]), label="Passive")
    axes[0].plot(
        controlled["time"],
        np.degrees(controlled["angle"]),
        label="PD + gravity compensation",
    )
    axes[0].axhline(np.degrees(controlled["target_rad"]), color="black", linestyle="--", label="Target")
    axes[0].set_ylabel("Joint angle (degrees)")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].plot(controlled["time"], controlled["control"], color="tab:orange")
    axes[1].set_xlabel("Simulation time (seconds)")
    axes[1].set_ylabel("Motor command")
    axes[1].grid(alpha=0.3)
    fig.suptitle("Same body, different control law")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _plot_contact(contact: dict[str, Any], path: Path) -> None:
    fig, axis_height = plt.subplots(figsize=(10, 5))
    axis_force = axis_height.twinx()
    axis_height.plot(contact["time"], contact["height"], color="tab:blue", label="Ball height")
    axis_force.plot(contact["time"], contact["normal_force"], color="tab:red", alpha=0.8, label="Normal force")
    axis_height.set_xlabel("Simulation time (seconds)")
    axis_height.set_ylabel("Ball height (meters)", color="tab:blue")
    axis_force.set_ylabel("Normal contact force (newtons)", color="tab:red")
    axis_height.grid(alpha=0.3)
    fig.suptitle("Contact is a short, high-force event")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_all(artifact_dir: Path, make_videos: bool = True) -> dict[str, Any]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    arm_video = artifact_dir / "arm_pd.mp4" if make_videos else None
    ball_video = artifact_dir / "ball_drop.mp4" if make_videos else None
    gym_video = artifact_dir / "reacher_random.mp4" if make_videos else None

    passive = simulate_arm("passive")
    controlled = simulate_arm("pd", video_path=arm_video)
    contact = simulate_contact(video_path=ball_video)
    gym_summary = run_gym_bridge(video_path=gym_video)

    _plot_arm(passive, controlled, artifact_dir / "arm_control.png")
    _plot_contact(contact, artifact_dir / "ball_contact.png")

    final_error = abs(float(controlled["angle"][-1]) - controlled["target_rad"])
    summary = {
        "versions": {
            "mujoco": mujoco.__version__,
            "gymnasium": gym.__version__,
            "numpy": np.__version__,
        },
        "arm": {
            **controlled["model"],
            "initial_angle_deg": 70.0,
            "target_angle_deg": math.degrees(controlled["target_rad"]),
            "passive_final_angle_deg": math.degrees(float(passive["angle"][-1])),
            "controlled_final_angle_deg": math.degrees(float(controlled["angle"][-1])),
            "controlled_final_error_deg": math.degrees(final_error),
            "controller": "PD feedback plus MuJoCo bias-force gravity compensation",
        },
        "contact": {
            "first_contact_time_s": contact["first_contact_time"],
            "max_normal_force_n": contact["max_normal_force"],
        },
        "gym_bridge": gym_summary,
    }

    if final_error > math.radians(5):
        raise RuntimeError(f"PD controller did not settle: {math.degrees(final_error):.2f} deg error")
    if contact["first_contact_time"] is None:
        raise RuntimeError("Ball never contacted the floor")

    summary_path = artifact_dir / "day1_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--no-video", action="store_true", help="Skip offscreen video rendering")
    args = parser.parse_args()

    summary = run_all(args.artifact_dir, make_videos=not args.no_video)
    print(json.dumps(summary, indent=2))
    print(f"\nArtifacts: {args.artifact_dir.resolve()}")


if __name__ == "__main__":
    main()

"""Run MicroDuck RL training on one Modal GPU.

The default invocation is intentionally small: 64 parallel environments and
5 PPO iterations. It verifies the complete CUDA/MuJoCo/mjlab training path
before any longer run is submitted.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import modal

APP_NAME = "microduck-rl"
DEFAULT_TASK = "Mjlab-Velocity-Flat-MicroDuck"
LOCAL_RL_DIR = Path(__file__).resolve().parent / "microduck_rl"
REMOTE_RL_DIR = Path("/root/microduck_rl")
REMOTE_LOG_DIR = REMOTE_RL_DIR / "logs"

if not (LOCAL_RL_DIR / "pyproject.toml").is_file():
    raise RuntimeError(f"MicroDuck RL source is missing: {LOCAL_RL_DIR}")


image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .pip_install("uv==0.11.6")
    .env(
        {
            "PYTHONUNBUFFERED": "1",
            "UV_HTTP_TIMEOUT": "600",
            "UV_LINK_MODE": "copy",
            "WANDB_MODE": "offline",
        }
    )
    .add_local_dir(
        LOCAL_RL_DIR,
        remote_path=str(REMOTE_RL_DIR),
        copy=True,
        ignore=[
            ".git",
            ".git/**",
            ".venv",
            ".venv/**",
            "logs",
            "logs/**",
            "**/__pycache__",
            "**/*.pyc",
        ],
    )
    .run_commands(
        f"cd {REMOTE_RL_DIR} && uv sync --frozen",
        f"mkdir -p {REMOTE_LOG_DIR}",
    )
)

app = modal.App(APP_NAME, image=image)
training_output = modal.Volume.from_name(
    "microduck-rl-output", create_if_missing=True
)


def _validate(task: str, num_envs: int, iterations: int, run_name: str) -> None:
    safe_text = re.compile(r"^[A-Za-z0-9._-]+$")
    if not safe_text.fullmatch(task) or not task.startswith("Mjlab-"):
        raise ValueError(f"Invalid task id: {task!r}")
    if not 1 <= num_envs <= 4096:
        raise ValueError("num_envs must be between 1 and 4096")
    if not 1 <= iterations <= 6000:
        raise ValueError("iterations must be between 1 and 6000")
    if not safe_text.fullmatch(run_name):
        raise ValueError("run_name may contain only letters, numbers, '.', '_' and '-'")


@app.function(
    gpu="L4",
    cpu=4,
    memory=8192,
    timeout=3 * 60 * 60,
    volumes={str(REMOTE_LOG_DIR): training_output},
)
def train_microduck(
    task: str = DEFAULT_TASK,
    num_envs: int = 64,
    iterations: int = 5,
    run_name: str = "modal-smoke",
) -> str:
    """Run one bounded training job and persist logs/checkpoints."""

    _validate(task, num_envs, iterations, run_name)

    subprocess.run(["nvidia-smi"], check=True)
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-c",
            (
                "import torch; "
                "assert torch.cuda.is_available(); "
                "print('CUDA ready:', torch.cuda.get_device_name(0))"
            ),
        ],
        cwd=REMOTE_RL_DIR,
        check=True,
    )

    command = [
        "uv",
        "run",
        "train",
        task,
        "--env.scene.num-envs",
        str(num_envs),
        "--agent.max_iterations",
        str(iterations),
        "--agent.run-name",
        run_name,
    ]

    try:
        subprocess.run(command, cwd=REMOTE_RL_DIR, check=True)
    finally:
        training_output.commit()

    checkpoints = sorted(
        str(path.relative_to(REMOTE_LOG_DIR))
        for path in REMOTE_LOG_DIR.rglob("model_*.pt")
    )
    return json.dumps(
        {
            "task": task,
            "num_envs": num_envs,
            "iterations": iterations,
            "run_name": run_name,
            "checkpoints": checkpoints,
        },
        indent=2,
    )


@app.local_entrypoint()
def main(
    task: str = DEFAULT_TASK,
    num_envs: int = 64,
    iterations: int = 5,
    run_name: str = "modal-smoke",
) -> None:
    """Submit one Modal run and print its result."""

    _validate(task, num_envs, iterations, run_name)
    print(train_microduck.remote(task, num_envs, iterations, run_name))


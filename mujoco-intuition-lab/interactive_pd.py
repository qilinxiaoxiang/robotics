"""Interactive MuJoCo viewer: disturb an arm while a PD controller recovers."""

from __future__ import annotations

import math
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np


MODEL_PATH = Path(__file__).resolve().parent / "models" / "one_joint_arm.xml"


def main() -> None:
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    data.qpos[0] = math.radians(70)
    mujoco.mj_forward(model, data)

    with mujoco.viewer.launch_passive(model, data) as viewer:
        viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = 1
        viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTFORCE] = 1
        while viewer.is_running():
            step_started = time.time()
            target = math.radians(30 + 20 * math.sin(0.6 * data.time))
            command = (
                12.0 * (target - data.qpos[0])
                - 3.0 * data.qvel[0]
                + data.qfrc_bias[0]
            )
            data.ctrl[0] = np.clip(command, -5.0, 5.0)
            mujoco.mj_step(model, data)
            viewer.sync()

            remaining = model.opt.timestep - (time.time() - step_started)
            if remaining > 0:
                time.sleep(remaining)


if __name__ == "__main__":
    main()

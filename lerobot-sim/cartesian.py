"""Map small tool-position requests to joint targets, without moving physics state."""
import mujoco
import numpy as np


def move_tool(model, controls, delta):
    delta = np.asarray(delta, dtype=float)
    if delta.shape != (3,) or not np.isfinite(delta).all() or np.linalg.norm(delta) > .020001:
        raise ValueError("Tool increment must be finite and at most 2 cm")
    scratch = mujoco.MjData(model)
    scratch.qpos[:6] = controls
    mujoco.mj_forward(model, scratch)
    site = model.site("gripperframe").id
    target = scratch.site_xpos[site].copy() + delta
    if not (-.35 <= target[0] <= .40 and abs(target[1]) <= .35 and .015 <= target[2] <= .42):
        return None, "目标超出当前练习范围，请往相反方向移动。"
    orientation = scratch.site_xmat[site].reshape(3, 3).copy()
    jp, jr = np.zeros((3, model.nv)), np.zeros((3, model.nv))
    for _ in range(90):
        mujoco.mj_forward(model, scratch)
        position_error = target - scratch.site_xpos[site]
        rotation = scratch.site_xmat[site].reshape(3, 3)
        rotation_error = sum(np.cross(rotation[:, i], orientation[:, i]) for i in range(3)) / 2
        if np.linalg.norm(position_error) < .0002 and np.linalg.norm(rotation_error) < .015:
            break
        mujoco.mj_jacSite(model, scratch, jp, jr, site)
        jacobian = np.vstack((jp[:, :5], .025 * jr[:, :5]))
        error = np.concatenate((position_error, .025 * rotation_error))
        step = jacobian.T @ np.linalg.solve(jacobian @ jacobian.T + .002**2 * np.eye(6), error)
        step *= min(1, .12 / max(np.linalg.norm(step), 1e-12))
        scratch.qpos[:5] = np.clip(scratch.qpos[:5] + step, model.jnt_range[:5, 0], model.jnt_range[:5, 1])
    mujoco.mj_forward(model, scratch)
    error_m = float(np.linalg.norm(target - scratch.site_xpos[site]))
    if error_m > .004:
        return None, "这个方向接近机械臂限位，试试先抬高或往回移动。"
    result = np.asarray(controls).copy()
    result[:5] = scratch.qpos[:5]
    return result, "已更新夹爪目标；遇到物体或关节限位时，实际运动可能受阻。"

import math

from day1_intuition import run_gym_bridge, simulate_arm, simulate_contact


def test_arm_model_and_feedback_controller() -> None:
    result = simulate_arm("pd", duration=3.0)
    error = abs(float(result["angle"][-1]) - result["target_rad"])

    assert result["model"] == {"nq": 1, "nv": 1, "nu": 1, "timestep": 0.002}
    assert error < math.radians(5)


def test_ball_reaches_contact() -> None:
    result = simulate_contact(duration=1.0)

    assert result["first_contact_time"] is not None
    assert 0.3 < result["first_contact_time"] < 0.6
    assert result["max_normal_force"] > 0


def test_gymnasium_bridge_uses_current_mujoco_environment() -> None:
    result = run_gym_bridge(steps=5)

    assert result["environment"] == "Reacher-v5"
    assert result["observation_shape"] == [10]
    assert result["action_shape"] == [2]

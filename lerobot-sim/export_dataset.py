"""Convert local simulation demonstrations to a LeRobot dataset, without upload."""
import argparse
from pathlib import Path

import numpy as np
from lerobot.datasets.lerobot_dataset import LeRobotDataset

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]

def export(source: Path):
    with np.load(source, allow_pickle=False) as episode:
        destination = source.with_suffix("")
        features = {
            "observation.state": {"dtype": "float32", "shape": (6,), "names": JOINTS},
            "action": {"dtype": "float32", "shape": (6,), "names": JOINTS},
            "observation.images.front": {
                "dtype": "image", "shape": tuple(episode["images"].shape[1:]),
                "names": ["height", "width", "channels"],
            },
        }
        dataset = LeRobotDataset.create(
            repo_id=f"local/{destination.name}", root=destination,
            fps=int(episode["fps"]), features=features, robot_type="so101_mujoco",
            use_videos=False, image_writer_threads=2, video_backend="pyav",
        )
        for state, action, pixels in zip(episode["state"], episode["action"], episode["images"], strict=True):
            dataset.add_frame({
                "observation.state": state, "action": action,
                "observation.images.front": pixels, "task": str(episode["task"]),
            })
        dataset.save_episode()
        dataset.finalize()
    # Read the saved result using the training library, not just file existence.
    readback = LeRobotDataset(f"local/{destination.name}", root=destination, video_backend="pyav")
    assert len(readback) > 0 and readback[0]["observation.state"].shape == (6,)
    print(f"Saved and read back {len(readback)} frames: {destination}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    export(parser.parse_args().source)

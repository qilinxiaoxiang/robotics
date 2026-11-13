"""learned_target.detect on real head-camera frames (learned-target-20261112/frames.json).

    ~/.venvs/microduck-walk/bin/python -m pytest -q test_learned_target.py

Needs onnxruntime, OpenCV and the exported model (runtime-overlay/models/learned_target.onnx or $LEARNED_TARGET_MODEL;
export_learned_target.py makes it on the Mac mini). The frames are PNG/JPEG and the model is ONNX, both git-ignored in
this tree, so on a checkout without them the frame tests skip and say which file is missing.
"""
import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import learned_target as lt  # noqa: E402

FIX = os.path.join(HERE, "learned-target-20261112")
ROWS = json.load(open(os.path.join(FIX, "frames.json")))["frames"]
KEYS = {"cx", "cy", "base_cx", "area", "bbox", "n_blobs", "score", "label"}


def frame(row):
    cv2 = pytest.importorskip("cv2")
    if not os.path.exists(lt.MODEL):
        pytest.skip(f"no model at {lt.MODEL}")
    p = os.path.join(FIX, "frames", row["file"])
    if not os.path.exists(p):
        pytest.skip(f"no frame {p}")
    img = cv2.imread(p)
    assert img is not None and img.shape[:2] == (360, 640)
    return img


def on_ball(bbox, ball):
    """The box holds the ball's centre and is not a much larger thing that merely contains it."""
    x, y, w, h = bbox
    gx, gy, gw, gh = ball
    cx, cy = gx + gw / 2, gy + gh / 2
    return x - 2 <= cx <= x + w + 2 and y - 2 <= cy <= y + h + 2 and max(w, h) <= 3 * max(gw, gh) + 12


def rows(expect):
    return [pytest.param(r, id=r["file"]) for r in ROWS if r["expect"] == expect]


def test_fixture_has_the_office_frames():
    names = {r["file"]: r["expect"] for r in ROWS}
    assert [names[f"look_{k}.png"] for k in ("a_code_lowest", "b", "c", "e")] == ["none"] * 4
    assert [names[k] for k in ("look_d.png", "cam.png", "grab.png")] == ["found"] * 3


@pytest.mark.parametrize("row", rows("found"))
def test_finds_the_ball(row):
    hit = lt.detect(frame(row))
    assert hit is not None, "ball missed"
    assert KEYS <= set(hit)
    assert on_ball(hit["bbox"], row["ball"]), f"box {hit['bbox']} is not on the ball {row['ball']}"
    x, y, w, h = hit["bbox"]
    assert hit["area"] == w * h and hit["n_blobs"] >= 1 and 0 < hit["score"] <= 1
    assert hit["cx"] == pytest.approx(x + w / 2) and hit["cy"] == pytest.approx(y + h / 2)
    assert hit["base_cx"] == hit["cx"]
    assert all(isinstance(v, int) for v in hit["bbox"])


@pytest.mark.parametrize("row", rows("none"))
def test_no_box_without_a_ball(row):
    hit = lt.detect(frame(row))
    assert hit is None, f"false positive {hit}"


@pytest.mark.parametrize("row", rows("found_or_none"))
def test_far_ball_is_missed_or_right_never_wrong(row):
    hit = lt.detect(frame(row))
    assert hit is None or on_ball(hit["bbox"], row["ball"]), f"wrong box {hit}"


def test_accept_and_mask_follow_orange_target():
    row = next(r for r in ROWS if r["file"] == "grab.png")
    img = frame(row)
    seen = []
    assert lt.detect(img, accept=lambda x, y, w, h: seen.append((x, y, w, h)) or False) is None
    assert seen and all(len(b) == 4 for b in seen)
    hit = lt.detect(img, mask=True)
    x, y, w, h = hit["bbox"]
    assert hit["mask"].shape == (360, 640) and hit["mask"].dtype == np.uint8
    assert int((hit["mask"] > 0).sum()) == w * h and hit["mask"][y, x] == 255
    assert lt.detect(img, min_area=10 ** 6) is None
    assert lt.detect(img, conf=0.999) is None


def test_unknown_prompt_is_an_error_not_a_silent_miss():
    row = next(r for r in ROWS if r["file"] == "grab.png")
    with pytest.raises(ValueError):
        lt.detect(frame(row), prompts=("a prompt that was never baked in",))


def test_nms_keeps_the_best_of_overlapping_boxes():
    boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]], np.float32)
    assert lt._nms(boxes, np.array([0.5, 0.9, 0.3], np.float32), 0.5) == [1, 2]

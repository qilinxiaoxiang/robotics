"""Tests for pet/see/detect.py: the selection rules orange_target / approach rely on, the HTTP service and client
with a stub detector (no model), the prompt bank, and, when the weights are present, YOLO-World on the fixture
frame (a real floor frame with an orange printed part pasted at (271, 208, 98, 92) and the duck's feet at the
bottom corners; fixture_body.png is the feet mask)."""
import json
import threading
from pathlib import Path

import cv2
import numpy as np
import pytest

from pet.see import detect as D

HERE = Path(__file__).resolve().parent
FRAME = HERE / "fixture_frame.png"
BODY = HERE / "fixture_body.png"
GT = (271, 208, 98, 92)


def det(bbox, score, label="orange block"):
    return {"bbox": bbox, "score": score, "label": label}


# ------------------------------------------------------------------------------------------ select()

def test_select_returns_orange_target_fields():
    hit = D.select([det((10, 20, 30, 40), 0.9)])
    assert hit["bbox"] == (10, 20, 30, 40) and hit["area"] == 1200 and hit["n_blobs"] == 1
    assert hit["cx"] == 25 and hit["cy"] == 40 and hit["base_cx"] == 25
    assert hit["score"] == 0.9 and hit["label"] == "orange block"


def test_select_prefers_score_then_area():
    big_low = det((0, 0, 100, 100), 0.3)
    small_high = det((200, 200, 10, 10), 0.8)
    assert D.select([big_low, small_high])["bbox"] == (200, 200, 10, 10)
    assert D.select([det((0, 0, 100, 100), 0.5), det((0, 0, 20, 20), 0.5)])["bbox"] == (0, 0, 100, 100)


def test_select_min_area_and_empty():
    assert D.select([]) is None
    assert D.select([det((0, 0, 5, 5), 0.99)]) is None            # 25 px < MIN_AREA
    assert D.select([det((0, 0, 5, 5), 0.99)], min_area=10) is not None


def test_select_horizon_callable_like_approach_below_horizon():
    # approach.below_horizon: accept when the box top is below the horizon row v
    v = 100
    accept = lambda x, y, w, h: y > v  # noqa: E731
    above = det((10, 50, 30, 30), 0.9)
    below = det((10, 150, 30, 30), 0.5)
    assert D.select([above, below], accept)["bbox"] == (10, 150, 30, 30)
    assert D.select([above], accept) is None


def test_select_horizon_int():
    assert D.select([det((10, 50, 30, 30), 0.9)], 100) is None
    assert D.select([det((10, 101, 30, 30), 0.9)], 100) is not None
    assert D.select([det((10, 100, 30, 30), 0.9)], 100) is None   # top on the row counts as above


def test_select_body_mask_and_negatives():
    mask = np.zeros((360, 640), np.uint8)
    mask[300:, :160] = 255
    foot = det((10, 310, 100, 50), 0.9)         # fully inside the mask
    obj = det((300, 200, 40, 40), 0.4)
    assert D.select([foot, obj], body_mask=mask)["bbox"] == obj["bbox"]
    assert D.select([foot], body_mask=mask) is None
    half = det((120, 310, 80, 50), 0.9)         # half in the mask: the 0.5 rule keeps it out
    assert D.select([half], body_mask=mask) is None
    neg = det((300, 200, 40, 40), 0.95, "robot foot")
    assert D.select([neg, obj], negatives=("robot foot",))["bbox"] == obj["bbox"]
    assert D.select([neg], negatives=("robot foot",)) is None


def test_as_accept():
    assert D.as_accept(None) is None
    f = lambda x, y, w, h: True  # noqa: E731
    assert D.as_accept(f) is f
    assert D.as_accept(10)(0, 11, 1, 1) and not D.as_accept(10)(0, 10, 1, 1)


# ------------------------------------------------------------------------------------------ annotate

def test_annotate_draws_without_error():
    img = cv2.imread(str(FRAME))
    dets = [det(GT, 0.7), det((0, 300, 50, 60), 0.2, "robot foot")]
    hit = D.select(dets)
    out = D.annotate(img, dets, hit, horizon=60, title="t")
    assert out.shape == img.shape and out is not img
    assert D.annotate(img, [], None).shape == img.shape


# ------------------------------------------------------------------------------------------ prompt bank

def test_expand_prompts():
    flat, label_of = D.expand_prompts(["orange block", "keys|house keys", "keys"])
    assert flat == ["orange block", "orange toy", "orange object", "keys", "house keys"]
    assert label_of["orange toy"] == "orange block" and label_of["house keys"] == "keys" and label_of["keys"] == "keys"
    assert D.expand_prompts(["cup"], synonyms={}) == (["cup"], {"cup": "cup"})


def test_text_encoder_bank_roundtrip(tmp_path, monkeypatch):
    enc = D.TextEncoder(tmp_path)              # no text tower, no bank: encode must fail with a clear message
    monkeypatch.setattr(enc, "_load", lambda: setattr(enc, "kind", "bank"))   # as on the Mac mini (no clip)
    with pytest.raises(RuntimeError, match="prompt bank"):
        enc.encode(["keys"])
    enc.bank = {"keys": np.ones(512, np.float32) / np.sqrt(512), "cup": np.zeros(512, np.float32)}
    bank = tmp_path / D.PROMPT_BANK
    assert enc.save_bank(bank) == ["cup", "keys"]
    enc2 = D.TextEncoder(tmp_path)
    f = enc2.encode(["keys", "cup"])
    assert f.shape == (2, 512) and f.dtype == np.float32 and abs(np.linalg.norm(f[0]) - 1) < 1e-5


# ------------------------------------------------------------------------------------------ service + client

class StubDetector:
    """Looks like OpenVocabDetector to serve(): returns one box per prompt, scaled by the frame size."""
    backend, device, conf, load_s = "stub", "cpu", 0.1, 0.0

    def __init__(self):
        self.prompts, self.calls, self.last_ms = ["orange block"], 0, 0.0

    def set_prompts(self, prompts):
        self.prompts = list(prompts)

    def all(self, frame):
        self.calls += 1
        h, w = frame.shape[:2]
        return [{"bbox": (w // 4, h // 2, w // 8, h // 8), "score": 0.9 - 0.1 * i, "label": p}
                for i, p in enumerate(self.prompts)] + [{"bbox": (0, 0, w // 2, h // 10), "score": 0.95, "label": "robot foot"}]


@pytest.fixture
def server():
    stub = StubDetector()
    srv = D.serve(stub, "127.0.0.1", 0, log=lambda s: None)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield stub, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def test_client_roundtrip_matches_local_selection(server):
    stub, url = server
    img = cv2.imread(str(FRAME))
    c = D.DetectorClient(url, ["keys"], negatives=("robot foot",))
    assert c.health()["backend"] == "stub"
    hit = c.detect(img, 60)
    assert stub.prompts == ["keys", "robot foot"] and stub.calls == 1
    assert hit["label"] == "keys" and hit["bbox"] == (160, 180, 80, 45) and c.last_ms is not None
    # the same dets through the local rule give the same answer (the client applies select() locally)
    assert D.select(c.last, 60, negatives=("robot foot",))["bbox"] == hit["bbox"]
    # the horizon rule runs on the client: a horizon below the box top rejects it
    assert c.detect(img, 300) is None
    # the negative label has the highest score in the reply and is still not chosen
    assert max(c.last, key=lambda d: d["score"])["label"] == "robot foot"


def test_client_conf_and_shape_passthrough(server):
    stub, url = server
    c = D.DetectorClient(url, ["cup"], conf=0.42)
    c.all(np.zeros((36, 64, 3), np.uint8))
    assert stub.conf == 0.42 and c.last[0]["bbox"] == (16, 18, 8, 4)


def test_client_returns_none_when_service_is_down():
    c = D.DetectorClient("http://127.0.0.1:1", ["keys"], timeout=0.2)
    assert c.detect(np.zeros((36, 64, 3), np.uint8)) is None and c.errors == 1


def test_service_rejects_garbage(server):
    import urllib.request
    _, url = server
    req = urllib.request.Request(url + "/detect", data=b"not a jpeg", method="POST")
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req, timeout=2)
    assert e.value.code == 400 and "decodable" in json.loads(e.value.read())["error"]


# ------------------------------------------------------------------------------------------ real model

@pytest.mark.skipif(not (D.MODELS_DIR / D.YOLO_WEIGHTS).exists()
                    or not ((D.MODELS_DIR / D.CLIP_TEXT_DIR).exists() or (D.MODELS_DIR / D.PROMPT_BANK).exists()),
                    reason="YOLO-World weights or CLIP text embeddings not fetched (see README)")
def test_yolo_world_finds_the_orange_part_and_ignores_the_feet():
    img = cv2.imread(str(FRAME))
    mask = cv2.imread(str(BODY), 0)
    d = D.OpenVocabDetector(["orange block"], body_mask=mask, conf=0.05)
    assert d.queries == ["orange block", "orange toy", "orange object"]
    hit = d.detect(img, 60)
    assert hit is not None and hit["label"] == "orange block"
    x, y, w, h = hit["bbox"]
    gx, gy, gw, gh = GT
    ix = max(0, min(x + w, gx + gw) - max(x, gx)) * max(0, min(y + h, gy + gh) - max(y, gy))
    assert ix / (w * h + gw * gh - ix) >= 0.3
    assert not D.box_in_mask(hit["bbox"], mask)
    # prompt change at runtime reaches the (fused) predictor model: the same frame asked for keys gives no keys box
    d.set_prompts(["keys"])
    assert all(x["label"] == "keys" for x in d.all(img))

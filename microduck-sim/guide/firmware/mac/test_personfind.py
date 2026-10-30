"""Person finder and the name-call attention that follows a body up to the face (NAMECALL.md 12), front-first search
and bearing_seen labels (2026-10-30). Pure-logic tests always run; the detector tests need the YOLOX-Tiny model
(pet/identity/fetch_models.sh) and the real duck frames, which are local only (images are not published)."""
import glob
import math
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facefind  # noqa: E402
import namecall as nc  # noqa: E402
import personfind as pf  # noqa: E402
from test_namecall_chain import args  # noqa: E402

W, H = 640, 360
FIX = os.path.join(HERE, "personfind-20261030")
CAL = os.path.join(HERE, "camera-calib-20261030")


# --- geometry of a person box

def test_box_cut_by_the_top_edge_points_up():
    a = pf.person_angles((2, 1, 162, 184), W, H)                 # the 16:54 legs box
    assert a["top_cut"] and abs(a["pitch_err"] - (180 - 1) / pf.F_PX) < 1e-9
    assert a["yaw_err"] < -0.6                                   # left of centre: the head must turn left


def test_box_inside_the_frame_aims_at_its_top():
    a = pf.person_angles((300, 60, 380, 340), W, H)
    y_head = 60 + pf.HEAD_FRAC * 280
    assert not a["top_cut"] and abs(a["pitch_err"] - (180 - y_head) / pf.F_PX) < 1e-9
    assert abs(a["yaw_err"] - (340 - 320) / pf.F_PX) < 1e-9


# --- the decision: face wins, cut box -> pitch up, inside box -> aim at its top

def test_person_aim_pitches_up_while_the_box_is_cut_then_holds_at_the_cap():
    p = dict(yaw_err=-0.4, pitch_err=0.5, top_cut=True)
    yaw, pitch, how = nc.person_aim(0.2, 0.3, p)
    assert how == "up" and abs(pitch - (0.3 + nc.PERSON_PITCH_STEP)) < 1e-9 and abs(yaw - (0.2 + nc.FACE_GAIN * 0.4)) < 1e-9
    yaw, pitch, how = nc.person_aim(0.2, 0.95, p)
    assert how == "up" and pitch == nc.FACE_PITCH[1]               # bounded by the pitch cap
    yaw, pitch, how = nc.person_aim(0.2, nc.FACE_PITCH[1], p)
    assert how == "cap" and pitch == nc.FACE_PITCH[1]


def test_person_aim_inside_box_aims_at_the_head_point():
    yaw, pitch, how = nc.person_aim(0.0, 0.4, dict(yaw_err=0.1, pitch_err=0.2, top_cut=False))
    assert how == "aim" and abs(pitch - (0.4 + nc.FACE_GAIN * 0.2)) < 1e-9 and abs(yaw + nc.FACE_GAIN * 0.1) < 1e-9


# --- front first

def test_fold_to_front_keeps_only_the_side():
    d = math.radians
    for heard, want, side in ((160, 20, 1), (87, 87, 1), (158, 22, 1), (126, 54, 1), (-18, -18, -1), (-120, -60, -1),
                              (90, 90, 1), (180, 0, 0), (5, 0, 0), (-175, 0, 0), (-172, 0, 0), (200, -20, -1)):
        f, s = nc.fold_front(d(heard))
        assert abs(f - d(want)) < 1e-9 and s == side, (heard, math.degrees(f), s)


# --- the attention phase with camera doubles

class World:
    """Camera double: a caller fixed in the world at gaze yaw `yaw`; their face at gaze pitch `face_pitch`, their body
    below it. The face detector finds the face only within 0.35 rad of the frame centre (it is small and at the edge
    of the fisheye); the person box is cut by the frame top while the face is more than 0.5 rad above the centre."""

    def __init__(self, gaze, yaw=0.5, face_pitch=1.0, person=True, face=True):
        self.gaze, self.yaw, self.fp, self.has_person, self.has_face = gaze, yaw, face_pitch, person, face
        self.rate_hz, self.det_size, self.person_hz = 4.0, 640, 2.0
        self.face_calls = self.person_calls = 0

    def latest(self, now=None, stale_s=1.0):
        gy, gp = self.gaze(now)
        if not self.has_face or abs(self.fp - gp) > 0.35 or abs(gy - self.yaw) > 0.6:
            return None
        self.face_calls += 1
        return dict(t=math.floor(now / 0.25) * 0.25, yaw_err=gy - self.yaw, pitch_err=self.fp - gp, size=0.1, score=0.8)

    def latest_person(self, now=None, stale_s=1.0):
        gy, gp = self.gaze(now)
        if not self.has_person or abs(gy - self.yaw) > 0.9:
            return None
        self.person_calls += 1
        up = self.fp - gp
        cut = up > 0.5
        return dict(t=math.floor(now / 0.5) * 0.5, yaw_err=gy - self.yaw, pitch_err=min(up, 0.5), top_cut=cut, height=0.6,
                    score=0.7, box=[0, 0 if cut else 40, 160, 184])

    def stats(self):
        return dict(frames=0)


class Life:
    """life_log.LifeLog double: one segment open since t0 (None = no segment open)."""

    def __init__(self, t0=0.0):
        self.notes = []
        self.seg = None if t0 is None else dict(t0=t0)

    def note(self, t, kind, **rec):
        self.notes.append((t, kind, rec))


def run(tmp_path, az, world=None, pitch=0.2, until=12.0, turn=False, life=None, call_t=0.0):
    a = args(cmd=str(tmp_path / "c.json"), seed=3, pitch=pitch)
    a.no_turn = not turn
    n = nc.NameCall(a, nc.Log(None, echo=False))
    if world is not None:
        n.finder = world(n.head.gaze)
    n.life = life
    recs = []
    n.log.write = lambda kind, **rec: recs.append((kind, rec))
    n.respond(dict(t=call_t, az_rad=az, az_deg=round(math.degrees(az)), bins=100, e_db=-30.0, floor_db=-48.0, margin=0.0), call_t)
    t = call_t
    while t < call_t + until:
        n.motion_tick(t)
        t += 0.02
    return n, recs


def test_legs_at_the_top_of_a_low_frame_lead_the_head_up_to_the_face(tmp_path):
    """The 16:54 case: the gaze starts low (pitch 0.2) on the caller's side; only the legs are in view, cut by the
    frame top. The head pitches up step by step, the face comes into view and the face lock takes over."""
    n, recs = run(tmp_path, az=0.5, world=lambda g: World(g, yaw=0.5, face_pitch=1.0))
    people = [r for k, r in recs if k == "person"]
    faces = [r for k, r in recs if k == "face"]
    assert people and people[0]["how"] == "up" and people[0]["top_cut"]
    assert len(faces) == 1
    t_face = next(i for i, (k, _) in enumerate(recs) if k == "face")
    t_person = next(i for i, (k, _) in enumerate(recs) if k == "person")
    assert t_person < t_face                                    # the body came first
    yaw, pitch = n.head.gaze(12.0)
    assert abs(pitch - 1.0) < 0.06 and abs(yaw - 0.5) < 0.06, (yaw, pitch)
    assert not [k for k, _ in recs if k == "scan"]               # no sweep while the body was in view


def test_face_in_view_wins_over_the_person(tmp_path):
    n, recs = run(tmp_path, az=0.5, world=lambda g: World(g, yaw=0.5, face_pitch=0.3), until=6.0)
    assert [k for k, _ in recs if k == "face"] == ["face"] and not [k for k, _ in recs if k == "person"]
    yaw, pitch = n.head.gaze(6.0)
    assert abs(pitch - 0.3) < 0.05


def test_person_box_inside_the_frame_is_aimed_at_its_top_without_a_face(tmp_path):
    """A seated caller whose face the detector never finds: the gaze settles on the box top (the head point) and stays
    there; the attention ends PERSON_MAX_S after the first person sighting at the latest."""
    n, recs = run(tmp_path, az=0.5, world=lambda g: World(g, yaw=0.6, face_pitch=0.45, face=False), until=30.0)
    hows = [r["how"] for k, r in recs if k == "person"]
    assert hows and hows[0] == "aim"
    assert any(k == "attend_done" for k, _ in recs)
    done = [i for i, (k, _) in enumerate(recs) if k == "attend_done"]
    assert done


def test_nobody_in_view_still_sweeps(tmp_path):
    n, recs = run(tmp_path, az=0.5, world=lambda g: World(g, person=False, face=False), pitch=nc.LOOK_PITCH)
    assert len([k for k, _ in recs if k == "scan"]) == 1 and not [k for k, _ in recs if k == "person"]


def test_front_search_first_then_the_back_turn_on_the_heard_side(tmp_path):
    """A call heard at 160 deg (really at 20 deg, the 2026-10-30 case): the head goes to +20 deg, not the cap; with
    nobody in front the body then turns left toward the back; with a person in front it never turns."""
    n, recs = run(tmp_path, az=math.radians(160), world=lambda g: World(g, person=False, face=False),
                  pitch=nc.LOOK_PITCH, until=14.0, turn=True)
    call = next(r for k, r in recs if k == "call")
    assert abs(call["target_yaw"] - math.radians(20)) < 1e-6 and call["behind_heard"]
    turns = [r for k, r in recs if k == "turn"]
    assert len(turns) == 1 and turns[0]["vtheta"] > 0 and abs(turns[0]["az_deg"] - 160) < 0.5
    k_scan = next(i for i, (k, _) in enumerate(recs) if k == "scan")
    k_turn = next(i for i, (k, _) in enumerate(recs) if k == "turn")
    assert k_scan < k_turn                                       # the front was searched first
    other = tmp_path / "second"                                  # a fresh control file (the first run's turn is in it)
    other.mkdir()
    n, recs = run(other, az=math.radians(160), world=lambda g: World(g, yaw=0.35, face_pitch=1.5, face=False),
                  pitch=nc.LOOK_PITCH, until=14.0, turn=True)
    assert not [k for k, _ in recs if k == "turn"] and [k for k, _ in recs if k == "person"]


def test_bearing_seen_labels_the_call_with_the_true_bearing(tmp_path):
    """The first face after a call: one bearing_seen with the call's t, the face's bearing in the body frame (gaze yaw
    minus the detector's offset), seconds after the call, and the same record in the life log."""
    life = Life(t0=96.0)                                         # the call's segment (PRE_S before it) is open
    n, recs = run(tmp_path, az=0.3, world=lambda g: World(g, yaw=0.7, face_pitch=0.5, person=False), pitch=0.5,
                  until=8.0, life=life, call_t=100.0)
    seen = [r for k, r in recs if k == "bearing_seen"]
    assert len(seen) == 1
    s = seen[0]
    assert s["t"] == 100.0 and s["source"] == "face" and s["body_rot_deg"] == 0.0
    assert abs(s["bearing_deg"] - math.degrees(0.7)) < 0.5 and abs(s["elev_gaze_deg"] - math.degrees(0.5)) < 0.5
    assert 0.5 < s["after_s"] < 8.0
    assert life.notes and life.notes[0][0] == 100.0 and life.notes[0][1] == "bearing_seen"
    assert abs(life.notes[0][2]["bearing_deg"] - s["bearing_deg"]) < 1e-9 and life.notes[0][2]["call_t"] == 100.0
    # the call's segment already closed: the note goes into the segment open now, still carrying the call's time
    other = tmp_path / "late"
    other.mkdir()
    life = Life(t0=None)
    run(other, az=0.3, world=lambda g: World(g, yaw=0.7, face_pitch=0.5, person=False), pitch=0.5, until=8.0, life=life,
        call_t=100.0)
    assert life.notes[0][0] > 100.5 and life.notes[0][2]["call_t"] == 100.0


def test_bearing_seen_adds_the_body_rotation_since_the_call(tmp_path):
    n = nc.NameCall(args(cmd=str(tmp_path / "c.json"), seed=3), nc.Log(None, echo=False))
    recs = []
    n.log.write = lambda kind, **rec: recs.append((kind, rec))
    n.call, n.body_rot = dict(t=5.0, now=5.0, seen=False), 1.5        # the body turned 86 deg left since the call
    n._bearing_seen(9.0, "person", 0.2, 0.9, dict(yaw_err=-0.1, pitch_err=0.05, top_cut=False, score=0.6))
    s = recs[0][1]
    assert abs(s["bearing_deg"] - math.degrees(0.2 + 0.1 + 1.5)) < 0.1 and s["after_s"] == 4.0 and s["source"] == "person"
    n._bearing_seen(9.5, "face", 0.2, 0.9, dict(yaw_err=0.0, pitch_err=0.0))
    assert len(recs) == 1                                            # one label per call


# --- FaceFinder runs the person detector only on face-less frames, at most PERSON_HZ

class FakePipe:
    def __init__(self):
        self.face = False

    def detect(self, img, max_num=0):
        if self.face:
            return np.array([[300, 100, 340, 150, 0.9]], np.float32), None
        return np.zeros((0, 5), np.float32), None


class FakePerson:
    def __init__(self):
        self.calls = 0

    def detect(self, img):
        self.calls += 1
        return np.array([[2, 1, 162, 184, 0.76]], np.float32)


def test_facefinder_runs_people_only_without_a_face_and_at_most_person_hz():
    pipe, person = FakePipe(), FakePerson()
    ff = facefind.FaceFinder(pipeline=pipe, person=person, person_hz=2.0, now=lambda: 0.0)
    img = np.zeros((H, W, 3), np.uint8)
    for i in range(8):                                   # 4 Hz for 2 s, no face
        ff.analyse(img, i * 0.25)
    assert person.calls == 4
    p = ff.latest_person(now=1.9)
    assert p is not None and p["top_cut"] and p["box"] == [2, 1, 162, 184]
    pipe.face = True
    for i in range(8, 16):
        ff.analyse(img, i * 0.25)
    assert person.calls == 4                             # a face in the frame: the face wins, no person run
    assert ff.latest(now=3.8) is not None and ff.latest_person(now=3.8) is None
    st = ff.stats()
    assert st["person_frames"] == 4


# --- the detector on real duck frames (local only)

MODEL_OK = os.path.exists(pf.MODEL)


def _frame(path):
    import cv2
    im = cv2.imread(path)
    if im.shape[:2] != (H, W):
        im = cv2.resize(im, (W, H), interpolation=cv2.INTER_AREA)
    return im


@pytest.fixture(scope="module")
def det():
    if not MODEL_OK:
        pytest.skip("no YOLOX-Tiny model (run pet/identity/fetch_models.sh)")
    pytest.importorskip("onnxruntime")
    return pf.PersonDetector(threads=4)


def test_model_file_is_the_official_release(det):
    import hashlib
    assert hashlib.sha256(open(pf.MODEL, "rb").read()).hexdigest() == pf.MODEL_SHA256


def test_detector_finds_the_legs_of_1654(det):
    path = os.path.join(FIX, "legs_1654.jpg")
    if not os.path.exists(path):
        pytest.skip("local frame missing")
    ps = pf.people(det.detect(_frame(path)), W, H)
    assert ps and ps[0]["top_cut"] and ps[0]["yaw_err"] < -0.5 and ps[0]["score"] > 0.5, ps
    assert ps[0]["box"][2] < 200 and ps[0]["box"][3] < 220               # the shoes-and-jeans corner


def test_detector_sees_nobody_on_the_same_spot_without_him(det):
    path = os.path.join(FIX, "empty_chair_1659.png")
    if not os.path.exists(path):
        pytest.skip("local frame missing")
    assert pf.people(det.detect(_frame(path)), W, H) == []


def test_detector_sees_nobody_on_the_calibration_frames(det):
    """Floor, ruler and the duck's own parts, 2026-10-30 (the ground-pick bend: close blurred wood that the raw model
    calls a person at up to 0.87 over the whole frame)."""
    files = sorted(glob.glob(os.path.join(CAL, "ruler", "*.png"))) + sorted(glob.glob(os.path.join(CAL, "bend-20261030", "check_*.png")))
    for d in ("sweep2", "sweep3", "sweep4"):
        files += sorted(glob.glob(os.path.join(CAL, "bend-20261030", d, "*.png")))[::3]
    if not files:
        pytest.skip("local frames missing")
    hits = [(os.path.basename(f), pf.people(det.detect(_frame(f)), W, H)) for f in files]
    hits = [h for h in hits if h[1]]
    assert not hits, hits[:5]


def test_detector_finds_the_sandals_in_the_bend_rise(det):
    """f012133: someone's feet in sandals at the far top-left of the frame during the 00:29 rise."""
    path = os.path.join(CAL, "bend-20261030", "frames", "f012133.png")
    if not os.path.exists(path):
        pytest.skip("local frame missing")
    ps = pf.people(det.detect(_frame(path)), W, H)
    assert ps and ps[0]["top_cut"] and ps[0]["box"][2] < 130

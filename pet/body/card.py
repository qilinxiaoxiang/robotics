"""Body card: schema validation and atomic reads and writes (contract in pet/state/README.md)."""
import json
import os
import tempfile

SENSOR_KINDS = ("camera", "mic", "imu", "touch", "range")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_DIR = os.path.join(REPO, "pet", "state")
CARD_PATH = os.path.join(STATE_DIR, "body_card.json")


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _range(x):
    return isinstance(x, list) and len(x) == 2 and all(_num(v) for v in x) and x[0] <= x[1]


def validate(card):
    """List of schema errors; empty means valid."""
    err = []
    if not isinstance(card, dict):
        return ["card is not an object"]
    for key, typ in (("name", str), ("sensors", list), ("actuators", list), ("primitives", list), ("notes", list)):
        if not isinstance(card.get(key), typ):
            err.append(f"{key}: missing or not {typ.__name__}")
    if err:
        return err
    for i, s in enumerate(card["sensors"]):
        if not isinstance(s, dict) or s.get("kind") not in SENSOR_KINDS:
            err.append(f"sensors[{i}].kind not one of {SENSOR_KINDS}")
            continue
        if not isinstance(s.get("id"), str) or not isinstance(s.get("notes"), str):
            err.append(f"sensors[{i}]: id and notes must be strings")
    ids = set()
    for i, a in enumerate(card["actuators"]):
        if not isinstance(a, dict):
            err.append(f"actuators[{i}] not an object")
            continue
        if not isinstance(a.get("id"), int) or isinstance(a.get("id"), bool):
            err.append(f"actuators[{i}].id not an integer")
        elif a["id"] in ids:
            err.append(f"actuators[{i}].id {a['id']} repeated")
        ids.add(a.get("id"))
        for k in ("name", "model"):
            if not isinstance(a.get(k), str):
                err.append(f"actuators[{i}].{k} not a string")
        if not (a.get("torque_nm") is None or _num(a.get("torque_nm"))):
            err.append(f"actuators[{i}].torque_nm not a number")
        if not _range(a.get("range_rad")):
            err.append(f"actuators[{i}].range_rad not [min, max]")
        if not isinstance(a.get("ok"), bool):
            err.append(f"actuators[{i}].ok not a bool")
    for i, p in enumerate(card["primitives"]):
        if not isinstance(p, dict) or not isinstance(p.get("name"), str):
            err.append(f"primitives[{i}].name missing")
            continue
        params = p.get("params")
        if not isinstance(params, dict) or not all(isinstance(k, str) and _range(v) for k, v in params.items()):
            err.append(f"primitives[{i}] ({p['name']}).params must map names to numeric [min, max]")
        if not isinstance(p.get("preconditions"), list) or not all(isinstance(c, str) for c in p["preconditions"]):
            err.append(f"primitives[{i}] ({p['name']}).preconditions must be a list of strings")
        if not _num(p.get("duration_s_max")) or p["duration_s_max"] <= 0:
            err.append(f"primitives[{i}] ({p['name']}).duration_s_max must be a positive number")
    if not all(isinstance(n, str) for n in card["notes"]):
        err.append("notes must be strings")
    return err


def load(path=CARD_PATH):
    with open(path) as f:
        return json.load(f)


def write(card, path=CARD_PATH):
    """Validate, then replace `path` atomically so a reader never sees half a card."""
    errors = validate(card)
    if errors:
        raise ValueError("invalid body card: " + "; ".join(errors))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(card, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    return path

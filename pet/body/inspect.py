"""Boot-time self-inspection: find out what this body is and write pet/state/body_card.json.

1. Bus scan (dynamixel-sdk): servo ids and model numbers -> model name, stall torque at the bus voltage, joint range.
2. Sensor enumeration: V4L2 cameras, ALSA capture devices, I2C IMU / touch / range boards.
3. Motor babbling: each joint moved a little at a lower gain while the IMU and the camera watch; what each joint does
   to the body ("tilts the body", "moves the camera", "does nothing visible", "did not move") goes into the notes,
   and a joint that does not move is marked failed.
4. Primitive discovery (primitives.py): the policy-library entries this actuator and sensor set supports.

  python -m pet.body.inspect --dry-run --body duck     recorded bus scan + recorded single-joint IMU windows
  python -m pet.body.inspect --sim                     recorded bus scan + babbling in the as-built MuJoCo duck
  python -m pet.body.inspect --dry-run --body arm      the OMX-F arm from its recorded read-only scan
  python -m pet.body.inspect --port /dev/ttyAS2 --baud 500000 [--babble --i-am-watching]   live (README.md)
"""
import argparse
import datetime
import json
import os
import sys

from . import babble, card, devices, dxl_models, primitives, profiles

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
SCAN_FIXTURE = {"microduck": "duck_bus_scan.json", "omx_arm": "omx_bus_scan.json"}


def actuators_from_scan(profile, scan, effects=None, volts_default=None):
    """Card actuators; a profile servo that did not answer is listed with ok false."""
    effects = {e["joint"]: e for e in (effects or [])}
    notes = []
    names = profiles.joint_names(profile) if profile else {}
    ranges = profiles.PROFILES[profile]["ranges"]() if profile else {}
    found = {m["id"]: m for m in scan["motors"]}
    ids = sorted(set(found) | (set(names) if profile else set()))
    out, above = [], set()
    for i in ids:
        m = found.get(i)
        name = names.get(i, f"joint_{i}")
        model = m["model"] if m else profiles.PROFILES[profile]["models"][i]
        volts = (m or {}).get("voltage_v") or scan.get("voltage_v") or volts_default
        ok, why = True, []
        if m is None:
            ok, why = False, ["did not answer the bus scan"]
        elif m.get("hardware_error"):
            ok = False
            why.append("hardware error " + ",".join(dxl_models.hw_error_names(m["hardware_error"]) or [str(m["hardware_error"])]))
        e = effects.get(name)
        if e and e["responds"] is False:
            ok = False
            why.append(f"babbling: reached {e['excursion_rad']} of {e['commanded_rad']} rad")
        if dxl_models.above_published(model, volts):
            above.add((dxl_models.model_name(model), volts))
        rng = ranges.get(name) if name in ranges else profiles.unknown_range(m or {})
        out.append(dict(id=i, name=name, model=dxl_models.model_name(model), torque_nm=dxl_models.stall_torque(model, volts),
                        range_rad=[round(float(rng[0]), 4), round(float(rng[1]), 4)], ok=ok))
        if why:
            notes.append(f"{name} (ID {i}) marked failed: " + "; ".join(why))
    for model_name, v in sorted(above):
        notes.append(f"{model_name}: bus at {v} V is above the highest published stall-torque point; torque_nm is that "
                     "point's value (ROBOTIS e-manual), not extrapolated")
    return out, notes


def build_card(profile, scan, sensors, sensor_notes, effects, mode, babble_note):
    p = profiles.PROFILES.get(profile) if profile else None
    volts_default = None
    if profile == "microduck":
        volts_default = float(profiles.state_facts(p["state"])["servo_rail_v"]["value"])
    acts, act_notes = actuators_from_scan(profile, scan, effects, volts_default)
    prims, prim_notes = primitives.discover(profile or "unknown", acts, sensors)
    notes = [f"inspected {datetime.datetime.now().isoformat(timespec='seconds')} in {mode} mode"]
    if profile:
        notes.append(f"recognised as {profile} from the servo ids and model numbers; joint ranges from {p['range_source']}")
    else:
        notes.append("unknown body: joint names joint_<id>, ranges from EEPROM limits")
    for k, v in (scan.get("provenance") or {}).items():
        notes.append(f"bus scan {k}: {v}")
    notes += act_notes + sensor_notes
    notes.append(babble_note)
    notes += [f"body schema: {e['text']}" for e in (effects or [])]
    notes += prim_notes
    c = dict(name=profile or "unknown", sensors=sensors, actuators=acts, primitives=prims, notes=notes)
    if p and p.get("fixed_location"):
        c["fixed_location"] = p["fixed_location"]
    if profile == "omx_arm":
        notes.append("fixed base: cannot locomote; set fixed_location to the room it stands in")
    return c


def run(args):
    profile = profiles.resolve(args.body) if args.body and args.body != "auto" else None
    if args.dry_run or args.sim:
        profile = profile or "microduck"
        scan = json.load(open(os.path.join(FIX, SCAN_FIXTURE[profile])))
        sensors, s_notes = devices.from_state(profile)
    else:
        from . import bus
        scan = bus.scan(args.port, args.baud)
        profile = profile or profiles.identify(scan)
        sensors, s_notes = devices.live([int(b) for b in args.i2c] if args.i2c else None)
    effects, traces = [], []
    if args.sim:
        if profile != "microduck":
            raise SystemExit("--sim exists for the MicroDuck only (the as-built MuJoCo model); use --dry-run for the arm")
        from . import sim_babble
        traces, info = sim_babble.run()
        effects = babble.analyse_all(traces)
        note = (f"babbling in MuJoCo (as-built duck, saddle mass, {info['volt']} V): {len(traces)} joints, amplitude grown "
                f"through {list(sim_babble.AMPS)} rad at KP {sim_babble.KP_BABBLE} while the trunk tilted under "
                f"{sim_babble.GROW_TILT_DEG} deg, the rest at KP {sim_babble.KP_STAND}; jaw not in the sim model"
                + ("" if info["renderer"] else f"; no camera render ({info['note']})"))
        aborted = [t["joint"] for t in traces if t.get("aborted")]
        if aborted:
            note += f"; aborted at {sim_babble.ABORT_TILT_DEG} deg tilt: {', '.join(aborted)}"
    elif args.dry_run:
        path = os.path.join(FIX, "duck_babble_recorded.json")
        if profile == "microduck":
            traces = json.load(open(path))["traces"]
            effects = babble.analyse_all(traces)
            missing = sorted(set(profiles.DUCK_IDS.values()) - {t["joint"] for t in traces})
            note = (f"babbling replayed from {len(traces)} recorded single-joint windows (fixtures/duck_babble_recorded.json, "
                    f"real IMU, no camera); no recorded window for: {', '.join(missing) or 'none'}")
        else:
            note = "no babbling: this body has no IMU and no recorded single-joint camera windows"
    elif args.babble:
        if not args.i_am_watching:
            raise SystemExit("--babble moves every joint: add --i-am-watching (someone at the robot, ready to catch it)")
        traces = live_babble(args, profile, scan, sensors)
        effects = babble.analyse_all(traces)
        note = f"live babbling on {len(traces)} joints"
    else:
        note = "no babbling (pass --babble --i-am-watching on the robot)"
    c = build_card(profile, scan, sensors, s_notes, effects, "sim" if args.sim else "dry-run" if args.dry_run else "live", note)
    path = card.write(c, args.out)
    if args.traces_out:
        json.dump(dict(traces=traces, effects=effects), open(args.traces_out, "w"))
    return c, path


def live_babble(args, profile, scan, sensors):
    """Babble every answering servo with the robot standing; IMU from the BNO085, image change from the first camera."""
    import math
    from . import bus
    imu = next((s for s in sensors if s["kind"] == "imu"), None)
    if imu is None:
        raise SystemExit("live babbling needs an IMU")
    from adafruit_bno08x import BNO_REPORT_GYROSCOPE, BNO_REPORT_ROTATION_VECTOR
    from adafruit_bno08x.i2c import BNO08X_I2C
    from adafruit_extended_bus import ExtendedI2C
    bno = BNO08X_I2C(ExtendedI2C(int(imu["id"].split("@i2c-")[1].split(":")[0])), address=0x4A)
    bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)
    bno.enable_feature(BNO_REPORT_GYROSCOPE)
    cam = None
    cams = [s for s in sensors if s["kind"] == "camera" and s["id"].startswith("/dev/video")]
    if cams:
        try:
            import cv2
            cam = cv2.VideoCapture(cams[0]["id"])
        except ImportError:
            cam = None
    ref = {}

    def sample():
        i, j, k, r = bno.quaternion
        # gravity in the sensor frame: R^T (0, 0, -1)
        g = (-2 * (i * k - r * j), -2 * (j * k + r * i), -(1 - 2 * (i * i + j * j)))
        img = None
        if cam is not None:
            ok, frame = cam.read()
            if ok:
                f = frame.astype("float32") / 255.0
                if "img" not in ref:
                    ref["img"], ref["mad"] = f, float(abs(f - f.mean()).mean()) or 1.0
                img = float(abs(f - ref["img"]).mean()) / ref["mad"]
        return g, bno.gyro, img

    names = profiles.joint_names(profile) if profile else {}
    traces = []
    for m in scan["motors"]:
        if m.get("operating_mode") not in (3, None):  # current-based or other modes: skip (the duck jaw runs mode 5)
            continue
        ref.clear()
        tr = bus.babble_joint(args.port, args.baud, m["id"], amps=(0.02, 0.04, 0.08), kp=args.babble_kp, sample=sample)
        tr.update(joint=names.get(m["id"], f"joint_{m['id']}"), source=f"live babbling ID {m['id']} at P {args.babble_kp}")
        traces.append(tr)
    return traces


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--body", default="auto", help="duck | arm | auto (live: from the scan)")
    ap.add_argument("--dry-run", action="store_true", help="recorded bus scan and recorded IMU windows (fixtures/)")
    ap.add_argument("--sim", action="store_true", help="recorded bus scan, babbling in the as-built MuJoCo duck")
    ap.add_argument("--port", default="/dev/ttyAS2")
    ap.add_argument("--baud", type=int, default=500000)
    ap.add_argument("--i2c", nargs="*", default=None, help="I2C bus numbers to probe live (default all)")
    ap.add_argument("--babble", action="store_true", help="live: move each joint (needs --i-am-watching)")
    ap.add_argument("--i-am-watching", action="store_true")
    ap.add_argument("--babble-kp", type=int, default=200, help="live babbling P gain (stand mode runs at 400)")
    ap.add_argument("--out", default=card.CARD_PATH)
    ap.add_argument("--traces-out", default=None, help="also write the babbling traces and their analysis here")
    args = ap.parse_args(argv)
    if args.sim:
        try:
            import mujoco  # noqa: F401
        except ImportError:  # the as-built model needs the patched bam in ~/.venvs/microduck-dyn
            os.chdir(card.REPO)
            os.execv(SIM_PYTHON, [SIM_PYTHON, "-m", "pet.body.inspect"] + (argv if argv is not None else sys.argv[1:]))
    c, path = run(args)
    print(f"{path}: {c['name']}, {len(c['sensors'])} sensors, {sum(a['ok'] for a in c['actuators'])}/{len(c['actuators'])} "
          f"actuators ok, primitives {[p['name'] for p in c['primitives']]}")


if __name__ == "__main__":
    main()

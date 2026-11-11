"""Export the released flight-pack CAD meshes for the design pages (flying-duck-design*.html).

Reads, writes nothing else:
- sim/out/visual/flightpack-nominal.json  visual_parts: the release-FlightPack-D1 printed parts and the bought-part dummies
  (cad/build/*-world.stl) with their release colours, the same list the simulator draws;
- cad/flight_params.py                   fan lip centres, lip top, cant (jets and fan labels);
- guide/print/world/sd_*.stl              the A7Z rear ports and the camera plug in the saddle (to show they stay free).
All STLs are in the guide frame (= trunk_base frame, mm). The duck's trunk sits at stand-world (0, 0, 120) with no rotation
in the stand keyframe (scene_battery-20261104.xml), so stand-world = guide + (0, 0, 120); duck_poses.json is in stand-world.

    /tmp/microduck-cad-venv/bin/python export_pack_meshes.py      -> pack_meshes.json
"""
import base64
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh

H = Path(__file__).resolve().parent
SIM = H.parents[1]
WORLD = SIM / "guide" / "print" / "world"
sys.path.insert(0, str(H / "cad"))
import flight_params as Pm  # noqa: E402

Z_STAND = 120.0
vis = json.loads((H / "sim" / "out" / "visual" / "flightpack-nominal.json").read_text())

GROUP = {  # part id -> page group (toggle and legend colour)
    "wing_plate": "plate", "tray_L": "plate", "tray_R": "plate", "fc_bracket": "plate",
    "nacelle_inner_L": "shell", "nacelle_outer_L": "shell", "nacelle_inner_R": "shell", "nacelle_outer_R": "shell",
    "dummy_fan_front_L": "fan", "dummy_fan_front_R": "fan", "dummy_fan_rear_L": "fan", "dummy_fan_rear_R": "fan",
    "dummy_battery_L": "battery", "dummy_battery_R": "battery", "dummy_fc_esc_stack": "fc", "dummy_mtf01": "flow",
    "dummy_esc_capacitor": "cap",
}
COLOUR = {  # page colours: printed parts in their filament colour, bought parts picked to tell them apart
    "plate": [0.95, 0.45, 0.06], "shell": [0.16, 0.16, 0.18], "fan": [0.55, 0.58, 0.63], "battery": [0.71, 0.20, 0.17],
    "fc": [0.12, 0.33, 0.70], "flow": [0.15, 0.55, 0.32], "cap": [0.20, 0.20, 0.22], "port": [0.95, 0.76, 0.0],
    "plug": [0.60, 0.63, 0.66],
}


def pack_mesh(m: trimesh.Trimesh):
    v = (np.asarray(m.vertices, float) + [0, 0, Z_STAND]).astype("<f4")
    f = np.asarray(m.faces, dtype="<u4")
    return base64.b64encode(v.tobytes()).decode(), base64.b64encode(f.tobytes()).decode()


parts = []
bounds = {}
for vp in vis["visual_parts"]:
    pid = vp["id"]
    src = SIM / vp["file"]
    m = trimesh.load(src, force="mesh")
    m.merge_vertices()
    g = GROUP[pid]
    pos, idx = pack_mesh(m)
    lo, hi = m.bounds + [0, 0, Z_STAND]
    bounds[pid] = [lo.round(1).tolist(), hi.round(1).tolist()]
    parts.append(dict(id=pid, group=g, color=COLOUR[g], pos=pos, idx=idx, faces=int(len(m.faces)),
                      src=str(src.relative_to(SIM)), sha12=hashlib.sha256(src.read_bytes()).hexdigest()[:12]))
for key, g in (("sd_usb_c_otg_dp", "port"), ("sd_usb_c_power", "port"), ("sd_micro_hdmi", "port"), ("sd_usb_c_plug", "plug")):
    src = WORLD / f"{key}.stl"
    m = trimesh.load(src, force="mesh")
    pos, idx = pack_mesh(m)
    lo, hi = m.bounds + [0, 0, Z_STAND]
    bounds[key] = [lo.round(1).tolist(), hi.round(1).tolist()]
    parts.append(dict(id=key, group=g, color=COLOUR[g], pos=pos, idx=idx, faces=int(len(m.faces)),
                      src=str(src.relative_to(SIM)), sha12=hashlib.sha256(src.read_bytes()).hexdigest()[:12]))

# fans: lip-face centre, exhaust direction and the axial distance of the dummy's far end (jet start)
S, C = math.sin(math.radians(Pm.CANT_DEG)), math.cos(math.radians(Pm.CANT_DEG))
fans = {}
for which in ("front", "rear"):
    for side, tag in ((+1, "L"), (-1, "R")):
        pid = f"dummy_fan_{which}_{tag}"
        lip = np.array([Pm.FAN_X[which], side * Pm.FAN_Y, Pm.LIP_Z + Z_STAND])
        axis = np.array([Pm.DIR[which] * S, 0.0, -C])
        v = np.asarray(trimesh.load(SIM / next(p["file"] for p in vis["visual_parts"] if p["id"] == pid), force="mesh").vertices)
        t_end = float(((v + [0, 0, Z_STAND] - lip) @ axis).max())
        fans[f"{which}_{tag}"] = dict(lip=lip.round(2).tolist(), axis=axis.round(5).tolist(), t_end=round(t_end, 1),
                                      lip_od=Pm.FAN["lip_od"], duct_od=Pm.FAN["duct_od"])


def top(pid, dz=3.0):
    lo, hi = bounds[pid]
    return [round((lo[0] + hi[0]) / 2, 1), round((lo[1] + hi[1]) / 2, 1), round(hi[2] + dz, 1)]


def bottom(pid, dz=3.0):
    lo, hi = bounds[pid]
    return [round((lo[0] + hi[0]) / 2, 1), round((lo[1] + hi[1]) / 2, 1), round(lo[2] - dz, 1)]


wlo, whi = bounds["wing_plate"]
anchors = {  # label anchor points, stand-world mm; the page supplies the words
    "fan_FR": [fans["front_R"]["lip"][0], fans["front_R"]["lip"][1], Pm.LIP_TOP_Z + Z_STAND + 3],
    "fan_FL": [fans["front_L"]["lip"][0], fans["front_L"]["lip"][1], Pm.LIP_TOP_Z + Z_STAND + 3],
    "fan_RR": [fans["rear_R"]["lip"][0], fans["rear_R"]["lip"][1], Pm.LIP_TOP_Z + Z_STAND + 3],
    "fan_RL": [fans["rear_L"]["lip"][0], fans["rear_L"]["lip"][1], Pm.LIP_TOP_Z + Z_STAND + 3],
    "battery_L": top("dummy_battery_L"), "battery_R": top("dummy_battery_R"),
    "wing_plate": [round((wlo[0] + whi[0]) / 2, 1), round(whi[1] - 8, 1), round(whi[2] + 2, 1)],
    "tray_R": bottom("tray_R"),
    "fc": top("dummy_fc_esc_stack"), "mtf01": bottom("dummy_mtf01"),
    "nacelle_L": bottom("nacelle_outer_L"),
    "ports": top("sd_usb_c_plug", 2.0),
}
out = dict(frame="stand-world mm (x forward, y left, z up) = guide frame + z 120; pack rides on trunk_base",
           release=vis.get("build"), cant_deg=Pm.CANT_DEG, parts=parts, bounds=bounds, fans=fans, anchors=anchors)
(H / "pack_meshes.json").write_text(json.dumps(out))
print(json.dumps(dict(parts=len(parts), faces=sum(p["faces"] for p in parts), kb=round((H / "pack_meshes.json").stat().st_size / 1024),
                      fans={k: v["t_end"] for k, v in fans.items()}, anchors=anchors)))

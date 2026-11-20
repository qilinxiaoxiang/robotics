"""Routed lead lengths of the flight pack from the CAD (guide frame, mm) and the wiring mass they give.
One waypoint list per lead, through the openings the parts provide: fan window (front fans), arm bay, gusset windows,
harness side run and rear crossing (left side), FC plate lead window (right battery), ESC pads and tabs as in
wiring/wiring.json (esc_pads_world, esc_tabs_world: pad set 1 FR, 2 RR, 3 FL, 4 RL). Writes checks/lead_lengths.json.
    /tmp/microduck-cad-venv/bin/python cad/lead_lengths.py
Rules: fan extension = route + 20 mm (two joints with strain relief, 10 mm each) - the factory lead (FAN lead_len, the
active fan set: ARESWEI about 140 mm per the seller), at least 40 mm; the lead may leave the motor in any of
Pm.lead_angles, and the longest of those routes sets the length, so every fan unplugs at its nacelle on bullets (wiring.json missing: female bullets);
battery pigtail = route from the pack's XT60 + 20 mm; the pack's own lead ends with its XT60 22 mm behind the web
(CNHL lead length not published: assumed); routes are rounded up to 10 mm.
"""
import json
import math
from pathlib import Path

import flight_params as Pm
from build_pack import A7Z_LINK, CAP_AXIS
from flight_params import FAN, WING

H = Path(__file__).resolve().parent
WJ = json.loads((H.parent / "wiring" / "wiring.json").read_text())["lengths"]
PAD = {k: tuple(v) for k, v in WJ["esc_pads_world"].items()}
TAB = {k: tuple(v) for k, v in WJ["esc_tabs_world"].items()}
G16, G12, XT60, BULLET = 15.0, 35.0, 4.0, 0.6        # g/m silicone 16 AWG, g/m 12 AWG, g per XT60 half, g per bullet
FAN_LEAD = FAN["lead_len"]


def length(p):
    return sum(math.dist(a, b) for a, b in zip(p[:-1], p[1:]))


def up10(v):
    return int(math.ceil(v / 10.0) * 10)


def ring(which, s, deg):
    """Where the motor leads leave the fan: motor front ring, radius motor_od / 2, direction deg (one of Pm.lead_angles)."""
    x, y, z = Pm.fan_point(which, sum(FAN["lead_t"]) / 2, s)
    a = math.radians(deg)
    r = FAN["motor_od"] / 2
    return (round(x + r * math.cos(a) * Pm.C, 1), round(y + r * math.sin(a), 1), round(z + r * math.cos(a) * Pm.DIR[which] * Pm.S, 1))


def longest(build, which, s):
    """The lead may leave in any of Pm.lead_angles: route each and keep the longest (the extension must reach from all)."""
    return max((build(ring(which, s, a)) for a in Pm.lead_angles(s)), key=length)


def main():
    routes = {}
    for s, nm in ((1, "L"), (-1, "R")):
        # front fans: out of the duct's inboard wall, rearward outboard of the tray edge (y 80.5) above deck level, clear of
        # the battery straps (they wrap the pack and the deck inboard of y 78.8), round the arm web's outer end (y 79)
        # into the bay; free radius >= 5 mm along y 82..84, z 30 (lane probe 2026-11-10)
        front_tail = [(20.0, s * 84.0, 28.5), (0.0, s * 84.0, 28.5), (-20.0, s * 84.0, 28.5), (-40.0, s * 83.5, 28.0),
                      (-48.5, s * 82.5, 26.5), (-53.0, s * 81.5, 26.0)]
        rear_tail = [(-55.0, s * 77.0, 24.0)]
        if s > 0:   # left: along the bay through the gusset windows to the harness, behind the backpack, up behind the ESC
            xc = WING["harness_cross_x"]          # behind the backpack cap (moves with the backpack)
            bay = [(-56.0, 75.0, 26.0), (-56.0, 50.0, 27.0), (-56.0, 39.0, 27.0)]
            # side run on y 35.0 (2.4 from the inboard gusset at 37.9, 0.6 outboard of the backpack wall at 32); the rise
            # at x -86.8, y -33: behind the backpack cap (x -82.5) and the ESC (x -83), inboard of the FC (y -38)
            cross = [(-58.0, 35.0, 24.0), (-64.0, 35.0, 21.0), (xc, 35.0, 10.0), (xc, -33.0, 10.0), (-86.8, -33.0, 24.0)]
            routes["fan FL"] = (longest(lambda r0: [r0] + front_tail + bay + cross + [(-86.8, -33.0, PAD["M3"][2]), PAD["M3"]], "front", s),
                                "outboard of the tray edge, round the arm end, arm bay, gusset windows, harness side run, rear crossing, up behind the ESC, pad set 3")
            routes["fan RL"] = (longest(lambda r0: [r0] + rear_tail + bay + cross + [(-86.8, -33.0, PAD["M4"][2]), PAD["M4"]], "rear", s),
                                "arm bay outer end, gusset windows, harness side run, rear crossing, up behind the ESC, pad set 4")
            routes["battery L"] = ([(-58.2, 61.0, 45.0), (-57.0, 58.0, 30.0), (-56.0, 50.0, 27.0), (-56.0, 39.0, 27.0)] + cross
                                   + [(-86.8, -33.0, 63.5), (-81.0, -37.0, 63.5), (-80.0, -45.0, 63.3), (-80.0, -56.0, 62.0)],
                                   "lead window, arm bay, gusset windows (open to the rear: laid in with the XT60 on), harness, rear crossing, up behind the ESC, tabs from above")
        else:       # right: round the FC plate's outboard edge to pad sets 1/2; battery through the plate lead window
            out = [(-56.0, -77.5, 26.0), (-66.0, -77.5, 30.0)]          # plate edge y -74: 1.3 mm clear
            routes["fan FR"] = (longest(lambda r0: [r0] + front_tail + out + [(-75.5, -79.0, 44.0), PAD["M1"]], "front", s),
                                "outboard of the tray edge, round the arm end, arm bay, round the FC plate outboard edge, ESC pad set 1")
            routes["fan RR"] = (longest(lambda r0: [r0] + [(-55.0, -77.5, 24.0), (-66.0, -77.5, 27.0), (-75.5, -79.0, 29.0), PAD["M2"]], "rear", s),
                                "arm bay outer end, round the FC plate outboard edge, ESC pad set 2")
            # up in the 10 mm gap between the plate (x -67) and the ESC front (x -77), not against the ESC
            routes["battery R"] = ([(-58.2, -61.0, 45.0), (-60.0, -61.0, 31.0), (-72.0, -61.0, 31.0), (-72.0, -61.0, 52.0), (-75.7, -60.6, 56.0), (-75.7, -60.6, 61.0)],
                                   "lead window, arm bay, FC plate lead window (passes the XT60), up between plate and ESC, onto the back face of the tabs")
    cap_end = (CAP_AXIS["x0"] - Pm.CAP["h"], CAP_AXIS["y"], WING["arm_z"][1] + Pm.CAP["d"] / 2)
    out = dict(rules=__doc__.split("Rules: ")[1].strip(), leads={})
    mass = {"left": 0.0, "right": 0.0}
    for k, (p, path) in routes.items():
        r = length(p)
        side = "left" if k.endswith("L") else "right"
        if k.startswith("fan"):
            ext = max(40, up10(r + 20 - FAN_LEAD))
            g = 3 * ext / 1000 * G16 + 3 * 2 * BULLET
            out["leads"][k] = dict(route_mm=round(r), extension_mm=ext, conductors="3 x 16 AWG", path=path, pts=p)
        else:
            ext = up10(r + 20)
            g = 2 * ext / 1000 * G12 + XT60
            out["leads"][k] = dict(route_mm=round(r), pigtail_mm=ext, conductors="2 x 12 AWG + XT60", path=path, pts=p)
        mass[side] += g
    a7z = length(A7Z_LINK) + 3.0
    out["leads"]["A7Z to FC"] = dict(route_mm=round(a7z), lead_mm=300, needed_mm=up10(a7z + 30),
                                     path="housing tops, along the header strip, over the right saddle wall in front of the lid, outboard of the lid edge along the wall's outer top corner (y -36.3), behind the transition column, over the ESC top, FC UART1 on the top edge",
                                     pts=A7Z_LINK, note="needed = route + 15 mm slack at each plug; the 300 mm lead leaves the rest coiled and tied")
    mass["right"] += 3.0
    out["capacitor"] = dict(end_face=cap_end, to_plus_tab_mm=round(math.dist(cap_end, TAB["+"]), 1),
                            to_minus_tab_mm=round(math.dist(cap_end, TAB["-"]), 1))
    out["mass_g"] = {k: round(v, 1) for k, v in mass.items()}
    out["wiring_agent"] = WJ["cad_agent_claims"] | {k: v for k, v in (("FL", WJ["fans"]["FL"]["ext_mm"]), ("RL", WJ["fans"]["RL"]["ext_mm"]),
                                                                   ("FR", WJ["fans"]["FR"]["ext_mm"]), ("RR", WJ["fans"]["RR"]["ext_mm"]))}
    (H / "checks" / "lead_lengths.json").write_text(json.dumps(out, indent=1))
    for k, v in out["leads"].items():
        print(f"{k:12s} route {v['route_mm']:4d}  ->", v.get("extension_mm", v.get("pigtail_mm", v.get("needed_mm"))), " ", v["path"])
    print("capacitor end to tabs", out["capacitor"]["to_plus_tab_mm"], out["capacitor"]["to_minus_tab_mm"], "mass", out["mass_g"])


if __name__ == "__main__":
    main()

"""Build scenes.json for render_views.py from results/summary.json (the poses the sim reached) and the kinematic postures.

  python3 make_scenes.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facegeom as fg  # noqa: E402

S = json.load(open(os.path.join(HERE, "results", "summary.json")))
scenes = []


def sim_scene(name, s, dist, face):
    scenes.append(dict(name=name, q=s["reached_q"], gb=s["trunk_gb"], dist_m=dist, face_m=face))


# stand61 with the default head (the sim trunk leans back about 3.5 deg on stand61; policy_head rows)
scenes.append(dict(name="stand61_default_seated_person_1.0m", q=dict(fg.NEUTRAL), gb=list(fg.gb_from_pitch(-3.5)), dist_m=1.0, face_m=1.1))
sim_scene("stand61_hp-1.10_adult_0.5m", S["policy_head"]["hp-1.10"], 0.5, 1.6)
sim_scene("stand61_hp-1.10_seated_person_1.0m", S["policy_head"]["hp-1.10"], 1.0, 1.1)
sim_scene("walk61_hp-0.75_adult_1.0m", S["walk_head"]["hp-0.75"], 1.0, 1.6)
sim_scene("sit_hp-1.10_adult_0.5m", S["sit"]["hp-1.10"], 0.5, 1.6)
sim_scene("sit_hp-1.10_seated_person_1.0m", S["sit"]["hp-1.10"], 1.0, 1.1)
sim_scene("groundpick_bow_adult_0.5m", S["gp"]["phase0.4"], 0.5, 1.6)
# open-loop neck-forward look-up (kinematic pose at the held rest pitch, if round 3 held it)
ol = S.get("openloop3", {}).get("O3_nk-0.47_hp-1.571") or S.get("openloop", {}).get("O_nk-0.47_hp-1.571")
if ol and ol.get("end_pitch_held"):
    pose = json.load(open(os.path.join(HERE, "poses_openloop3.json")))["O3_nk-0.47_hp-1.571"]
    scenes.append(dict(name="openloop_nk-0.47_hp-1.571_adult_0.5m", q=pose, gb=list(fg.gb_from_pitch(ol["end_pitch_held"][0])), dist_m=0.5, face_m=1.6))
# lying on the back, head toward the feet (sim row: trunk -91 deg)
scenes.append(dict(name="lying_hp+0.80_adult_0.5m", q=dict(fg.STAND, head_pitch=1.149), gb=list(fg.gb_from_pitch(-91.0)), dist_m=0.5, face_m=1.6))
json.dump(scenes, open(os.path.join(HERE, "scenes.json"), "w"), indent=1)
print(len(scenes), "scenes")

"""Renders for the battery cap study with guide/content/render.py (vtk, light background): the as-built robot at HOME
(feet flat, posed by battery_cap_study.py into scene_home.pkl), the released layout-F box (frame, cap, boards, 5991,
V1.8 pack, OpenRB) and one grey box per pack in its chosen position, plus the XT30 envelope.

    /tmp/microduck-cad-venv/bin/python render_study.py        (under run_bounded_cad.py; needs scene_home.pkl)
Writes renders/<pack>-rear34_0.png (rear 3/4 from the -y side) and renders/<pack>-side_0.png."""
import sys, json, pickle
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent
SIM = Path('/Users/xiangzheng/code/robotics/microduck-sim')
sys.path.insert(0, str(SIM / 'guide/content'))
from render import render
S = pickle.load(open(HERE / 'scene_home.pkl', 'rb')); R, p = S['trunkR'], S['trunkPos'] / 0.001
J = json.loads((HERE / 'battery_cap_study.json').read_text())
LF = SIM / 'guide/print/back-plate/layout-F'
PARTS = [(LF / 'rear_frame-world.stl', (237, 128, 26)), (LF / 'rear_lid-world.stl', (250, 158, 51)), (SIM / 'guide/print/world/rear_pack-v18.stl', (237, 128, 26)),
         (LF / 'xl4015_top_7V_render.stl', (31, 77, 230)), (LF / 'xl4015_mid_5V_render.stl', (31, 77, 230)), (LF / 'pd5991_F-world.stl', (20, 20, 20)),
         (SIM / 'guide/print/world/openrb-board-upright.stl', (38, 89, 51))]
def world(v):
    return (np.asarray(v, float) @ R.T + p).astype(np.float32)
base = dict(S['scene'])
for f, c in PARTS:
    tm = trimesh.load(str(f), force='mesh'); base[f.stem] = dict(v=world(tm.vertices), f=tm.faces.copy(), color=list(c), module='box')
# floor tile for the shadow line
fl = trimesh.creation.box(bounds=[[-220, -160, -1.0], [160, 160, 0.0]]); base['floor'] = dict(v=fl.vertices.astype(np.float32), f=fl.faces.copy(), color=[225, 225, 222], module='floor')
CHOICE = json.loads((HERE / 'render_choice.json').read_text())      # {"tattu650": placementKey, "tattu850": placementKey, "connector": key}
out = HERE / 'renders'; out.mkdir(exist_ok=True); done = {}
for pk in ('tattu650', 'tattu850'):
    sc = dict(base); key = CHOICE[pk]; P = J['placements'][key]
    lo, hi = np.array(P['packBoxMm'][0]), np.array(P['packBoxMm'][1])
    bx = trimesh.creation.box(bounds=[lo, hi]); sc['pack_' + pk] = dict(v=world(bx.vertices), f=bx.faces.copy(), color=[120, 120, 120], module='battery')
    plo, phi = np.array(P['pocketOuterMm'][0]), np.array(P['pocketOuterMm'][1])
    pb = trimesh.creation.box(bounds=[plo, phi]); sc['pocket_' + pk] = dict(v=world(pb.vertices), f=pb.faces.copy(), color=[250, 158, 51], module='pocket')
    C = J['connectors'][CHOICE['connector']]; clo, chi = np.array(C['envelopeMm'][0]), np.array(C['envelopeMm'][1])
    cb = trimesh.creation.box(bounds=[clo, chi]); sc['xt30'] = dict(v=world(cb.vertices), f=cb.faces.copy(), color=[200, 40, 40], module='xt30')
    look = np.array([-45.0, 0, 0.0]) @ R.T + p
    views = [((look + np.array([-360.0, -330.0, 190.0])).tolist(), look.tolist(), [0, 0, 1]),      # rear 3/4 from -y, above
             ((look + np.array([-10.0, -430.0, 40.0])).tolist(), look.tolist(), [0, 0, 1])]        # -y side
    done[pk] = render(sc, views, str(out / f'{pk}-view.png'), size=(1100, 850), ghost=('pocket',))
print(json.dumps(done, indent=1))

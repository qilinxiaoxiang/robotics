"""Measure the two converter boards and place them in the world frame at the contract positions (mm, x forward, y left, z up).

XL4015: ROBOTIS mesh ../candidates/back-box-20261014/parts/xl4015_board_local_mm.stl (local X = PCB normal to the
component face, Y = long axis, Z = short axis). Measured here: the PCB occupies local X -1.95..-0.40, so its mid-plane is
local X = -1.175 (the parts README's "origin at the PCB centre" is off by 1.175 mm along X).
Contract pose: component face towards -x, long axis along y, PCB mid-plane at world x -51.75, centres z 0.5 / 27.9:
    world = (-51.75 - (X + 1.175), -Y, zc + Z)      (180 deg about z; local +Y end -> world -y)
Adafruit 5991: outline, holes and part placements from Adafruit's own Eagle board file
https://github.com/adafruit/Adafruit-USB-Type-C-PD-Switchable-PCB (Adafruit USB Type C PD Switchable.brd, main branch,
fetched 2026-10-14). Board frame (u, v) in mm, v along the 27.813 edge, USB-C X1 at v 23.876 (R180), terminal X4 at v 3.81.
Contract pose: PCB vertical, USB-C down, terminal up, component side towards -x, PCB back face at x -47.5 (0.5 behind the
plate face), receptacle face on the bottom wall inner face z -34.8, centred on y 0.
Writes xl4015_lower-world.stl, xl4015_upper-world.stl, pd5991-world.stl, board_facts.json."""
import sys, json
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rear-pack'))
import pack_lib as P

XL_SRC = HERE.parent / 'candidates/back-box-20261014/parts/xl4015_board_local_mm.stl'
PCB_X = (-1.95, -0.40)                      # measured PCB faces (local X): largest +X / -X normal planes of the mesh
PCB_MID = sum(PCB_X) / 2
XL_MID_X = -51.75
XL_ZC = {'lower': 0.5, 'upper': 27.9}
HOLES_LOCAL = [(sy * 28.25, sz * 10.5) for sy in (1, -1) for sz in (1, -1)]   # (Y, Z), pattern 56.5 x 21.0


def xl_world(V, zc):
    V = np.asarray(V, float)
    return np.c_[XL_MID_X - (V[:, 0] - PCB_MID), -V[:, 1], zc + V[:, 2]]


# ---------------------------------------------------------------- 5991 from the Adafruit board file (mm)
PD = dict(pcb=(20.32, 27.813, 1.6), holes_uv=[(2.413, 25.273), (17.653, 25.273), (2.54, 2.54), (17.78, 2.54)], hole_d=2.5,
          usbc=dict(uv0=(10.16 - 4.47, 23.876 - 2.27), uv1=(10.16 + 4.47, 23.876 + 5.08), h=3.3),      # CUSB31 package extent, R180
          term=dict(uv0=(10.16 - 3.4, 3.81 - 3.6), uv1=(10.16 + 3.6, 3.81 + 3.4), h=8.5),             # 3.5 mm 2-pin block, entries face v = 0
          dip=dict(uv0=(15.621 - 2.7, 12.573 - 3.97), uv1=(15.621 + 2.7, 12.573 + 3.97), h=2.0),       # 6-way DIP, R90
          qt=dict(uv0=(3.1115 - 2.594, 16.256 - 3.0), uv1=(3.1115 + 1.706, 16.256 + 3.1), h=3.0))      # STEMMA QT JST-SH, R270
PD_BACK_X = -47.5
PD_USB_FACE_Z = -34.8
PD_V_EDGE_Z = PD_USB_FACE_Z + (PD['usbc']['uv1'][1] - PD['pcb'][1])   # USB-C overhangs the PCB edge by 1.147


def pd_world(u, v, w):
    """board (u, v, w: w = height above the PCB bottom face, components on +w) -> world."""
    return np.array([PD_BACK_X - w, u - PD['pcb'][0] / 2, PD_V_EDGE_Z + (PD['pcb'][1] - v)])


def pd_box(uv0, uv1, w0, w1):
    a = pd_world(uv0[0], uv0[1], w0); b = pd_world(uv1[0], uv1[1], w1)
    lo = np.minimum(a, b); hi = np.maximum(a, b)
    return trimesh.creation.box(extents=hi - lo, transform=trimesh.transformations.translation_matrix((lo + hi) / 2)), (lo, hi)


if __name__ == '__main__':
    src = trimesh.load(str(XL_SRC), force='mesh')
    facts = {'xl4015': {}, 'pd5991': {}}
    V = src.vertices
    f = facts['xl4015']
    f['source'] = str(XL_SRC)
    f['pcbFacesLocalX'] = list(PCB_X); f['pcbThickness'] = round(PCB_X[1] - PCB_X[0], 3); f['pcbMidLocalX'] = PCB_MID
    f['outlineLocalYZ'] = [[round(float(V[:, 1].min()), 3), round(float(V[:, 1].max()), 3)], [round(float(V[:, 2].min()), 3), round(float(V[:, 2].max()), 3)]]
    f['componentHeightAboveComponentFace'] = round(float(V[:, 0].max() - PCB_X[1]), 3)
    f['pinDepthBelowBackFace'] = round(float(PCB_X[0] - V[:, 0].min()), 3)
    f['stackTotal'] = round(float(V[:, 0].max() - V[:, 0].min()), 3)
    f['stackFromMidPlane'] = dict(componentSide=round(float(V[:, 0].max() - PCB_MID), 3), pinSide=round(float(PCB_MID - V[:, 0].min()), 3))
    # named bodies (local bounding boxes measured from the mesh split)
    f['bodiesLocal'] = {
        'inductor': dict(lo=[0.6, 1.74, -7.56], hi=[13.17, 8.95, 5.56], note='tallest part (wound coil slices to X 13.17)'),
        'trimmer_a': dict(lo=[-3.0, -11.72, 7.99], hi=[11.15, -2.18, 12.82], screwHeadYZ=[[-11.6, -9.28], [10.46, 12.68]], note='9.54 x 4.83 multi-turn trimmer, adjusting screw at its -Y end on the long edge'),
        'trimmer_b': dict(lo=[-3.0, -1.22, 7.99], hi=[11.15, 8.31, 12.82], screwHeadYZ=[[-1.1, 1.22], [10.46, 12.68]], note='second identical trimmer (CV and CC trimmers of a CC/CV module; which is which is not on the mesh)'),
        'regulator_ic': dict(lo=[-0.4, -10.94, -12.68], hi=[4.18, -0.76, -2.48], note='10 x 10 TO-263 body = XL4015'),
        'caps': [dict(lo=[0.6, 11.61, -11.62], hi=[10.23, 21.78, -1.33]), dict(lo=[0.6, -21.86, -11.62], hi=[10.21, -11.69, -1.33])],
        'terminal_plusY': dict(lo=[-0.4, 23.1, -5.17], hi=[9.6, 30.76, 5.0], wireEntriesFace='+Y (board end)', entryCentresYZ=[[30.15, 2.5], [30.15, -2.5]], entryXRange=[1.5, 3.5]),
        'terminal_minusY': dict(lo=[-0.4, -30.76, -5.0], hi=[9.6, -23.1, 5.11], wireEntriesFace='-Y (board end)', entryCentresYZ=[[-30.15, 2.5], [-30.15, -2.5]], entryXRange=[1.5, 3.5]),
    }
    f['inOutEnds'] = 'not identifiable from the mesh (no silkscreen); the contract puts IN on -y for both boards, i.e. local +Y, to be read from the board label'
    f['holesLocalYZ'] = HOLES_LOCAL; f['holeDia'] = 2.5
    f['worldPose'] = 'world = (-51.75 - (X + 1.175), -Y, zc + Z)'
    for nm, zc in XL_ZC.items():
        W = xl_world(V, zc)
        mesh = trimesh.Trimesh(W, src.faces, process=False)
        mesh.export(HERE / f'xl4015_{nm}-world.stl')
        f[nm] = dict(zc=zc, worldBounds=np.round(mesh.bounds, 3).tolist(), pcbWorldX=[XL_MID_X - (PCB_X[1] - PCB_MID), XL_MID_X + (PCB_MID - PCB_X[0])],
                     holesWorld=[[round(float(XL_MID_X), 3), -y, round(zc + z, 3)] for (y, z) in HOLES_LOCAL],
                     trimmerScrewHeadsWorld={t: dict(y=sorted([-a for a in f['bodiesLocal'][t]['screwHeadYZ'][0]]), z=[zc + a for a in f['bodiesLocal'][t]['screwHeadYZ'][1]],
                                                     x=round(XL_MID_X - (11.15 - PCB_MID), 3)) for t in ('trimmer_a', 'trimmer_b')})
    # ---- 5991
    g = facts['pd5991']
    g['source'] = 'https://github.com/adafruit/Adafruit-USB-Type-C-PD-Switchable-PCB (Eagle .brd, fetched 2026-10-14); product page https://www.adafruit.com/product/5991 (29.1 x 20.3 x 10.1 mm, 3.5 g)'
    g['boardFile'] = PD
    g['finding'] = 'USB-C receptacle on one 20.32 mm short edge (v = 27.8), screw terminal on the opposite short edge (v = 0); four dia 2.5 plated holes at the corners'
    parts = []; ext = {}
    pcb, ext['pcb'] = pd_box((0, 0), PD['pcb'][:2], 0, PD['pcb'][2]); parts.append(pcb)
    for k in ('usbc', 'term', 'dip', 'qt'):
        b, ext[k] = pd_box(PD[k]['uv0'], PD[k]['uv1'], PD['pcb'][2], PD['pcb'][2] + PD[k]['h']); parts.append(b)
    pdm = trimesh.util.concatenate(parts)
    pdm.export(HERE / 'pd5991-world.stl')
    g['worldBounds'] = np.round(pdm.bounds, 3).tolist()
    g['worldBoxes'] = {k: np.round(np.array(v), 3).tolist() for k, v in ext.items()}
    g['holesWorld'] = [np.round(pd_world(u, v, 0), 3).tolist() for u, v in PD['holes_uv']]
    g['note'] = 'box model: PCB + USB-C, terminal, DIP and STEMMA QT envelopes from the board file; component heights are estimates (total 10.1 from the product page)'
    P.jdump(facts, HERE / 'board_facts.json')
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ('bodiesLocal', 'boardFile')} for k, v in facts.items()}, indent=1))

"""Build the V1.6 incremental release manifest from the V1.5 manifest (read-only) plus the notched head cap and the new OpenRB-150 tray."""
import copy, hashlib, json, trimesh, numpy as np
from pathlib import Path
G = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print')
R = G / 'release-V1.6'
V15 = Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/printing/15-COMPLETE-INCREMENTAL-20261009/complete-incremental.json')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): p = Path(p).resolve(); return dict(path=str(p), sha256=sha(p))
def bed_area(p):
    m = trimesh.load(p, force='mesh', process=False); v, inv = np.unique(m.vertices, axis=0, return_inverse=True); m = trimesh.Trimesh(v, inv[m.faces], process=False)
    m.apply_translation([0, 0, -m.bounds[0, 2]]); at = np.max(np.abs(m.triangles[:, :, 2]), 1) <= .01; return float(m.area_faces[at].sum())
tray_dir = G / 'tray'
tray_ev = dict(
    schemaVersion=1, date='2026-10-09', part='openrb_tray', decision='addition', replacesStockIds=[],
    reason='OpenRB-150 moves from the head to the power-support lower deck (board flat, USB-C rearward). No original89 printed part holds the board at this location, so this is a new printed part, not a reprint of stock.',
    boardPose=dict(frame='robot frame, mm, x forward, y left, z up', nativeToRobot='x_r = -45.95 - y_n, y_r = x_n, z_r = z_n + Zb', Zb=-50.5,
                   pinTailNote='Header pin tails below the PCB must be trimmed to 1.5 mm below the PCB bottom (robot z >= -52.0) before fitting.'),
    printOrientation='Base plate down (robot z = -55.5 is the bed plane), identity rotation; print STL = world STL translated by worldToPrint.',
    worldToPrint=json.load(open(R / 'evidence/tray-print-frame.json'))['worldToPrint'],
    supportBlockers='Two non-printing blockers keep tree supports out of the 1.9 mm PCB slot under the front lips (2.2 mm horizontal lip overhang printed unsupported).',
    files={k: ref(tray_dir / k) for k in ('tray.py', 'tray-params.json', 'openrb_tray-world.step', 'acceptance-static.json', 'allparts-check.json', 'insertion-path.json')} | {
        'world/openrb_tray.stl': ref(G / 'world/openrb_tray.stl'), 'world/openrb-board.stl': ref(G / 'world/openrb-board.stl'), 'stl/openrb_tray.stl': ref(G / 'stl/openrb_tray.stl')},
)
json.dump(tray_ev, open(R / 'evidence/openrb_tray-change.json', 'w'), indent=1)
cap_report = json.load(open(R / 'evidence/cap-notch-report-snapshot.json'))
def measure(p):
    m = trimesh.load(p, force='mesh', process=False); v, inv = np.unique(m.vertices, axis=0, return_inverse=True); m = trimesh.Trimesh(v, inv[m.faces], process=False)
    return dict(sha256=sha(p), volumeMm3=round(float(m.volume), 3), watertight=bool(m.is_watertight), windingConsistent=bool(m.is_winding_consistent), bodies=len(m.split(only_watertight=False)), bounds=np.round(m.bounds, 3).tolist(), bedContactMm2Within0p01=round(bed_area(p), 2))
cap_measured = dict(printStl=measure(G / 'stl/head_cap.stl'), worldStl=dict(sha256=sha(G / 'world/head_cap.stl')))
cap_ev = dict(
    schemaVersion=1, date='2026-10-09', part='head_cap', decision='replacement', replacesStockIds=['4'],
    reason='V1.5 head cap with a rear cable notch (9.0 mm wide at the top, 6.7 mm max bundle) and an external zip-tie hood, for the OpenRB-150 harness leaving the head. All geometry outside the edit box is identical to the V1.5 print source; same print orientation; same Bambu support blocker.',
    v15Source=dict(path='/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/power-sensor/head-controller-study/final-integration-20261009/prototype-adoption/head-cap-prototype-print.stl', sha256='3ca84ce24333fdfbf55016b7ce5142eaff2c6df21ef663fb885a1b9176711f07'),
    files={'stl/head_cap.stl': ref(G / 'stl/head_cap.stl'), 'world/head_cap.stl': ref(G / 'world/head_cap.stl'), 'capNotchReportSnapshot': ref(R / 'evidence/cap-notch-report-snapshot.json')},
    keyNumbers=dict(notch=cap_report['notch'], printability=cap_report['printability']),
    measuredFromFinalStl=cap_measured,
    reportSnapshotNote='cap-notch-report-snapshot.json was written before the rebuild that restored solid wall on the slanted +y notch side (thin 0.03-0.8 mm skin removed). Notch size, tie hood, local frame, print transform and bed contact are unchanged by that rebuild; its file hashes and volume refer to the earlier build. measuredFromFinalStl holds the final-file numbers.',
)
json.dump(cap_ev, open(R / 'evidence/head_cap-change.json', 'w'), indent=1)
m = json.load(open(V15)); n = copy.deepcopy(m)
n['version'] = 'V1.6'
n['prototypeScope'] = 'V1.5 complete incremental set with the notched head cap (rear cable exit) and the new OpenRB-150 lower-back tray; all four colours, both machines.'
n['knownFitBoundary'] = 'OpenRB-150 sits on the power-support lower deck; header pin tails must be trimmed to 1.5 mm below the PCB. Harness from the head exits through the cap rear notch; routing, tie placement and no-pinch checks are physical steps.'
n['deliveryContract'] = dict(n['deliveryContract'], supersedes=['V1.5 print package'], status='COMPLETE_CURRENT_INCREMENTAL_INVENTORY')
parts = []
for p in n['parts']:
    if p['key'] == 'head_cap':
        p = dict(p); p.update(ref(G / 'stl/head_cap.stl'))
        p['changeReason'] = 'V1.5 head cap plus a rear cable notch and external zip-tie hood for the OpenRB-150 harness; geometry outside the edit box is identical to V1.5.'
        p['incrementalEvidence'] = ref(R / 'evidence/head_cap-change.json')
        p['flatContact'] = dict(minimumAreaMm2=100)
    parts.append(p)
tray_area = bed_area(G / 'stl/openrb_tray.stl')
blk = [dict(ref(R / f'blockers/openrb_tray-lip-blocker-{s}-print.stl'), machines=['Bambu', 'Elegoo'], reason='Keep supports out of the PCB slot under the front lip (print frame).') for s in ('left', 'right')]
parts.append(dict(key='openrb_tray', color='Black', quantity=1, **ref(G / 'stl/openrb_tray.stl'), sourceToPrint=np.eye(4).tolist(),
                  flatContact=dict(minimumAreaMm2=float(np.floor(tray_area))), decision='addition', replacesStockIds=[],
                  changeReason='New OpenRB-150 tray on the power-support lower deck (board moved out of the head); no original89 stock counterpart.',
                  supportBlockers=blk, incrementalEvidence=ref(R / 'evidence/openrb_tray-change.json')))
n['parts'] = parts
n['placements']['Black'] = n['placements']['Black'] + [dict(key='openrb_tray', copy=1, translation=[45.0, 110.0, 0.0])]
# the notched cap hood adds 5.36 mm at +x in the print frame: keep the V1.5 12.4 mm gap to the speaker cradle
for pl in n['placements']['Orange']:
    if pl['key'] == 'speaker_cradle': pl['translation'][0] += 5.36
ov_path = R / 'pose-overrides.json'
if ov_path.exists():
    ov = json.load(open(ov_path))
    for p in n['parts']:
        if p['key'] in ov:
            o = ov[p['key']]; p['sourceToPrint'] = o['sourceToPrint']
            if 'flatContactMinimumAreaMm2' in o: p['flatContact'] = dict(minimumAreaMm2=o['flatContactMinimumAreaMm2'])
            if 'changeReasonSuffix' in o: p['changeReason'] = p['changeReason'] + ' ' + o['changeReasonSuffix']
            for c, pls in n['placements'].items():
                for pl in pls:
                    if pl['key'] == p['key'] and 'translation' in o: pl['translation'] = o['translation']
json.dump(n, open(R / 'complete-incremental-V1.6.json', 'w'), indent=2)
print('parts', len(parts), 'tray bed area', round(tray_area, 2))

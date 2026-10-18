"""V1.9 (as built 2026-10-14) signed mass manifest against the official MicroDuck MJCF.

Every entry is a signed point/mesh mass in a MuJoCo body frame, consumed by add_signed_inertias() in the
September evaluator (parallel-axis theorem). Nothing in the September folders is modified.

Frames: guide robot frame = MJCF trunk_base frame at qpos0, mm (guide/content/interference-audit/
power-support-origin/pso_lib.py, guide/extension-20261012-neck-audio/neck-route/nr_lib.py). A guide-frame point p
maps to body b as R_b^T (p - x_b), with (x_b, R_b) the body pose relative to trunk_base at qpos0.

Mass bases (each entry carries `basis`):
  slicer  : per-object model filament (walls+infill+skin, no support/brim) from the released Elegoo G-code
            (slicer-part-masses.json, gcode_part_masses.py), distributed over the closed audit solid.
  rho_eff : closed solid volume x the slicer-calibrated effective density of the sliced parts (computed here);
            used for printed parts with no per-object slice and for ORIGINAL printed parts removed from the
            official lumped bodies (assumption: the official lumped inertia used the same print density).
  datasheet / sept_source : manufacturer or reseller mass with URL and verification date.
  assumption : engineering allowance, labelled.
The official NP-F970 battery mass is unknown (lumped); it is removed through the evaluator's existing
`remove_old_battery_kg` key and swept by the runner, not fixed here.
"""
from pathlib import Path
import json, math
import numpy as np, trimesh, mujoco

HERE = Path(__file__).resolve().parent
WHOLE = HERE.parents[1]
SIM = WHOLE.parents[1]
GUIDE = SIM / 'guide'
MODEL = SIM / 'microduck_rl/src/mjlab_microduck/robot/microduck/scene.xml'
IA_CACHE = Path('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/'
                'scratchpad/ia-cache')
V19 = json.loads((GUIDE / 'print/release-V1.9/manifest-V1.9.json').read_text())
SLICE = json.loads((HERE / 'slicer-part-masses.json').read_text())
GD = json.loads((GUIDE / 'data/guide-data.json').read_text())
STEEL = 7.85e-3  # g/mm3

# guide key -> official MJCF body (nr_lib.py BODY_OF; legs from pso_lib.py SIDE)
BODY_OF = {}
for b, ks in {
    'trunk_base': ['torso_base', 'shell_left', 'shell_right', 'ring10_torso', 'ring5_torso', 'imu_board',
                   'imu_sh4_receiving', 'openrb_board', 'rear_pack', 'rear_pack_cover', 'idler12', 'idler_cap12',
                   'motor10', 'motor5', 'clip_torso'],
    'neck': ['motor12', 'motor11', 'neck_link_a', 'neck_link_b'],
    'neck_pitch': ['neck_pitch', 'neck_pitch_ring', 'idler11', 'idler_cap11', 'clip_bracket'],
    'yaw_roll_motion': ['motor13', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b'],
    'jaw_soft': ['motor14', 'motor15', 'jaw_support', 'head_bottom', 'head_cap', 'face_panel', 'eye_trim',
                 'camera_board', 'mouth_sliding_ring', 'pi', 'jaw_frame', 'speaker', 'amplifier',
                 'speaker_retainer', 'clip_head', 'clip_cap'],
    'yaw2roll': ['yaw', 'motor9', 'ring9', 'passive', 'washer9'], 'hip_l': ['hip', 'ring8'],
    'upper_leg_left': ['thigh', 'plate', 'motor8', 'motor7', 'ring7'],
    'leg': ['lower', 'motor6', 'smallring', 'washer6'], 'ankle_left': ['ankle', 'foot'],
    'bearing_roll': ['right_yaw', 'motor4', 'ring4', 'right_passive', 'washer4'], 'hip_l_2': ['right_hip', 'ring3'],
    'upper_leg_right': ['right_thigh', 'right_plate', 'motor3', 'motor2', 'ring2'],
    'leg_2': ['right_lower', 'motor1', 'right_smallring', 'washer1'], 'ankle_right': ['right_ankle', 'right_foot'],
}.items():
    for k in ks:
        BODY_OF[k] = b


def body_of(key):
    return 'jaw_soft' if key.startswith('head_pi_') else BODY_OF[key]


m = mujoco.MjModel.from_xml_path(str(MODEL)); d = mujoco.MjData(m)
mujoco.mj_kinematics(m, d)
tb = m.body('trunk_base').id; R0 = d.xmat[tb].reshape(3, 3); p0 = d.xpos[tb]
POSE = {m.body(i).name: (R0.T @ d.xmat[i].reshape(3, 3), R0.T @ (d.xpos[i] - p0)) for i in range(m.nbody)}


def to_body(body, pts_mm):
    R, x = POSE[body]
    return (np.asarray(pts_mm) / 1000.0 - x) @ R  # rows: R^T (p - x)


# As-built correction (Shawn via coordinator, 2026-10-14): the robot carries the V1.8 printed parts; the orange V1.9
# plate (rear pack, head cap, speaker retainer, four clips) is NOT fitted, and no amplifier, speaker or microphone is
# installed (PROJECT-CONTEXT: "audio parts are not installed in the V1.8 build"; design_gate.physicalAcceptance
# v19_printed_and_fitted is still an open item). The audit-solid cache holds the V1.9 cap/pack, so those two keys use
# the V1.8 release files (sha256 equal to manifest-V1.8.json).
V18_MESH = {'head_cap': GUIDE / 'print/world/head_cap-v18.stl', 'rear_pack': GUIDE / 'print/world/rear_pack-v18.stl'}
NOT_FITTED = ['speaker_retainer', 'clip_torso', 'clip_bracket', 'clip_head', 'clip_cap', 'speaker', 'amplifier']
NOT_FITTED_CABLES = ['amp-lrc', 'amp-bclk', 'amp-din', 'amp-gnd', 'amp-vin', 'spk-plus', 'spk-minus']


def solid(key):
    if key in V18_MESH:
        return trimesh.load(V18_MESH[key], force='mesh')
    z = np.load(IA_CACHE / f'solid-{key}.npz')
    return trimesh.Trimesh(z['v'], z['f'], process=False)


def mesh_entry(ident, body, mesh_mm, mass_g, basis, source, **extra):
    """Uniform-density mesh mass in body coordinates (inertia about its own COM, rotated into body axes)."""
    R, x = POSE[body]
    vol = mesh_mm.volume
    assert vol > 0, ident
    com = to_body(body, mesh_mm.center_mass[None])[0]
    I_mm = mesh_mm.moment_inertia / vol * mass_g  # g mm2, guide axes, about COM
    I = R.T @ I_mm @ R * 1e-9  # kg m2
    return dict(id=ident, body=body, mass_kg=mass_g / 1000.0, position_m=com.tolist(),
                inertia_about_com_kg_m2=I.tolist(), basis=basis, source=source, **extra)


def point_entry(ident, body, p_mm, mass_g, basis, source, dims_mm=(10, 10, 10), **extra):
    return dict(id=ident, body=body, mass_kg=mass_g / 1000.0, position_m=to_body(body, [p_mm])[0].tolist(),
                dimensions_m=[v / 1000 for v in dims_mm], basis=basis, source=source, **extra)


# ---------- slicer-calibrated effective density ----------
SLICED = {  # guide key -> (plate, object prefix)
    'rear_pack': ('V1.8-Orange', 'rear_pack_1'), 'head_cap': ('V1.8-Orange', 'head_cap_1'), 'head_bottom': ('V1.8-Yellow', 'head_bottom_1'),
    'jaw_frame': ('V1.8-Yellow', 'jaw_frame_1'), 'face_panel': ('V1.8-White', 'face_panel_1'),
    'eye_trim': ('V1.8-Black', 'eye_trim_1'), 'rear_pack_cover': ('V1.8-Black', 'rear_pack_cover_1'),
}


def slicer_g(key):
    plate, prefix = SLICED[key]
    hits = [v for o, v in SLICE[plate]['objects'].items() if o.startswith(prefix + '_id')]
    assert len(hits) == 1, (key, hits)
    return hits[0]['model_g']


sliced_mass = {k: slicer_g(k) for k in SLICED}
sliced_vol = {k: solid(k).volume / 1000.0 for k in SLICED}  # cm3
RHO_EFF = sum(sliced_mass.values()) / sum(sliced_vol.values())  # g/cm3

parts = []
# ---------- additions: printed ----------
for k in SLICED:
    parts.append(mesh_entry(f'add-{k}', body_of(k), solid(k), sliced_mass[k], 'slicer',
                            f"{SLICE[SLICED[k][0]]['file']} object {SLICED[k][1]}",
                            solid_volume_cm3=round(sliced_vol[k], 3)))
for k in ['jaw_support', 'mouth_sliding_ring', 'neck_pitch']:
    s = solid(k)
    parts.append(mesh_entry(f'add-{k}', body_of(k), s, s.volume / 1000 * RHO_EFF, 'rho_eff',
                            'guide audit solid x slicer-calibrated effective density (no per-object slice on file)'))

# ---------- additions: electronics ----------
ELEC = [  # key, mass g, basis, source
    ('openrb_board', 13.0, 'sept_source', 'ROBOTIS OpenRB-150 https://en.robotis.com/shop_en/item.php?it_id=902-0183-000 '
     '(verified 2026-09-12, electrical/component-mass-envelope.json)'),
    ('imu_board', 2.5, 'sept_source', 'Adafruit BNO085 #4754 https://www.adafruit.com/product/4754 (verified 2026-09-12)'),
    ('camera_board', 4.0, 'sept_source', 'Raspberry Pi Camera Module 3 Wide, '
     'https://www.raspberrypi.com/documentation/accessories/camera.html (verified 2026-09-12)'),
    ('pi', 9.3, 'datasheet', 'Raspberry Pi Zero W 9.3 g, https://www.adafruit.com/product/3400 (read 2026-10-14)'),
    ('speaker_NOT_FITTED', 2.30, 'datasheet', 'Same Sky CMS-30204-18SP solder-pad model typ 2.30 g (2.07-2.53), '
     'https://www.sameskydevices.com/product/resource/cms-30204-18x.pdf (read 2026-10-14)'),
    ('amplifier', 1.2, 'sept_source', 'Adafruit MAX98357A #3006 1.2 g, https://www.adafruit.com/product/3006 '
     '(verified 2026-09-12); fitted without header'),
]
ELEC = [e for e in ELEC if e[0] not in NOT_FITTED and not e[0].endswith('_NOT_FITTED')]
for k, g, basis, src in ELEC:
    parts.append(mesh_entry(f'add-{k}', body_of(k), solid(k), g, basis, src))
parts.append(mesh_entry('add-pi-gpio-header', 'jaw_soft', solid('head_pi_zero_w_header_base'), 2.5, 'estimate',
                        'soldered 2x20 male header (plastic base + 40 pins), engineering estimate'))
if False:  # amplifier not fitted
  parts.append(point_entry('add-gain-resistor-and-solder', 'jaw_soft', solid('amplifier').center_mass, 0.3,
                         'estimate', '100 kOhm GAIN resistor and solder joints'))

# ---------- additions: cables (mass distributed along the drawn route, assigned by nearest part solid) ----------
from scipy.spatial import cKDTree
keys = [r['key'] for r in json.loads((GUIDE / 'content/interference-audit/solids-report.json').read_text())['records']]
pts, lab = [], []
for k in keys:
    try:
        b = body_of(k)
    except KeyError:
        continue
    v = solid(k).vertices
    sel = v[:: max(1, len(v) // 2000)]
    pts.append(sel); lab += [b] * len(sel)
TREE = cKDTree(np.vstack(pts)); LAB = np.array(lab)

# DXL: ROBOTIS lists the 10-pack of Robot Cable-X3P 180 mm at 0.1 lb (https://robotis.us/robot-cable-x3p-180mm-10pcs/,
# read 2026-10-14) -> 4.54 g per 180 mm cable incl. both housings = 0.0252 g/mm of kit length. The listing weight is
# rounded and may include the bag, so this is the high side; basis 'datasheet (reseller listing)'.
DXL_G_PER_MM = 45.36 / 10 / 180
CABLE = {  # kind -> (g per mm of cable, g per end, note, basis)
    'dxl': (DXL_G_PER_MM, 0.0, 'ROBOTIS X3P kit cable, whole kit length, housings included', 'datasheet'),
    'power-5v': (0.0039 * 2, 0.1, '22 AWG solid pair: Cu 0.326 mm2 x 8.96 g/cm3 = 2.92 g/m + PVC ~1.0 g/m per '
                 'conductor', 'estimate'),
    'i2c': (0.006, 0.3, 'STEMMA QT 4-wire 28 AWG (~1.5 g/m per conductor) with JST SH ends', 'estimate'),
    'uart': (0.0025 * 2, 0.15, 'two Dupont jumpers, 26-28 AWG ~2.5 g/m each, 0.1-0.15 g per housing', 'estimate'),
    'i2s': (0.0025, 0.1, 'one Dupont jumper soldered at the amp, one housing on the Pi pin', 'estimate'),
    'speaker': (0.002, 0.0, 'short soldered lead', 'estimate'),
    'csi': (0.006, 0.2, '200 mm 15-to-22 pin FFC', 'estimate'),
}
cable_rows = []
for c in GD['cables']:
    if c['id'] in NOT_FITTED_CABLES:
        continue
    per_mm, per_end, note, cbasis = CABLE[c['kind']]
    path = np.array(c['path'], float)
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    drawn = float(seg.sum())
    if c['id'] == 'supply':
        length = drawn  # only the on-robot part; the bench tether beyond the robot is not modelled
    elif c['id'] == 'csi':
        length = 200.0
    elif c['kind'] == 'dxl':
        import re
        length = float(re.search(r'(\d+) mm kit cable', c['label']).group(1))  # whole kit cable is on the robot
    else:
        length = max(float(c.get('lengthMM') or drawn), drawn)
    if c['id'] == 'pi-trunk':
        per_mm = 0.0025 * 2; per_end = 0.15 * 2  # two jumper chains, red + black, joined mid-way
    total = per_mm * length + 2 * per_end
    mids = (path[1:] + path[:-1]) / 2
    _, idx = TREE.query(mids)
    bodies = LAB[idx]
    for b in sorted(set(bodies)):
        w = seg[bodies == b].sum() / drawn
        if w <= 0:
            continue
        com = (mids[bodies == b] * seg[bodies == b, None]).sum(0) / seg[bodies == b].sum()
        parts.append(point_entry(f"add-cable-{c['id']}-{b}", b, com, total * w, cbasis,
                                 f"{c['label']}; {note}; {per_mm:.4f} g/mm x {length:.0f} mm + ends, share {w:.2f}",
                                 dims_mm=(20, 20, 20)))
    cable_rows.append(dict(id=c['id'], kind=c['kind'], length_mm=round(length), mass_g=round(total, 3), basis=cbasis,
                           bodies=sorted(set(bodies))))

# ---------- additions: fasteners through or into V1.x-changed parts ----------
CHANGED = {'rear_pack', 'rear_pack_cover', 'openrb_board', 'imu_board', 'jaw_support', 'head_bottom', 'head_cap',
           'pi', 'camera_board', 'eye_trim', 'speaker_retainer', 'amplifier', 'clip_torso', 'clip_bracket',
           'clip_head', 'clip_cap', 'jaw_frame'}
screw_g = {}
for s in GD['screws']:
    tp, ip = s.get('throughPart'), s.get('intoPart')
    if tp in NOT_FITTED or ip in NOT_FITTED or (tp == 'imu_board' and ip == 'rear_pack'):
        continue  # V1.8 pack holds the BNO085 on a zip-tie shelf; the 2 x M2 x 4 rib screws are V1.9
    dmm, L, D, h = s['diameterMm'], s['lengthMm'], s['headDiameterMm'], s['headHeightMm']
    g = STEEL * (math.pi / 4 * dmm ** 2 * L * 0.8 + math.pi / 4 * D ** 2 * h * 0.8)
    b = body_of(tp)  # the screw rides with the part it clamps (motor horns: the printed part)
    screw_g[b] = screw_g.get(b, 0) + g
    parts.append(point_entry(f"add-screw-{s['id']}", b, s['center'], g, 'estimate',
                             f"{s['spec']} steel, 0.8 fill of shank and head cylinders", dims_mm=(D, D, L)))

# ---------- removals: official parts V1.9 lacks ----------
def official_mesh(body, name):
    hits = []
    for g in range(m.ngeom):
        if m.geom_bodyid[g] != m.body(body).id or m.geom_type[g] != 7 or m.geom_contype[g] != 0:
            continue
        if mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_MESH, m.geom_dataid[g]) != name:
            continue
        mid = m.geom_dataid[g]; va, vn = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
        fa, fn = m.mesh_faceadr[mid], m.mesh_facenum[mid]
        R = np.zeros(9); mujoco.mju_quat2Mat(R, m.geom_quat[g]); R = R.reshape(3, 3)
        v = m.mesh_vert[va:va + vn] @ R.T + m.geom_pos[g]  # body frame, m
        hits.append(trimesh.Trimesh(v, m.mesh_face[fa:fa + fn], process=False))
    assert len(hits) == 1, (body, name, len(hits))
    return hits[0]


def removal(ident, body, name, mass_g, basis, source):
    t = official_mesh(body, name)
    com = t.center_mass; I = t.moment_inertia / t.volume * (mass_g / 1000.0)
    return dict(id=ident, body=body, mass_kg=-mass_g / 1000.0, position_m=com.tolist(),
                inertia_about_com_kg_m2=(-I).tolist(), basis=basis, source=source,
                official_mesh_volume_cm3=round(t.volume * 1e6, 3))


ORIGINAL_PRINTED = {'trunk_base': ['power_support', 'banana_pcb_locker'],
                    'jaw_soft': ['top_head_shell', 'bottom_head_shell', 'face_part', 'noenoeil', 'jaw', 'jaw_soft',
                                 'soft_mouth_top', 'motor_support'],
                    'neck_pitch': ['neck_pitch']}
for body, names in ORIGINAL_PRINTED.items():
    for n in names:
        t = official_mesh(body, n)
        parts.append(removal(f'remove-official-{n}', body, n, t.volume * 1e6 * RHO_EFF, 'rho_eff',
                             'official visual mesh volume x slicer-calibrated density; true lumped share unknown'))
parts.append(removal('remove-official-pi-zero-2w', 'jaw_soft', 'pcb__raspberry_pi_zero_2_w', 10.0, 'sept_source',
                     'Pi Zero 2 W 10 g (https://www.adafruit.com/product/5291, verified 2026-09-12); assumes the '
                     'official lumped head carried it at that mass'))
OLD_SHARES = {'lens': .25, 'elec_rpi_robot_hat_pcb': .45, 'm12_lens_holder': .15, 'speaker': .15}
OLD_HEAD_ELEC_G = 15.0
for n, sh in OLD_SHARES.items():
    parts.append(removal(f'remove-official-{n}', 'jaw_soft', n, OLD_HEAD_ELEC_G * sh, 'assumption',
                         'September head-electronics removal assumption (15 g total, shares as prepare_full_model.py)'))

# ---------- frame check: official XL330 meshes vs guide motors ----------
checks = []
for body, motor in [('jaw_soft', 'motor15'), ('jaw_soft', 'motor14'), ('trunk_base', 'motor10'),
                    ('yaw_roll_motion', 'motor13')]:
    gm = to_body(body, solid(motor).center_mass[None])[0]
    best = None
    for g in range(m.ngeom):
        if m.geom_bodyid[g] == m.body(body).id and m.geom_type[g] == 7 and m.geom_contype[g] == 0 and \
                mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_MESH, m.geom_dataid[g]) == 'xl330':
            dist = float(np.linalg.norm(m.geom_pos[g] - gm))
            best = dist if best is None else min(best, dist)
    checks.append(dict(body=body, guide_motor=motor, nearest_official_xl330_geom_origin_mm=round(best * 1000, 2)))

LABEL = {'slicer': 'slicer', 'rho_eff': 'CAD-volume', 'sept_source': 'datasheet', 'datasheet': 'datasheet',
         'estimate': 'estimate', 'assumption': 'estimate'}
for p in parts:
    p['label'] = LABEL[p['basis']]
items = {}
for p in parts:
    items.setdefault(p['body'], []).append(dict(id=p['id'], g=round(p['mass_kg'] * 1000, 3), label=p['label'],
                                                com_body_mm=[round(v * 1000, 1) for v in p['position_m']],
                                                source=p['source']))
(HERE / 'v19-mass-items.json').write_text(json.dumps(dict(
    note='Every signed mass line of v19-mass-manifest.json by MuJoCo body; label = datasheet / slicer / CAD-volume '
         '(solid volume x 1.24 g/cm3 PLA x the slicer fill fraction measured on this print profile) / estimate. '
         'The NP-F970 battery removal is applied by the runner (remove_old_battery_kg), not listed here.',
    rho_eff_g_cm3=round(RHO_EFF, 4), fill_fraction_vs_PLA_1p24=round(RHO_EFF / 1.24, 3), bodies=items,
    body_net_g={b: round(sum(i['g'] for i in v), 2) for b, v in items.items()},
    total_net_g=round(sum(p['mass_kg'] for p in parts) * 1000, 2)), indent=1) + '\n')
summary = dict(rho_eff_g_cm3=round(RHO_EFF, 4), sliced_mass_g=sliced_mass,
               sliced_solid_volume_cm3={k: round(v, 3) for k, v in sliced_vol.items()},
               body_delta_g={}, cables=cable_rows, screws_g={k: round(v, 2) for k, v in screw_g.items()},
               frame_check=checks)
for p in parts:
    summary['body_delta_g'][p['body']] = round(summary['body_delta_g'].get(p['body'], 0) + p['mass_kg'] * 1000, 2)
by_basis = {}
for p in parts:
    by_basis.setdefault(p['label'], [0, 0])
    by_basis[p['label']][0 if p['mass_kg'] > 0 else 1] += p['mass_kg'] * 1000
summary['by_basis_add_remove_g'] = {k: [round(a, 2), round(r, 2)] for k, (a, r) in by_basis.items()}
manifest = dict(
    schema='signed mass parts for add_signed_inertias (dynamics/evaluate.py)', build='as built 2026-10-14: V1.8 printed parts, no audio, USB-C 5 V tether',
    frame='official MJCF body frames, m; guide geometry mapped from trunk_base qpos0 frame',
    excluded=[f'Not fitted on the as-built robot: orange V1.9 parts (V1.9 rear pack and head cap replaced by the '
              f'printed V1.8 ones; speaker_retainer, clip_torso, clip_bracket, clip_head, clip_cap omitted), '
              f'MAX98357A amplifier, CMS-30204-18SP speaker, no microphone; cables {NOT_FITTED_CABLES} and their screws',
              'BNO085 zip ties on the V1.8 shelf (< 0.3 g)','NP-F970 battery: removed by the runner through remove_old_battery_kg (assumption sweep)',
              'Bench tether beyond the robot (USB-C cable, Adafruit 5991 on the bench): not modelled; only the 98 mm '
              'of 22 AWG pair drawn on the robot is included. Its drag/pull force is not simulated.',
              'Community printed rings vs official seeed bearings, neck_pitch_ring, neck shims: unchanged or < 1 g',
              'Threaded inserts: none in the guide screw list (all screws are self-tapping TAP)'],
    parts=parts, summary=summary)
(HERE / 'v19-mass-manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
print(json.dumps(summary, indent=1))

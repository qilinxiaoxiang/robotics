"""Candidate screw definitions for the V1.6 schedule (robot frame, mm; axis = insertion direction, unit vector).

Nominal centres come from (a) the verified V1.4 records in guide/data/sources/full-build-data-current.json (`screws`,
insertion = -world_axis), (b) earlier head records in build-pack-.../leg-guide-20261006/full-build-data.json for parts
whose holes did not move, or (c) the V1.6 part geometry (tray.py parameters, hole inventory). probe.py snaps each
centre to the measured head seat and measures the stack; nothing here is accepted without that measurement.
"""
from __future__ import annotations

import json
from pathlib import Path

G = Path(__file__).resolve().parents[2]
ROOT = G.parent
V14 = G / 'data/sources/full-build-data-current.json'
HIST = ROOT / 'build-pack-20260913/redesign-20260913/leg-guide-20261006/full-build-data.json'

# Head envelope assumptions (no purchased-screw drawing on file): M2/M2.5 pan or cross-recessed head 4.0 x 1.5 mm,
# matching the earlier procurement assumption "head<=4 diameter x1.5 high"; M2.6 4.5 x 1.8.
SPECS = {
    'M2': dict(d=2.0, headD=4.0, headH=1.5),
    'M2.5': dict(d=2.5, headD=4.0, headH=1.5),
    'M2.6': dict(d=2.6, headD=4.5, headH=1.8),
}


def rec(id, step, size, L, center, axis, through, into, *, kind='TAP', source='', note='', role='', expect=None):
    s = SPECS[size]
    return dict(id=id, step=step, size=size, spec=f'{size} x {L:g} {"TAP" if kind == "TAP" else "machine"}', kind=kind,
                diameterMm=s['d'], lengthMm=float(L), headDiameterMm=s['headD'], headHeightMm=s['headH'],
                center=[float(x) for x in center], axis=[float(x) for x in axis], throughPart=list(through), intoPart=into,
                source=source, note=note, role=role, expect=expect or {})


def _load(path):
    return {s['id']: s for s in json.loads(Path(path).read_text())['screws']}


def defs():
    v14 = _load(V14)
    hist = _load(HIST)
    out = []

    def from_v14(sid, step, through, into, role, size=None, L=None, **kw):
        s = v14[sid]
        sz, ln = s['spec'].split(' x ')[0], s['length_mm']
        ax = [-x for x in s['world_axis']]
        out.append(rec(sid, step, size or sz, L or ln, s['world_center_mm'], ax, through, into,
                       source='V1.4 verified record full-build-data-current.json#' + sid, role=role, **kw))

    # ---- chapter 4 torso: hip-yaw cases (V1.4 records; parts unchanged in V1.6)
    for sid, thr in (('S10-case-069', ['torso_base', 'power_support']), ('S10-case-070', ['torso_base']),
                     ('S05-case-073', ['torso_base']), ('S05-case-074', ['torso_base', 'power_support']),
                     ('S10-case-072', ['power_support']), ('S05-case-076', ['power_support'])):
        into = 'motor10' if sid.startswith('S10') else 'motor5'
        from_v14(sid, 'torso-fasten', thr, into, 'hip-yaw case to torso')

    # ---- OpenRB on tray (new): rear holes of the 61.5 x 20.5 pattern, PCB top z = -50.5 + 1.6
    for i, y in enumerate((10.25, -10.25), 1):
        out.append(rec(f'B-openrb-0{i}', 'board', 'M2', 6, [-76.7, y, -48.9], [0, 0, -1], ['openrb_board'], 'openrb_tray',
                       source='guide/print/tray/tray.py rear_holes; OpenRB-150 drawing (guide/data/sources/openrb-drawing.png)',
                       role='OpenRB-150 rear corner hole to tray pad'))

    # ---- IMU (changed clamp and cover)
    for sid in ('E-imu_clamp-01', 'E-imu_clamp-02'):
        from_v14(sid, 'imu-holder', [], 'imu_clamp', 'IMU holder pressure screw (tip bears on the fixed rail)',
                 size='M2', L=6, expect={'pressure': True, 'tipTarget': 'power_support'})
    for sid in ('E-imu_rear_cover-01', 'E-imu_rear_cover-02', 'E-imu_rear_cover-03', 'E-imu_rear_cover-04'):
        from_v14(sid, 'imu-cover', ['imu_cover'], 'imu_clamp', 'IMU rear cover to holder', size='M2', L=6)

    # ---- chapter 5 neck (V1.4 records)
    for sid in ('S12-case-087', 'S12-case-088', 'S12-case-089', 'S12-case-090'):
        s = v14[sid]; link = 'neck_link_b' if s['world_center_mm'][1] > 0 else 'neck_link_a'
        from_v14(sid, 'neck-lower-fasten', [link], 'motor12', 'neck link to ID12 case')
    for sid in ('S11-case-091', 'S11-case-092', 'S11-case-093', 'S11-case-094'):
        s = v14[sid]; link = 'neck_link_b' if s['world_center_mm'][1] > 0 else 'neck_link_a'
        from_v14(sid, 'neck-lower-fasten', [link], 'motor11', 'neck link to ID11 case')
    from_v14('S12-rear_center-117', 'neck-lower-fasten', ['idler_cap12', 'idler12'], 'motor12', 'ID12 rear idler centre')
    from_v14('S11-rear_center-118', 'neck-lower-fasten', ['idler_cap11', 'idler11'], 'motor11', 'ID11 rear idler centre')
    for sid in ('S13-horn-041', 'S13-horn-042', 'S13-horn-043', 'S13-horn-044'):
        from_v14(sid, 'neck-pitch', ['neck_pitch'], 'motor13', 'yaw output horn to pitch bracket (1 mm integral seats)')
    for sid in ('S14-horn-049', 'S14-horn-050', 'S14-horn-051', 'S14-horn-052'):
        from_v14(sid, 'neck-roll', ['head_yaw_link'], 'motor14', 'roll output horn to yaw fork')
    for sid in ('S13-case-095', 'S13-case-096', 'S13-case-097', 'S13-case-098'):
        from_v14(sid, 'neck-yaw-case', ['head_yaw_link'], 'motor13', 'yaw fork to ID13 case')
    for sid in ('S11-horn-033', 'S11-horn-034', 'S11-horn-035', 'S11-horn-036'):
        from_v14(sid, 'neck-upper-join', ['neck_pitch'], 'motor11', 'pitch bracket to ID11 output horn')
    for sid in ('S11-horn-037', 'S11-horn-038', 'S11-horn-039', 'S11-horn-040'):
        from_v14(sid, 'neck-upper-join', ['neck_pitch'], 'idler11', 'pitch bracket to ID11 printed rear idler')
    for sid in ('S12-horn-025', 'S12-horn-026', 'S12-horn-027', 'S12-horn-028'):
        from_v14(sid, 'shells', ['shell_right'], 'idler12', 'right shell to ID12 printed rear idler')
    for sid in ('S12-horn-029', 'S12-horn-030', 'S12-horn-031', 'S12-horn-032'):
        from_v14(sid, 'shells', ['shell_left'], 'motor12', 'left shell to ID12 output horn')
    from_v14('S10-case-071', 'shells', ['shell_left'], 'motor10', 'left shell to ID10 hip-yaw case')
    from_v14('S05-case-075', 'shells', ['shell_right'], 'motor5', 'right shell to ID5 hip-yaw case')

    # ---- chapter 6 head mechanics
    for sid in ('S15-horn-045', 'S15-horn-046', 'S15-horn-047', 'S15-horn-048'):
        s = hist[sid]
        out.append(rec(sid, 'jaw', 'M2', s['length_mm'], s['world_center_mm'], [-x for x in s['world_axis']], ['jaw_frame'], 'motor15',
                       source='earlier head record leg-guide-20261006/full-build-data.json#' + sid + ' (jaw_frame and ID15 unchanged)',
                       role='jaw frame to ID15 output horn'))
    for i, sid in enumerate(('E-motor_support_frame-01', 'E-motor_support_frame-02', 'E-motor_support_frame-03', 'E-motor_support_frame-04'), 1):
        s = hist[sid]
        out.append(rec(f'H-jaw_support-0{i}', 'head-bottom', 'M2.5', 6, s['world_center_mm'], [-x for x in s['world_axis']], ['jaw_support'], 'head_bottom',
                       source='hole positions from earlier record ' + sid + '; re-measured on V1.6 jaw_support_original and head_bottom',
                       role='jaw support base to lower head shell boss'))
    for i, (y, z) in enumerate(((-18.091378, 119.0), (-18.091378, 147.2), (17.908622, 147.2)), 1):
        out.append(rec(f'C-camera_clamp-0{i}', 'camera', 'M2', 4, [76.38, y, z], [1, 0, 0], ['camera_retainer'], 'face_panel',
                       source='camera-ribbon-repair/positive-x225/camera-three-screw-clamp-report.json', role='camera retainer to face anchor'))

    # ---- chapter 7 head electronics (cap on the bench, upside down)
    for i, x in enumerate((5.0, 45.0), 1):
        out.append(rec(f'E-speaker-0{i}', 'speaker', 'M2.5', 8, [x, -21.5, 131.44], [0, 0, 1], ['speaker_cradle', 'speaker_keeper'], 'head_cap',
                       source='V1.6 speaker_cradle/keeper holes and cap posts (hole inventory); speaker_mount_screw_N display models',
                       role='speaker cage to cap post'))
    for i, x in enumerate((19.65, 32.35), 1):
        out.append(rec(f'E-amp-0{i}', 'amp', 'M2.5', 8, [x, 17.287, 132.515], [0, 0, 1], ['amplifier'], 'head_cap',
                       source='head-flexible-harness/amp-mounts/amp-mount-fragment.json; V1.6 cap posts', role='amplifier PCB to cap post'))
    n = [0.98480775, 0.0, -0.17364818]   # Pi PCB normal (header side, towards the face)
    # V1.7 cap: the Pi seat is 4.6 mm further back; the +y lower seat (E-pi-02) sits in the trimmed rail and takes M2 x 4.
    for i, (y, base) in enumerate(((-29.0, (55.815, 117.514)), (29.0, (55.815, 117.514)), (-29.0, (59.809, 140.164)), (29.0, (59.809, 140.164))), 1):
        c = [base[0] + 1.6 * n[0], y, base[1] + 1.6 * n[2]]
        out.append(rec(f'E-pi-0{i}', 'pi', 'M2', 4 if i == 2 else 6, c, [-n[0], 0, -n[2]], ['pi'], 'head_cap',
                       source='final-integration-20261009/mount-design.json pi-roof-side-rail seats; V1.6 cap rail pilots',
                       role='Pi Zero W corner hole to cap rail'))

    # ---- chapter 9 head closure: lower shell tabs into cap bosses (from below)
    for i, sid in enumerate(('E-head_cap_closure-01', 'E-head_cap_closure-02', 'E-head_cap_closure-03'), 1):
        s = hist[sid]
        out.append(rec(f'K-head_close-0{i}', 'close', 'M2.5', 8, s['world_center_mm'], [-x for x in s['world_axis']], ['head_bottom'], 'head_cap',
                       source='hole positions from earlier record ' + sid + '; re-measured on V1.6 head_bottom and head_cap',
                       role='lower head shell tab to cap boss'))
    return out


if __name__ == '__main__':
    d = defs()
    print(len(d))
    from collections import Counter
    print(Counter(x['step'] for x in d))

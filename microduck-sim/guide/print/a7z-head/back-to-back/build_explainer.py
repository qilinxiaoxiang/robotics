"""Builds ducts-explainer.html: cuts the real head meshes (this folder's cap, insert, duct walls and board unit, the
guide's fixed parts) at the planes the explainer draws, and writes the outlines into explainer_template.html as SVG
path data in mm. Run with the CAD venv after build_b2b.py."""
import json
import sys

import numpy as np
import trimesh

import build_b2b as B

PARTS = B.HERE / 'parts'
# plane name -> (axis normal index, offset, the two drawn axes, part keys); the top cut runs through the fin at d 22
PLANES = {
    'top122': (2, 121.1, (0, 1), ['jaw_frame', 'jaw_support', 'motor15', 'camera_board', 'face_panel', 'cap',
                                  'walls', 'insert', 'fan_inlet_zone', 'heatsink_6530b', 'a7z_pcb', 'fan_lead_loop']),
    'side15': (1, 15.0, (0, 2), ['head_bottom', 'jaw_frame', 'jaw_support', 'motor15', 'camera_board', 'face_panel', 'cap',
                                 'walls', 'fan_inlet_zone', 'heatsink_6530b', 'a7z_pcb', 'a7z_header', 'dupont_plugs']),
    'sideM10': (1, -10.0, (0, 2), ['head_bottom', 'jaw_frame', 'jaw_support', 'camera_board', 'face_panel', 'cap', 'walls',
                                   'insert', 'heatsink_6530b', 'a7z_pcb', 'a7z_header', 'dupont_plugs']),
    'rail137': (2, 137.0, (0, 1), ['cap', 'walls', 'insert', 'heatsink_6530b', 'a7z_pcb', 'dupont_plugs']),
}


def load_all():
    m = {'cap': trimesh.load(B.HERE / 'head_cap_b2b-world.stl'), 'insert': trimesh.load(B.HERE / 'shroud_insert-world.stl'),
         'walls': trimesh.load(B.HERE / 'duct_walls_only.stl')}
    for f in PARTS.glob('*.stl'):
        m[f.stem] = trimesh.load(f)
    gp = B.guide_parts()
    for k in ('head_bottom', 'jaw_frame', 'jaw_support', 'motor15', 'face_panel', 'camera_board'):
        m[k] = gp[k]
    m['heatsink_6530b'] = m['heatsink_6530b_detail']            # fins, grooves and the blower pocket, not the envelope
    return m


def outline(mesh, axis, off, uv):
    n = np.zeros(3); n[axis] = 1.0
    o = np.zeros(3); o[axis] = off
    s = mesh.section(plane_origin=o, plane_normal=n)
    if s is None:
        return ''
    d = []
    for line in s.discrete:
        p = np.round(line[:, list(uv)], 2)
        if len(p) < 3:
            continue
        d.append('M' + 'L'.join(f'{a:g},{b:g}' for a, b in p) + 'Z')
    return ''.join(d)


def main():
    m = load_all()
    data = {}
    for name, (axis, off, uv, keys) in PLANES.items():
        data[name] = {k: outline(m[k], axis, off, uv) for k in keys}
        data[name] = {k: v for k, v in data[name].items() if v}
    chk = json.loads((B.HERE / 'checks.json').read_text())['ducts']
    data['checks'] = {k: chk[k] for k in ('insertPairs', 'wallPairs', 'slotOpen_mm2', 'plugInsertMinGap_mm',
                                          'headCloseMinGapToInsert_mm', 'jawSweepInsertWalls')}
    data['checks']['insertPath'] = chk['insertPath']['minGapCap_mm'], chk['insertPath']['minGapUnit_mm']
    data['slots'] = [dict(kind=s['kind'], side=s['side'], x=s['x'], z=s['z']) for s in chk['slots']]
    html = (B.HERE / 'explainer_template.html').read_text().replace('/*DATA*/null', json.dumps(data, separators=(',', ':')))
    out = B.HERE / 'ducts-explainer.html'
    out.write_text(html)
    print(out, {k: list(v) for k, v in data.items() if k in PLANES}, len(html))


if __name__ == '__main__':
    main()

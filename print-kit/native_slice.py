"""Native slicing from slicer system presets, shared by every robotics project.

A caller names a printer by its system presets (machine, process, filament) and gives meshes that are already in print
pose. This module flattens the presets from the installed slicer's profile folders, applies the caller's process
overrides, packs the parts onto as few plates as fit the machine's printable area, writes one editable 3MF project per
plate (per-object settings and modifier parts in Metadata/model_settings.config), slices it with the slicer CLI and
reads the result back from the G-code itself.

Generalised from the MicroDuck pipeline (microduck-sim/build-pack-20260913/redesign-20260913/printing/
13-RELEASE-PIPELINE-20261009/release_pipeline_v2.py and microduck-sim/guide/print/make_h2s.py). Those stay frozen
because MicroDuck release receipts bind their bytes; they keep their donor-project route. This module carries over:
exact-vertex mesh loading, the 3MF project layout, the Bambu filament_self_index fix and --min-save archive rule
(the GUI opens the sliced file on Preview), system-preset flattening, ETA parsing, and the G-code preview block layout.

Dependencies: numpy and trimesh. The preview renderer writes PNG with zlib, so no imaging library is needed.

Typical use (see scout-mini-design-review/scripts/slice_prints.py):

    import native_slice as ns
    printer = ns.Printer(key='A1', slicer='bambu', vendor='BBL', machine='Bambu Lab A1 0.4 nozzle',
                         process='0.20mm Standard @BBL A1', filament='Generic PETG @BBL A1', bed_type='Textured PEI Plate')
    cfg = ns.project_config(printer, {'wall_loops': '4'})
    plates = ns.pack(parts, ns.bed_size(cfg), margin=15, gap=10)
    for plate in plates: ns.write_project(path, cfg, plate, printer); ns.slice_project(path, printer, outdir)
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import plistlib
import re
import subprocess
import zipfile
import zlib
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import trimesh

SLICERS = {
    'bambu': dict(app=Path('/Applications/BambuStudio.app'), name='BambuStudio'),
    'orca': dict(app=Path('/Applications/OrcaSlicer.app'), name='OrcaSlicer'),
}
NS = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
Q = '{' + NS + '}'
ET.register_namespace('', NS)
META = {'name', 'type', 'from', 'inherits', 'include', 'instantiation', 'version', 'setting_id', 'description',
        'renamed_from', 'filament_id', 'compatible_printers', 'compatible_printers_condition', 'compatible_prints',
        'compatible_prints_condition'}
CONTENT_TYPES = (b'<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
                 b'content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
                 b'relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing'
                 b'-3dmodel+xml"/><Default Extension="png" ContentType="image/png"/></Types>')
RELS = (b'<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
        b'relationships"><Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufa'
        b'cturing/2013/01/3dmodel"/></Relationships>')


@dataclass
class Printer:
    key: str                  # short name used in file names, e.g. A1
    slicer: str               # 'bambu' or 'orca'
    vendor: str               # profile folder, e.g. BBL or Anycubic
    machine: str
    process: str
    filament: str
    bed_type: str | None = None   # None keeps the slicer's default for the machine
    label: str = ''
    # Set only when the slicer ships no filament preset for this machine and a vendor preset written for its sibling
    # machines is used instead: the reason is recorded and the compatible_printers check is skipped for the filament.
    filament_not_listed_reason: str = ''


# ---------------------------------------------------------------- files and hashes
def sha(path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def exe(slicer: str) -> Path:
    s = SLICERS[slicer]
    p = s['app'] / 'Contents/MacOS' / s['name']
    assert p.is_file(), f'{s["name"]} is not installed at {s["app"]}'
    return p


def version(slicer: str) -> str:
    info = plistlib.loads((SLICERS[slicer]['app'] / 'Contents/Info.plist').read_bytes())
    return info['CFBundleShortVersionString']


def profile_root(slicer: str) -> Path:
    return SLICERS[slicer]['app'] / 'Contents/Resources/profiles'


# ---------------------------------------------------------------- system presets
def _find(slicer: str, vendor: str, domain: str, name: str) -> Path:
    root = profile_root(slicer)
    for folder in (root / vendor / domain, root / 'OrcaFilamentLibrary' / domain):
        hits = sorted(folder.rglob(f'{name}.json')) if folder.is_dir() else []
        if hits:
            return hits[0]
    raise FileNotFoundError(f'{slicer}: no {domain} preset named "{name}" under {root / vendor}')


def resolve(slicer: str, vendor: str, domain: str, name: str) -> dict:
    """Flatten one system preset through its inherits/include chain."""
    x = json.loads(_find(slicer, vendor, domain, name).read_text())
    out = {}
    if x.get('inherits'):
        out.update(resolve(slicer, vendor, domain, x['inherits']))
    for n in x.get('include', []):
        out.update(resolve(slicer, vendor, domain, n))
    out.update(x)
    return out


def presets(p: Printer) -> tuple[dict, dict, dict]:
    m = resolve(p.slicer, p.vendor, 'machine', p.machine)
    pr = resolve(p.slicer, p.vendor, 'process', p.process)
    f = resolve(p.slicer, p.vendor, 'filament', p.filament)
    for d, kind in ((pr, 'process'), (f, 'filament')):
        if kind == 'filament' and p.filament_not_listed_reason:
            continue
        comp = d.get('compatible_printers') or []
        assert not comp or p.machine in comp, f'{kind} preset "{d["name"]}" does not list {p.machine}: {comp}'
    return m, pr, f


def project_config(p: Printer, overrides: dict) -> dict:
    """Machine + process + filament system presets, then the caller's process overrides (recorded as user changes)."""
    m, pr, f = presets(p)
    cfg = {}
    for d in (m, pr, f):
        cfg.update({k: v for k, v in d.items() if k not in META})
    for k, v in overrides.items():
        assert k in cfg or k in ('brim_type', 'brim_width', 'brim_object_gap'), f'unknown setting {k}'
        cfg[k] = v
    cfg.update(printer_settings_id=p.machine, print_settings_id=p.process, filament_settings_id=[p.filament],
               inherits_group=[p.process, p.filament, p.machine], filament_ids=[f.get('filament_id', '')],
               print_compatible_printers=pr.get('compatible_printers', [p.machine]),
               different_settings_to_system=[';'.join(sorted(overrides)), '', ''],
               filament_colour=cfg.get('filament_colour') or ['#F2F2F2'])
    if p.bed_type:
        cfg['curr_bed_type'] = p.bed_type
    if p.slicer == 'bambu':
        cfg['filament_self_index'] = ['1'] * len(cfg.get('filament_extruder_variant', [''])) or ['1']
    return cfg


def bed_size(cfg: dict) -> tuple[float, float]:
    pts = np.array([[float(a) for a in s.split('x')] for s in cfg['printable_area']])
    assert np.allclose(pts.min(0), 0), 'non-zero bed origin is not handled'
    return tuple(pts.max(0))


# ---------------------------------------------------------------- meshes and plates
def load_mesh(path) -> trimesh.Trimesh:
    """Exact vertex deduplication (per-triangle STL vertices once gave a false, almost empty first layer), dropped to z 0."""
    m = trimesh.load(path, force='mesh', process=False)
    v, inv = np.unique(m.vertices, axis=0, return_inverse=True)
    m = trimesh.Trimesh(v, inv.reshape(-1)[m.faces], process=False)
    assert m.is_watertight and m.is_winding_consistent, f'not a closed mesh: {path}'
    m.apply_translation([-m.bounds[0, 0], -m.bounds[0, 1], -m.bounds[0, 2]])
    return m


def bed_contact_mm2(mesh) -> float:
    tri = mesh.triangles
    return float(mesh.area_faces[np.max(np.abs(tri[:, :, 2]), axis=1) <= 0.01].sum())


@dataclass
class Part:
    key: str
    mesh: trimesh.Trimesh
    quantity: int
    settings: dict = field(default_factory=dict)          # per-object slicer settings
    modifiers: list = field(default_factory=list)         # [(trimesh in the part frame, {setting: value}, name)]
    clearance: float = 0.0                                # extra keep-out around the footprint (brim width)


def pack(parts: list[Part], bed_xy, margin=15.0, gap=10.0) -> list[list[dict]]:
    """Bottom-left packing, largest footprint first, onto as few plates as fit; each plate's footprint is centred.

    Rectangles are footprints grown by each part's clearance; neighbours keep `gap` between grown rectangles and the bed
    edge keeps `margin`."""
    W, H = bed_xy
    items = [(p, i + 1) for p in sorted(parts, key=lambda p: -p.mesh.extents[0] * p.mesh.extents[1])
             for i in range(p.quantity)]
    plates = []
    for p, copy in items:
        w, h = p.mesh.extents[:2] + 2 * p.clearance
        assert w <= W - 2 * margin and h <= H - 2 * margin, f'{p.key} does not fit the {W:g} x {H:g} bed'
        for plate in plates + [[]]:
            rects = [r['rect'] for r in plate]
            cands = [(margin, margin)] + [(c[2] + gap, c[1]) for c in rects] + [(c[0], c[3] + gap) for c in rects]
            ok = [(y, x) for x, y in cands if x + w <= W - margin + 1e-9 and y + h <= H - margin + 1e-9 and
                  all(x + w + gap <= c[0] + 1e-9 or c[2] + gap <= x + 1e-9 or y + h + gap <= c[1] + 1e-9 or
                      c[3] + gap <= y + 1e-9 for c in rects)]
            if ok:
                y, x = min(ok)
                if not plate:
                    plates.append(plate)
                plate.append(dict(part=p, copy=copy, rect=(x, y, x + w, y + h),
                                  xy=np.array([x + p.clearance, y + p.clearance])))
                break
    for plate in plates:
        lo = np.min([r['rect'][:2] for r in plate], axis=0)
        hi = np.max([r['rect'][2:] for r in plate], axis=0)
        shift = (np.array([W, H]) - (lo + hi)) / 2
        for r in plate:
            r['xy'] = r['xy'] + shift
    return plates


def line_spacing(segments, min_len=0.3):
    """Median spacing of the dominant direction among parallel extrusion lines [(x0, y0, x1, y1)] of one layer."""
    s = np.asarray(segments, float)
    d = s[:, 2:] - s[:, :2]
    L = np.hypot(d[:, 0], d[:, 1])
    s, d, L = s[L >= min_len], d[L >= min_len], L[L >= min_len]
    if len(s) < 3:
        return None
    ang = np.round(np.degrees(np.arctan2(d[:, 1], d[:, 0])) % 180 / 5) * 5 % 180
    best = max(set(ang), key=lambda a: L[ang == a].sum())
    k = ang == best
    t = np.radians(best)
    n = np.array([-math.sin(t), math.cos(t)])
    off = np.sort(np.unique(np.round(((s[k, :2] + s[k, 2:]) / 2) @ n, 2)))
    gaps = np.diff(off)
    gaps = gaps[gaps > 0.05]
    return float(np.median(gaps)) if len(gaps) else None


def _mesh_object(resources, oid, name, mesh):
    obj = ET.SubElement(resources, Q + 'object', {'id': str(oid), 'type': 'model', 'name': name})
    el = ET.SubElement(obj, Q + 'mesh')
    ve, fa = ET.SubElement(el, Q + 'vertices'), ET.SubElement(el, Q + 'triangles')
    for v in mesh.vertices:
        ET.SubElement(ve, Q + 'vertex', {k: format(float(c), '.9g') for k, c in zip('xyz', v)})
    for f in mesh.faces:
        ET.SubElement(fa, Q + 'triangle', {k: str(int(c)) for k, c in zip(('v1', 'v2', 'v3'), f)})


def write_project(path, cfg: dict, plate: list[dict], printer: Printer, plate_name='Plate 1') -> dict:
    """One editable 3MF project for one plate. Returns the placement record (object name -> footprint)."""
    model = ET.Element(Q + 'model', {'unit': 'millimeter', '{http://www.w3.org/XML/1998/namespace}lang': 'en-US'})
    ET.SubElement(model, Q + 'metadata', {'name': 'Application'}).text = f'{SLICERS[printer.slicer]["name"]}-{version(printer.slicer)}'
    resources, build = ET.SubElement(model, Q + 'resources'), ET.SubElement(model, Q + 'build')
    settings = ET.Element('config')
    pl = ET.SubElement(settings, 'plate')
    for k, v in (('plater_id', '1'), ('plater_name', plate_name), ('locked', 'false')) + \
            ((('bed_type', cfg['curr_bed_type']),) if 'curr_bed_type' in cfg else ()):
        ET.SubElement(pl, 'metadata', {'key': k, 'value': v})
    oid, record = 1, {}
    for r in plate:
        p = r['part']
        name = f'{p.key}_{r["copy"]}'
        parent, oid = oid, oid + 1
        po = ET.SubElement(resources, Q + 'object', {'id': str(parent), 'type': 'model', 'name': name})
        comps = ET.SubElement(po, Q + 'components')
        st = ET.SubElement(settings, 'object', {'id': str(parent)})
        for k, v in [('name', name), ('extruder', '1')] + sorted(p.settings.items()):
            ET.SubElement(st, 'metadata', {'key': k, 'value': str(v)})
        for mesh, sub, extra, pname in [(p.mesh, 'normal_part', {}, name)] + \
                [(mm, 'modifier_part', s, f'{name}_{n}') for mm, s, n in p.modifiers]:
            mid, oid = oid, oid + 1
            _mesh_object(resources, mid, pname, mesh)
            ET.SubElement(comps, Q + 'component', {'objectid': str(mid)})
            part = ET.SubElement(st, 'part', {'id': str(mid), 'subtype': sub})
            for k, v in [('name', pname)] + sorted(extra.items()):
                ET.SubElement(part, 'metadata', {'key': k, 'value': str(v)})
        t = f'1 0 0 0 1 0 0 0 1 {r["xy"][0]:.6f} {r["xy"][1]:.6f} 0'
        ET.SubElement(build, Q + 'item', {'objectid': str(parent), 'transform': t, 'printable': '1'})
        ins = ET.SubElement(pl, 'model_instance')
        for k, v in (('object_id', str(parent)), ('instance_id', '0'), ('identify_id', str(1000 + parent))):
            ET.SubElement(ins, 'metadata', {'key': k, 'value': v})
        lo = r['xy']
        record[name] = dict(key=p.key, copy=r['copy'], identify_id=1000 + parent,
                            footprint=[float(lo[0]), float(lo[1]), float(lo[0] + p.mesh.extents[0]), float(lo[1] + p.mesh.extents[1])],
                            height=float(p.mesh.extents[2]))
    W, H = bed_size(cfg)
    boxes = [v['footprint'] for v in record.values()]
    assert min(b[0] for b in boxes) >= 0 and min(b[1] for b in boxes) >= 0 and max(b[2] for b in boxes) <= W and \
        max(b[3] for b in boxes) <= H, 'plate placement leaves the bed'
    assert max(v['height'] for v in record.values()) <= float(cfg['printable_height']), 'part taller than the machine'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', CONTENT_TYPES)
        z.writestr('_rels/.rels', RELS)
        z.writestr('3D/3dmodel.model', ET.tostring(model, encoding='utf-8', xml_declaration=True))
        z.writestr('Metadata/model_settings.config', ET.tostring(settings, encoding='utf-8', xml_declaration=True))
        z.writestr('Metadata/project_settings.config', json.dumps(cfg, indent=2))
    return record


def axis_in_pose(axis, poses) -> np.ndarray:
    """A fit axis (design frame) carried through the part's print-pose rotations [[axis, degrees], ...]."""
    a = np.array(axis, float)
    for ax, deg in poses or []:
        a = trimesh.transformations.rotation_matrix(math.radians(deg), ax)[:3, :3] @ a
    return a / np.linalg.norm(a)


def _loops(segments, ndigits=5):
    """Chain plane-section segments (n, 2, 2) into closed loops; open chains are dropped."""
    key = lambda p: (round(float(p[0]), ndigits), round(float(p[1]), ndigits))
    adj = {}
    for i, (p, q) in enumerate(segments):
        adj.setdefault(key(p), []).append((i, key(q)))
        adj.setdefault(key(q), []).append((i, key(p)))
    used, loops = set(), []
    for i, (p, q) in enumerate(segments):
        if i in used:
            continue
        used.add(i)
        start, cur, pts = key(p), key(q), [key(p)]
        while cur != start:
            pts.append(cur)
            nxt = next(((j, o) for j, o in adj.get(cur, []) if j not in used), None)
            if nxt is None:
                pts = None
                break
            used.add(nxt[0])
            cur = nxt[1]
        if pts and len(pts) >= 3:
            loops.append(np.array(pts))
    return loops


def find_holes(mesh, d, axis, step=0.5, tol=0.12):
    """Round (or teardrop) holes of nominal diameter d along a given axis, from planar sections of the mesh.

    Returns [(start, end)] points on each hole axis in the mesh frame. A loop counts when it is an inner loop (inside an
    odd number of other loops), its area-equivalent diameter lies within d .. d*(1+tol) (a teardrop adds about 8 %)
    and it is compact."""
    from shapely.geometry import Point, Polygon
    a = np.array(axis, float) / np.linalg.norm(axis)
    u = np.cross(a, [0, 0, 1] if abs(a[2]) < 0.9 else [1, 0, 0])
    u /= np.linalg.norm(u)
    v = np.cross(a, u)
    proj = mesh.vertices @ a
    hits = []
    for s in np.arange(proj.min() + step / 2, proj.max(), step):
        seg = trimesh.intersections.mesh_plane(mesh, plane_normal=a, plane_origin=a * s)
        if len(seg) == 0:
            continue
        seg2 = np.stack([seg @ u, seg @ v], axis=-1)
        polys = [Polygon(l) for l in _loops(seg2)]
        polys = [q for q in polys if q.is_valid and q.area > 0]
        for q in polys:
            deq = 2 * math.sqrt(q.area / math.pi)
            if not (d * 0.98 <= deq <= d * (1 + tol) and 4 * math.pi * q.area / q.length ** 2 > 0.75):
                continue
            c = q.centroid
            depth = sum(1 for o in polys if o is not q and o.area > q.area and o.contains(Point(c.x, c.y)))
            if depth % 2 == 1:
                hits.append((s, np.array([c.x, c.y])))
    holes = []
    for s, c in hits:
        for h in holes:
            if np.linalg.norm(h['c'] - c) < 1.0 and s - h['s'][1] <= 2 * step:
                h['s'] = (h['s'][0], s)
                break
        else:
            holes.append(dict(c=c, s=(s, s)))
    return [(a * (h['s'][0] - step / 2) + u * h['c'][0] + v * h['c'][1],
             a * (h['s'][1] + step / 2) + u * h['c'][0] + v * h['c'][1]) for h in holes]


def ring_modifier(p0, p1, radius, extend=1.0) -> trimesh.Trimesh:
    a = (p1 - p0) / np.linalg.norm(p1 - p0)
    return trimesh.creation.cylinder(radius=radius, segment=[p0 - a * extend, p1 + a * extend], sections=32)


# ---------------------------------------------------------------- slicing
def slice_project(project, printer: Printer, outdir, timeout=600) -> Path:
    """Slice with the native CLI and export a sliced 3MF (Bambu: --min-save, so the GUI opens it on Preview)."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [str(exe(printer.slicer)), '--allow-newer-file', '--arrange', '0', '--orient', '0', '--slice', '0']
    if printer.slicer == 'bambu':
        cmd.append('--min-save')
    cmd += ['--export-3mf', 'sliced.3mf', '--outputdir', str(outdir), str(project)]
    with (outdir / 'cli.log').open('w') as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
    (outdir / 'command.json').write_text(json.dumps(dict(argv=cmd, returncode=r.returncode), indent=1) + '\n')
    assert r.returncode == 0, f'{printer.key}: slicer exit {r.returncode}, see {outdir / "cli.log"}'
    arc = outdir / 'sliced.3mf'
    assert arc.is_file(), f'no sliced archive in {outdir}'
    return arc


def archive_payload(path) -> tuple[bytes, dict, dict]:
    with zipfile.ZipFile(path) as z:
        g = [n for n in z.namelist() if n.endswith('.gcode')]
        assert len(g) == 1, f'{path}: expected one G-code member, got {g}'
        return z.read(g[0]), json.loads(z.read('Metadata/project_settings.config')), \
            {n: z.read(n) for n in z.namelist() if n.endswith('.png')}


def check_bambu_archive(path):
    """The GUI opens a sliced .gcode.3mf on Preview only with a consistent filament_self_index and no model objects."""
    with zipfile.ZipFile(path) as z:
        cfg = json.loads(z.read('Metadata/project_settings.config'))
        names = z.namelist()
        mdl = z.read('3D/3dmodel.model').decode(errors='replace')
    assert len(cfg.get('filament_self_index', [])) == len(cfg.get('filament_extruder_variant', [])), \
        f'{path}: filament_self_index does not match filament_extruder_variant'
    assert '<object' not in mdl and not any(n.startswith('3D/Objects/') for n in names), f'{path}: model objects in archive'
    assert any(re.fullmatch(r'Metadata/plate_\d+\.gcode', n) for n in names), f'{path}: no stored G-code'


# ---------------------------------------------------------------- G-code readback
def gcode_config(g: bytes) -> dict:
    """The '; key = value' settings block both slicers append (CONFIG_BLOCK_START ... CONFIG_BLOCK_END)."""
    s = g.decode(errors='replace')
    a, b = s.rfind('; CONFIG_BLOCK_START'), s.rfind('; CONFIG_BLOCK_END')
    assert 0 <= a < b, 'no config block in the G-code'
    out = {}
    for line in s[a:b].splitlines()[1:]:
        if line.startswith('; ') and ' = ' in line:
            k, v = line[2:].split(' = ', 1)
            out[k.strip()] = v
    return out


def eta_seconds(g: bytes) -> int:
    s = g[:200000].decode(errors='replace')
    m = re.search(r'total estimated time:\s*([^;\r\n]+)', s) or \
        re.search(r'estimated printing time \(normal mode\)\s*=\s*([^\r\n]+)', g.decode(errors='replace'))
    assert m, 'no slicer ETA in the G-code'
    sec = sum(int(n) * {'d': 86400, 'h': 3600, 'm': 60, 's': 1}[u] for n, u in re.findall(r'(\d+)\s*([dhms])', m.group(1)))
    assert sec > 0
    return sec


def filament_grams(g: bytes) -> float:
    s = g.decode(errors='replace')
    m = re.search(r'total filament weight \[g\]\s*:\s*([\d.]+)', s) or \
        re.search(r'total filament used \[g\]\s*=\s*([\d.]+)', s) or re.search(r'filament used \[g\]\s*=\s*([\d.,]+)', s)
    assert m, 'no filament weight in the G-code'
    return round(sum(float(x) for x in m.group(1).split(',') if x), 2)


def eta_label(sec: int) -> str:
    return f'{sec // 3600}h{sec % 3600 // 60:02d}m'


FEATURE = re.compile(r'^(?:; FEATURE: |;TYPE:)(.+)$')


def extrusions(g: bytes):
    """Yield (feature, z, x0, y0, x1, y1) for every extruding G1/G2/G3 move after the start G-code (arcs as chords)."""
    s = g.decode(errors='replace')
    start = max(s.find('; MACHINE_START_GCODE_END'), s.find(';TYPE:'), 0)
    end = s.find('; MACHINE_END_GCODE_START')
    body = s[start:end if end > 0 else len(s)]
    x = y = z = 0.0
    feat, relative, e = 'Custom', True, 0.0
    for line in body.splitlines():
        if line.startswith(';'):
            m = FEATURE.match(line)
            if m:
                feat = m.group(1).strip()
            continue
        c = line.split(';', 1)[0]
        if c.startswith('M82'):
            relative = False
        elif c.startswith('M83'):
            relative = True
        elif c.startswith('G92'):
            m = re.search(r'E([-+\d.]+)', c)
            if m:
                e = float(m.group(1))
        if not re.match(r'G[0123] ', c):
            continue
        v = {k: float(t) for k, t in re.findall(r'([XYZE])([-+]?\d*\.?\d+)', c)}
        nx, ny, nz = v.get('X', x), v.get('Y', y), v.get('Z', z)
        de = v.get('E', 0.0) if relative else v.get('E', e) - e
        if 'E' in v and not relative:
            e = v['E']
        if de > 0 and (nx, ny) != (x, y):
            yield feat, nz, x, y, nx, ny
        x, y, z = nx, ny, nz


def has_thumbnail(g: bytes) -> bool:
    return b'; thumbnail begin ' in g[:2_000_000]


# ---------------------------------------------------------------- plate preview (for slicers whose CLI writes none)
def _png(rgb: np.ndarray) -> bytes:
    h, w, _ = rgb.shape
    raw = b''.join(b'\x00' + rgb[i].astype(np.uint8).tobytes() for i in range(h))

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + \
        chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')


def render_plate(meshes_xy: list[tuple[trimesh.Trimesh, np.ndarray]], size=(230, 110), colour=(90, 150, 120)) -> bytes:
    """A shaded oblique view of the plate's parts (z-buffer rasteriser), framed on the parts, light background."""
    W, H = size
    el, az = math.radians(55), math.radians(-30)
    Rz = np.array([[math.cos(az), -math.sin(az), 0], [math.sin(az), math.cos(az), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, math.cos(el), -math.sin(el)], [0, math.sin(el), math.cos(el)]])
    R = Rx @ Rz
    tris = np.concatenate([(m.triangles + np.array([xy[0], xy[1], 0])) @ R.T for m, xy in meshes_xy])
    lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    s = 0.9 * min(W / (hi[0] - lo[0]), H / (hi[1] - lo[1]))
    off = np.array([W, H]) / 2 - s * (lo[:2] + hi[:2]) / 2
    P = tris[:, :, :2] * s + off
    Z = tris[:, :, 2]
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    light = np.array([0.3, 0.4, 0.87]) / np.linalg.norm([0.3, 0.4, 0.87])
    shade = 0.35 + 0.65 * np.clip(np.abs(n @ light), 0, 1)
    img = np.full((H, W, 3), 246.0)
    zb = np.full((H, W), -np.inf)
    for t in range(len(P)):
        (x0, y0), (x1, y1), (x2, y2) = P[t]
        d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(d) < 1e-9:
            continue
        xa, xb = max(int(min(x0, x1, x2)), 0), min(int(max(x0, x1, x2)) + 1, W)
        ya, yb = max(int(min(y0, y1, y2)), 0), min(int(max(y0, y1, y2)) + 1, H)
        if xa >= xb or ya >= yb:
            continue
        gx, gy = np.meshgrid(np.arange(xa, xb) + .5, np.arange(ya, yb) + .5)
        a = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / d
        b = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / d
        c = 1 - a - b
        inside = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
        zz = a * Z[t, 0] + b * Z[t, 1] + c * Z[t, 2]
        sub = zb[ya:yb, xa:xb]
        win = inside & (zz > sub)
        sub[win] = zz[win]
        img[ya:yb, xa:xb][win] = np.array(colour) * shade[t]
    return _png(np.flipud(img))


def insert_thumbnail(g: bytes, png: bytes, size) -> bytes:
    """Put a PNG preview block where OrcaSlicer writes its own: right after HEADER_BLOCK_END, before the first command."""
    enc = base64.b64encode(png).decode()
    w, h = size
    block = ('; THUMBNAIL_BLOCK_START\n\n;\n; thumbnail begin %dx%d %d\n' % (w, h, len(enc)) +
             ''.join('; ' + enc[i:i + 78] + '\n' for i in range(0, len(enc), 78)) +
             '; thumbnail end\n; THUMBNAIL_BLOCK_END\n\n').encode()
    k = b'; HEADER_BLOCK_END\n'
    i = g.index(k) + len(k)
    if g[i:i + 1] == b'\n':
        i += 1
    out = g[:i] + block + g[i:]
    check_thumbnail(out, g)
    return out


def check_thumbnail(payload: bytes, original: bytes | None = None) -> dict:
    lines = payload[:3_000_000].split(b'\n')
    n = next((i for i, l in enumerate(lines) if l.startswith(b'; thumbnail begin ') or l[:1] in (b'G', b'M')), None)
    assert n is not None and lines[n].startswith(b'; thumbnail begin '), 'no preview before the first G-code command'
    dims, length = lines[n].split()[3:5]
    end = next(i for i in range(n + 1, len(lines)) if lines[i].startswith(b'; thumbnail end'))
    raw = base64.b64decode(b''.join(l[2:] for l in lines[n + 1:end]))
    assert len(b''.join(l[2:] for l in lines[n + 1:end])) == int(length), 'preview length does not match its header'
    assert raw[:8] == b'\x89PNG\r\n\x1a\n', 'preview is not a PNG'
    w, h = struct.unpack('>II', raw[16:24])
    assert f'{w}x{h}'.encode() == dims, 'preview size does not match its header'
    if original is not None and payload != original:
        s = payload.index(b'; THUMBNAIL_BLOCK_START')
        e = payload.index(b'; THUMBNAIL_BLOCK_END\n\n') + len(b'; THUMBNAIL_BLOCK_END\n\n')
        assert payload[:s] + payload[e:] == original, 'preview insertion changed the command stream'
    return dict(width=w, height=h, line=n + 1, png_bytes=len(raw))

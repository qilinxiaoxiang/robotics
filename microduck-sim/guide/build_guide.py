#!/usr/bin/env python3
"""Bundle a MicroDuck assembly guide (guide-data.json, schemaVersion 1) into one self-contained HTML file.

    python3 guide/build_guide.py --data <guide-data.json> --out <file.html>

The output needs no server, CDN or network: three.js r164.1 and OrbitControls are inlined, the guide JSON is
embedded gzip+base64, and part geometry is moved out of the JSON into one gzip+base64 binary block (parts[].geom
holds byte offsets) so the meshes are not base64-encoded twice. A step with a `wiring` field (a wiring-kit bench)
also inlines ~/code/wiring-kit/dist (wiring-kit.js and wiring-kit.css). Python standard library only.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import html
import json
import math
import os
import re
import sys
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
VIEWER_DIR = HERE / 'viewer'
DEFAULT_THREE = HERE.parent / 'microduck-simulator' / 'app' / 'node_modules' / 'three'
EXPECTED_THREE = '0.164.1'
DEFAULT_WIRING_KIT = Path.home() / 'code' / 'wiring-kit' / 'dist'

HEX = re.compile(r'^#[0-9a-fA-F]{6}$')
STATUSES = {'assembled', 'printed', 'reprint', 'new-print', 'purchased', 'owned'}
PREP_KINDS = {'fastener', 'printed', 'electronic', 'tool', 'cable', 'other'}
CABLE_KINDS = {'dxl', 'power-20v', 'power-15v', 'power-7v', 'power-5v', 'ground', 'usb', 'uart', 'i2c', 'i2s', 'speaker', 'csi', 'touch'}
BOUNDS_TOLERANCE_MM = 1.0


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def is_vec3(v) -> bool:
    return isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in v)


def is_path(v) -> bool:
    """An approach as the viewer reads it: a vector [dx,dy,dz], or a list of waypoints that ends at (or gets) [0,0,0]."""
    return is_vec3(v) or (isinstance(v, list) and len(v) >= 1 and all(is_vec3(w) for w in v) and (len(v) > 1 or any(v[0])))


def decode_b64(text, what: str, rep: Report) -> bytes | None:
    if not isinstance(text, str) or not text:
        rep.error(f'{what}: missing base64 data')
        return None
    try:
        return base64.b64decode(text, validate=True)
    except (ValueError, TypeError) as exc:
        rep.error(f'{what}: invalid base64 ({exc})')
        return None


def le_array(code: str, raw: bytes) -> array:
    arr = array(code)
    arr.frombytes(raw)
    if sys.byteorder != 'little':
        arr.byteswap()
    return arr


# --------------------------------------------------------------------------- validation + geometry packing

def pack_parts(parts: list, rep: Report) -> tuple[list, bytearray, dict]:
    """Validate part geometry and move it into one little-endian binary blob."""
    blob = bytearray()
    out = []
    keys: set[str] = set()
    stats = {'parts': 0, 'triangles': 0, 'vertices': 0}
    for n, p in enumerate(parts):
        where = f'parts[{n}]'
        if not isinstance(p, dict):
            rep.error(f'{where}: not an object')
            continue
        key = p.get('key')
        if not isinstance(key, str) or not key:
            rep.error(f'{where}: missing key')
        elif key in keys:
            rep.error(f'{where}: duplicate key "{key}"')
        else:
            keys.add(key)
        where = f'part "{key}"'
        if not isinstance(p.get('name'), str) or not p.get('name'):
            rep.warn(f'{where}: missing name')
        if not (isinstance(p.get('color'), str) and HEX.match(p['color'])):
            rep.error(f'{where}: color must be "#rrggbb", got {p.get("color")!r}')
        if p.get('status') not in STATUSES:
            rep.error(f'{where}: status must be one of {sorted(STATUSES)}, got {p.get("status")!r}')
        if not isinstance(p.get('module'), str) or not p.get('module'):
            rep.warn(f'{where}: missing module')
        q = {k: v for k, v in p.items() if k not in ('positionB64', 'indexB64')}
        pos = decode_b64(p.get('positionB64'), f'{where} positionB64', rep)
        idx = decode_b64(p.get('indexB64'), f'{where} indexB64', rep)
        if pos is None or idx is None:
            out.append(q)
            continue
        if len(pos) % 12 or not pos:
            rep.error(f'{where}: positionB64 must hold float32 xyz triples ({len(pos)} bytes)')
            out.append(q)
            continue
        if len(idx) % 12 or not idx:
            rep.error(f'{where}: indexB64 must hold uint32 triangles ({len(idx)} bytes)')
            out.append(q)
            continue
        fl = le_array('f', pos)
        ix = le_array('I', idx)
        nverts = len(fl) // 3
        if max(ix) >= nverts:
            rep.error(f'{where}: triangle index {max(ix)} exceeds vertex count {nverts}')
            out.append(q)
            continue
        if any(not math.isfinite(v) for v in fl):
            rep.error(f'{where}: positions contain NaN or infinity')
            out.append(q)
            continue
        actual = [[min(fl[a::3]) for a in range(3)], [max(fl[a::3]) for a in range(3)]]
        b = p.get('bounds')
        if isinstance(b, list) and len(b) == 2 and is_vec3(b[0]) and is_vec3(b[1]):
            dev = max(abs(actual[s][a] - b[s][a]) for s in range(2) for a in range(3))
            if dev > BOUNDS_TOLERANCE_MM:
                rep.warn(f'{where}: declared bounds differ from the mesh by {dev:.2f} mm')
        else:
            rep.warn(f'{where}: bounds missing or malformed; the viewer uses the mesh bounds')
        q['geom'] = [len(blob), len(pos), len(blob) + len(pos), len(idx)]
        out.append(q)
        blob += pos
        blob += idx
        stats['parts'] += 1
        stats['triangles'] += len(ix) // 3
        stats['vertices'] += nverts
    return out, blob, stats


def validate_guide(data: dict, rep: Report) -> None:
    if data.get('schemaVersion') != 1:
        rep.error(f'schemaVersion must be 1, got {data.get("schemaVersion")!r}')
    for field in ('title',):
        if not isinstance(data.get(field), str) or not data.get(field):
            rep.error(f'missing {field}')
    if data.get('units') not in (None, 'mm'):
        rep.error(f'units must be "mm", got {data.get("units")!r}')
    parts = data.get('parts') if isinstance(data.get('parts'), list) else []
    keys = {p.get('key') for p in parts if isinstance(p, dict)}
    modules = {p.get('module') for p in parts if isinstance(p, dict) and p.get('module')}
    names = keys | modules

    chapters = data.get('chapters')
    if not isinstance(chapters, list) or not chapters:
        rep.error('chapters must be a non-empty list')
        chapters = []
    chapter_ids = []
    for c in chapters:
        cid = c.get('id') if isinstance(c, dict) else None
        if not isinstance(cid, str) or not cid:
            rep.error(f'chapter without id: {c!r}'[:200])
            continue
        if cid in chapter_ids:
            rep.error(f'duplicate chapter id "{cid}"')
        chapter_ids.append(cid)
        if not c.get('title'):
            rep.warn(f'chapter "{cid}": missing title')

    cables = data.get('cables') if isinstance(data.get('cables'), list) else []
    cable_ids = set()
    for n, c in enumerate(cables):
        cid = c.get('id') if isinstance(c, dict) else None
        where = f'cable "{cid}"' if cid else f'cables[{n}]'
        if not isinstance(cid, str) or not cid:
            rep.error(f'{where}: missing id')
            continue
        if cid in cable_ids:
            rep.error(f'{where}: duplicate id')
        cable_ids.add(cid)
        if c.get('kind') not in CABLE_KINDS:
            rep.error(f'{where}: kind must be one of {sorted(CABLE_KINDS)}, got {c.get("kind")!r}')
        if not (isinstance(c.get('color'), str) and HEX.match(c['color'])):
            rep.error(f'{where}: color must be "#rrggbb"')
        path = c.get('path')
        if not isinstance(path, list) or len(path) < 2 or not all(is_vec3(v) for v in path):
            rep.error(f'{where}: path must be at least two [x,y,z] points')
        else:
            for a, b in zip(path, path[1:]):
                if math.dist(a, b) < 1e-6:
                    rep.warn(f'{where}: repeated consecutive path point {a}')
                    break
        if 'radius' in c and not (isinstance(c['radius'], (int, float)) and c['radius'] > 0):
            rep.error(f'{where}: radius must be a positive number')
        for f in ('label', 'from', 'to'):
            if not c.get(f):
                rep.warn(f'{where}: missing {f}')

    steps = data.get('steps')
    if not isinstance(steps, list) or not steps:
        rep.error('steps must be a non-empty list')
        steps = []
    step_ids = set()
    added_at: dict[str, str] = {}
    last_chapter_pos = -1
    used_cables = set()
    for n, s in enumerate(steps):
        sid = s.get('id') if isinstance(s, dict) else None
        where = f'step "{sid}"' if sid else f'steps[{n}]'
        if not isinstance(sid, str) or not sid:
            rep.error(f'{where}: missing id')
            continue
        if sid in step_ids:
            rep.error(f'{where}: duplicate id')
        step_ids.add(sid)
        if s.get('chapter') not in chapter_ids:
            rep.error(f'{where}: unknown chapter {s.get("chapter")!r}')
        else:
            pos = chapter_ids.index(s['chapter'])
            if pos < last_chapter_pos:
                rep.warn(f'{where}: steps are not grouped in chapter order; the viewer orders steps by chapter')
            last_chapter_pos = max(last_chapter_pos, pos)
        if not s.get('title'):
            rep.error(f'{where}: missing title')
        for field in ('show', 'add', 'context'):
            val = s.get(field, [])
            if not isinstance(val, list):
                rep.error(f'{where}: {field} must be a list')
                continue
            for ref in val:
                if ref not in names:
                    rep.error(f'{where}: {field} references unknown part or module "{ref}"')
        group = s.get('group')
        if group is not None and not (isinstance(group, dict) and isinstance(group.get('label'), str) and is_path(group.get('approach'))):
            rep.error(f'{where}: group needs a label and approach [dx,dy,dz] or a waypoint list')
        pose = s.get('pose')
        if pose is not None and not (isinstance(pose, dict) and is_vec3(pose.get('pivot')) and is_vec3(pose.get('axis'))
                                     and is_vec3(pose['axis'] if any(pose.get('axis') or []) else None)
                                     and isinstance(pose.get('deg'), (int, float)) and isinstance(pose.get('parts'), list)):
            rep.error(f'{where}: pose needs parts, pivot [x,y,z], a non-zero axis and deg')
        flex = s.get('flex')
        pair = lambda v: isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) and math.isfinite(x) for x in v)
        if flex is not None and not (isinstance(flex, dict) and isinstance(flex.get('parts'), list) and pair(flex.get('ramp'))
                                     and pair(flex.get('spread')) and pair(flex.get('window'))
                                     and (flex.get('shift') is None or (isinstance(flex.get('shift'), (int, float)) and math.isfinite(flex['shift'])))):
            rep.error(f'{where}: flex needs parts, ramp [a,b], spread [-y,+y], window [in,out] and an optional numeric shift')
        for ref in s.get('add', []) or []:
            # A group step places a bench subassembly; its parts were added on the bench.
            if ref in added_at and group is None:
                rep.warn(f'{where}: "{ref}" was already added in step "{added_at[ref]}"')
            else:
                added_at[ref] = sid
        approach = s.get('approach', {}) or {}
        if not isinstance(approach, dict):
            rep.error(f'{where}: approach must be an object')
        else:
            for ref, vec in approach.items():
                if not is_path(vec):
                    rep.error(f'{where}: approach "{ref}" must be [dx,dy,dz] or a waypoint list')
                if ref not in (s.get('add') or []):
                    rep.warn(f'{where}: approach "{ref}" is not in add and will be ignored')
        cam = s.get('camera')
        if cam is None:
            rep.warn(f'{where}: no camera; the viewer frames the shown parts automatically')
        elif not (isinstance(cam, dict) and is_vec3(cam.get('position')) and is_vec3(cam.get('target'))):
            rep.error(f'{where}: camera needs position and target as [x,y,z]')
        elif math.dist(cam['position'], cam['target']) < 1:
            rep.error(f'{where}: camera position and target coincide')
        for i, p in enumerate(s.get('prepare', []) or []):
            if not isinstance(p, dict) or not p.get('item'):
                rep.error(f'{where}: prepare[{i}] needs an item')
            elif p.get('kind') not in PREP_KINDS:
                rep.error(f'{where}: prepare[{i}] kind must be one of {sorted(PREP_KINDS)}, got {p.get("kind")!r}')
        for field in ('instructions', 'checks', 'warnings'):
            val = s.get(field, [])
            if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                rep.error(f'{where}: {field} must be a list of strings')
        for cid in s.get('cables', []) or []:
            if cid not in cable_ids:
                rep.error(f'{where}: unknown cable "{cid}"')
            used_cables.add(cid)
        for i, im in enumerate(s.get('images', []) or []):
            if not isinstance(im, dict) or not isinstance(im.get('src'), str) or not im['src'].startswith('data:image/'):
                rep.error(f'{where}: images[{i}].src must be a data:image/... URI (no external files)')
        if 'wiring' in s:
            validate_wiring(s['wiring'], f'{where}: wiring', rep)
        if not s.get('add') and not s.get('cables') and not s.get('instructions'):
            rep.warn(f'{where}: adds no parts, draws no cables and has no instructions')
    for cid in sorted(cable_ids - used_cables):
        rep.warn(f'cable "{cid}" is not used by any step')
    for leg in data.get('legend', []) or []:
        if not (isinstance(leg, dict) and leg.get('kind') and isinstance(leg.get('color'), str) and HEX.match(leg['color'])):
            rep.error(f'legend entry needs kind and "#rrggbb" color: {leg!r}'[:200])


def validate_wiring(w, where: str, rep: Report) -> None:
    """A step's wiring drawing: {title?, caption?, pinText?, bench: wiring-kit Bench}. Structural checks only;
    wiring-kit's own checkBench runs in the page and lists electrical issues under the drawing."""
    bench = w.get('bench') if isinstance(w, dict) else None
    if not isinstance(bench, dict):
        rep.error(f'{where} needs a bench object')
        return
    for key in ('modules', 'placements', 'wires', 'groups'):
        if not isinstance(bench.get(key), list):
            rep.error(f'{where}: bench.{key} must be a list')
            return
    pins = {}
    for m in bench['modules']:
        if not isinstance(m, dict) or not isinstance(m.get('id'), str) or '.' in m['id']:
            rep.error(f'{where}: module needs an id without a dot')
            continue
        pins[m['id']] = {p.get('id') for p in m.get('pins', []) if isinstance(p, dict)}
        svg = (m.get('drawing') or {}).get('svg') if isinstance(m.get('drawing'), dict) else None
        if isinstance(svg, str) and re.search(r'(href|src)\s*=\s*["\'](?!data:|#)', svg):
            rep.error(f'{where}: module "{m["id"]}" drawing references an external file; embed it as a data: URI')
    placed = {pl.get('module') for pl in bench['placements'] if isinstance(pl, dict)}
    for mid in pins:
        if mid not in placed:
            rep.error(f'{where}: module "{mid}" has no placement')
    groups = {g.get('id') for g in bench['groups'] if isinstance(g, dict)}
    for wire in bench['wires']:
        if not isinstance(wire, dict):
            rep.error(f'{where}: wire must be an object')
            continue
        for end in ('from', 'to'):
            ref = wire.get(end)
            mid, _, pid = ref.partition('.') if isinstance(ref, str) else ('', '', '')
            if pid not in pins.get(mid, set()):
                rep.error(f'{where}: wire "{wire.get("id")}" {end} "{ref}" is not a module pin')
        if wire.get('group') not in groups:
            rep.error(f'{where}: wire "{wire.get("id")}" has unknown group "{wire.get("group")}"')


def load_wiring_kit(dist: Path) -> tuple[str, str, str]:
    js_path, css_path = dist / 'wiring-kit.js', dist / 'wiring-kit.css'
    if not js_path.is_file() or not css_path.is_file():
        raise SystemExit(f'wiring-kit not found in {dist}; build it with `npm run build` in ~/code/wiring-kit or pass --wiring-kit')
    js, css = js_path.read_text(encoding='utf-8'), css_path.read_text(encoding='utf-8')
    if '</style' in css.lower():
        raise SystemExit('wiring-kit.css: contains "</style"')
    sha = hashlib.sha256(js.encode('utf-8') + css.encode('utf-8')).hexdigest()[:12]
    # The bundle's SVG cleaner holds "<!--" in a string and in a regex without the u flag; "<\\!--" means the same
    # there and cannot open an HTML comment inside the inline script.
    return script_safe(js.replace('<!--', '<\\!--'), 'wiring-kit.js'), css, sha


# --------------------------------------------------------------------------- three.js inlining

def script_safe(js: str, what: str) -> str:
    if '<!--' in js:
        raise SystemExit(f'{what}: contains "<!--", which is unsafe inside an inline script')
    return re.sub(r'</(script)', r'<\\/\1', js, flags=re.I)


def load_three(three_dir: Path) -> tuple[str, str]:
    pkg = json.loads((three_dir / 'package.json').read_text())
    if pkg.get('version') != EXPECTED_THREE:
        print(f'warning: three.js {pkg.get("version")} found, viewer was written for {EXPECTED_THREE}', file=sys.stderr)
    src = (three_dir / 'build' / 'three.module.js').read_text(encoding='utf-8')
    m = re.search(r'export\s*\{([^}]+)\};?\s*$', src)
    if not m:
        raise SystemExit('three.module.js: final export list not found')
    body = src[:m.start()]
    if re.search(r'^\s*(import|export)\s', body, re.M) or 'import.meta' in body:
        raise SystemExit('three.module.js: unexpected import/export; the IIFE wrapper would break')
    members = []
    for term in m.group(1).split(','):
        term = term.strip()
        if not term:
            continue
        local, _, exported = term.partition(' as ')
        members.append(f'{(exported or local).strip()}:{local.strip()}')
    three_js = "const THREE=(function(){'use strict';\n" + body + '\nreturn {' + ','.join(members) + '};\n})();\n'

    orbit = (three_dir / 'examples' / 'jsm' / 'controls' / 'OrbitControls.js').read_text(encoding='utf-8')
    orbit, n_imp = re.subn(r"import\s*\{([^}]+)\}\s*from\s*'three';", lambda mm: 'const {' + mm.group(1) + '} = THREE;', orbit, count=1)
    orbit, n_exp = re.subn(r'export\s*\{\s*OrbitControls\s*\};?\s*$', 'return OrbitControls;', orbit)
    if n_imp != 1 or n_exp != 1 or re.search(r'^\s*(import|export)\s', orbit, re.M):
        raise SystemExit('OrbitControls.js: could not convert the module to an IIFE')
    orbit_js = "const OrbitControls=(function(){'use strict';\n" + orbit + '\n})();\n'
    return script_safe(three_js, 'three.module.js'), script_safe(orbit_js, 'OrbitControls.js')


# --------------------------------------------------------------------------- packing

def gzip_b64(raw: bytes) -> str:
    packed = gzip.compress(raw, compresslevel=9, mtime=0)
    if hashlib.sha256(gzip.decompress(packed)).digest() != hashlib.sha256(raw).digest():
        raise SystemExit('gzip readback differs from the input')
    return base64.b64encode(packed).decode('ascii')


def build(data_path: Path, out_path: Path, three_dir: Path, allow_errors: bool = False, manifest: Path | None = None,
          wiring_kit: Path = DEFAULT_WIRING_KIT) -> dict:
    source_bytes = data_path.read_bytes()
    data = json.loads(source_bytes)
    rep = Report()
    if not isinstance(data, dict):
        raise SystemExit('guide data must be a JSON object')
    validate_guide(data, rep)
    parts, blob, geo_stats = pack_parts(data.get('parts') if isinstance(data.get('parts'), list) else [], rep)
    for w in rep.warnings:
        print('warning: ' + w, file=sys.stderr)
    for e in rep.errors:
        print('error: ' + e, file=sys.stderr)
    if rep.errors and not allow_errors:
        raise SystemExit(f'{len(rep.errors)} error(s); fix the data or pass --allow-errors to build anyway')

    packed_data = dict(data)
    packed_data['parts'] = parts
    data_json = json.dumps(packed_data, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    data_b64 = gzip_b64(data_json)
    geo_b64 = gzip_b64(bytes(blob))

    three_js, orbit_js = load_three(three_dir)
    app_js = script_safe((VIEWER_DIR / 'app.js').read_text(encoding='utf-8'), 'app.js')
    css = (VIEWER_DIR / 'style.css').read_text(encoding='utf-8')
    if '</style' in css.lower():
        raise SystemExit('style.css: contains "</style"')
    template = (VIEWER_DIR / 'template.html').read_text(encoding='utf-8')
    for marker in ('/*__STYLE__*/', '<!--__SCRIPTS__-->', '__GUIDE_BUILD__'):
        if template.count(marker) != 1:
            raise SystemExit(f'template.html: marker {marker} must appear exactly once')
    if re.search(r'<(script|link|img|iframe)[^>]+(src|href)\s*=\s*["\']?(https?:)?//', template, re.I):
        raise SystemExit('template.html: references an external resource')

    wiring_steps = [s.get('id') for s in data.get('steps') or [] if isinstance(s, dict) and s.get('wiring')]
    wk_js = wk_css = wk_sha = ''
    if wiring_steps:
        wk_js, wk_css, wk_sha = load_wiring_kit(wiring_kit)
        css = css + '\n' + wk_css

    data_sha = hashlib.sha256(source_bytes).hexdigest()
    build_info = f'source-sha256={data_sha}; three={EXPECTED_THREE}; parts={geo_stats["parts"]}; triangles={geo_stats["triangles"]}'
    if wk_sha:
        build_info += f'; wiring-kit={wk_sha}'
    title = data.get('title') or 'Assembly guide'
    head, tail = template.replace('__GUIDE_TITLE__', html.escape(title)).replace('__GUIDE_BUILD__', html.escape(build_info)).split('<!--__SCRIPTS__-->')
    head = head.replace('/*__STYLE__*/', css)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(out_path.name + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        f.write(head)
        f.write('<script>\n'); f.write(three_js); f.write(orbit_js); f.write('</script>\n')
        if wk_js:
            f.write('<script>\n'); f.write(wk_js); f.write('\n</script>\n')
        f.write('<script type="application/octet-stream" id="guide-data" data-encoding="gzip+base64">')
        f.write(data_b64); f.write('</script>\n')
        f.write('<script type="application/octet-stream" id="guide-geometry" data-encoding="gzip+base64">')
        f.write(geo_b64); f.write('</script>\n')
        f.write('<script>\n'); f.write(app_js); f.write('\n</script>\n')
        f.write(tail)
    os.replace(tmp, out_path)

    summary = {
        'out': str(out_path),
        'outBytes': out_path.stat().st_size,
        'sourceSha256': data_sha,
        'title': title,
        'revision': data.get('revision'),
        'chapters': len(data.get('chapters') or []),
        'steps': len(data.get('steps') or []),
        'cables': len(data.get('cables') or []),
        'parts': len(parts),
        'partsWithGeometry': geo_stats['parts'],
        'triangles': geo_stats['triangles'],
        'vertices': geo_stats['vertices'],
        'jsonBytes': len(data_json),
        'jsonEmbeddedBytes': len(data_b64),
        'geometryBytes': len(blob),
        'geometryEmbeddedBytes': len(geo_b64),
        'errors': rep.errors,
        'warnings': len(rep.warnings),
        'three': EXPECTED_THREE,
        'wiringSteps': wiring_steps,
        'wiringKit': wk_sha or None,
    }
    if manifest:
        manifest.write_text(json.dumps(summary, indent=2) + '\n')
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--data', required=True, type=Path, help='guide-data.json (schemaVersion 1)')
    ap.add_argument('--out', type=Path, help='output HTML file')
    ap.add_argument('--three', type=Path, default=DEFAULT_THREE, help='three.js package directory (default: simulator node_modules)')
    ap.add_argument('--wiring-kit', type=Path, default=DEFAULT_WIRING_KIT, help='wiring-kit dist directory (default: ~/code/wiring-kit/dist)')
    ap.add_argument('--manifest', type=Path, help='also write the build summary JSON here')
    ap.add_argument('--check', action='store_true', help='validate the data only; write nothing')
    ap.add_argument('--allow-errors', action='store_true', help='build even when validation reports errors')
    args = ap.parse_args(argv)
    if args.check:
        data = json.loads(args.data.read_bytes())
        rep = Report()
        validate_guide(data, rep)
        _, _, stats = pack_parts(data.get('parts') if isinstance(data.get('parts'), list) else [], rep)
        for w in rep.warnings:
            print('warning: ' + w, file=sys.stderr)
        for e in rep.errors:
            print('error: ' + e, file=sys.stderr)
        print(json.dumps({'errors': len(rep.errors), 'warnings': len(rep.warnings), **stats}))
        return 1 if rep.errors else 0
    if not args.out:
        ap.error('--out is required unless --check is given')
    summary = build(args.data, args.out, args.three, args.allow_errors, args.manifest, args.wiring_kit)
    print(json.dumps(summary))
    return 0


if __name__ == '__main__':
    sys.exit(main())

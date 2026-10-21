#!/usr/bin/env python3
"""Write the print delivery folder for a released MicroDuck print version (Shawn 2026-10-14: no zip, one folder per printer,
one preview picture per plate).

    /tmp/microduck-cad-venv/bin/python guide/print/make_delivery_folder.py guide/print/release-V1.13

Creates ~/Downloads/zhengxia_MicroDuck_<version>/ with
  X1C/      the Bambu X1C .gcode.3mf files     (copy this folder onto the X1C SD card)
  Elegoo/   the Elegoo Centauri Carbon .gcode   (copy this folder onto the Centauri SD card)
  <Colour>-plate.png  one picture per plate: a top view of the 256 mm bed with every part's footprint, the bed centre,
                      the excluded corners and the measured centre offset (Shawn 2026-10-15), the thumbnail embedded in
                      each machine file (X1C and Elegoo), and every part rendered on its own, in the pose it prints in
                      on the bed (Shawn 2026-10-20: cards drawn in the model frame did not match the Elegoo file).
Nothing else goes in the folder (Shawn 2026-10-20: no HTML in it).
Every machine file is copied from run/delivery-index.json and checked byte for byte against its recorded sha256, and each
part's footprint centre in the picture is checked against the object boxes written in both machine files.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / 'content'))
from render import render  # noqa: E402
sys.path.insert(0, str(HERE))
import make_parts_sheet as sheet  # noqa: E402  (part names, colours)

FOLDERS = {'Bambu X1 Carbon': 'X1C', 'Elegoo Centauri Carbon': 'Elegoo'}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def font(size: int):
    for f in ('/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/System/Library/Fonts/Helvetica.ttc', '/Library/Fonts/Arial.ttf'):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def part_image(path: Path, colour: str, size=(420, 330), T=None) -> Image.Image:
    m = trimesh.load(path, force='mesh', process=False)
    if T is not None:   # the print pose on the bed (print z up)
        m.apply_transform(np.asarray(T, dtype=float))
    v = np.asarray(m.vertices, dtype=np.float64)
    c = (v.min(0) + v.max(0)) / 2
    r = float(np.linalg.norm(v.max(0) - v.min(0))) / 2
    d = np.array([1.0, -1.25, 0.9]); d /= np.linalg.norm(d)
    pos = c + d * r / np.tan(np.radians(15)) * 1.1
    shade = {'White': (205, 203, 196)}.get(colour, sheet.RGB[colour])   # pure white vanishes on the light background
    scene = {'p': {'v': v, 'f': np.asarray(m.faces), 'color': shade, 'module': 'p'}}
    with tempfile.TemporaryDirectory() as tmp:
        out = render(scene, [(pos.tolist(), c.tolist(), (0, 0, 1))], str(Path(tmp) / 'x.png'), size=size)[0]
        return Image.open(out).convert('RGB')


BED_MM = 256.0
EXCLUDED = {'X1C': (0, 0, 18, 28), 'Elegoo': (246, 0, 256, 20)}   # release_pipeline_v2.first_layer exclusion boxes (x0, y0, x1, y1)


def bed_map(prep: dict, colour: str, size: int = 470) -> tuple[Image.Image, list[float]]:
    """Top-down view of the 256 x 256 mm bed as the slicer shows it (front edge at the bottom): grid every 32 mm, the bed
    centre cross, both printers' excluded corners and every part's footprint at its plate position. Returns the image and
    the model footprint centre offset from the bed centre in mm."""
    row = next(r for r in prep['rows'] if r['color'] == colour and r['machine'] == 'Bambu')
    parts = {p['key']: p for p in prep['parts']}
    m = 34; s = (size - 2 * m) / BED_MM
    px = lambda x, y: (m + x * s, m + (BED_MM - y) * s)
    img = Image.new('RGB', (size, size), (255, 255, 255)); d = ImageDraw.Draw(img)
    d.rectangle((*px(0, BED_MM), *px(BED_MM, 0)), fill=(236, 236, 232), outline=(120, 120, 124), width=2)
    for g in range(32, 256, 32):
        d.line((*px(g, 0), *px(g, BED_MM)), fill=(220, 220, 214)); d.line((*px(0, g), *px(BED_MM, g)), fill=(220, 220, 214))
    for name, (x0, y0, x1, y1) in EXCLUDED.items():
        d.rectangle((*px(x0, y1), *px(x1, y0)), fill=(242, 205, 205)); d.text((px(x0, y1)[0] + (2 if x0 < 128 else -44), px(x0, y1)[1] - 16), name, fill=(170, 60, 60), font=font(12))
    shade = {'White': (190, 188, 180)}.get(colour, sheet.RGB[colour])
    for pl in row['placements']:
        p = parts[pl['key']]; T = np.array(p['sourceToPrint'], float); T[2, 3] += p['dropToBedMm']
        mesh = trimesh.load(p['source']['path'], force='mesh', process=False); mesh.apply_transform(T)
        tri = mesh.triangles[:, :, :2] + np.array(pl['translation'][:2])
        for t in tri:
            d.polygon([px(*v) for v in t], fill=shade)
    b = [np.array(x) for x in row['modelBounds']]
    lo = np.min([x[0][:2] for x in b], axis=0); hi = np.max([x[1][:2] for x in b], axis=0); off = ((lo + hi) / 2 - BED_MM / 2).round(1) + 0.0   # no "-0.0"
    d.rectangle((*px(lo[0], hi[1]), *px(hi[0], lo[1])), outline=(60, 110, 200), width=1)
    c = px(BED_MM / 2, BED_MM / 2); fc = px(*((lo + hi) / 2))
    d.line((c[0] - 12, c[1], c[0] + 12, c[1]), fill=(29, 29, 31), width=2); d.line((c[0], c[1] - 12, c[0], c[1] + 12), fill=(29, 29, 31), width=2)
    d.ellipse((fc[0] - 5, fc[1] - 5, fc[0] + 5, fc[1] + 5), outline=(60, 110, 200), width=2)
    d.text((m, 8), 'Bed 256 x 256 mm, top view, front edge at the bottom', fill=(93, 93, 99), font=font(15))
    d.text((m, size - m + 8), 'front', fill=(93, 93, 99), font=font(14))
    return img, off.tolist()


def elegoo_thumbnail(gcode: Path) -> Image.Image:
    """The largest PNG thumbnail embedded in an Orca/Elegoo .gcode (the picture the printer shows for the file)."""
    best = None; lines = gcode.read_text(errors='replace').splitlines()[:4000]
    for i, l in enumerate(lines):
        if l.startswith('; thumbnail') and ' begin ' in l:
            w = int(l.split(' begin ')[1].split('x')[0]); j = i + 1; b = []
            while ' end' not in lines[j]:
                b.append(lines[j][2:].strip()); j += 1
            if best is None or w > best[0]:
                best = (w, base64.b64decode(''.join(b)))
    assert best, f'{gcode}: no embedded thumbnail'
    return Image.open(io.BytesIO(best[1]))


def file_objects(files: list[dict]) -> dict:
    """Per machine, object name -> XY centre as written in the machine file itself: Bambu Metadata/plate_1.json
    bbox_objects (brim included, so compared with a looser tolerance), Elegoo EXCLUDE_OBJECT_DEFINE CENTER."""
    out = {}
    for f in files:
        path = Path(f['path'])
        if f['machine'] == 'Bambu X1 Carbon':
            with zipfile.ZipFile(path) as z:
                objs = json.loads(z.read('Metadata/plate_1.json'))['bbox_objects']
            out['X1C'] = {o['name']: ((o['bbox'][0] + o['bbox'][2]) / 2, (o['bbox'][1] + o['bbox'][3]) / 2) for o in objs}
        else:
            c = {}
            for l in path.read_text(errors='replace').splitlines():
                if l.startswith('EXCLUDE_OBJECT_DEFINE'):
                    name = l.split('NAME=')[1].split()[0]; x, y = l.split('CENTER=')[1].split()[0].split(',')
                    c[name.split('_id_')[0]] = (float(x), float(y))
            out['Elegoo'] = c
    return out


def check_footprints(prep: dict, colour: str, files: list[dict]) -> None:
    """Every part drawn on the bed map (Bambu row placement) sits where both machine files put it."""
    row = next(r for r in prep['rows'] if r['color'] == colour and r['machine'] == 'Bambu')
    drawn = {f'{pl["key"]}_{pl.get("copy", 1)}': ((np.array(b[0][:2]) + np.array(b[1][:2])) / 2)
             for pl, b in zip(row['placements'], row['modelBounds'])}
    for machine, objs in file_objects(files).items():
        assert set(objs) == set(drawn), (machine, sorted(objs), sorted(drawn))
        tol = 1.0 if machine == 'Elegoo' else 3.0   # the X1C box includes the brim, whose loops are not symmetric
        for name, c in objs.items():
            assert np.hypot(*(np.array(c) - drawn[name])) <= tol, (machine, name, c, drawn[name].tolist())


def plate_picture(version: str, colour: str, parts: list[dict], files: list[dict], thumbs: list, names: dict, prep: dict) -> Image.Image:
    W, pad, cw, ch = 1500, 24, 460, 380
    cols = 3
    rows = (len(parts) + cols - 1) // cols
    top = 600
    H = top + rows * (ch + pad) + pad
    img = Image.new('RGB', (W, H), (247, 246, 242)); d = ImageDraw.Draw(img)
    d.text((pad, pad), f'MicroDuck {version} · {colour} plate · {sum(p["quantity"] for p in parts)} parts', fill=(29, 29, 31), font=font(40))
    y = pad + 58
    for f in files:
        d.text((pad, y), f'{FOLDERS[f["machine"]]}/  {f["filename"]}', fill=(93, 93, 99), font=font(22)); y += 32
    d.text((pad, y + 8), 'Load this colour, print one file on one printer. Right: the parts on the bed. Below: each part.', fill=(93, 93, 99), font=font(22))
    bm, off = bed_map(prep, colour)
    img.paste(bm, (W - pad - bm.size[0], pad))
    ok = max(abs(v) for v in off) <= 1.0
    d.text((pad, y + 48), f'Centre of the parts vs bed centre: x {off[0]:+.1f} mm, y {off[1]:+.1f} mm' + ('  (centred)' if ok else '  (NOT CENTRED)'),
           fill=(40, 120, 60) if ok else (190, 40, 40), font=font(24))
    x = pad
    for label, thumb in thumbs:
        th = thumb.convert('RGBA'); th = th.resize((260, round(260 * th.size[1] / th.size[0])), Image.LANCZOS)
        bg = Image.new('RGBA', th.size, (255, 255, 255, 255)); bg.alpha_composite(th)
        img.paste(bg.convert('RGB'), (x, top - pad - 30 - th.size[1]))
        d.text((x, top - pad - 26), label, fill=(93, 93, 99), font=font(18)); x += 260 + pad
    for i, p in enumerate(parts):
        x0 = pad + (i % cols) * (cw + pad); y0 = top + (i // cols) * (ch + pad)
        d.rounded_rectangle((x0, y0, x0 + cw, y0 + ch), 14, fill=(255, 255, 255), outline=(227, 225, 218), width=2)
        T = np.array(p['sourceToPrint'], float)
        pi = part_image(Path(p['source']['path']), colour, size=(cw - 20, ch - 70), T=T); img.paste(pi, (x0 + 10, y0 + 10))
        label = names.get(p['key'], p['key']) + (f'  × {p["quantity"]}' if p['quantity'] > 1 else '') + ', as on the bed'
        d.text((x0 + 16, y0 + ch - 50), label, fill=(29, 29, 31), font=font(23))
    return img


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument('release', type=Path)
    ap.add_argument('--out-root', type=Path, default=Path.home() / 'Downloads'); a = ap.parse_args()
    rel = a.release.resolve(); run = rel / 'run'
    index = json.loads((run / 'delivery-index.json').read_text())
    assert index['status'] == 'RELEASED', index['status']
    prep = json.loads((run / 'preparation.json').read_text())
    version = index['version']
    out = a.out_root / f'zhengxia_MicroDuck_{version}'
    if out.exists():
        shutil.rmtree(out)
    names = sheet.INCREMENTAL_NAMES_BY_VERSION.get(version, {})
    written = []
    for f in index['files']:
        src = Path(f['path']); assert sha(src) == f['sha256'], src
        dst = out / FOLDERS[f['machine']] / f['filename']; dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst); assert sha(dst) == f['sha256'], dst; written.append(str(dst))
    for colour in sorted({f['color'] for f in index['files']}):
        files = [f for f in index['files'] if f['color'] == colour]
        thumbs = []
        for f in files:
            if f['machine'] == 'Bambu X1 Carbon':
                with zipfile.ZipFile(f['path']) as z:
                    thumbs.append(('X1C file thumbnail', Image.open(io.BytesIO(z.read('Metadata/plate_1.png')))))
            else:
                thumbs.append(('Elegoo file thumbnail', elegoo_thumbnail(Path(f['path']))))
        check_footprints(prep, colour, files)
        parts = [p for p in prep['parts'] if p['color'] == colour]
        pic = out / f'{colour}-plate.png'
        plate_picture(version, colour, parts, files, thumbs, names, prep).save(pic, optimize=True); written.append(str(pic))
    extra = sorted(str(x.relative_to(out)) for x in out.rglob('*') if x.is_file() and str(x) not in written)
    assert not extra, f'unexpected files in the delivery folder: {extra}'
    print(json.dumps({'out': str(out), 'files': written}, indent=1))


if __name__ == '__main__':
    main()

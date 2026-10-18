#!/usr/bin/env python3
"""Contact sheet per part: every candidate pose from an orientation_check.py report, seen from above and from
below. Grey/colour = part, red = downward area steeper than 60 deg from vertical (what the slicer supports),
blue = hole-end facets that face down above the bed. Bed plane in light grey.

    run_bounded_cad.py ... -- /tmp/microduck-cad-venv/bin/python scripts/render_candidates.py REPORT.json OUT_DIR [KEY ...]
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import vtk
from PIL import Image, ImageDraw
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from orientation_check import detect_holes, load_mesh  # noqa: E402

RGB = {'Orange': (232, 120, 30), 'Black': (90, 90, 96), 'Yellow': (236, 196, 60), 'White': (215, 213, 205)}


def actor(v, f, color, opacity=1.0):
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(v.astype(np.float32), deep=True))
    cells = np.hstack([np.full((len(f), 1), 3, dtype=np.int64), f.astype(np.int64)]).ravel()
    ca = vtk.vtkCellArray()
    ca.SetCells(len(f), numpy_to_vtkIdTypeArray(cells, deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(ca)
    n = vtk.vtkPolyDataNormals()
    n.SetInputData(pd)
    n.SetFeatureAngle(35)
    n.Update()
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(n.GetOutput())
    a = vtk.vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetColor(*[c / 255 for c in color])
    a.GetProperty().SetOpacity(opacity)
    a.GetProperty().SetDiffuse(0.85)
    a.GetProperty().SetAmbient(0.2)
    return a


def render(groups, views, size=(420, 330)):
    ren = vtk.vtkRenderer()
    ren.SetBackground(0.97, 0.97, 0.95)
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.AddRenderer(ren)
    rw.SetSize(*size)
    for v, f, c, o in groups:
        if len(f):
            ren.AddActor(actor(v, f, c, o))
    out = []
    for pos, foc in views:
        cam = ren.GetActiveCamera()
        cam.SetPosition(*pos)
        cam.SetFocalPoint(*foc)
        cam.SetViewUp(0, 0, 1)
        cam.SetViewAngle(30)
        ren.ResetCameraClippingRange()
        rw.Render()
        w2i = vtk.vtkWindowToImageFilter()
        w2i.SetInput(rw)
        w2i.ReadFrontBufferOff()
        w2i.Update()
        img = w2i.GetOutput()
        w, h, _ = img.GetDimensions()
        arr = vtk.util.numpy_support.vtk_to_numpy(img.GetPointData().GetScalars()).reshape(h, w, -1)[::-1]
        out.append(Image.fromarray(arr[:, :, :3].copy()))
    return out


def main():
    report = json.loads(Path(sys.argv[1]).read_text())
    outdir = Path(sys.argv[2])
    keys = set(sys.argv[3:])
    outdir.mkdir(parents=True, exist_ok=True)
    for part in report['parts']:
        if keys and part['key'] not in keys:
            continue
        mesh = load_mesh(part['source'])
        holes = [h for h in detect_holes(mesh) if h['kind'] == 'hole']
        rows = []
        for c in part['candidates']:
            T = np.array(c['sourceToPrint'])
            v = mesh.vertices @ T[:3, :3].T + T[:3, 3]
            v[:, 2] -= v[:, 2].min()
            f = mesh.faces
            n = mesh.face_normals @ T[:3, :3].T
            tri = v[f]
            above = tri[:, :, 2].min(1) > 0.05
            red = above & (-n[:, 2] > math.sin(math.radians(60)))
            blue = np.zeros(len(f), bool)
            for h in holes:
                for e in h['ends']:
                    if (T[:3, :3] @ e['normal'])[2] < -0.7:
                        blue[mesh.facets[e['facet']]] = True
            blue &= above
            red &= ~blue
            lo, hi = v.min(0), v.max(0)
            ctr = (lo + hi) / 2
            r = max(np.linalg.norm(hi - lo) / 2, 5)
            pad = r * 0.25
            bed = np.array([[lo[0] - pad, lo[1] - pad, -0.05], [hi[0] + pad, lo[1] - pad, -0.05],
                            [hi[0] + pad, hi[1] + pad, -0.05], [lo[0] - pad, hi[1] + pad, -0.05]])
            groups = [(v, f[~red & ~blue], RGB.get(part['color'], (180, 180, 180)), 1.0), (v, f[red], (215, 40, 40), 1.0),
                      (v, f[blue], (40, 90, 220), 1.0), (bed, np.array([[0, 1, 2], [0, 2, 3]]), (200, 200, 200), 0.35)]
            dist = r / math.tan(math.radians(15)) * 0.95
            up = np.array([0.9, -1.2, 0.9]) / np.linalg.norm([0.9, -1.2, 0.9])
            dn = np.array([-0.9, -1.2, -0.8]) / np.linalg.norm([-0.9, -1.2, -0.8])
            imgs = render(groups, [((ctr + up * dist).tolist(), ctr.tolist()), ((ctr + dn * dist).tolist(), ctr.tolist())])
            label = (f"#{c['rank']} {c['name']}  h={c['heightMm']}  contact={c['contactMm2']}  tip={c['tipAngleDeg']}  "
                     f"ov60={c['overhang60Mm2']}  holes V/I/H={c['holesVertical']}/{c['holesInclined']}/{c['holesHorizontal']}  "
                     f"seatsDown={c['holeEndsFacingDown']}  penalty={c['penalty']}")
            row = Image.new('RGB', (imgs[0].width * 2, imgs[0].height + 22), 'white')
            row.paste(imgs[0], (0, 22))
            row.paste(imgs[1], (imgs[0].width, 22))
            ImageDraw.Draw(row).text((6, 5), label, fill=(0, 0, 0))
            rows.append(row)
        sheet = Image.new('RGB', (rows[0].width, sum(r.height for r in rows)), 'white')
        y = 0
        for r in rows:
            sheet.paste(r, (0, y))
            y += r.height
        sheet.save(outdir / f"{part['key']}.png", optimize=True)
        print(part['key'], len(rows), 'candidates')
        del mesh


if __name__ == '__main__':
    main()

"""Offscreen shaded renders with VTK (no window). render(items, out_png, cam=(pos, focal, up), size=(w, h), labels=...)
items: list of (trimesh.Trimesh, (r, g, b) in 0..1, opacity). Parallel projection optional (scale = half height mm)."""
from __future__ import annotations

import numpy as np
import vtk
from vtk.util import numpy_support as ns


def _poly(m):
    pts = vtk.vtkPoints()
    pts.SetData(ns.numpy_to_vtk(np.ascontiguousarray(m.vertices, dtype=np.float64), deep=True))
    f = np.asarray(m.faces, dtype=np.int64)
    cells = np.hstack([np.full((len(f), 1), 3, np.int64), f]).ravel()
    ca = vtk.vtkCellArray()
    ca.SetCells(len(f), ns.numpy_to_vtkIdTypeArray(cells, deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(ca)
    nf = vtk.vtkPolyDataNormals()
    nf.SetInputData(pd)
    nf.SetFeatureAngle(35)
    nf.SplittingOn()
    nf.Update()
    return nf.GetOutput()


def render(items, out_png, cam, size=(1200, 900), parallel_scale=None, title=None, labels=(), bg=(1, 1, 1),
           lines=()):
    """lines: list of (Nx3 points, (r,g,b), width) drawn as polylines; labels: list of (xyz, text, (r,g,b))."""
    ren = vtk.vtkRenderer()
    ren.SetBackground(*bg)
    for m, col, op in items:
        if m is None or len(m.faces) == 0:
            continue
        mp = vtk.vtkPolyDataMapper()
        mp.SetInputData(_poly(m))
        a = vtk.vtkActor()
        a.SetMapper(mp)
        p = a.GetProperty()
        p.SetColor(*col)
        p.SetOpacity(op)
        p.SetAmbient(0.25)
        p.SetDiffuse(0.75)
        p.SetSpecular(0.1)
        ren.AddActor(a)
    for P, col, w in lines:
        P = np.asarray(P, float)
        pts = vtk.vtkPoints()
        for q in P:
            pts.InsertNextPoint(*q)
        pl = vtk.vtkPolyLine()
        pl.GetPointIds().SetNumberOfIds(len(P))
        for i in range(len(P)):
            pl.GetPointIds().SetId(i, i)
        ca = vtk.vtkCellArray()
        ca.InsertNextCell(pl)
        pd = vtk.vtkPolyData()
        pd.SetPoints(pts)
        pd.SetLines(ca)
        mp = vtk.vtkPolyDataMapper()
        mp.SetInputData(pd)
        a = vtk.vtkActor()
        a.SetMapper(mp)
        a.GetProperty().SetColor(*col)
        a.GetProperty().SetLineWidth(w)
        ren.AddActor(a)
    for xyz, text, col in labels:
        ta = vtk.vtkBillboardTextActor3D()
        ta.SetInput(text)
        ta.SetPosition(*xyz)
        tp = ta.GetTextProperty()
        tp.SetFontSize(16)
        tp.SetColor(*col)
        tp.SetBold(True)
        tp.SetBackgroundColor(1, 1, 1)
        tp.SetBackgroundOpacity(0.7)
        ren.AddActor(ta)
    if title:
        t = vtk.vtkTextActor()
        t.SetInput(title)
        t.GetTextProperty().SetFontSize(18)
        t.GetTextProperty().SetColor(0.1, 0.1, 0.1)
        t.SetDisplayPosition(12, size[1] - 30)
        ren.AddViewProp(t)
    pos, foc, up = cam
    c = ren.GetActiveCamera()
    c.SetPosition(*pos)
    c.SetFocalPoint(*foc)
    c.SetViewUp(*up)
    if parallel_scale:
        c.ParallelProjectionOn()
        c.SetParallelScale(parallel_scale)
    ren.ResetCameraClippingRange()
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetSize(*size)
    rw.AddRenderer(ren)
    rw.SetMultiSamples(4)
    rw.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.Update()
    wr = vtk.vtkPNGWriter()
    wr.SetFileName(str(out_png))
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()
    rw.Finalize()

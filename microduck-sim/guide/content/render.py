import pickle, sys, json, numpy as np, vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
def load(p): return pickle.load(open(p,'rb'))
def polydata(v,f):
    pts=vtk.vtkPoints(); pts.SetData(numpy_to_vtk(v.astype(np.float32),deep=True))
    cells=np.hstack([np.full((len(f),1),3,dtype=np.int64),f.astype(np.int64)]).ravel()
    ca=vtk.vtkCellArray(); ca.SetCells(len(f),numpy_to_vtkIdTypeArray(cells,deep=True))
    pd=vtk.vtkPolyData(); pd.SetPoints(pts); pd.SetPolys(ca)
    n=vtk.vtkPolyDataNormals(); n.SetInputData(pd); n.SetFeatureAngle(35); n.Update()
    return n.GetOutput()
def render(scene, views, out, size=(1100,850), ghost=(), hide=(), only=None, labels=False, highlight=()):
    ren=vtk.vtkRenderer(); ren.SetBackground(0.96,0.96,0.94)
    rw=vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren); rw.SetSize(*size)
    rw.SetAlphaBitPlanes(1); rw.SetMultiSamples(4)
    ren.SetUseDepthPeeling(1); ren.SetMaximumNumberOfPeels(8)
    for k,p in scene.items():
        if only is not None and k not in only and p.get('module') not in only: continue
        if k in hide or p.get('module') in hide: continue
        m=vtk.vtkPolyDataMapper(); m.SetInputData(polydata(p['v'],p['f']))
        a=vtk.vtkActor(); a.SetMapper(m)
        c=[x/255 for x in p['color']]
        if k in highlight: c=[1.0,0.85,0.1]
        a.GetProperty().SetColor(*c); a.GetProperty().SetSpecular(0.2); a.GetProperty().SetDiffuse(0.85); a.GetProperty().SetAmbient(0.15)
        if k in ghost or p.get('module') in ghost: a.GetProperty().SetOpacity(0.18)
        ren.AddActor(a)
    imgs=[]
    for i,(pos,foc,up) in enumerate(views):
        cam=ren.GetActiveCamera(); cam.SetPosition(*pos); cam.SetFocalPoint(*foc); cam.SetViewUp(*up)
        ren.ResetCameraClippingRange()
        cam.SetViewAngle(30)
        rw.Render()
        w2i=vtk.vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.ReadFrontBufferOff(); w2i.Update()
        wr=vtk.vtkPNGWriter(); fn=out.replace('.png',f'_{i}.png'); wr.SetFileName(fn); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
        imgs.append(fn)
    return imgs
if __name__=='__main__':
    cfg=json.loads(sys.argv[2])
    sc=load(sys.argv[1])
    print(render(sc,cfg['views'],cfg['out'],ghost=set(cfg.get('ghost',[])),hide=set(cfg.get('hide',[])),only=set(cfg['only']) if cfg.get('only') else None, highlight=set(cfg.get('highlight',[]))))

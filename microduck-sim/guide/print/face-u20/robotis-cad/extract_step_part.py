"""Walk the OMX-F STEP assembly; print the tree under the Innomaker camera with world bounding boxes; export each camera leaf as STL (world frame, mm)."""
import sys
from pathlib import Path
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.TopLoc import TopLoc_Location
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(exist_ok=True)
doc = TDocStd_Document(TCollection_ExtendedString('d'))
r = STEPCAFControl_Reader(); r.SetNameMode(True); r.ReadFile(src); r.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
def name(l):
    a = TDataStd_Name()
    return a.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(), a) else '?'
def bbox(s):
    b = Bnd_Box(); BRepBndLib.Add_s(s, b); x0,y0,z0,x1,y1,z1 = b.Get(); return [round(v,2) for v in (x0,y0,z0,x1,y1,z1)]
n = [0]
def walk(l, loc, depth, inside, path):
    nm = name(l); ref = TDF_Label()
    if st.IsReference_s(l):
        st.GetReferredShape_s(l, ref); loc = loc.Multiplied(st.GetLocation_s(l)); body = ref
    else: body = l
    bn = name(body); here = inside or any(k in (nm+bn).upper() for k in sys.argv[3:])
    kids = TDF_LabelSequence(); st.GetComponents_s(body, kids)
    if here:
        s = st.GetShape_s(body).Moved(loc)
        print('  '*depth + f'{nm} [{bn}] bbox {bbox(s)} kids {kids.Length()}')
        if kids.Length() == 0:
            BRepMesh_IncrementalMesh(s, 0.05); n[0] += 1; w = StlAPI_Writer(); w.Write(s, str(out / f'{n[0]:02d}_{bn[:40]}.stl'))
    for i in range(1, kids.Length()+1): walk(kids.Value(i), loc, depth+1, here, path)
roots = TDF_LabelSequence(); st.GetFreeShapes(roots)
for i in range(1, roots.Length()+1): walk(roots.Value(i), TopLoc_Location(), 0, False, '')

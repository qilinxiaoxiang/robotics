from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from pathlib import Path
import json,hashlib
F=Path(__file__).resolve().parent;p=F/'sources/7semi-10113.STEP';rd=STEPControl_Reader();assert rd.ReadFile(str(p))==1;rd.TransferRoots();s=rd.OneShape();e=TopExp_Explorer(s,TopAbs_SOLID);out=[]
b=Bnd_Box();BRepBndLib.AddOptimal_s(s,b,False,False);print("TOTAL",list(b.Get()));BRepMesh_IncrementalMesh(s,.02,False,.1,True).Perform();w=StlAPI_Writer();w.ASCIIMode=False;w.Write(s,str(F/"7semi-all-source.stl"))
while e.More():
 a=e.Current();assert BRepCheck_Analyzer(a).IsValid();b=Bnd_Box();BRepBndLib.AddOptimal_s(a,b,False,False);f=F/('7semi-native-%02d.stl'%len(out));BRepMesh_IncrementalMesh(a,.02,False,.1,True).Perform();w=StlAPI_Writer();w.ASCIIMode=False;assert w.Write(a,str(f));out.append({'id':len(out),'boundsMm':list(b.Get()),'file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()});e.Next()
(F/'7semi-native-bounds.json').write_text(json.dumps({'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'solids':out},indent=2)+'\n');print(json.dumps(out,indent=2))

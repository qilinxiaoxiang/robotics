from pathlib import Path
import json,hashlib
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence,TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.TopLoc import TopLoc_Location
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRepTools import BRepTools
from OCP.BRepCheck import BRepCheck_Analyzer
D=Path(__file__).resolve().parent;R=D.parents[1];SIM=R.parents[1];P=SIM/'hardware-design-20260912/reference/microduck/cad/microduck.step'
doc=TDocStd_Document(TCollection_ExtendedString('source'));r=STEPCAFControl_Reader();r.SetNameMode(True);assert r.ReadFile(str(P))==IFSelect_RetDone;assert r.Transfer(doc)
tool=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main());roots=TDF_LabelSequence();tool.GetFreeShapes(roots);rows=[];assemblies=[];(D/'source-brep').mkdir(exist_ok=True)
def name(l):
 a=TDataStd_Name();return a.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(),a) else '(unnamed)'
def matrix(loc):
 t=loc.Transformation();return [[t.Value(i,j) for j in range(1,5)] for i in range(1,4)]+[[0,0,0,1]]
def walk(label,parent,path):
 ref=TDF_Label();isref=tool.GetReferredShape_s(label,ref);ref=ref if isref else label
 loc=parent.Multiplied(tool.GetLocation_s(label));n=name(label);rn=name(ref);current=path+[n];children=TDF_LabelSequence()
 if tool.GetComponents_s(ref,children):
  assemblies.append({'path':current,'name':n,'referenceName':rn,'transform':matrix(loc),'children':children.Length()})
  for i in range(1,children.Length()+1):walk(children.Value(i),loc,current)
 else:
  s=tool.GetShape_s(ref).Moved(loc);b=Bnd_Box();BRepBndLib.Add_s(s,b);p=GProp_GProps();BRepGProp.VolumeProperties_s(s,p);i=len(rows);out=D/'source-brep'/f'{i:03}.brep';BRepTools.Write_s(s,str(out));rows.append({'index':i,'path':current,'name':n,'referenceName':rn,'transform':matrix(loc),'bounds':list(b.Get()),'volumeMm3':p.Mass(),'centerOfMass':[p.CentreOfMass().X(),p.CentreOfMass().Y(),p.CentreOfMass().Z()],'valid':BRepCheck_Analyzer(s).IsValid(),'brep':str(out)})
for i in range(1,roots.Length()+1):walk(roots.Value(i),TopLoc_Location(),[])
report={'source':str(P),'sourceSha256':hashlib.sha256(P.read_bytes()).hexdigest(),'sourceFileUnits':'STEP reader normalized mm (to be crosschecked against34mm XL330 body)','rootCount':roots.Length(),'assemblies':assemblies,'leaves':rows,'sourceCoordinateRegistrationVerified':False}
(D/'source-inventory.json').write_text(json.dumps(report,indent=2)+'\n');print('ROOTS',roots.Length(),'ASSEMBLIES',len(assemblies),'LEAVES',len(rows));print([(x['index'],x['referenceName'],[round(t,3)for t in x['bounds']]) for x in rows if not any(s in x['referenceName'].lower() for s in ['stp','screw','bts','xl330','washer'])])

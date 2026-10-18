"""Closest removed material to actual mounting axes; no structural strength claim."""
import argparse,json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;O=D/'yaw-structural-channel';ap=argparse.ArgumentParser();ap.add_argument('--pose',type=int,required=True);ap.add_argument('--part',required=True);a=ap.parse_args();rfile=O/f'{a.pose}__{a.part}.json';r=json.loads(rfile.read_text());f=Path(r['hit']['file']);assert c.sha(f)==r['hit']['sha256'];m=trimesh.load(f,force='mesh');assert m.is_watertight and m.is_volume;s=mf.Manifold(mf.Mesh(np.array(m.vertices,np.float32),np.array(m.faces,np.uint32)));assert s.status()==mf.Error.NoError and s.volume()>0;rows=[]
for p in r['protectedRegions']:
 if 'centerWorld' not in p:continue
 x,y,z=p['centerWorld'];line=mf.Manifold.cylinder(40,.001,.001,12).translate([x,y,95]);gap=line.min_gap(s,8);rows.append({'id':p['id'],'axisToRemovedMaterialDistanceLowerBoundMm':float(gap),'distanceMayBeCappedAt8Mm':gap>=8-1e-8,'guidePilotRadiusMm':1.1,'radialNativeWallNotRemovedLowerBoundMm':float(gap)-1.1,'headNominalRadiusMm':2,'headPerimeterRadialMarginLowerBoundMm':float(gap)-2,'caution':'Lower bound to removed material alongfullZ95..135 axis; does not establish material originallyfilled cylinder, bridges to outer shell, load capacity or print strength.'})
out={'accepted':False,'pose':a.pose,'part':a.part,'rows':rows,'sourceHashes':{str(p):c.sha(p) for p in [Path(__file__),rfile,f]}};c.save(O/f'{a.pose}__{a.part}__post-clearance.json',out);print(json.dumps(out))

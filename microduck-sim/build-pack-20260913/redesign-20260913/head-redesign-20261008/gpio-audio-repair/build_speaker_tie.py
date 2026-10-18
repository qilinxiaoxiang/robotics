"""Dimensioned receiving tie and local saddle underside clearance; not stock certification."""
import json,math
from pathlib import Path
import bounded_amp_check as c
import precision_mesh as pm
D=Path(__file__).resolve().parent;O=D/'speaker-rewire';c.guarded_import();x=34.8;cy=-23.25;cz=138.505;hy=4.25;hz=1.98;r=1.;pts=[]
for yy,zz,a0 in [(cy+hy-r,cz+hz-r,0),(cy-hy+r,cz+hz-r,90),(cy-hy+r,cz-hz+r,180),(cy+hy-r,cz-hz+r,270)]:
 for j in range(17):
  a=math.radians(a0+j*90/16);pts.append([yy+r*math.cos(a),zz+r*math.sin(a)])
# Curve order starts right, top, left, bottom; corner centers above produce CCW loop.
verts=[];faces=[]
for i,p in enumerate(pts):
 tangent=c.np.array(pts[(i+1)%len(pts)])-c.np.array(pts[(i-1)%len(pts)]);tangent/=c.np.linalg.norm(tangent);normal=c.np.array([tangent[1],-tangent[0]])
 for xx,rad in [(-1.25,-.5),(1.25,-.5),(1.25,.5),(-1.25,.5)]:verts.append([x+xx,p[0]+normal[0]*rad,p[1]+normal[1]*rad])
for i in range(len(pts)):
 for j in range(4):
  a=4*i+j;b=4*i+(j+1)%4;dd=4*((i+1)%len(pts))+j;cc=4*((i+1)%len(pts))+(j+1)%4;faces.extend([[a,b,cc],[a,cc,dd]])
m=c.tm.Trimesh(verts,faces,process=True)
if m.volume<0:m.invert()
assert m.is_watertight;band=c.mf.Manifold(c.mf.Mesh64(c.np.asarray(m.vertices),c.np.asarray(m.faces,c.np.uint64)));assert band.status()==c.mf.Error.NoError
head=c.mf.Manifold.cube([4.6,5,3.8],True).translate([x,-29.8,137.2]);tie=band+head;tf=O/'speaker-tie-receiving-world.stl';pm.export(c,tie,tf)
oldf=O/'speaker-pair-roof-saddle-world.stl';old=pm.load(c,oldf);removed=old^c.mf.Manifold.cube([10,10,40]).translate([x-5,cy-5,97.135]);new=old-removed;sf=O/'speaker-pair-roof-saddle-tie-clearance-world.stl';pm.export(c,new,sf)
r={'integrationReady':False,'tieSource':'../tie-source-dimensions.json','strapReceivingMm':[2.5,1],'headReceivingMm':[4.6,5,3.8],'analyticCornerCenterRadiusMm':1,'headPlacementWorldMm':[x,-29.8,137.2],'newSaddleAddedMm3':max(0,float((new-old).volume())),'newSaddleRemovedMm3':max(0,float(removed.volume())),'tieVsSaddleMm3':max(0,float((tie^new).volume())),'inputHashes':c.fingerprint([Path(__file__),D/'tie-source-dimensions.json',oldf]),'outputs':{str(f):c.sha(f) for f in [tf,sf]},'scope':'Band/head receiving body; contact with installed wire insulation is intentional retention interface. Stock and tightening force remain physical gates. Thread free tail through slot before fitting the prewired pair; head stays outside slot.'};c.atomic_json(O/'speaker-tie-receiving.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ['inputHashes','outputs']}))

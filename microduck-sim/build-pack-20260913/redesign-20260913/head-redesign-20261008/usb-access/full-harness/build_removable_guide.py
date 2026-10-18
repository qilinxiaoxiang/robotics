"""Optional removable guide on existing rear cap screw; no new shell holes."""
from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_harness.py').read_text().split('# PUBLISHED_CONNECTOR_FROM_SOURCE_SHOULDER')[0])
r=json.loads((D/'full-harness-report.json').read_text());points=np.array(r['geometry']['acCenterlineMm']);# vertical rear-side leg
idx=int(np.argmin(np.linalg.norm(points-[-48,30,157],axis=1)));cc=points[idx].copy();cc[2]=157
# Guide at known straight vertical segment; its receiving bore is4.8mm, against
# published4.5mm cable. Frictional strain relief is not claimed from geometry.
def cyl(a,b,r):
 a=np.array(a,float);b=np.array(b,float);T=trimesh.geometry.align_vectors([0,0,1],b-a);T[:3,3]=(a+b)/2;return man(trimesh.creation.cylinder(radius=r,height=np.linalg.norm(b-a),sections=40).apply_transform(T))
def bx(c,d):return man(box(c,d))
ring=cyl(cc-[0,0,3],cc+[0,0,3],4.5)-cyl(cc-[0,0,4],cc+[0,0,4],2.4)
for dy in [-5.5,5.5]:ring+=cyl(cc+[-4.5,dy,0],cc+[4.5,dy,0],2.2)
body=ring^bx(cc+[5,0,0],[10,30,20]);cover=ring^bx(cc+[-5.2,0,0],[10,30,20])
for dy in [-5.5,5.5]:
 body-=cyl(cc+[-1,dy,0],cc+[5,dy,0],.8);cover-=cyl(cc+[-6,dy,0],cc+[0,dy,0],1.1)
seat=np.array([-23.4,0,112.311]);base=(bx([-30.7,0,97.311],[14.6,6,2])+cyl(seat-[0,0,16],seat-[0,0,14],3)+cyl(seat-[0,0,14],seat,1.9))-cyl(seat-[0,0,18],seat+[0,0,2],1.4)
path=np.array([[-38,0,97.311],[-41,0,116],[-43,cc[1]+5.5,120],[-43,cc[1]+5.5,157]])
arm=base
for a,b in zip(path,path[1:]):arm+=cyl(a,b,2.2)+man(trimesh.creation.icosphere(subdivisions=2,radius=2.2).apply_translation(a))
arm+=man(trimesh.creation.icosphere(subdivisions=2,radius=2.2).apply_translation(path[-1]));body+=arm
out={};parts={'removable_rear_cable_guide':body,'removable_rear_cable_guide_cover':cover}
for k,p in parts.items():
 out[k]={n:hits(p,o) for n,o in obs.items() if hits(p,o)>1e-4};tri(p).export(D/(k+'-world.stl'))
print(json.dumps({'center':cc.tolist(),'staticCollisions':out,'bodyCount':len(body.decompose()),'coverCount':len(cover.decompose())}),flush=True)
(D/'removable-guide-investigation.json').write_text(json.dumps({'status':'optional-guide-candidate','clipCenterWorldMm':cc.tolist(),'staticIntersectionsMm3':out,'mount':'Existing rear cap screw; replaceM2.5x8 withM2.5x25 through added16mm base/spacer stack; tip1mm deeper than oldM2.5x8 and must be independently checked','retention':'TwoM2x8tapping closure screws.4.8mm receiving bore for4.5mm cable prevents lateral movement; axial frictional strainrelief is NOT verified.','bodyConnectedComponents':len(body.decompose()),'coverConnectedComponents':len(cover.decompose()),'physicalFitVerified':False},indent=2)+'\n')

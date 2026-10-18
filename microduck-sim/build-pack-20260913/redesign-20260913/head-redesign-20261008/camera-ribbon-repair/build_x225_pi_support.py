"""Independent +2.25X Pi support and shifted bottom receiver; no published mutations."""
from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(D/'build_reverse_nut_camera.py')
face=load(O/'face_three_screw_camera-world.stl');oldFace=face;cap=load(H/'usb-access/usb-repair/cap-usb-positive-x225-world.stl');pose=json.loads(read(D/'positive-x225-pose.json'));T=np.array(pose['worldTransform']);normal=T[:3,0];rows=json.loads(read(D/'head-source-cache/head-screws.json'));pilots=mf.Manifold();hardware={};details=[]
def cylinder(a,d,length,r):
 d=np.asarray(d)/np.linalg.norm(d);u=np.cross(d,[0,0,1.]);u/=np.linalg.norm(u);v=np.cross(d,u);return mf.Manifold.cylinder(length,r,circular_segments=48).transform(np.column_stack([u,v,d,a]))
for i,sc in enumerate(rows):
 a=(T@np.r_[sc['world_center_mm'],1])[:3];b=a+normal*1.6;length=(80.9-b[0])/normal[0]
 if i==2:
  M=np.column_stack([T[:3,:3],a]);pad=cylinder(b,normal,1.,2.5);rib=mf.Manifold.cube([1.,5.8,3.]).translate([1.6,0,-1.5]).transform(M);bridge=mf.Manifold.cube([(80.9-a[0])/normal[0]-2.1,3,3]).translate([2.1,4.3,-1.5]).transform(M);face+=pad+rib+bridge;continue
 face+=cylinder(b,normal,length,3);pilots+=cylinder(b-normal*.01,normal,4.86,1.05);hardware[sc['id']]=cylinder(a-normal*.01,normal,6.01,1.25)+cylinder(a,-normal,1.5,2)
 details.append({'id':sc['id'],'headSeatMm':a.tolist(),'spec':'M2.5 x 6 TAP','printedEngagementMm':4.4,'pilotDepthMm':4.85,'pilotTipMarginMm':.45,'postLengthMm':length,'outwardAxis':(-normal).tolist()})
face-=pilots
# Preserve pre-existing face; only trim added Pi stock against the cap receiving clearance.
cut=cap+cap.translate([0,.3,0]);face-=cut-oldFace
bottomOld=n['source']('head_bottom');x0,x1,y0,y1,r,z0,z1=60.15,73.65,-35.8,-5.,.6,108.,114.
cut=box([x0+r,y0,z0],[x1-r,y1,z1])+box([x0,y0+r,z0],[x1,y1-r,z1])
for x in [x0+r,x1-r]:
 for y in [y0+r,y1-r]:cut+=mf.Manifold.cylinder(z1-z0,r,circular_segments=48).translate([x,y,z0])
bottom=bottomOld-cut;exports={'face_panel':export(face,'face_x225_complete'),'head_bottom':export(bottom,'head_bottom_x225_receiver')}
for k,s in hardware.items():exports[k]=export(s,k+'_x225')
checks=[];coreChecks=[]
for row in details:
 a=np.array(row['headSeatMm'])+normal*1.6;core=cylinder(a,normal,4.85,2.25)-cylinder(a-normal*.01,normal,4.87,1.05);coreChecks.append({'id':row['id'],'requiredRadialMaterialMm':1.2,'missingMaterialMm3':max(0,(core-face).volume())})
obstacles=json.loads(read(O/'pi-geometry-manifest.json'))['parts']+[{'key':k,'mesh':str((O/f).relative_to(H))} for k,f in [('camera','camera_board_clamped-world.stl'),('clamp','camera_three_screw_clamp-world.stl'),('eye','eye_three_screw_camera-world.stl')]]
for row in obstacles:
 q=load(H/row['mesh'])
 for k,s in [('face',face),('bottom',bottom)]:
  v,bb=n['volume'](s,q);checks.append({'part':k,'obstacle':row['key'],'overlapMm3':v,'boundsMm':bb})
 del q;gc.collect()
for k,q in [('face',face),('bottom',bottom)]:
 v,bb=n['volume'](q,cap);checks.append({'part':k,'obstacle':'cap','overlapMm3':v,'boundsMm':bb})
report={'integrationReady':False,'scope':'Pi supports and bottom receiver only; complete routes and full cable pending','exports':exports,'screws':details,'piFastenedIds':['E-pi-01','E-pi-02','E-pi-04'],'passiveSupportedId':'E-pi-03','fourthScrewMeaning':'Only original ID04 is installed; total three Pi screws, never four.','candidateFaceBodies':len(face.decompose()),'candidateBottomBodies':len(bottom.decompose()),'coreChecks':coreChecks,'windowBoundsMm':[x0,y0,z0,x1,y1,z1],'primarySupportMaxXBoundMm':52.3,'minimumWindowXSeparationToPrimarySupportMm':x0-52.3,'sourceBottomRemovedVolumeMm3':max(0,(bottomOld-bottom).volume()),'checks':checks,'sourceHashes':n['hashes'],'physicalStrengthVerified':False};(O/'pi-support-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'faceBodies':report['candidateFaceBodies'],'bottomBodies':report['candidateBottomBodies'],'coreChecks':coreChecks,'hits':[x for x in checks if x['overlapMm3']>1e-5]},indent=2))

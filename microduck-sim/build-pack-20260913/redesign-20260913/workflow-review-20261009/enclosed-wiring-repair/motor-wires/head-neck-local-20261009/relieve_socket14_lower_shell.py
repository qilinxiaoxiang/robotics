from check_local import *
plan=json.loads((D/'plan.json').read_text());o=next(q for q in plan['obstacles']if q['key']=='REFERENCE fixed head head_bottom');m=load(o);base=solid(m)
port=plan['ports']['motor-14-socket-13'];lo,hi=np.array(port['housingLocalBounds']);env=trimesh.creation.box(hi-lo);env.apply_translation((lo+hi)/2);env.apply_transform(port['transform']);elo,ehi=env.bounds;clo,chi=elo-.4,ehi+.4
cutter=trimesh.creation.box(chi-clo);cutter.apply_translation((clo+chi)/2);cut=solid(cutter);out=base-cut;removed=base^cut
assert out.status()==mf.Error.NoError and out.volume()>0
mesh=out.to_mesh64();n=trimesh.Trimesh(vertices=mesh.vert_properties[:,:3],faces=mesh.tri_verts,process=False)
f=D/'head-bottom-eh14-clearance-world.stl'
with f.open('w')as h:
 h.write('solid head_bottom_eh14_clearance\n')
 for face in n.triangles:
  h.write(' facet normal 0 0 0\n  outer loop\n')
  for v in face:h.write('   vertex '+' '.join(format(float(x),'.17g')for x in v)+'\n')
  h.write('  endloop\n endfacet\n')
 h.write('endsolid head_bottom_eh14_clearance\n')
read=trimesh.load_mesh(f,process=True);assert read.is_volume;rt=solid(read)
assert (rt^solid(env)).volume()<1e-7
# Clip lower-facing source triangles to the clearance footprint, retaining their exact plane.
def clip(poly,axis,value,sgn):
 res=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  da=sgn*(a[axis]-value);db=sgn*(b[axis]-value)
  if da>=-1e-12:res.append(a)
  if (da>=0)!=(db>=0):res.append(a+(b-a)*(da/(da-db)))
 return res
skin=[]
for tri,no in zip(m.triangles,m.face_normals):
 if no[2]>=-1e-5 or tri[:,2].min()>clo[2]:continue
 poly=list(tri)
 for ax,val,sgn in [(0,clo[0],1),(0,chi[0],-1),(1,clo[1],1),(1,chi[1],-1)]:
  if poly:poly=clip(poly,ax,val,sgn)
 if len(poly)<3:continue
 ar=abs(sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(poly,poly[1:]+poly[:1])))/2
 if ar<1e-8:continue
 gap=clo[2]-max(x[2]for x in poly)
 if gap>0:skin.append({'verticalMaterialBelowCutFloorMm':gap,'normalProjectionMm':gap*abs(float(no[2])),'planeNormal':no.tolist(),'clippedXYAreaMm2':ar})
assert skin
G=E.parents[1]/'leg-guide-20261006/full-build-data.json';g=json.loads(G.read_text());near=[]
for s in g['screws']:
 a=np.array(s['world_center_mm']);axis=np.array(s['world_axis']);b=a-axis*s['length_mm'];ss=np.linspace(a,b,51);ds=np.linalg.norm(np.maximum(clo-ss,0)+np.maximum(ss-chi,0),axis=1);near.append({'id':s['id'],'partKey':s.get('partKey'),'minimumSampledAxisDistanceToClearanceBoxMm':float(min(ds)),'sampleSpacingUpperMm':s['length_mm']/50})
assert removed.bounding_box()[2]>101.5
assert np.allclose(m.bounds,read.bounds,atol=1e-8,rtol=0)
for q in near:q['conservativeAxisDistanceLowerMm']=max(0,q['minimumSampledAxisDistanceToClearanceBoxMm']-q['sampleSpacingUpperMm']/2)
near.sort(key=lambda q:q['minimumSampledAxisDistanceToClearanceBoxMm']);added=(rt-base).volume();assert added<1e-7
report={'passed':True,'scope':'Local internal rib-top clearance subtraction. Bottom floor below Z101.5 and overall part bounds are unchanged; no strength or printed-tolerance certification.','source':o,'output':{'file':str(f),'sha256':sha(f),'closedPositiveVolume':read.is_volume,'solidBodyCount':len(out.decompose())},'receivingBodyBoundsMm':env.bounds.tolist(),'clearanceEachAxisMm':.4,'cuttingToolBoundsMm':[clo.tolist(),chi.tolist()],'removedMaterialMm3':removed.volume(),'removedBoundsMm':list(removed.bounding_box()),'newMaterialOutsideSourceMm3':added,'originalHousingIntersectionMm3':(base^solid(env)).volume(),'repairedHousingIntersectionMm3':(rt^solid(env)).volume(),'clearanceToolResidualIntersectionMm3':(rt^cut).volume(),'minimumResidualRibAndFloorVerticalMm':min(q['verticalMaterialBelowCutFloorMm']for q in skin),'minimumResidualRibAndFloorProjectionMm':min(q['normalProjectionMm']for q in skin),'skinTriangleCount':len(skin),'skinMethod':'All lower-facing source triangle planes clipped against the XY clearance footprint. The reported 6 mm dimension includes the remaining internal rib plus bottom floor; it is not the sheet wall thickness or a strength calculation.', 'unchangedBelowWorldZMm':101.5, 'minimumRemovedWorldZMm':float(removed.bounding_box()[2]), 'sourceBoundsMm':m.bounds.tolist(), 'repairedBoundsMm':read.bounds.tolist(), 'overallBoundsUnchanged':bool(np.allclose(m.bounds,read.bounds,atol=1e-8,rtol=0)),'nearestExistingScrewAxes':near[:6],'sourceHashes':{str(D/'plan.json'):sha(D/'plan.json'),o['file']:o['sha256'],str(G):sha(G),str(Path(__file__)):sha(__file__)},'existingPrintedPart':'If the original part already accepts the actual plug freely, this revised internal relief is not an instruction to replace it. New-build receiver has explicit 0.4 mm catalogue-box clearance.'}
(D/'head-bottom-clearance-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k in ['removedMaterialMm3','removedBoundsMm','minimumLocalVerticalSkinMm','minimumLocalPlaneNormalProjectionMm','nearestExistingScrewAxes','output']},indent=2))

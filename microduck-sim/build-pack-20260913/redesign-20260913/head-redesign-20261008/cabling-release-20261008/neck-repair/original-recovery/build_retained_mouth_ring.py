from pathlib import Path
exec((Path(__file__).parent/'check_mouth_ring.py').read_text().split("report={'accepted'")[0])
R=ring(10.4,14.4,2.1,-39.6)+ring(12.4,16.4,.3,-39.9)
report={'accepted':False,'dimensionsMm':{'sleeveID':10.4,'sleeveOD':14.4,'sleeveThickness':2.1,'sleeveStartY':-39.6,'flangeOD':16.4,'flangeThickness':.3,'backFlangeID':12.4,'backFlangeStartY':-39.9,'frontFlange':False},'static':{},'routes':{}}
fixed={'support':S,'jaw':J,'pad':P,'motor15':M,'V1_bottom':V}
for k,s in fixed.items():
 it=R^s;m=it.to_mesh64();v=np.asarray(m.vert_properties)[:,:3];report['static'][k]={'intersection':it.volume(),'gap':R.min_gap(s,1),'bounds':None if not len(v) else [v.min(0).tolist(),v.max(0).tolist()]}
exec('def scan('+(D/'check_mouth_ring.py').read_text().split('def scan(')[1].split("scan('ring_over")[0])
scan('ring_on_loose_jaw',{'ring':R},{'jaw':J},[0,30,0])
scan('support_down_onto_ring_jaw',{'support':S},{'jaw':J,'ring':R,'motor15':M,'V1_bottom':V},[0,0,30])
report['retention']={}
for sign in [-1,1]:
 hits=[]
 for d in np.linspace(0,.8,17):
  vols={k:(R.translate([0,sign*d,0])^s).volume() for k,s in fixed.items()};v={k:q for k,q in vols.items() if q>1e-7}
  if v:hits.append({'d':float(sign*d),'contacts':v})
 report['retention'][str(sign)]=hits[:2]

# The ring stays in the support while the original jaw rotates about its own axis.
pivot=np.array([26.1,0,118.6146]);motion=[]
for a in np.linspace(0,45,91):
 j=J.translate(-pivot).rotate([0,float(a),0]).translate(pivot)
 it=R^j;assert it.status()==mf.Error.NoError;motion.append({'jawDegrees':float(a),'intersectionMm3':it.volume(),'gapSearch1Mm':R.min_gap(j,1)})
report['ringJawRotation']={'expected':91,'completed':len(motion),'anglesDegrees':[0,45],'maxIntersectionMm3':max(q['intersectionMm3'] for q in motion),'minimumGapMm':min(q['gapSearch1Mm'] for q in motion)}
report['digitalLocalInterfacePassed']=all(q['intersection']<1e-7 for q in report['static'].values()) and all(not q['peakMm3'] for q in report['routes'].values()) and report['ringJawRotation']['maxIntersectionMm3']<1e-7 and all(report['retention'][k] for k in ['-1','1'])
assert report['digitalLocalInterfacePassed']
report['acceptedCompleteAssembly']=False;report['physicalFitVerified']=False
report['boundary']=['Only this ring interface, its loose-jaw insertion and original-support drop-in are accepted digitally. The original one-piece jaw seating into the V1 head-bottom has not been proved by a rigid path. No PLA splay or strength acceptance is inferred.','Minimum nominal assembly gap is about0.094mm radially to V1 bottom, and0.10mm axially at each rear flange face. Printing error is not covered. Check ring freedom without forcing or tightening the support to pull it into place.','Ring axial flange is0.3mm. Preserve it in slicing; confirm it is not omitted. It is a retaining feature, not a load-rated thrust bearing.','AI-FanGe video9:14 indicates the head-roll large ring, not evidence for a mouth ring SKU. This is one new dimension-matched sliding ring; original jaw/support/pad are unchanged.']
report['exports']={}
for name,s in [('mouth-ring-retained-world.stl',R),('mouth-ring-retained-print.stl',R.translate([-26.1,39.9,-118.6146]).rotate([90,0,0]))]:
 m=s.to_mesh64();t=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False);assert t.is_watertight and t.is_volume;p=D/name;p.write_text(trimesh.exchange.stl.export_stl_ascii(t));r=trimesh.load(p,force='mesh');assert r.is_watertight and r.is_volume and len(r.split())==1
 report['exports'][name]={'sha256':c.sha(p),'singleClosedBody':True,'boundsMm':r.bounds.tolist(),'volumeMm3':float(r.volume)}
inputs += [D/'check_mouth_ring.py',D.parent/'short_path_worker.py',D/'ear-splay-diagnostic.json',D/'mouth-ring-v1-report.json']
report['sourceHashes']={str(p.resolve()):c.sha(p) for p in inputs};c.save(D/'mouth-ring-retained-report.json',report)
manifest={'partKey':'mouth_sliding_ring','name':'Separate mouth sliding ring with rear retaining flange','quantity':1,'color':'Black','sourceCommunityId':None,'sourceRole':'New ring matched to original community support24 and original jaw4; not a replacement body','printMesh':'mouth-ring-retained-print.stl','worldMesh':'mouth-ring-retained-world.stl','report':'mouth-ring-retained-report.json','reportSha256':c.sha(D/'mouth-ring-retained-report.json'),'printSha256':report['exports']['mouth-ring-retained-print.stl']['sha256'],'worldSha256':report['exports']['mouth-ring-retained-world.stl']['sha256'],'digitalLocalInterfacePassed':True,'acceptedCompleteAssembly':False,'physicalFitVerified':False,'printOrientation':'Already flat with wide rear flange on bed; centeredXY, Z0. No rotation required.','boundsMm':report['exports']['mouth-ring-retained-print.stl']['boundsMm'],'requiredSliceFeature':'Retain0.3mm flange; use0.10mm or0.15mm layers. Flat flange down; vertical bore and2.4mm total height.'}
c.save(D/'mouth-ring-print-manifest.json',manifest);print(json.dumps(manifest))

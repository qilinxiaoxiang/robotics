from pathlib import Path
exec((Path(__file__).parent/'check_mouth_ring.py').read_text().split("report={'accepted'")[0])
R=ring(10.4,14.4,2.4,-39.55)
report={'acceptedCompleteAssembly':False,'partStatus':'separate-mouth-ring-fit-candidate','dimensionsMm':{'innerDiameter':10.4,'outerDiameter':14.4,'thickness':2.4,'axis':[0,1,0],'start':[26.1,-39.55,118.6146]},'static':{},'routes':{}}
fixed={'support':S,'jaw':J,'pad':P,'motor15':M,'bottom_v1':V}
for k,s in fixed.items():report['static'][k]={'intersectionMm3':(R^s).volume(),'minGapSearch2Mm':R.min_gap(s,2)}
exec('def scan('+(D/'check_mouth_ring.py').read_text().split('def scan(')[1].split("scan('ring_over")[0])
scan('ring_onto_loose_jaw_before_shell',{'ring':R},{'jaw':J},[0,30,0])
scan('original_support_from_above',{'support':S},{'jaw':J,'ring':R,'motor15':M,'bottom_v1':V},[0,0,30])
report['retentionAxial']={}
for sign in [-1,1]:
 rows=[]
 for d in np.linspace(0,5,101):
  vols={k:(R.translate([0,sign*d,0])^s).volume() for k,s in fixed.items()};hits={k:v for k,v in vols.items() if v>1e-7}
  if hits:rows.append({'offsetMm':float(d*sign),'hits':hits})
 report['retentionAxial'][str(sign)]={'firstContact':rows[0] if rows else None,'lastContact':rows[-1] if rows else None}
report['exports']={}
for name,s in [('mouth-ring-v1-world.stl',R),('mouth-ring-v1-print.stl',R.translate([-26.1,39.55,-118.6146]).rotate([90,0,0]))]:
 m=s.to_mesh64();t=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False);p=D/name;p.write_text(trimesh.exchange.stl.export_stl_ascii(t));read=trimesh.load(p,force='mesh');assert read.is_watertight and read.is_volume and len(read.split())==1;report['exports'][name]={'sha256':c.sha(p),'closedSingleBody':True,'volumeMm3':read.volume,'boundsMm':read.bounds.tolist()}
report['boundaries']=['Original jaw-to-bottom seating is not rigid-path accepted; finite selected routes fail near original hinge ears. No body split or undocumented elastic acceptance is authorized by this part fit report.','This is a new dimension-matched sliding ring, not proof of a third community source ring or purchased bearing.','Video 9:14 identifies head-roll large ring; it does not establish mouth ring dimensions.']
report['sourceHashes']={str(p.resolve()):c.sha(p) for p in inputs};c.save(D/'mouth-ring-v1-report.json',report);print(json.dumps(report))

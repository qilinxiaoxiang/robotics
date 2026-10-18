"""Independent readback of exported geometry, colors, screws and native foot interface."""
from pathlib import Path
import json,sys,base64,hashlib,re,gzip
import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent
SIM=HERE.parents[2]
d=json.loads((HERE/'leg-data.json').read_text())
assert d['side']=='left' and len(d['parts'])==19
assert len(d['screws'])==35
assert d['screwTotals']=={'M2 x 6 TAP':13,'M2 x 5 TAP':4,'M2 x 4 TAP':4,'M2 x 8 TAP':8,'M2 x 10 TAP':2,'M2.6 x 6 TAP':3,'M2.6 x 8 TAP':1}
assert sum(bool(c.get('washer_mm')) for c in d['screws'])==2
assert sum(c['stage']==1 for c in d['screws'])==6
assert sum(c['stage']==2 for c in d['screws'])==12
assert sum(c['stage']==3 for c in d['screws'])==13
assert sum(c['stage']==4 for c in d['screws'])==4
base=json.loads((HERE.parent/'assembly-fasteners.json').read_text())
original={c['id']:c for c in base['connections']}
for c in d['screws']:
    if c['id']=='left-foot-retainer':continue
    src=original[c['id']]
    for field in ['spec','length_mm','world_center_mm','world_axis','washer_mm','source_ids']:
        assert c[field]==src[field],(c['id'],field)
for name,expected in d['sourceHashes'].items():
    assert hashlib.sha256((SIM/name).read_bytes()).hexdigest()==expected,name

print_groups=json.loads((HERE/'sources/print-colors.json').read_text())['instances']
group_color={'old-orange-plate1':'Orange','orange':'Orange','yellow':'Yellow','black':'Black','old-black-plate5':'Black','WHITE':'White'}
meshes={}
parts={p['key']:p for p in d['parts']}
for p in d['parts']:
    v=np.frombuffer(base64.b64decode(p['positionB64']),dtype='<f4').reshape(-1,3)
    f=np.frombuffer(base64.b64decode(p['indexB64']),dtype='<u4').reshape(-1,3)
    assert np.isfinite(v).all() and f.max()<len(v) and len(f)==p['triangles']
    m=trimesh.Trimesh(v,f,process=False)
    assert np.allclose(m.bounds,np.array(p['bounds']),atol=1e-4)
    meshes[p['key']]=m
    if p['sourceId'] is not None:
        candidates=[r for r in print_groups if re.search(r'community-'+str(p['sourceId'])+r'\.stl$',r['file'])]
        if p['sourceId']==53 and not candidates:
            candidates=[r for r in print_groups if 'community-87.stl' in r['file']]
        assert candidates and group_color[candidates[0]['reference_group']]==p['colorName'],p['key']
assert parts['thigh']['sourceId']==74 and parts['ankle']['sourceId']==66 and parts['foot']['sourceId']==44
for sid in [6,9]:
    p=parts[f'washer{sid}'];c=next(c for c in d['screws'] if c['id']==p['fastenerId'])
    axis=np.array(c['world_axis']);center=np.array(p['center']);seat=np.array(c['world_center_mm'])
    assert p['geometryKind']=='specified-fastener-envelope' and p['colorName']=='Metal'
    assert np.linalg.norm(center-(seat+.25*axis))<1e-5
    v=np.asarray(meshes[p['key']].vertices);relative=v-seat
    axial=relative@axis;radius=np.linalg.norm(relative-np.outer(axial,axis),axis=1)
    assert np.allclose([axial.min(),axial.max()],[0,.5],atol=1e-4)
    assert np.allclose([radius.min(),radius.max()],[1.35,2.5],atol=1e-4)

# Re-read source meshes, and intersect rays through the RETAINING hole annuli,
# not the empty axis, to recover actual head seats/pilot entry/blind bottom.
A=SIM/'build-pack-20260913/assembly'
ns={'__file__':str(A/'prepare_geometry.py')}
exec((A/'prepare_geometry.py').read_text().split('rows=[]')[0],ns)
native44=ns['mesh']('3D/3dmodel.model','44')
native66=ns['mesh']('3D/3dmodel.model','66')
def intersections(m,x,z):
    loc,_,_=m.ray.intersects_location([[x,-40,z]],[[0,1,0]],multiple_hits=True)
    return np.unique(np.round(loc[:,1],5))
foot_shell=intersections(native44,10.5+.85,0)
foot_void=intersections(native44,10.5+.65,0)
foot_mating=intersections(native44,10.5+1.5,0)
ankle_seat=intersections(native66,13.91+1.5,.11)
assert np.any(np.isclose(foot_shell,.453,.006)) and np.any(np.isclose(foot_shell,5.453,.006)),foot_shell
assert np.any(np.isclose(foot_mating,5.953,.006)),foot_mating
assert all(y<0 for y in foot_void),foot_void  # Pilot opens into foot cavity, not a blind bottom.
assert np.any(np.isclose(ankle_seat,-4.57,.01)),ankle_seat
assert np.any(np.isclose(ankle_seat,-6.07,.01)),ankle_seat
T44=np.array(parts['foot']['sourceTransformWorld']);T66=np.array(parts['ankle']['sourceTransformWorld'])
axis44=(T44@np.array([10.5,0,0,1]))[:3]
axis66=(T66@np.array([13.91,0,.11,1]))[:3]
axis=T66[:3,:3]@np.array([0,1,0])
radial=(axis44-axis66)-axis*np.dot(axis44-axis66,axis)
assert np.linalg.norm(radial)<.001,np.linalg.norm(radial)
foot_top=(T44@np.array([10.5,5.953,0,1]))[:3]
ankle_bottom=(T66@np.array([13.91,-6.07,.11,1]))[:3]
assert np.linalg.norm(foot_top-ankle_bottom)<.001
head=(T66@np.array([13.91,-4.57,.11,1]))[:3]
entry=(T44@np.array([10.5,5.453,0,1]))[:3]
bottom=(T44@np.array([10.5,.453,0,1]))[:3]
head_stack=np.linalg.norm(head-entry)
blind_depth=np.linalg.norm(entry-bottom)
assert abs(head_stack-2)<.006 and abs(blind_depth-5)<.006
assert abs((6-head_stack)-4)<.006 and abs((blind_depth-(6-head_stack))-1)<.006

retainer=next(c for c in d['screws'] if c['id']=='left-foot-retainer')
assert np.dot(np.array(retainer['world_axis']),entry-head)<0, 'Insertion arrow must point into pilot, opposite outward axis'

html=(HERE/'LEFT-LEG.html').read_text()
assert '/*__APP__*/' not in html
assert '1 · Identify parts' in html and '2 · Prepare screws' in html and '3 · Assemble' in html
packed=re.search(r'const packed="([A-Za-z0-9+/=]+)";',html)
assert packed, 'Self-contained compressed geometry payload missing'
embedded=json.loads(gzip.decompress(base64.b64decode(packed.group(1))))
left_keys=set(d.get('leftPartKeys', [p['key'] for p in d['parts']]))
assert all(next(e for e in embedded['parts'] if e['key']==p['key'])['positionB64']==p['positionB64'] for p in d['parts'])
assert all(next(e for e in embedded['parts'] if e['key']==p['key'])['indexB64']==p['indexB64'] for p in d['parts'])
embedded_left_ids=set(embedded.get('leftScrewIds',[c['id'] for c in embedded['screws']]))
assert embedded_left_ids=={c['id'] for c in d['screws']}
assert 'sectionScrews().length' in html and 'Where are the washers?' in html
assert "window.LEG_GUIDE_STATE" in html and 'data-stage' in html
assert not re.search(r'<script[^>]+src=',html)
assert 'fetch(' not in (HERE/'viewer.js').read_text()
assert not d['physicalAssemblyVerified']
report={'passed':True,'geometry_meshes':19,'source_print_and_motor_meshes':17,'specified_washer_meshes':2,'triangles':sum(p['triangles'] for p in d['parts']),
        'left_sources':[74,66,44],'screws':35,'washers':2,
        'foot_interface':{'head_to_pilot_mm':round(head_stack,4),'pilot_depth_mm':round(blind_depth,4),
                          'screw_insertion_mm':round(6-head_stack,4),'remaining_pilot_before_boss_exit_mm':round(blind_depth-(6-head_stack),4),
                          'coaxial_error_mm':float(np.linalg.norm(radial))},
        'offline_inline_dependencies':True,'physical_trials':0}
(HERE/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('LEG_GUIDE_CHECK_PASS '+json.dumps(report))
from verify_ring_explanation import verify as verify_ring
ring_report=verify_ring()
assert ring_report['passed'],ring_report['errors']
print('RING_INTERFACE_CHECK_PASS '+json.dumps(ring_report['metrics']))

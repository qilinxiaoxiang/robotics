"""Independent read-only source and assembly-data review; write review JSON only.

Does not import or execute the data builder, change geometry, or launch a UI.
Rendered interactions and collision-free assembly paths have separate acceptance.
"""
from pathlib import Path
import argparse, base64, collections, gzip, hashlib, json, re, sys
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
import trimesh
from scipy.spatial import cKDTree

D=Path(__file__).resolve().parent
SIM=D.parents[2]
N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
PN='{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def matrix(s):
    t=np.eye(4)
    if s:t[:3,:]=np.array(list(map(float,s.split()))).reshape(4,3).T
    return t

def decoded(p):
    v=np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3)
    f=np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3)
    return trimesh.Trimesh(v,f,process=False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=D/'full-guide-review.json');args=ap.parse_args()
    data=json.loads((D/'full-build-data.json').read_text());left=json.loads((D/'leg-data.json').read_text())
    stockpath=SIM/'team-share-20261001/02-STL-and-Editable-Projects/STL-Instance-Manifest.json'
    stock=json.loads(stockpath.read_text())['instances'];sched=json.loads((D.parent/'assembly-fasteners.json').read_text())['connections']
    errors=[];findings=[];proof={};by={p['key']:p for p in data['parts']};sby={c['id']:c for c in data['screws']}
    def check(ok,msg):
        if not ok:errors.append(msg)
    bindings=[]
    for rel,want in data['sourceHashes'].items():
        p=SIM/rel;got=sha(p);record={'file':str(p),'expected':want,'actual':got,'matched':want==got}
        if want!=got and rel=='build-pack-20260913/redesign-20260913/assembly-fasteners.json':
            import importlib.util
            spec=importlib.util.spec_from_file_location('baseline_refresh_proof',D/'non-head-review/baseline_refresh_proof.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            try:record['exactCanonicalRebuildProof']=module.verify(want);record['matched']=True
            except AssertionError:pass
        bindings.append(record);check(record['matched'],'Stale source hash: '+rel)
    proof['sourceBindings']=bindings
    for p in left['parts']:
        q=by[p['key']];check(p['positionB64']==q['positionB64'] and p['indexB64']==q['indexB64'],'Left mesh payload changed: '+p['key'])
    check(len(by)==len(data['parts']),'Duplicate mesh keys')
    check(len(sby)==len(data['screws']),'Duplicate screw ids')
    check(sum(p.get('partKind')=='motor' for p in by.values())==15,'Motor count is not15')
    adds=collections.Counter();fastens=collections.Counter()
    for mod in data['modules']:
        for i,op in enumerate(mod['operations']):
            check(op['kind']==('place' if i%2==0 else 'fasten'),'Operation alternation: '+op['id'])
            adds.update(op['add']);fastens.update(op['screwIds'])
            check(set(op['add'])<=by.keys() and set(op['screwIds'])<=sby.keys(),'Unbound operation reference: '+op['id'])
    check(set(adds)==set(by) and set(adds.values())=={1},'Part introduction coverage is not exactly once')
    check(set(fastens)==set(sby) and set(fastens.values())=={1},'Screw operation coverage is not exactly once')
    used=[];allocation=[];groupcolor={'old-orange-plate1':'Orange','orange':'Orange','old-black-plate5':'Black','black':'Black','yellow':'Yellow','WHITE':'White'}
    for row in data['coverage']['sourceStockAllocation']:
        actual=next((s for s in stock if s['manifest_instance_index']==row['manifest_instance_index']),None);p=by[row['partKey']]
        check(actual is not None,'Stock index absent: '+row['partKey'])
        if actual is None:continue
        check(all(row[k]==actual[k] for k in ['file','sha256','reference_group']),'False stock binding: '+row['partKey'])
        source=stockpath.parent/actual['file'];check(sha(source)==actual['sha256'],'Changed stock STL: '+str(source))
        check(p['colorName']==groupcolor[actual['reference_group']],'Saved color mismatch: '+row['partKey'])
        used.append(row['manifest_instance_index']);allocation.append({'part':p['key'],'source_stock_index':row['manifest_instance_index'],'matched':True})
    check(len(used)==len(set(used)),'One physical print-stock instance assigned more than once')
    check(len(used)==sum(p['partKind']=='print' for p in by.values()),'Installed prints missing a stock binding')
    retained=[r['manifest_instance_index'] for r in data['coverage']['retainedStock']]
    stockids={r['manifest_instance_index'] for r in stock}
    check(len(retained)==len(set(retained)) and not set(used)&set(retained),'Retained stock duplicates installed stock')
    check(set(used)|set(retained)==stockids,'Installed and retained stock do not cover the actual source inventory')
    proof['stockAllocation']=allocation
    # Read native3MF components directly, without the exporting program.
    archive=zipfile.ZipFile(SIM/'Microduck-build-tutorial/microduck3D打印.3mf');cache={}
    def native(path,oid):
        key=path,oid
        if key in cache:return cache[key].copy()
        rt=ET.fromstring(archive.read(path));o=next(o for o in rt.find(N+'resources') if o.get('id')==str(oid));m=o.find(N+'mesh')
        if m is not None:
            v=[[float(q.get(k)) for k in 'xyz'] for q in m.find(N+'vertices')];f=[[int(q.get(k)) for k in ['v1','v2','v3']] for q in m.find(N+'triangles')];res=trimesh.Trimesh(v,f,process=True)
        else:res=trimesh.util.concatenate([native(q.get(PN+'path',path).lstrip('/'),q.get('objectid')).apply_transform(matrix(q.get('transform'))) for q in o.find(N+'components')])
        cache[key]=res;return res.copy()
    geometry=[]
    for p in by.values():
        mesh=decoded(p);check(np.isfinite(mesh.vertices).all() and mesh.faces.max()<len(mesh.vertices),'Invalid mesh: '+p['key']);check(np.allclose(mesh.bounds,p['bounds'],atol=2e-5),'False bounds: '+p['key'])
        if p['key'] in {q['key'] for q in left['parts']}:continue
        expected=None
        if p.get('sourceId'):expected=native('3D/3dmodel.model',p['sourceId'])
        elif p.get('sourceFile'):expected=trimesh.load(SIM/p['sourceFile'],force='mesh')
        if expected is None:continue
        t=np.array(p['sourceTransformWorld']);check(np.allclose(t[:3,:3].T@t[:3,:3],np.eye(3),atol=1e-7) and abs(np.linalg.det(t[:3,:3])-1)<1e-7,'Scale or reflection in source pose: '+p['key']);expected.apply_transform(t)
        err=max(float(cKDTree(mesh.vertices).query(expected.vertices)[0].max()),float(cKDTree(expected.vertices).query(mesh.vertices)[0].max()))
        same=len(expected.faces)==len(mesh.faces);check(same and err<2e-5,'Native source geometry differs: '+p['key']);geometry.append({'part':p['key'],'same_triangle_count':same,'bidirectional_vertex_max_mm':err})
    proof['nativeAndCurrentSourceGeometry']=geometry
    # Electronic source axes are insertion, while guide axes are outward.
    sys.path.insert(0,str(SIM/'hardware-design-20260912/whole-robot-20260912/assembly'))
    from assembly_fk import fk
    bodies,geoms=fk();mounts=[];motorposes=[]
    motor_template=decoded(next(p for p in left['parts'] if p['key']=='motor8')).apply_transform(np.linalg.inv(by['motor8']['sourceTransformWorld']))
    for sid in range(1,16):
        source=next(c for c in sched if c.get('servo_ids')==[sid])
        body,_,index=source['frame'].split(' local;',1)[0].split(':')
        expected=next(g['world'] for g in geoms if g['body']==body and g['mesh']=='xl330' and g['index']==int(index))
        p=by['motor'+str(sid)];check(np.allclose(p['sourceTransformWorld'],expected,atol=1e-8),'Motor FK source pose mismatch: '+str(sid))
        target=motor_template.copy().apply_transform(expected);actual=decoded(p)
        error=float(cKDTree(actual.vertices).query(target.vertices)[0].max())
        check(error<2e-5 and len(target.faces)==len(actual.faces),'Manufacturer motor placement mismatch: '+str(sid))
        motorposes.append({'motor':sid,'source_frame':source['frame'],'world_vertex_max_error_mm':error})
    proof['motorPoseChecks']=motorposes
    for src in sched:
        if src.get('servo_ids'):
            q=sby[src['id']];check(q['spec']==src['spec'] and np.allclose(q['world_center_mm'],src['world_center_mm']) and np.allclose(q['world_axis'],src['world_axis']),'Joint changed: '+src['id']);continue
        t=bodies[src['coordinate_frame']]
        for i,point in enumerate(src['hole_centers_mm']):
            q=sby[f"E-{src['id']}-{i+1:02d}"];wantpoint=(t@np.r_[point,1])[:3];wantaxis=-t[:3,:3]@src['axis'];check(np.allclose(q['world_center_mm'],wantpoint,atol=1e-8) and np.allclose(q['world_axis'],wantaxis,atol=1e-8),'Mount point/axis wrong: '+q['id']);mounts.append({'id':q['id'],'source_insertion_reversed_for_outward_axis':True})
    proof['mountAxisChecks']=mounts
    hardware=[]
    for c in sby.values():
        axis=np.array(c['world_axis']);head=np.array(c['world_center_mm'])
        for key in c.get('washerKeys',[]):
            mesh=decoded(by[key]);ab=(mesh.vertices-head)@axis;interval=[float(ab.min()),float(ab.max())]
            index=c['washerKeys'].index(key);expected=[-.5,0.] if index==0 else[-17.,-16.5]
            check(np.allclose(interval,expected,atol=2e-5),'Camera washer datum wrong: '+key);check(c['washer_mm']==0,'Camera head datum washer shift duplicated: '+c['id']);hardware.append({'part':key,'outward_axis_interval_from_head_mm':interval,'expected':expected})
        if c.get('washer_mm'):
            key=c.get('washerKey','washer'+str(c['servo_ids'][0]));mesh=decoded(by[key]);ab=(mesh.vertices-head)@axis;check(np.allclose([ab.min(),ab.max()],[0,.5],atol=2e-5),'Motor washer datum wrong: '+key);hardware.append({'part':key,'outward_axis_interval_from_head_mm':[float(ab.min()),float(ab.max())],'viewer_head_offset_mm':.5})
        for key in c.get('nutKeys',[]):
            mesh=decoded(by[key]);ab=(mesh.vertices-head)@axis;diam=float(re.match(r'M([\d.]+)',c['spec'])[1]);height=1.6 if diam==2 else 2.4;far=c['length_mm']-c['tip_beyond_nut_mm'];check(np.allclose([ab.min(),ab.max()],[-far,-far+height],atol=2e-5),'Nut position wrong: '+key)
    proof['washerIntervals']=hardware
    viewer=(D/'viewer.js').read_text()
    if "'Fastens the yellow foot to the orange ankle.'" in viewer and "c.category==='print_retainer'" not in viewer.split('function selectScrew(c)',1)[1].split('function viewWasher',1)[0]:findings.append({'severity':'failure','id':'mount-description','detail':'Electronic mount selection falls into the foot-retainer sentence. Add an explicit mount branch.'})
    animation_disclaimer='illustrative' in viewer.lower() or 'not a collision' in viewer.lower() or 'not a verified' in viewer.lower()
    if not animation_disclaimer:findings.append({'severity':'failure','id':'animation-path-disclosure','detail':'The UI animates generic approach vectors but does not visibly distinguish an illustrative path from a collision-validated insertion path.'})
    wiring=json.loads((D/'wiring-guide-data.json').read_text());contract=json.loads((D.parent/'design-contract.json').read_text());groups=[g['motor_ids'] for g in wiring['motor_fused_groups']];check(groups==contract['fuses']['motor_branches']['groups'],'Motor power groups differ from current contract');check(sum(p['used'] for p in wiring['pi_header_pins'])==12,'Pi used pins differ');check(len([c for c in wiring['connections'] if c['id'].startswith('data-')])==15,'DATA bus link count differs')
    html=(D/'LEFT-LEG.html').read_text();packed=re.search(r'const packed="([A-Za-z0-9+/=]+)"',html)
    check(packed is not None,'The full guide does not contain a compressed embedded payload')
    if packed:
        from bundle_guide import apply_fastener_revision
        revision_path=D.parent/'fastener-review-20261008/fastener-patch-proposal.json'
        revision=json.loads(revision_path.read_text())
        derived=apply_fastener_revision(data, revision, revision_path)
        embedded=gzip.decompress(base64.b64decode(packed[1]));canonical=json.dumps(derived,separators=(',',':')).encode()
        check(embedded==canonical,'HTML embeds stale or different assembly data')
        embedded_wiring=json.JSONDecoder().raw_decode(html.split('const WIRING=',1)[1])[0]
        check(embedded_wiring==wiring,'HTML embeds stale or different wiring data')
        check(viewer.strip() in html,'HTML does not contain the exact current viewer source')
        proof['actualBundleReadback']={'guide_sha256':sha(D/'LEFT-LEG.html'),'assembly_payload_byte_equal_verified_derived_json':embedded==canonical,'base_data_sha256':sha(D/'full-build-data.json'),'embedded_payload_sha256':hashlib.sha256(embedded).hexdigest(),'wiring_equal':embedded_wiring==wiring,'current_viewer_source_embedded':viewer.strip() in html,'fastenerRevisionApplied':True}
    result={'passed':not errors and not findings,'errors':errors,'actionable_findings':findings,'evidence':proof,'full_data_sha256':sha(D/'full-build-data.json'),'builder_sha256':sha(D/'build_full_guide_data.py'),'viewer_sha256':sha(D/'viewer.js'),'wiring_sha256':sha(D/'wiring-guide-data.json'),'scope':'Independent static source, stock allocation, source geometry, axes, washer/nut positions and wiring invariants. Browser actions, screw insertion collisions and physical assembly are separate.','animation_clearance_verified':False,'physical_fit_verified':False,'gui_test_performed':False}
    result['display_geometry_limitations']=['The animated screw heads use a generic diameter1.7×thread diameter and height1mm. They are schematic, unlike the sourced washers/nuts and actual printed meshes; no head-shape fit or insertion collision acceptance is inferred.']
    result['counts']={'parts':len(by),'screws':len(sby),'operations':sum(len(m['operations']) for m in data['modules']),'installed_prints':len(used),'retained_print_stock':len(retained),'source_stock_total':len(stock)}
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'errors':errors,'findings':findings,'geometry_checked':len(geometry),'mounts_checked':len(mounts),'washers_checked':len(hardware)}));return 0 if result['passed'] else 1

if __name__=='__main__':sys.exit(main())

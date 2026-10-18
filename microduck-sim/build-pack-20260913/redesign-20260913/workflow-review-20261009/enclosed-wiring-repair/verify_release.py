"""Read-only acceptance of one active repair release. Never builds or launches CAD."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
SIM=HERE.parents[3]
DEFAULT=HERE/'release-manifest.json'
COVERAGE={
 'mechanical':{'assembly_order','rigid_insertion','installed_fasteners','tool_access','cable_before_cover'},
 'head':{'openrb','pi_populated','gpio_connectors','usb_connectors','ttl_connectors','camera_audio','internal_wiring','populated_closure'},
 'harness':{'all_connections','power_zones','motor_data','camera','imu','audio','wire_retention','closure_clearance'},
 'guide':{'mechanical_operations','wiring_steps','data_spatial_same_revision','prepare_assemble_check'},
 'print':{'incremental_inventory','native_slicing','first_layer','functional_holes'},
 'liveDeployment':{'deployed_same_bytes','browser_assembly','browser_wiring','browser_return_navigation'},
}
ROLE_GATE={
 'mechanical_inventory':'mechanical','head_inventory':'head','wiring_inventory':'harness',
 'guide_data':'guide','guide_wiring':'guide','guide_spatial':'guide','guide_html':'guide',
 'print_zip':'print','printer_file':'print',
}
PROJECT_COVERAGE={'physical_commissioning','selected_board_qualified','loaded_power','connector_fit',
                  'camera_control_timing','stale_data_stop','lost_command_stop'}


def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()


def read(path):
 return json.loads(Path(path).read_text())


def resolve(path,base):
 p=Path(path)
 return p.resolve() if p.is_absolute() else (base/p).resolve()


def review(manifest_path=DEFAULT,scope='design',context_path=SIM/'PROJECT-CONTEXT.json',project_review=None):
 manifest_path=Path(manifest_path).resolve();base=manifest_path.parent;issues=[]
 result={'scope':scope,'passed':False,'designPassed':False,'status':'incomplete',
         'manifest':str(manifest_path),'physicalTests':0,'generatorsExecuted':False,'issues':issues}
 def issue(code,detail):issues.append({'code':code,'detail':detail})
 def checked(ref,label):
  if not isinstance(ref,dict) or not ref.get('path') or not ref.get('sha256'):
   issue('missing_binding',label);return None
  try:
   p=resolve(ref['path'],base)
   if sha(p)!=ref['sha256']:issue('stale_artifact',label+': '+str(p));return None
   return p
  except (OSError,TypeError,ValueError) as e:issue('unreadable_artifact',label+': '+str(e));return None
 try:context=read(context_path)
 except (OSError,ValueError) as e:issue('context_unavailable',str(e));return result
 result['contextSha256']=sha(context_path)
 try:m=read(manifest_path)
 except (OSError,ValueError) as e:
  issue('release_manifest_missing_or_invalid',str(e))
  for gate in COVERAGE:issue('missing_gate',gate)
  if scope=='project':issue('project_not_accepted','Design and hardware evidence are absent.')
  return result
 result['manifestSha256']=sha(manifest_path);result['releaseRevision']=m.get('releaseRevision')
 if m.get('schemaVersion')!=1 or not isinstance(m.get('releaseRevision'),str) or not m['releaseRevision'].strip():issue('invalid_schema','schemaVersion=1 and nonempty releaseRevision are required')
 if m.get('status')!='ready':issue('release_not_ready',str(m.get('status')))
 # A snapshot is exact input identity, not permission to alter the canonical context.
 ctx=checked(m.get('projectContext'),'projectContext')
 if ctx and ctx!=Path(context_path).resolve():issue('wrong_context','projectContext must bind the current canonical context path')
 artifacts={};role_ids={role:[] for role in ROLE_GATE}
 for a in m.get('artifacts',[]):
  key=a.get('id');role=a.get('role')
  if not key or key in artifacts:issue('duplicate_or_missing_artifact_id',str(key));continue
  p=checked(a,'artifact '+str(key));artifacts[key]=(a,p)
  if role not in ROLE_GATE:issue('unknown_artifact_role',str(role));continue
  role_ids[role].append(key)
 for role,ids in role_ids.items():
  if not ids:issue('missing_artifact_role',role)
 for key,(a,p) in artifacts.items():
  if not p or not a.get('role','').endswith('_inventory'):continue
  try:
   inventory=read(p);hashes=inventory.get('sourceHashes')
   if not isinstance(hashes,dict) or not hashes:issue('inventory_leaf_bindings_missing',key);continue
   for source,digest in hashes.items():checked({'path':source,'sha256':digest},key+' inventory leaf')
  except (OSError,ValueError,TypeError) as e:issue('inventory_invalid',key+': '+str(e))
 gates=m.get('gates',{})
 receipts={}
 def check_receipt(ref,name,coverage,required_ids):
  p=checked(ref,'gate '+name)
  if not p:return None
  try:r=read(p)
  except (OSError,ValueError) as e:issue('invalid_receipt',name+': '+str(e));return None
  if r.get('passed') is not True or r.get('complete') is not True or r.get('unresolved')!=[]:
   issue('receipt_incomplete',name+' must explicitly pass its complete scope with unresolved=[]')
  if r.get('releaseRevision')!=m.get('releaseRevision'):issue('receipt_revision_mismatch',name)
  missing=coverage-set(r.get('coverage',[]))
  if missing:issue('receipt_scope_incomplete',name+': '+', '.join(sorted(missing)))
  # All checked artifacts and leaf evidence must be tied to actual file bytes.
  hashes=r.get('sourceHashes',{})
  if not isinstance(hashes,dict) or not hashes:issue('receipt_sources_missing',name);hashes={}
  resolved_hashes={}
  for source,digest in hashes.items():
   leaf=checked({'path':source,'sha256':digest},name+' source')
   if leaf:resolved_hashes[str(leaf)]=digest
  for key in required_ids:
   a,actual=artifacts[key]
   if actual and resolved_hashes.get(str(actual))!=a['sha256']:
    issue('receipt_does_not_bind_artifact',name+': '+key)
  return r
 for name,cov in COVERAGE.items():
  if name not in gates:issue('missing_gate',name);continue
  required=[key for key,(a,p) in artifacts.items() if ROLE_GATE.get(a.get('role'))==name]
  if name=='head':required+=role_ids['wiring_inventory']
  if name=='harness':required+=role_ids['head_inventory']+role_ids['mechanical_inventory']
  if name=='guide':required+=role_ids['mechanical_inventory']+role_ids['head_inventory']+role_ids['wiring_inventory']
  if name=='print':required+=role_ids['mechanical_inventory']+role_ids['head_inventory']
  if name=='liveDeployment':required+=role_ids['guide_html']+role_ids['guide_data']+role_ids['guide_wiring']+role_ids['guide_spatial']
  receipts[name]=check_receipt(gates[name],name,cov,set(required))
  if name in ['head','harness'] and receipts[name]:
   field='wholeHeadAccepted' if name=='head' else 'wholeHarnessAccepted'
   if receipts[name].get(field) is not True:issue('local_receipt_not_whole_acceptance',name+': '+field)
 live=receipts.get('liveDeployment')
 if live and (live.get('liveReadbackMatched') is not True or live.get('browserChecked') is not True or not live.get('url') or not live.get('checkedAt')):
  issue('live_deployment_incomplete','Need dated live byte readback plus actual browser acceptance for the bound bundle')
 # One file per color/machine; archive entries must be exactly the declared printer exports.
 exports=[(a,p) for a,p in artifacts.values() if a.get('role')=='printer_file'];pairs=set()
 for a,p in exports:
  pair=(a.get('color'),a.get('machine'))
  if not pair[0] or pair[1] not in ['bambu','elegoo'] or pair in pairs:issue('printer_inventory_invalid',str(pair))
  pairs.add(pair)
  if not a.get('archiveEntry') or not Path(a['archiveEntry']).name.startswith('zhengxia_'):issue('printer_archive_entry_invalid',str(a.get('id')))
 for color in {x[0] for x in pairs}:
  if {(color,'bambu'),(color,'elegoo')}-pairs:issue('printer_machine_missing',str(color))
 zip_ids=role_ids['print_zip']
 if len(zip_ids)!=1:issue('print_archive_count','Exactly one incremental delivery archive is required')
 elif artifacts[zip_ids[0]][1]:
  try:
   with zipfile.ZipFile(artifacts[zip_ids[0]][1]) as z:
    names=[x.filename for x in z.infolist() if not x.is_dir()]
    expected=[a.get('archiveEntry') for a,p in exports]
    if len(names)!=len(set(names)) or set(names)!=set(expected):issue('print_archive_inventory_mismatch','ZIP must contain only the declared per-color machine exports')
    for a,p in exports:
     if a.get('archiveEntry') in names:
      h=hashlib.sha256()
      with z.open(a['archiveEntry']) as f:
       for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
      if h.hexdigest()!=a['sha256']:issue('print_archive_bytes_mismatch',a['id'])
  except (OSError,zipfile.BadZipFile,RuntimeError) as e:issue('print_archive_invalid',str(e))
 result['designPassed']=not issues
 if scope=='project':
  # Preserve the existing canonical visual-learning gate. Call its read-only function,
  # never main(), which writes a report, and never a historical build pipeline.
  project_ids=set(artifacts)
  r=check_receipt(m.get('projectAcceptance'),'physical commissioning',PROJECT_COVERAGE,project_ids)
  if r:
   if r.get('kind')!='hardware_commissioning' or type(r.get('physicalTests')) is not int or r.get('physicalTests',0)<1:
    issue('physical_commissioning_missing','Actual hardware commissioning with recorded tests is required')
   else:result['physicalTests']=r['physicalTests']
  try:
   if project_review is None:
    script=Path(context_path).resolve().parent/'build-pack-20260913/phase1/check_project_context.py'
    namespace={'__name__':'microduck_project_context_readonly','__file__':str(script)}
    exec(compile(script.read_text(),str(script),'exec'),namespace)
    evidence=namespace['review'](root=Path(context_path).resolve().parent)
   else:evidence=project_review(Path(context_path).resolve().parent)
   result['projectContextReview']=evidence
   if evidence.get('training_evidence_verified') is not True:issue('training_not_accepted',str(evidence.get('training_errors')))
   if evidence.get('project_handoff_ready') is not True or evidence.get('physical_acceptance_verified') is not True:
    issue('visual_pickup_not_accepted','Canonical capability/training/camera-source hardware trial gates remain open')
   # A new release cannot borrow hardware pickup trials from the old contract revision.
   contract=read(Path(context_path).resolve().parent/context['current_build']['contract'])
   if contract.get('revision')!=m.get('releaseRevision'):issue('project_build_revision_mismatch','Hardware trial contract must identify this release')
  except (OSError,ValueError,KeyError,TypeError,ImportError) as e:issue('project_evidence_unavailable',str(e))
 result['passed']=not issues;result['status']='accepted' if result['passed'] else 'incomplete'
 return result


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--scope',choices=['design','project'],default='design')
 parser.add_argument('--manifest',type=Path,default=DEFAULT)
 args=parser.parse_args()
 try:r=review(args.manifest,args.scope)
 except (OSError,ValueError,KeyError,TypeError) as e:
  r={'scope':args.scope,'passed':False,'status':'incomplete','generatorsExecuted':False,'issues':[{'code':'invalid_release_data','detail':str(e)}]}
 print(json.dumps(r,indent=2));return 0 if r['passed'] else 1

if __name__=='__main__':raise SystemExit(main())

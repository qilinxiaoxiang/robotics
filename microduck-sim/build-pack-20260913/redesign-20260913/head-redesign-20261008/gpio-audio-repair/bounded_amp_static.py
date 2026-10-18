#!/usr/bin/env python3
"""One exact static pair per guarded child; metadata/bounds phase uses stdlib."""
import argparse,array,base64,json,sys
from pathlib import Path
import bounded_amp_check as core
from amp16_aabb_precheck import bounds,compare
D=Path(__file__).resolve().parent;H=D.parent;C=H/'camera-ribbon-repair'

def rows():
 data=json.loads(core.SOURCE.read_text());config=json.loads(core.CONFIG.read_text());index=core.scene_index(data,config)
 for k in ['amplifier','speaker_wire_0','speaker_wire_1','camera_mount_screws','pi_usb_receiving']:
  index.pop(k,None)
 local=json.loads((C/'local-candidate-manifest.json').read_text())
 assert local['baseViewerCandidateSha256']==core.sha(core.CONFIG)
 for p,h in local['sourceHashes'].items():
  if core.sha(p)!=h:raise ValueError('Stale local candidate: '+p)
 for k in local['removedParts']:index.pop(k,None)
 for k,f in local['replacementMeshes'].items():index[k]={'key':k,'path':H/f,'transform':None}
 for p in local['additionalParts']:index[p['key']]={'key':p['key'],'path':H/p['mesh'],'transform':None}
 for k,f in local['diagnosticGeometry'].items():index[k]={'key':k,'path':H/f,'transform':None}
 index['csi_free_straight_receiving']={'key':'csi_free_straight_receiving','path':C/'csi_free_straight_receiving-lowered-pose-world.stl','transform':None}
 return index

def rowbounds(row):
 if row.get('path'):
  assert not row.get('transform'), 'Explicit transformed STL needs expanded vertices'
  return bounds(row['path'])
 p=row['data'];v=array.array('f');v.frombytes(base64.b64decode(p['positionB64']))
 if sys.byteorder!='little':v.byteswap()
 low=[float('inf')]*3;high=[float('-inf')]*3;T=row.get('transform')
 for i in range(0,len(v),3):
  q=v[i:i+3]
  if T:q=[sum(T[j][a]*q[a] for a in range(3))+T[j][3] for j in range(3)]
  for j in range(3):low[j]=min(low[j],q[j]);high[j]=max(high[j],q[j])
 return [low,high]

def manifest(name,delta):
 index=rows();amp=D/'amplifier-terminal-receiving-world.stl';ab=bounds(amp);ab=[[p[i]+delta[i] for i in range(3)] for p in ab]
 inputs=[Path(__file__),D/'bounded_amp_check.py',D/'amp16_aabb_precheck.py',core.SOURCE,core.CONFIG,amp,C/'local-candidate-manifest.json']
 inputs.extend(r['path'] for r in index.values() if r.get('path'))
 result={'name':name,'deltaMm':delta,'integrationReady':False,'amplifierBoundsMm':ab,'rows':[],'inputHashes':core.fingerprint(inputs),'omitted':['amplifier self','obsolete speaker wires needing reroute','obsolete aggregate camera screws replaced by six local screws','obsolete Pi USB receiving; new USB design separate gate']}
 for k,r in index.items():
  bb=rowbounds(r);result['rows'].append({'key':k,'boundsMm':bb,**compare(ab,bb)})
 out=D/(name+'-static-manifest.json');core.atomic_json(out,result)
 print(json.dumps({'path':str(out),'count':len(result['rows']),'exactPairsNeeded':[r['key'] for r in result['rows'] if r['aabbOverlap']]}))

def pair(name,key):
 report=json.loads((D/(name+'-static-manifest.json')).read_text())
 for p,h in report['inputHashes'].items():
  if core.sha(p)!=h:raise ValueError('Stale input '+p)
 index=rows();assert key in index
 core.guarded_import();a=core.solid({'path':D/'amplifier-terminal-receiving-world.stl'}).translate(report['deltaMm']);b=core.solid(index[key]);v,bb=core.volume_pair(a,b)
 out={'key':key,'deltaMm':report['deltaMm'],'volumeMm3':v,'intersectionBoundsMm':bb,'passed':v<=1e-4,'manifestSha256':core.sha(D/(name+'-static-manifest.json')),'integrationReady':False}
 core.atomic_json(D/(name+'-static-'+key+'.json'),out);print(json.dumps(out));return 0 if out['passed'] else 2

def main():
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--manifest',action='store_true');p.add_argument('--delta',type=float,nargs=3,default=[16,0,0]);p.add_argument('--key');a=p.parse_args();assert a.name.replace('-','').isalnum()
 if a.manifest:manifest(a.name,a.delta);return 0
 return pair(a.name,a.key)
if __name__=='__main__':sys.exit(main())

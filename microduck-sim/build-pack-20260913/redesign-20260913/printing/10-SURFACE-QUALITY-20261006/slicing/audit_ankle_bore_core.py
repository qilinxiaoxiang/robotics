"""Check exact source-frame through-bore cores against actual model/support paths.
Small strict core only, not full bore diameter, counterbore ledge or physical fit.
"""
from pathlib import Path
import argparse,json,math
import numpy as np
from audit_surface_paths import read_code,parse,samples
from audit_ankle_headseats import matrix,D,P

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--gcode',required=True);ap.add_argument('--project',required=True);ap.add_argument('--output',required=True);args=ap.parse_args();q=json.loads((D.parent/'geometry/ankle-early-candidates.json').read_text());row=next(r for r in q if r['object_id']=='20');orig=P/'09-REPRINT-READY-20260930/Elegoo/old-orange-plate1/MicroDuck_Elegoo_old-orange-plate1_REPRINT_editable.3mf';raw_to_current=matrix(args.project,'20')@np.linalg.inv(matrix(orig,'20'))@np.array(row['raw_source_to_bed4x4']);inverse=np.linalg.inv(raw_to_current);code,cfg,fh,gh=read_code(args.gcode,args.project);paths,_,_=parse(code,collect_all=True);key=next(k for k in paths if 'community-66' in k);pts=[];kinds=[]
 for z,pp in paths[key].items():
  for p in pp:
   if any(k in p['kind'].lower() for k in ['brim','skirt']):continue
   ss=samples(p['points'],step=.15)
   for a in ss:pts.append([a[0],a[1],z-p['height']/2])
   kinds.extend([p['kind']]*len(ss))
 current=np.array(pts);raw=current@inverse[:3,:3].T+inverse[:3,3];kinds=np.array(kinds);results=[]
 for seat in row['headseat_feature_samples']:
  center=np.array(seat['source_point_mm']);d=raw-center;rho=np.linalg.norm(d[:,:2],axis=1);mask=(rho<.6)&(d[:,2]>.25)&(d[:,2]<1.5);found=kinds[mask];model=[s for s in found if 'support' not in s.lower()];support=[s for s in found if 'support' in s.lower()];results.append({'feature_id':seat['id'],'bore_core_radius_mm':.6,'source_axis_window_from_headseat_mm':[.25,1.5],'model_centerline_sample_count_in_core':len(model),'support_centerline_sample_count_in_core':len(support),'model_features_in_core':sorted(set(model)),'support_features_in_core':sorted(set(support))})
 out={'project':args.project,'gcode_file':args.gcode,'gcode_sha256':gh,'method':'Native extrusion centerline sampled at0.15mm; nozzle-Z minus bead-height/2 mapped into exact source frame. Strict0.6mm core intentionally smaller than nominal through-hole. No thickness inflation; tests center paths, not full bead envelope.','features':results,'model_core_clear':all(r['model_centerline_sample_count_in_core']==0 for r in results),'support_core_empty':all(r['support_centerline_sample_count_in_core']==0 for r in results),'full_bore_fit_verified':False};Path(args.output).write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k in ['model_core_clear','support_core_empty']})
if __name__=='__main__':main()

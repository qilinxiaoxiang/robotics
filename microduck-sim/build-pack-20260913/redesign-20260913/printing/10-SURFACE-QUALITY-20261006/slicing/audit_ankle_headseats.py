"""Read headseat ROI mesh samples and query actual native support paths below them.
8 samples/seat are finite critical-feature probes, not full seat coverage or fit proof.
"""
from pathlib import Path
import argparse,json,zipfile,xml.etree.ElementTree as E,math
import numpy as np
from scipy.spatial import cKDTree
from audit_surface_paths import read_code,parse,samples,number
D=Path(__file__).resolve().parent;P=D.parents[1];N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
def matrix(path,oid):
 with zipfile.ZipFile(path) as z:rt=E.fromstring(z.read('3D/3dmodel.model'))
 i=next(i for i in rt.find(N+'build') if i.get('objectid')==oid);m=np.eye(4);m[:3,:]=np.array(list(map(float,i.get('transform').split()))).reshape(4,3).T;return m

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--gcode',required=True);ap.add_argument('--project',required=True);ap.add_argument('--geometry',default=str(D.parent/'geometry/ankle-early-candidates.json'));ap.add_argument('--output',required=True);args=ap.parse_args();q=json.loads(Path(args.geometry).read_text());feature=next(x for x in q if x['object_id']=='20');origin=P/'09-REPRINT-READY-20260930/Elegoo/old-orange-plate1/MicroDuck_Elegoo_old-orange-plate1_REPRINT_editable.3mf';delta=matrix(args.project,'20')@np.linalg.inv(matrix(origin,'20'));code,cfg,filehash,gchash=read_code(args.gcode,args.project);paths,_,_=parse(code);key=next(n for n in paths if 'community-66' in n);interfaces={z:[p for p in ps if p['kind']=='Support interface'] for z,ps in paths[key].items()};interfaces={z:ps for z,ps in interfaces.items() if ps};trees={z:cKDTree(np.array([pt for p in ps for pt in samples(p['points'])])) for z,ps in interfaces.items()};gap=number(cfg.get('support_top_z_distance'),.2);results=[]
 for seat in feature['headseat_feature_samples']:
  axis=delta[:3,:3]@np.array(seat['axis']);points=np.array(seat['points'])@delta[:3,:3].T+delta[:3,3];probes=[]
  for point in points:
   eligible=[z for z in trees if gap-.10 <= point[2]-z <= gap+.25];hit=[]
   for z in eligible:
    dist=float(trees[z].query(point[:2])[0]);width=max(p['width'] for p in interfaces[z]);
    if dist <= width/2+.15:hit.append({'support_top_z_mm':z,'actual_gap_to_mesh_probe_mm':float(point[2]-z),'xy_distance_to_interface_centerline_mm':dist})
   probes.append({'point_mm':point.tolist(),'matching_support_interface':sorted(hit,key=lambda h:h['actual_gap_to_mesh_probe_mm'])})
  results.append({'feature_id':seat['id'],'spec':seat['spec'],'outward_axis_in_current_bed_frame':axis.tolist(),'requires_underneath_support_by_45degree_test':bool(axis[2]<-math.sqrt(.5)),'sample_count':len(probes),'sample_count_with_near_interface':sum(bool(p['matching_support_interface']) for p in probes),'probes':probes})
 out={'gcode_sha256':gchash,'file_sha256':filehash,'geometry_sample_source':str(Path(args.geometry).resolve()),'project':args.project,'settings':{'gap':gap,'interface_spacing':cfg.get('support_interface_spacing'),'top_layers':cfg.get('support_interface_top_layers')},'headseats':results,'acceptance_boundary':'8 annular samples per exact mesh seat. Interface samples must be integrated with full seat shape, hole-axis bridges and extraction path checks. For side orientation seats are vertical and do not require underneath support; any hole-axis bridge remains separately reviewed.'};Path(args.output).write_text(json.dumps(out,indent=2)+'\n');print([(r['feature_id'],r['requires_underneath_support_by_45degree_test'],r['sample_count_with_near_interface']) for r in results])
if __name__=='__main__':main()

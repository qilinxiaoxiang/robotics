from pathlib import Path
import argparse,zipfile,json,sys,hashlib
D=Path(__file__).resolve().parents[1];P=D.parent
sys.path.insert(0,str(P/'09-REPRINT-READY-20260930'));from native_tools import parse
sys.path.insert(0,str(P/'04-FOUR-COLOR-20260929/05-BAMBU-WHITE-YELLOW'));from audit_bambu_spacing import audit_archive
class TextPath:
 def __init__(self,text):self.text=text
 def open(self):import io;return io.StringIO(self.text)
 def read_bytes(self):return self.text.encode()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--archive',required=True);ap.add_argument('--printer',required=True);ap.add_argument('--expected',type=int,required=True);ap.add_argument('--output',required=True);args=ap.parse_args();path=Path(args.archive)
 if args.printer=='Elegoo':
  with zipfile.ZipFile(path) as z:code=z.read(next(n for n in z.namelist() if n.endswith('.gcode'))).decode();cfg=json.loads(z.read('Metadata/project_settings.config'))
  report=parse(TextPath(code))[0];bounds=report['actual_extrusion_bounds_conservative_mm'];gap=report['minimum_interobject_extrusion_gap_lower_bound_mm'];edge=report['minimum_bed_edge_margin_mm'];count=report['object_count'];excount=report['extruding_objects'];passed=report['passed_nonoverlap_and_inside_bed'];report.update(source_archive=str(path.resolve()),archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),filament_ids=cfg.get('filament_ids'))
 else:
  from native_material_spacing import audit_archive as audit_material
  report=audit_material(path,args.expected);objects=report['objects'];bounds=[min(o['extrusion_bounds_mm'][0] for o in objects),min(o['extrusion_bounds_mm'][1] for o in objects),max(o['extrusion_bounds_mm'][2] for o in objects),max(o['extrusion_bounds_mm'][3] for o in objects)];gap=report['minimum_interobject_gap_lower_bound_mm'];edge=report['minimum_bed_margin_mm'];count=report['object_count'];excount=report['extruding_object_count'];passed=report['passed']
 center=[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2];error=max(abs(v-128) for v in center);report['coordinate_frame']='configured physical material bed frame (commandXY plus active-extruder offset); Elegoo offset0x0';report.update(all_layer_model_support_brim_bounds_mm=bounds,footprint_center_xy_mm=center,center_error_mm=error,expected_count=args.expected,actual_native_count_correct=count==args.expected and excount==args.expected,minimum_gap_at_least4mm=gap>=4-.001,center_within1mm=error<=1,passed_for_project_handoff=bool(passed and count==args.expected and excount==args.expected and gap>=4-.001 and error<=1));Path(args.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed_for_project_handoff'],'count':count,'gap':gap,'edge':edge,'center':center,'output':args.output}));return 0 if report['passed_for_project_handoff'] else 1
if __name__=='__main__':sys.exit(main())

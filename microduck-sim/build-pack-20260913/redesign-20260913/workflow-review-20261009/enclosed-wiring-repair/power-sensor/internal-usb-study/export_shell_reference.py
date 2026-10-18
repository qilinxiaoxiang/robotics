from pathlib import Path
import cadquery as cq,json,hashlib,sys
D=Path(__file__).resolve().parent; S=D.parents[2]/'enclosed-wiring-repair/head-layout/body-partition/native-usb-passage'; key=sys.argv[1];p=S/(key+'-usb-u-notch.step');sh=cq.importers.importStep(str(p)).val();assert sh.isValid(); out=D/(key+'-usb-u-notch.stl');cq.exporters.export(sh,str(out),tolerance=.02,angularTolerance=.1)
(D/(key+'-reference.json')).write_text(json.dumps({'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'stl':str(out),'stlSha256':hashlib.sha256(out.read_bytes()).hexdigest(),'nativeSolids':len(sh.Solids()),'nativeValid':sh.isValid()},indent=2)+'\n')

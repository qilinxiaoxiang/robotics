"""Inspect actual native extrusion, including supports, in physical bed coordinates."""
from pathlib import Path
import argparse,hashlib,itertools,json,math,re,sys,zipfile
import numpy as np
from shapely.geometry import MultiLineString,MultiPoint,Polygon
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent/'09-REPRINT-READY-20260930'))
from native_tools import normalize_bambu,first_layer_summary
NUM=re.compile(r'([XYZEIJ])([-+]?\d*\.?\d+)')

def audit(path):
    with zipfile.ZipFile(path) as z:
        members=[n for n in z.namelist() if n.endswith('.gcode')]
        assert len(members)==1
        data=z.read(members[0]);code=data.decode();cfg=json.loads(z.read('Metadata/project_settings.config'))
    bambu='BambuStudio' in code[:1000]
    # Bambu emits OBJECT_ID instead of start/stop labels on single-object plates.
    # Normalize that native ownership marker; do not infer ownership from location.
    if bambu and '; start printing object' not in code:
        assert '; OBJECT_ID:' in code
        code=re.sub(r'^; OBJECT_ID: (\d+)$',r'; start printing object, unique label id: \1',code,flags=re.M)
    native=normalize_bambu(code,path) if bambu else code
    offset=np.asarray([float(v) for v in cfg['extruder_offset'][0].split('x')])
    bed=Polygon([list(map(float,p.split('x'))) for p in cfg['printable_area']])
    exclusion=Polygon([list(map(float,p.split('x'))) for p in cfg['bed_exclude_area']])
    x=y=0.;width=0.;kind='Custom';cur=None;started=False;paths={};unowned=[]
    for line in native.splitlines():
        if line.startswith('M82'):raise ValueError('Absolute extrusion unsupported')
        if line.startswith('EXCLUDE_OBJECT_START'):
            cur=re.search(r'NAME=(\S+)',line)[1];started=True
        elif line.startswith('EXCLUDE_OBJECT_END'):cur=None
        elif line.startswith(';TYPE:'):kind=line[6:].strip()
        elif line.startswith(';WIDTH:'):width=max(width,float(line[7:]))
        if not re.match(r'^G[0123] ',line):continue
        cmd=line.split()[0];v={k:float(t) for k,t in NUM.findall(line.split(';')[0])}
        xx=v.get('X',x);yy=v.get('Y',y);pts=[(x,y),(xx,yy)]
        if cmd in ('G2','G3') and ('I' in v or 'J' in v):
            cx=x+v.get('I',0);cy=y+v.get('J',0);r=math.hypot(x-cx,y-cy)
            a=math.atan2(y-cy,x-cx);b=math.atan2(yy-cy,xx-cx);sgn=1 if cmd=='G3' else -1
            span=((b-a)*sgn)%(2*math.pi) or 2*math.pi
            step=2*math.acos(max(-1,min(1,1-.02/max(r,.02))))
            n=max(1,math.ceil(span/max(step,.01)))
            pts=[(cx+r*math.cos(a+sgn*span*i/n),cy+r*math.sin(a+sgn*span*i/n)) for i in range(n+1)]
            pts[0]=(x,y);pts[-1]=(xx,yy)
        if v.get('E',0)>0 and kind!='Custom' and (xx!=x or yy!=y or cmd in ('G2','G3')):
            if cur:paths.setdefault(cur,[]).append((np.asarray(pts)+offset).tolist())
            elif started:unowned.append(line)
        x,y=xx,yy
    assert paths
    rad=max(.3,width/2)+.02
    lines={k:MultiLineString(v) for k,v in paths.items()}
    hulls={k:MultiPoint(np.concatenate(v)).convex_hull for k,v in paths.items()}
    gaps=[]
    for a,b in itertools.combinations(hulls,2):
        gap=hulls[a].distance(hulls[b])-2*rad
        if gap<0:gap=lines[a].distance(lines[b])-2*rad
        gaps.append({'a':a,'b':b,'gapLowerBoundMm':gap})
    bounds=np.asarray([h.bounds for h in hulls.values()])
    bounds=[float(bounds[:,0].min()-rad),float(bounds[:,1].min()-rad),float(bounds[:,2].max()+rad),float(bounds[:,3].max()+rad)]
    center=[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2]
    margin=min(bed.boundary.distance(h.buffer(rad)) if bed.covers(h.buffer(rad)) else -1 for h in hulls.values())
    excluded=min(h.distance(exclusion)-rad for h in hulls.values())
    first=first_layer_summary(code,'Bambu' if bambu else 'Elegoo',path)
    result={'archive':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'gcodeSha256':hashlib.sha256(data).hexdigest(),'nativeSlicer':'Bambu' if bambu else 'Orca',
        'objects':len(paths),'allLayerSupportBrimBoundsMm':bounds,'physicalMaterialCenterMm':center,
        'recenterTranslationMm':[128-center[0],128-center[1]],'offsetMm':offset.tolist(),
        'beadRadiusWithArcErrorMm':rad,'bedMarginMm':margin,'exclusionMarginMm':excluded,
        'unownedExtrusionCount':len(unowned),'gaps':gaps,'nativeFirstLayer':first,
        'printSequence':cfg['print_sequence'],'profile':cfg['printer_settings_id'],'bedType':cfg['curr_bed_type'],
        'spacingPassed':all(g['gapLowerBoundMm']>=4 for g in gaps) and margin>=0 and excluded>=0 and not unowned,
        'firstLayerModelPresent':len(first)==len(paths) and all(r['model_area_mm2']>0 for r in first),
        'boundary':'Toolpath spacing/first-layer evidence only. Functional seats and support removability require their own inspection.'}
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('archives',nargs='+',type=Path);ap.add_argument('--output',required=True,type=Path);args=ap.parse_args()
    rows=[audit(p.resolve()) for p in args.archives]
    args.output.write_text(json.dumps({'plates':rows},indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ['nativeSlicer','objects','spacingPassed','firstLayerModelPresent','recenterTranslationMm']} for r in rows]))

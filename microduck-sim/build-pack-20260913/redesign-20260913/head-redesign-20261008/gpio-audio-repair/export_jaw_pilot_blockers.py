from pathlib import Path
import math,json,hashlib
D=Path(__file__).resolve().parent;R=D.parent.parent;P=R/'printing/11-ASSEMBLY-REPAIR-20261008';O=D/'jaw-print-blockers';O.mkdir(exist_ok=True)
part=next(q for q in json.loads((P/'orientation-preparation.json').read_text())['parts'] if q['key']=='jaw_frame');T=part['printTransform'];half=14.782238006591797
features=[('new-blind-pilot-60',60.,102.5,-30.3,-25.3,1.5,True),('new-blind-pilot-76',76.,102.5,-30.3,-25.3,1.5,True),('horn-045',26.1,112.6146,39.2,44.25428549,1.4,False),('horn-046',32.1,118.6146,39.2,44.81875769,1.4,False),('horn-047',26.1,124.6146,39.2,44.88271307,1.4,False)]
rows=[]
def apply(p):return [sum(T[i][j]*p[j] for j in range(3))+T[i][3] for i in range(3)]
def write(p,faces):
 s=['solid local_support_blocker']
 for tri in faces:
  s+=['facet normal 0 0 0','outer loop']+['vertex '+' '.join(format(v,'.15g') for v in q) for q in tri]+['endloop','endfacet']
 s+=['endsolid local_support_blocker'];p.write_text('\n'.join(s)+'\n')
for name,cx,cz,lo,hi,rad,required in features:
 n=64;rr=rad/math.cos(math.pi/n);a=[[cx+rr*math.cos(i*2*math.pi/n),lo,cz+rr*math.sin(i*2*math.pi/n)] for i in range(n)];b=[[p[0],hi,p[2]] for p in a];faces=[]
 for i in range(n):
  j=(i+1)%n;faces.extend([[a[i],b[i],b[j]],[a[i],b[j],a[j]],[[cx,lo,cz],a[i],a[j]],[[cx,hi,cz],b[j],b[i]]])
 paths={}
 for frame in ['world','prepared','native-object']:
  ff=faces if frame=='world' else [[apply(p) for p in tri] for tri in faces]
  if frame=='native-object':ff=[[[p[0],p[1],p[2]-half] for p in tri] for tri in ff]
  p=O/f'{name}-{frame}.stl';write(p,ff);paths[frame]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 rows.append({'name':name,'requiredForCurrentBlindPilotFix':required,'owner':'jaw_frame','subtype':'support_blocker','worldAxis':[0,1,0],'worldCenter':[cx,(lo+hi)/2,cz],'worldYRange':[lo,hi],'receivingRadiusMm':rad,'circumscribed64FacetRadiusMm':rr,'meshFrames':paths})
r={'integrationReady':True,'modifiesPrintedGeometry':False,'instruction':'Add as support_blocker volume under jaw_frame, never normal_part. prepared = printTransform only (same bed-zero part preparation); native-object = prepared minus native object Z center14.782238006591797. Native jaw_frame build item supplies104.659045,128,14.782238 translation. Do not apply placement twice.','sourceOrientationSha256':hashlib.sha256((P/'orientation-preparation.json').read_bytes()).hexdigest(),'sourceJawSha256':part['sourceSha256'],'currentYellowSha256':hashlib.sha256((P/'yellow-preflight/Yellow_preflight.3mf').read_bytes()).hexdigest(),'blockers':rows,'verificationNeeded':'Reslice native Yellow, then repeat exact bore support-center audit. Blockers are settings; no claim that old G-code is corrected.'}
(O/'manifest.json').write_text(json.dumps(r,indent=2)+'\n');print(O/'manifest.json')

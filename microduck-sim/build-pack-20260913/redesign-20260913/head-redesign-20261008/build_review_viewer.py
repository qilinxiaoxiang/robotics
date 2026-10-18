"""Build a self-contained source-mesh review; candidate is distinct from accepted assembly."""
from pathlib import Path
import base64,gzip,json,re,hashlib
D=Path(__file__).resolve().parent;G=D.parent/'leg-guide-20261006';SIM=D.parents[2]
d=json.loads((G/'full-build-data.json').read_text());config=json.loads((D/'viewer-candidate.json').read_text())
keys=['head_cap','head_bottom','face_panel','eye_trim','jaw_frame','upper_pad','lower_pad','jaw_support','motor14','motor15','head_yaw_link','head_roll_ring_a','head_roll_ring_b','pi','openrb','audio_carrier','amplifier','speaker','camera_board','camera_pitch_foot','camera_cradle']
parts=[dict(p) for p in d['parts'] if p['key'] in keys]
for p in parts:
 if p['key']=='pi':p['name']='First-generation Pi Zero outline reference; Pi 3 fit unverified'
# Candidate replacements must be generated from source-bound investigation, never decorative placeholders.
import numpy as np,trimesh
for key,path in config.get('replacementMeshes',{}).items():
 m=trimesh.load(D/path,force='mesh');p=next(p for p in parts if p['key']==key)
 p['candidatePositionB64']=base64.b64encode(np.asarray(m.vertices,dtype='<f4').tobytes()).decode();p['candidateIndexB64']=base64.b64encode(np.asarray(m.faces,dtype='<u4').tobytes()).decode()
original_cap=trimesh.load(D/'curved-head/community-curved-head-world.stl',force='mesh')
p=next(p for p in parts if p['key']=='head_cap')
p['originalCurvedPositionB64']=base64.b64encode(np.asarray(original_cap.vertices,dtype='<f4').tobytes()).decode()
p['originalCurvedIndexB64']=base64.b64encode(np.asarray(original_cap.faces,dtype='<u4').tobytes()).decode()
for spec in config.get('additionalParts',[]):
 m=trimesh.load(D/spec['mesh'],force='mesh');p=dict(spec)
 p['positionB64']=base64.b64encode(np.asarray(m.vertices,dtype='<f4').tobytes()).decode();p['indexB64']=base64.b64encode(np.asarray(m.faces,dtype='<u4').tobytes()).decode();p['candidateOnly']=True;parts.append(p)
lib=SIM/'microduck-simulator/app/node_modules/three';three=(lib/'build/three.module.js').read_text();match=re.search(r'export \{([^}]+)\};?\s*$',three);members=[]
for term in match.group(1).split(','):
 bits=term.strip().split(' as ');members.append(bits[-1]+':'+bits[0])
three=three[:match.start()]+'\nreturn {'+','.join(members)+'};'
orbit=(lib/'examples/jsm/controls/OrbitControls.js').read_text();orbit=re.sub(r"import\s*\{([^}]+)\}\s*from\s*'three';",r'const {\1}=THREE;',orbit,count=1);orbit=re.sub(r'export \{ OrbitControls \};?\s*$','return OrbitControls;',orbit)
payload=dict(parts=parts,config=config);packed=base64.b64encode(gzip.compress(json.dumps(payload,separators=(',',':')).encode(),mtime=0)).decode()
# Preserve real sharp edges; averaged normals across roof/side triangles made planar
# walls appear dented. Use Three's own crease-aware normal utility, not mesh deformation.
utils=(lib/'examples/jsm/utils/BufferGeometryUtils.js').read_text()
crease=utils[utils.index('function toCreasedNormals('):utils.index('\nexport {',utils.index('function toCreasedNormals('))]
script='const THREE=(()=>{' +three+'})();const OrbitControls=(()=>{'+orbit+'})();const {Vector3,BufferAttribute}=THREE;'+crease+'\n(async()=>{const packed="'+packed+'";const raw=Uint8Array.from(atob(packed),c=>c.charCodeAt(0));const DATA=JSON.parse(await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream("gzip"))).text());\n'+(D/'review-viewer.js').read_text()+'\n})().catch(e=>{document.getElementById("status").textContent=e.message;console.error(e)});'
html=(D/'review-template.html').read_text().replace('/*APP*/',script);(D/'HEAD-EYE-REVIEW.html').write_text(html)
(D/'viewer-manifest.json').write_text(json.dumps({'sourceDataSha256':hashlib.sha256((G/'full-build-data.json').read_bytes()).hexdigest(),'configSha256':hashlib.sha256((D/'viewer-candidate.json').read_bytes()).hexdigest(),'htmlSha256':hashlib.sha256(html.encode()).hexdigest(),'purpose':'eye-camera spatial candidate; not final manufacturing acceptance'},indent=2)+'\n');print('HEAD_REVIEW_BUILT')

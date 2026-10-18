"""One-scene display conversion only: no booleans, fitting, CAD or geometry redesign."""
from pathlib import Path
import json,hashlib,base64,gzip,re,gc
import numpy as np,trimesh as tm
D=Path(__file__).resolve().parent;H=D.parent;C=H/'camera-ribbon-repair';Q=C/'fixed-pose-local-bend';O=C/'positive-x225';SIM=H.parents[2]
hashes={}
def read(p):p=Path(p);b=p.read_bytes();hashes[str(p)]=hashlib.sha256(b).hexdigest();return b
def js(p):return json.loads(read(p))
def arr(a,t):return base64.b64encode(np.asarray(a,dtype=t).tobytes()).decode()
base=js(H/'viewer-candidate.json');overlay=js(H/'current-closure/restored-source-overlay.json');pos=js(O/'candidate-manifest.json');pose=js(Q/'pi-spacer2-pose.json');sp=js(Q/'pi-spacer2-parts.json');accept=js(Q/'full-ribbon-acceptance.json')
assert all(accept[k] for k in ['complete200mm','staticClear','selfClear','populatedCapClosureClear','integrationReady'])
for r in accept['receipts']+[accept['mesh']]:assert hashlib.sha256(read(r['path'])).hexdigest()==r['sha256']
for rel,h in overlay['sourceHashes'].items():assert hashlib.sha256(read(H/rel)).hexdigest()==h
specs={}
basekeys=['head_cap','head_bottom','face_panel','eye_trim','jaw_frame','upper_pad','lower_pad','jaw_support','motor14','motor15','head_yaw_link','head_roll_ring_a','head_roll_ring_b','pi','openrb','amplifier','speaker']
for key in basekeys:specs[key]={'key':key,'cache':C/'head-source-cache'/f'{key}.json'}
for cfg in [base,pos,overlay]:
 for s in cfg.get('additionalParts',[]):specs[s['key']]={**s}
 for k,v in cfg.get('replacementMeshes',{}).items():specs.setdefault(k,{'key':k});specs[k]['mesh']=v
 for k in cfg.get('removedParts',[]):specs.pop(k,None)
# Filled40-pin union and obsolete full-height component slab are not actual hardware.
for k in ['zero_w_gpio_male_receiving','zero_w_components','pi_usb_receiving','zero_w_populated_receiving','jaw_passive_cheek','jaw_cheek_screw_1','jaw_cheek_screw_2']:specs.pop(k,None)
shift={x['key'] for x in js(O/'pi-geometry-manifest.json')['parts']};delta=np.array(pose['translationFromPositiveX225Mm']);T=np.array(pose['worldTransform'])
for row in sp['rows']:
 specs[row['id']+'_revision_screw']={'key':row['id']+'_revision_screw','mesh':row['screwMesh'],'name':row['id']+' M2.5×8 TAP','color':'#acb1b8'}
 specs[row['id']+'_spacer2']={'key':row['id']+'_spacer2','mesh':row['spacerMesh'],'name':'Pi 2mm垫圈','color':'#242725'}
specs['camera_ribbon_200']={'key':'camera_ribbon_200','mesh':accept['mesh']['path'],'name':'200mm柔性排线摆放示例','color':'#e88d29','flexible':True}
lidkeys={'head_cap','openrb','amplifier','speaker','speaker_cradle','speaker_keeper','curved_cap_hardware'}
parts=[]
def packed(key,verts,faces,**props):
 # Exact duplicate vertex indexing only; no triangle deletion or simplification.
 verts, inverse=np.unique(np.asarray(verts),axis=0,return_inverse=True);faces=inverse[np.asarray(faces)]
 p=dict(key=key,positionB64=arr(verts,'<f4'),indexB64=arr(faces,'<u4'),**props);parts.append(p);return p
for key,s in specs.items():
 meta={}
 if s.get('cache') and s['cache'].exists():meta=js(s['cache'])
 name=s.get('name',meta.get('name',key));color=s.get('color',meta.get('color','#888888'))
 if s.get('mesh'):
  path=Path(s['mesh']);path=path if path.is_absolute() else H/path;read(path);m=tm.load(path,force='mesh',process=False);v=np.asarray(m.vertices);f=np.asarray(m.faces)
  if key in shift:v=v+delta
 else:
  v=np.frombuffer(base64.b64decode(meta['positionB64']),dtype='<f4').reshape(-1,3);f=np.frombuffer(base64.b64decode(meta['indexB64']),dtype='<u4').reshape(-1,3)
 envelope=key.startswith('gpio_pin_') or key.endswith('_receiving') or key=='zero_w_gpio_solder_tails'
 p=packed(key,v,f,name=name,color=('#285942' if key=='pi' else color),lidMounted=key in lidkeys,envelope=envelope,flexible=s.get('flexible',False))
 if envelope:p.update(opacity=.32,color='#6085b5',name=name+' · 接收空间')
 del v,f;gc.collect()
# Use the already checked discrete header dimensions; merely display them as boxes.
read(C/'check_spacer_discrete_male.py');read(Q/'spacer-discrete-male.json')
def box(key,size,center,color,name):
 m=tm.creation.box(extents=size);v=np.asarray(m.vertices)+center;v=v@T[:3,:3].T+T[:3,3];packed(key,v,m.faces,color=color,name=name,lidMounted=False,envelope=False,flexible=False)
box('zero_w_header_base',[2.54,52,7],[67.31-1.27,-.011,119.5496],'#232628','40针排针塑料条 · 接收尺寸')
for pin in range(1,41):
 yy=-24.141+2.54*((pin-1)//2);zz=118.2796+(2.54 if pin%2==0 else 0)
 box(f'zero_w_header_pin_{pin:02}',[8.5-2.54,.64,.64],[67.31-(8.5+2.54)/2,yy,zz],'#bfad68',f'排针{pin} · 0.64mm名义模型')
# Honest optional component occupancy visualization, not the false solidwhole-board box.
occ=js(H/'cabling-release-20261008/neck-repair/pi-local-components/local-occupancy.json')
B=np.array([[0,0,-1,8.1],[0,1,0,0],[1,0,0,115.6146],[0,0,0,1]],float);Cmat=np.array([[0,1,0,.435],[1,0,0,-32.511],[0,0,1,-59.21],[0,0,0,1]],float);M=T@B@Cmat
for row in occ['rows']:
 xy=np.array(row['footprintOfficialXYMm']);n=len(xy);v=np.r_[np.c_[xy,np.zeros(n)],np.c_[xy,np.full(n,row['heightAbovePcbMm'])]];faces=[]
 for i in range(1,n-1):faces.extend([[0,i+1,i],[n,n+i,n+i+1]])
 for i in range(n):j=(i+1)%n;faces.extend([[i,j,n+j],[i,n+j,n+i]])
 v=v@M[:3,:3].T+M[:3,3];packed('component_'+row['key'],v,faces,name='局部元件轮廓接收（非实物高度测量）',color='#6085b5',opacity=.25,envelope=True,lidMounted=False,flexible=False)
config={'version':'2026-10-08-final-200mm-local-s','description':'现有鸭头曲面、原下颌结构与当前相机固定件。','findings':['保留原下颌、轴支架和软垫；嘴部独立滑动环已装入模型。','Pi Zero W使用三处2mm垫圈和三颗M2.5×8螺丝；40针排针朝元件面。','200mm橙色排线的完整数字路径、自交与合盖检查通过；这是可调整的软线摆放示例。','实际安装先插好两端并扣紧锁片，再用自然缓弯整理余线；不必照着模型折出固定曲线。'],'boundary':'这里展示当前装配几何和排线示例。数字检查通过不等于实物、电机或运行调试完成；接收空间可单独查看，不能当作元件实物。','routeReceiptSha256':hashes[str(Q/'full-ribbon-acceptance.json')],'physicalValidated':False,'motorCommissioningAccepted':False,'runtimeAccepted':False}
payload={'parts':parts,'config':config};raw=json.dumps(payload,separators=(',',':'),ensure_ascii=False).encode();(D/'scene.json').write_bytes(raw);packeddata=base64.b64encode(gzip.compress(raw,mtime=0)).decode();del raw
lib=SIM/'microduck-simulator/app/node_modules/three';three=read(lib/'build/three.module.js').decode();match=re.search(r'export \{([^}]+)\};?\s*$',three);members=[]
for term in match.group(1).split(','):bits=term.strip().split(' as ');members.append(bits[-1]+':'+bits[0])
three=three[:match.start()]+'\nreturn {'+','.join(members)+'};'
orbit=read(lib/'examples/jsm/controls/OrbitControls.js').decode();orbit=re.sub(r"import\s*\{([^}]+)\}\s*from\s*'three';",r'const {\1}=THREE;',orbit,count=1);orbit=re.sub(r'export \{ OrbitControls \};?\s*$','return OrbitControls;',orbit)
u=read(lib/'examples/jsm/utils/BufferGeometryUtils.js').decode();crease=u[u.index('function toCreasedNormals('):u.index('\nexport {',u.index('function toCreasedNormals('))]
runtime='const THREE=(()=>{'+three+'})();const OrbitControls=(()=>{'+orbit+'})();const {Vector3,BufferAttribute}=THREE;'+crease+'\n(async()=>{const packed="'+packeddata+'";const raw=Uint8Array.from(atob(packed),c=>c.charCodeAt(0));const DATA=JSON.parse(await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream("gzip"))).text());\n'+read(D/'viewer.js').decode()+'\n})().catch(e=>{document.getElementById("status").textContent=e.message;console.error(e)});'
template=read(H/'review-template.html').decode();style=re.search(r'<style>(.*?)</style>',template,re.S).group(1)
html='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MicroDuck · 当前头部装配</title><style>'+style+'</style></head><body><header><small>MICRODUCK · 2026-10-08</small><h1>当前头部装配 · 200mm软排线</h1><p>原鸭头曲面 · 眼内相机 · Pi Zero W与2mm垫圈</p></header><nav><button id="front">正面</button><button id="threequarter">斜视</button><button id="side">侧面</button><button id="inside">查看内部</button><button id="lid">开盖位置</button><button id="ribbon" class="active">隐藏排线示例</button><button id="envelopes">查看接收空间</button></nav><main><div id="viewport" aria-label="当前头部互动装配模型"></div><aside><span class="pill">当前几何 · 数字检查通过</span><h2>主体不再改动</h2><ul id="findings"></ul><p class="note" id="boundary"></p><p id="status">正在加载模型…</p><footer>拖动旋转，滚轮缩放。橙色软排线只是摆放示例。<br>AI assistance was used to draft.</footer></aside></main><script>'+runtime+'</script></body></html>'
(D/'HEAD-EYE-REVIEW.html').write_text(html);read(Path(__file__))
manifest={'sourceHashes':hashes,'outputHashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in [D/'HEAD-EYE-REVIEW.html',D/'scene.json',D/'viewer.js']},'parts':len(parts),'partKeys':[p['key']for p in parts],'noCAD':True,'singleScene':True,'routeMeshSha256':accept['mesh']['sha256'],'scope':config,'removedObsoleteKeys':['jaw_passive_cheek','jaw_cheek_screw_1','jaw_cheek_screw_2','zero_w_populated_receiving','zero_w_gpio_male_receiving']}
(D/'viewer-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'parts':len(parts),'htmlBytes':len(html.encode()),'outputs':manifest['outputHashes']}))

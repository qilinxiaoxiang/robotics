"""Bundle exact candidate meshes into an offline, self-contained 3D review."""
from pathlib import Path
import json,base64,gzip,hashlib,re,shutil
import numpy as np
import trimesh
P=Path(__file__).resolve().parent
G=P.parent/'leg-guide-20261006'
SIM=P.parents[2]

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encode(a,typ):return base64.b64encode(np.asarray(a,dtype=typ).tobytes()).decode()
def from_mesh(key,name,color,m,**extra):
    return dict(key=key,name=name,color=color,center=m.bounds.mean(axis=0).tolist(),bounds=m.bounds.tolist(),positionB64=encode(m.vertices,'<f4'),indexB64=encode(m.faces.flatten(),'<u4'),triangles=len(m.faces),**extra)
def main():
    proto=json.loads((P/'preview-data.json').read_text())
    assert all(s['steps'] for s in proto['sides'].values()), 'assembly sequence not finalized'
    copy_path=P/'review-copy.json'
    if copy_path.exists():proto.update(json.loads(copy_path.read_text()))
    full=json.loads((G/'full-build-data.json').read_text()); old={p['key']:p for p in full['parts']}
    closure=json.loads((G/'closure-approach-investigation.json').read_text())
    data={k:proto[k] for k in ['fastenerSummary','fitNote','statusNote','rotationResult','checkSummary'] if k in proto};data['sides']={}
    for side,s in proto['sides'].items():
        parts=[]
        for p in s['parts']:
            path=Path(p['stl']);path=path if path.is_absolute() else P/path
            assert p['coordinateFrame']=='guide-world-mm'
            m=trimesh.load(path,force='mesh',process=False)
            hardware='screw' in p['key']
            display_names={'base':'Orange ankle base','cheek':'Removable orange side','sleeve':'Black sliding sleeve'}
            name=(side.title()+' · '+display_names[p['key'].split('_')[-1]]) if not hardware else p['name']
            filename=(path.name.replace('-world.stl','-PRINT.stl')+(' · orientation trial' if 'cheek' in p['key'] else '')) if not hardware else 'Hardware envelope · use listed screw'
            parts.append(from_mesh(p['key'],name,p['color'],m,isNew=not hardware,hardware=hardware,spec=next((f['spec'] for f in s.get('fasteners',[]) if f['key']==p['key']),None),filename=filename,colorName='Metal' if hardware else p.get('colorName','Black' if 'sleeve' in p['key'] else 'Orange'),sourceSha256=digest(path)))
        for key in s['contextKeys']:
            p=dict(old[key]);p.update(isNew=False,baseline=False);parts.append(p)
        for key in (['ankle','smallring'] if side=='left' else ['right_ankle','right_smallring']):
            p=dict(old[key]);p.update(key='old_'+key,name='Original · '+p['name'],isNew=False,baseline=True);parts.append(p)
        for f in s.get('fasteners',[]):
            # CAD owner may provide validated screw-envelope meshes directly.
            if f.get('stl'):
                path=Path(f['stl']);path=path if path.is_absolute() else P/path
                parts.append(from_mesh(f['key'],f.get('name',f['spec']), '#48524c',trimesh.load(path,force='mesh',process=False),isNew=False,hardware=True,spec=f['spec'],sourceSha256=digest(path)))
        data['sides'][side]={**s,'parts':parts,'lowerKey':'lower' if side=='left' else 'right_lower','baselineStop':closure['paths'][side+'-leg']['stopTranslation']}
        known={p['key'] for p in parts}
        short_titles=['Link','Case screws','Metal washer','Rear screw','Black sleeve','Into open base','Output screws','Close side','Side screws','Check fit','Yellow foot']
        for i,st in enumerate(s['steps']):
            if len(s['steps'])==len(short_titles):st.setdefault('shortTitle',short_titles[i])
            for field in ['title','text']:
                st[field]=st[field].replace('cheek','removable side').replace('boss','round post').replace('removable removable','removable')
            if i == 2:
                st['text'] = 'Place one silver metal washer (2.7 mm bore, 5 mm outside, 0.5 mm thick) under the rear-centre screw head. This is not the black printed sleeve. Purchase or receipt of this exact washer is not confirmed; check spare hardware or RoboClub stock.'
            st.setdefault('evidence',st.get('pathStatus','Model preview; printed fit and screw retention remain unverified.'))
            assert set(st['visibleKeys'])<=known, ('unknown visible',set(st['visibleKeys'])-known)
            assert set(st['movingKeys'])<=set(st['visibleKeys'])
    payload=json.dumps(data,separators=(',',':')).encode();packed=base64.b64encode(gzip.compress(payload,mtime=0)).decode()
    three_path=SIM/'microduck-simulator/app/node_modules/three'
    three=(three_path/'build/three.module.js').read_text();ex=re.search(r'export \{([^}]+)\};?\s*$',three)
    members=[]
    for term in ex.group(1).split(','):
        bits=term.strip().split(' as ');members.append(bits[-1]+':'+bits[0])
    three=three[:ex.start()]+'\nreturn {'+','.join(members)+'};'
    orbit=(three_path/'examples/jsm/controls/OrbitControls.js').read_text();orbit=re.sub(r"import\s*\{([^}]+)\}\s*from\s*'three';",r'const {\1}=THREE;',orbit,count=1);orbit=re.sub(r'export \{ OrbitControls \};?\s*$','return OrbitControls;',orbit)
    script='const THREE=(()=>{'+three+'})();\nconst OrbitControls=(()=>{'+orbit+'})();\n(async()=>{const raw=Uint8Array.from(atob("'+packed+'"),c=>c.charCodeAt(0));const DATA=JSON.parse(await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream("gzip"))).text());\n'+(P/'review-viewer.js').read_text()+'\n})().catch(e=>{document.getElementById("error").style.display="block";document.getElementById("error").textContent="Preview could not load: "+e.message;console.error(e);});'
    html=(P/'review-template.html').read_text().replace('/*__APP__*/',script)
    (P/'ANKLE-REDESIGN.html').write_text(html);(G/'ANKLE-REDESIGN.html').write_text(html)
    manifest={'dataSha256':hashlib.sha256(payload).hexdigest(),'htmlSha256':digest(P/'ANKLE-REDESIGN.html'),'prototypeSha256':digest(P/'preview-data.json'),'sourceHashes':{str(p):digest(p) for p in [P/'review-viewer.js',P/'review-template.html',P/'review-copy.json',G/'full-build-data.json',G/'closure-approach-investigation.json']},'sides':{k:{'parts':len(v['parts']),'steps':len(v['steps'])} for k,v in data['sides'].items()}}
    (P/'review-bundle.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('ANKLE_REDESIGN_PREVIEW_BUNDLE_PASS',json.dumps(manifest['sides']))
if __name__=='__main__':main()

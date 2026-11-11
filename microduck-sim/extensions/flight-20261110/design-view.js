// 3D view of the design pages (both languages). The page supplies #mesh (duck_poses.json), #pack (pack_meshes.json),
// #three-src (three.js module) and #i18n ({labels}); build_design.py inlines all four.
const THREE=await import(URL.createObjectURL(new Blob([document.getElementById('three-src').textContent],{type:'text/javascript'})));
const data=JSON.parse(document.getElementById('mesh').textContent);
const PK=JSON.parse(document.getElementById('pack').textContent);
const T=JSON.parse(document.getElementById('i18n').textContent);
const cv=document.getElementById('view'),stage=document.getElementById('stage');
const R=new THREE.WebGLRenderer({canvas:cv,antialias:true,preserveDrawingBuffer:true});R.setPixelRatio(Math.min(devicePixelRatio,2));
const scene=new THREE.Scene();scene.background=new THREE.Color(0xfbfaf7);
const cam=new THREE.PerspectiveCamera(32,1,10,6000);cam.up.set(0,0,1);
scene.add(new THREE.HemisphereLight(0xffffff,0xb8b2a4,1.15));
const sun=new THREE.DirectionalLight(0xffffff,1.6);sun.position.set(400,-300,700);scene.add(sun);
const fill=new THREE.DirectionalLight(0xffffff,.5);fill.position.set(-300,400,200);scene.add(fill);
const b64=(s,Tp)=>{const b=atob(s),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return new Tp(u.buffer)};
const meshOf=(p,mat)=>{let geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(b64(p.pos,Float32Array),3));
  geo.setIndex(new THREE.BufferAttribute(b64(p.idx,Uint32Array),1));geo=geo.toNonIndexed();geo.computeVertexNormals();return new THREE.Mesh(geo,mat)};
const col=c=>new THREE.Color().setRGB(c[0],c[1],c[2],THREE.SRGBColorSpace);
// the duck: one mesh per (body, colour), moved per pose by the exported body matrices
const bodies={};
for(const p of data.parts){const m=meshOf(p,new THREE.MeshStandardMaterial({color:col(p.color),roughness:.6,metalness:.05}));
  m.matrixAutoUpdate=false;(bodies[p.body]??=[]).push(m);scene.add(m)}
const grid=new THREE.GridHelper(900,18,0xbdb8aa,0xdedacf);grid.rotation.x=Math.PI/2;scene.add(grid);
// the pack: released CAD meshes in the stand-world frame, riding on the trunk
const pack=new THREE.Group();pack.matrixAutoUpdate=false;scene.add(pack);
const marks=new THREE.Group();marks.matrixAutoUpdate=false;scene.add(marks);       // A7Z ports: duck parts, always shown
const shells=[],jets=[];
for(const p of PK.parts){
  const o=p.group==='shell'?{transparent:true,opacity:.42,depthWrite:false}:{};
  const m=meshOf(p,new THREE.MeshStandardMaterial(Object.assign({color:col(p.color),roughness:.55,metalness:p.group==='fan'?.35:.08,side:THREE.DoubleSide},o)));
  if(p.group==='shell'){m.renderOrder=2;shells.push(m)}
  (p.group==='port'||p.group==='plug'?marks:pack).add(m)}
const jetM=new THREE.MeshStandardMaterial({color:0x4f8df5,transparent:true,opacity:.16,depthWrite:false});
for(const f of Object.values(PK.fans)){const a=new THREE.Vector3(...f.axis),lip=new THREE.Vector3(...f.lip);
  const ex=lip.clone().addScaledVector(a,f.t_end),L=ex.z/(-a.z)+30;
  const j=new THREE.Mesh(new THREE.CylinderGeometry(f.duct_od/2,f.duct_od/2+11,L,40,1,true),jetM);
  j.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),a.clone().negate());j.position.copy(ex).addScaledVector(a,L/2);jets.push(j);pack.add(j)}
const labels=Object.entries(T.labels).filter(([k])=>PK.anchors[k]).map(([k,t])=>{const e=document.createElement('div');e.className='lab';e.textContent=t;stage.appendChild(e);
  return{e,p:new THREE.Vector3(...PK.anchors[k]),port:k==='ports'}});
const mat=a=>new THREE.Matrix4().set(a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7],a[8],a[9],a[10],a[11],0,0,0,1);
let show={pack:true,shell:true,jet:true,lab:true},pose='stand';
function setPose(n){pose=n;const P=data.poses[n];for(const b in bodies)for(const m of bodies[b]){m.matrix.copy(mat(P[b]));m.matrixWorldNeedsUpdate=true}
  for(const g of[pack,marks]){g.matrix.copy(mat(P[data.trunk]));g.matrixWorldNeedsUpdate=true}
  document.querySelectorAll('[data-pose]').forEach(b=>b.classList.toggle('on',b.dataset.pose===n));window.__pose=n;draw()}
const tgt=new THREE.Vector3(-10,0,135);let az=-.9,el=.32,dist=innerWidth<600?980:700;
function draw(){const w=cv.clientWidth,h=cv.clientHeight,pr=R.getPixelRatio();if(cv.width!==Math.round(w*pr)||cv.height!==Math.round(h*pr)){R.setSize(w,h,false);cam.aspect=w/h;cam.updateProjectionMatrix()}
  pack.visible=show.pack;shells.forEach(s=>s.visible=show.shell);jets.forEach(j=>j.visible=show.jet&&pose==='stand');
  cam.position.set(tgt.x+dist*Math.cos(el)*Math.cos(az),tgt.y+dist*Math.cos(el)*Math.sin(az),tgt.z+dist*Math.sin(el));cam.lookAt(tgt);cam.updateMatrixWorld();R.render(scene,cam);
  // labels nearest the camera first; a label that would overlap one already placed is hidden (rotate to see it)
  const placed=[];
  const proj=labels.map(l=>{const wv=l.p.clone().applyMatrix4(pack.matrix);return{l,v:wv.clone().project(cam),d:wv.distanceTo(cam.position)}}).sort((a,b)=>a.d-b.d);
  for(const{l,v}of proj){let on=show.lab&&(show.pack||l.port)&&v.z<1;
    if(on){const x=(v.x+1)/2*w,y=(1-v.y)/2*h;l.e.style.display='block';l.e.style.left=x+'px';l.e.style.top=y+'px';
      const bw=l.e.offsetWidth,bh=l.e.offsetHeight,r=[x-bw/2-2,y-bh*1.2-2,x+bw/2+2,y-bh*.2+2];
      if(placed.some(q=>r[0]<q[2]&&r[2]>q[0]&&r[1]<q[3]&&r[3]>q[1]))on=false;else placed.push(r)}
    l.e.style.display=on?'block':'none'}}
const pts=new Map();let pinch=0;
cv.addEventListener('pointerdown',e=>{cv.setPointerCapture(e.pointerId);pts.set(e.pointerId,[e.clientX,e.clientY])});
cv.addEventListener('pointermove',e=>{if(!pts.has(e.pointerId))return;const p=pts.get(e.pointerId);
  if(pts.size===1){az-=(e.clientX-p[0])*.008;el=Math.max(-.2,Math.min(1.5,el+(e.clientY-p[1])*.006))}
  pts.set(e.pointerId,[e.clientX,e.clientY]);
  if(pts.size===2){const a=[...pts.values()],d=Math.hypot(a[0][0]-a[1][0],a[0][1]-a[1][1]);if(pinch)dist=Math.max(300,Math.min(2500,dist*pinch/d));pinch=d}draw()});
const up=e=>{pts.delete(e.pointerId);pinch=0};cv.addEventListener('pointerup',up);cv.addEventListener('pointercancel',up);
cv.addEventListener('wheel',e=>{e.preventDefault();dist=Math.max(300,Math.min(2500,dist*(1+Math.sign(e.deltaY)*.08)));draw()},{passive:false});
const views={iso:[-.9,.32],front:[0,.02],side:[-Math.PI/2,.02],back:[Math.PI,.15],top:[-Math.PI/2,1.5]};
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{[az,el]=views[b.dataset.view];draw()});
document.querySelectorAll('[data-pose]').forEach(b=>b.onclick=()=>setPose(b.dataset.pose));
for(const[id,k]of[['tPack','pack'],['tShell','shell'],['tJet','jet'],['tLab','lab']])document.getElementById(id).onclick=e=>{show[k]=!show[k];e.target.classList.toggle('on',show[k]);draw()};
addEventListener('resize',draw);
const q=new URLSearchParams(location.search);if(q.get('view')&&views[q.get('view')])[az,el]=views[q.get('view')];if(q.get('lab')==='0'){show.lab=false;document.getElementById('tLab').classList.remove('on')}
setPose(q.get('pose')||'stand');window.__ready=true;

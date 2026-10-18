const $=x=>document.getElementById(x),host=$('viewport');
const scene=new THREE.Scene();scene.background=new THREE.Color('#e8ede7');
const camera=new THREE.OrthographicCamera(-100,100,80,-80,.1,2500);camera.up.set(0,0,1);
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;host.append(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);scene.add(new THREE.HemisphereLight(0xffffff,0x617b64,2.5));
for(const pos of [[180,-160,260],[-150,80,180]]){const l=new THREE.DirectionalLight(0xffffff,2);l.position.set(...pos);scene.add(l)}
const meshes=[];let variant='candidate',inside=false,showPlugs=false;
function decode(s,T){const b=atob(s),v=new Uint8Array(b.length);for(let i=0;i<b.length;i++)v[i]=b.charCodeAt(i);return new T(v.buffer)}
function geo(p,prefix=''){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(decode(p[prefix?prefix+'PositionB64':'positionB64'],Float32Array),3));g.setIndex(new THREE.BufferAttribute(decode(p[prefix?prefix+'IndexB64':'indexB64'],Uint32Array),1));const creased=toCreasedNormals(g,Math.PI/6);g.dispose();return creased}
for(const p of DATA.parts){const m=new THREE.Mesh(geo(p),new THREE.MeshStandardMaterial({color:p.key==='camera_board'?'#244536':p.color,roughness:.72,transparent:!!p.opacity,opacity:p.opacity??1,depthWrite:!p.opacity}));m.userData={part:p,original:m.geometry,candidate:p.candidatePositionB64?geo(p,'candidate'):null,curved:p.originalCurvedPositionB64?geo(p,'originalCurved'):null};meshes.push(m);scene.add(m)}
function render(){renderer.render(scene,camera)}
function view(direction,name){controls.target.set(30,0,125);camera.position.copy(controls.target).add(new THREE.Vector3(...direction).normalize().multiplyScalar(340));controls.update();host.dataset.view=name;render()}
function update(){
 const candidate=variant==='candidate',original=variant==='original';
 const removed=new Set(DATA.config.removedParts||['camera_cradle','camera_pitch_foot']);
 const outer=new Set(['head_cap','head_bottom','face_panel','eye_trim','jaw_frame','upper_pad','lower_pad']);
 for(const m of meshes){const p=m.userData.part;m.matrixAutoUpdate=true;m.position.set(0,0,0);m.quaternion.identity();m.scale.set(1,1,1);
  m.visible=(!p.plugEnvelope||showPlugs)&&!(candidate&&removed.has(p.key))&&(!p.candidateOnly||candidate)&&(!original||outer.has(p.key));
  m.geometry=original&&m.userData.curved?m.userData.curved:candidate&&m.userData.candidate?m.userData.candidate:m.userData.original;
  if(candidate&&DATA.config.transforms?.[p.key]){m.matrix.fromArray(DATA.config.transforms[p.key].flat()).transpose();m.matrix.decompose(m.position,m.quaternion,m.scale)}
  if(inside&&!original&&['head_cap','face_panel','eye_trim'].includes(p.key))m.visible=false;
 }
 for(const key of ['candidate','baseline','original'])$(key).classList.toggle('active',variant===key);
 $('plugs').disabled=!candidate;$('plugs').classList.toggle('active',showPlugs&&candidate);$('inside').disabled=original;$('inside').classList.toggle('active',inside&&!original);
 $('title').textContent=candidate?'Original curves, eye-mounted camera':original?'Original community shell':'Rejected earlier box conversion';
 $('description').textContent=candidate?DATA.config.description:original?'The real curved community shell, with its original face and jaw outline. This is an exterior reference; it does not claim that the revised electronics fit unchanged.':'The earlier electronics integration replaced curved surfaces with a hollow rectangular box. This rejected shape is retained only to make the error visible.';
 const findings=candidate?DATA.config.findings:original?['No box added to the head.','Original shell geometry, not a rounded substitute.','Use the same view to compare the restored candidate.']:['The box was introduced before the eye-camera change.','Matching overall dimensions failed to preserve the curved surfaces.','This enclosure shape is not the proposed repair.'];
 $('findings').replaceChildren(...findings.map(t=>{const li=document.createElement('li');li.textContent=t;return li}));
 $('boundary').textContent=DATA.config.boundary;
 host.dataset.variant=variant;host.dataset.inside=String(inside&&!original);host.dataset.visibleKeys=JSON.stringify(meshes.filter(x=>x.visible).map(x=>x.userData.part.key));host.dataset.cameraTransform=JSON.stringify(candidate?(DATA.config.transforms.camera_board||null):null);
 host.dataset.plugClearance=String(showPlugs&&candidate);host.dataset.headGeometry=original?'community-curved':candidate?'restored-curved':'rejected-box';host.dataset.projection='orthographic';
 $('status').textContent=inside&&!original?'Internal layout: cap, face and eye trim hidden.':original?'Source curved shell · exterior reference':candidate?'Actual geometry · original curves preserved in candidate':'Rejected rectangular conversion · reference only';render();
}
$('candidate').onclick=()=>{variant='candidate';update()};$('baseline').onclick=()=>{variant='baseline';update()};$('original').onclick=()=>{variant='original';update()};$('inside').onclick=()=>{inside=!inside;update()};
$('plugs').onclick=()=>{showPlugs=!showPlugs;update()};
$('front').onclick=()=>view([1,0,0],'front');$('side').onclick=()=>view([0,-1,.05],'side');$('threequarter').onclick=()=>view([1,-1,.4],'threequarter');controls.addEventListener('change',render);
new ResizeObserver(()=>{const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h);camera.left=-80*w/h;camera.right=80*w/h;camera.top=80;camera.bottom=-80;camera.updateProjectionMatrix();render()}).observe(host);update();view([1,-1,.4],'threequarter');

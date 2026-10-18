const $=x=>document.getElementById(x),host=$('viewport');
const scene=new THREE.Scene();scene.background=new THREE.Color('#e8ede7');
const camera=new THREE.OrthographicCamera(-100,100,80,-80,.1,2500);camera.up.set(0,0,1);
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputColorSpace=THREE.SRGBColorSpace;host.append(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);scene.add(new THREE.HemisphereLight(0xffffff,0x617b64,2.5));
for(const pos of [[180,-160,260],[-150,80,180]]){const l=new THREE.DirectionalLight(0xffffff,2);l.position.set(...pos);scene.add(l)}
const meshes=[];let inside=false,cable=true,envelopes=false,lidOpen=false;
function decode(s,T){const b=atob(s),v=new Uint8Array(b.length);for(let i=0;i<b.length;i++)v[i]=b.charCodeAt(i);return new T(v.buffer)}
for(const p of DATA.parts){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(decode(p.positionB64,Float32Array),3));g.setIndex(new THREE.BufferAttribute(decode(p.indexB64,Uint32Array),1));const smooth=toCreasedNormals(g,Math.PI/6);g.dispose();const m=new THREE.Mesh(smooth,new THREE.MeshStandardMaterial({color:p.color||'#888888',roughness:.72,transparent:!!p.opacity,opacity:p.opacity??1,depthWrite:!p.opacity,side:p.flexible?THREE.DoubleSide:THREE.FrontSide}));m.userData.part=p;meshes.push(m);scene.add(m)}
function render(){renderer.render(scene,camera)}
function view(direction,name){controls.target.set(32,0,131);camera.position.copy(controls.target).add(new THREE.Vector3(...direction).normalize().multiplyScalar(340));controls.update();host.dataset.view=name;render()}
function update(){
 for(const m of meshes){const p=m.userData.part;m.visible=(!p.envelope||envelopes)&&(!p.flexible||cable)&&!(inside&&['head_cap','face_panel','eye_trim'].includes(p.key));m.position.set(0,0,lidOpen&&p.lidMounted?40:0)}
 for(const [id,on]of [['inside',inside],['ribbon',cable],['envelopes',envelopes],['lid',lidOpen]])$(id).classList.toggle('active',on);
 $('inside').textContent=inside?'显示外壳':'查看内部';$('ribbon').textContent=cable?'隐藏排线示例':'显示排线示例';$('lid').textContent=lidOpen?'合盖位置':'开盖位置';
 host.dataset.visibleKeys=JSON.stringify(meshes.filter(x=>x.visible).map(x=>x.userData.part.key));host.dataset.inside=String(inside);host.dataset.cable=String(cable);host.dataset.lidOpen=String(lidOpen);host.dataset.version=DATA.config.version;
 $('status').textContent=lidOpen?'盖上部件整体抬起40 mm；排线保留在头内。此按钮展示两端状态。':inside?'当前内部布局；外壳、面板和眼圈已隐藏。':'当前合盖布局；拖动旋转，滚轮缩放。';render();
}
$('inside').onclick=()=>{inside=!inside;update()};$('ribbon').onclick=()=>{cable=!cable;update()};$('envelopes').onclick=()=>{envelopes=!envelopes;update()};$('lid').onclick=()=>{lidOpen=!lidOpen;update()};
$('front').onclick=()=>view([1,0,0],'front');$('side').onclick=()=>view([0,-1,.05],'side');$('threequarter').onclick=()=>view([1,-1,.4],'threequarter');controls.addEventListener('change',render);
new ResizeObserver(()=>{const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h);camera.left=-80*w/h;camera.right=80*w/h;camera.top=80;camera.bottom=-80;camera.updateProjectionMatrix();render()}).observe(host);
$('findings').replaceChildren(...DATA.config.findings.map(t=>{const li=document.createElement('li');li.textContent=t;return li}));$('boundary').textContent=DATA.config.boundary;update();view([1,-1,.4],'threequarter');

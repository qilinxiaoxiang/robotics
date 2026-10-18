import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import * as THREE from '../../../microduck-simulator/app/node_modules/three/build/three.module.js';
import {toCreasedNormals} from '../../../microduck-simulator/app/node_modules/three/examples/jsm/utils/BufferGeometryUtils.js';
const dir=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(fs.readFileSync(path.join(dir,'../leg-guide-20261006/full-build-data.json')));
const rows=[];
for(const key of ['head_cap','face_panel','eye_trim']){
 const p=data.parts.find(p=>p.key===key);
 const vb=Buffer.from(p.positionB64,'base64'),ib=Buffer.from(p.indexB64,'base64');
 const vertices=new Float32Array(vb.buffer,vb.byteOffset,vb.byteLength/4).slice();
 const faces=new Uint32Array(ib.buffer,ib.byteOffset,ib.byteLength/4).slice();
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(vertices,3));g.setIndex(new THREE.BufferAttribute(faces,1));g.computeVertexNormals();
 const before=g.toNonIndexed(),after=toCreasedNormals(g,Math.PI/6);
 const a=before.attributes.position.array,b=after.attributes.position.array;
 const unchanged=a.length===b.length&&a.every((x,i)=>x===b[i]);
 const norm=after.attributes.normal.array,valid=norm.every(Number.isFinite);
 if(!unchanged||!valid)throw Error('Geometry changed or invalid normal: '+key);
 rows.push({key,triangles:a.length/9,triangleCoordinatesUnchanged:unchanged,finiteNormals:valid});
}
fs.writeFileSync(path.join(dir,'render-normal-verification.json'),JSON.stringify({passed:true,scope:'Crease-aware shading only; triangle positions and topology remain unchanged.',creaseDegrees:30,checks:rows},null,2)+'\n');
console.log('RENDER_NORMALS_GEOMETRY_UNCHANGED',rows.length);

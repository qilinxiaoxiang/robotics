// MicroDuck head extension: interactive exploded 3D view. THREE and OrbitControls are inlined before this script.
(async () => {
  'use strict';
  const D = JSON.parse(document.getElementById('head-data').textContent);
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const rich = (s) => esc(s).replace(/\{推测\}/g, '<span class="guess">推测</span>');
  const CLS = Object.fromEntries(D.classes.map((c) => [c.id, c]));
  const ITEM = Object.fromEntries(D.items.map((it) => [it.id, it]));
  const loading = $('#loading');
  const view = $('#view');
  const fail = (msg) => { loading.hidden = false; loading.textContent = msg; loading.classList.add('err'); };
  const GHOST = '#aab3b9';
  const mobileMQ = window.matchMedia('(max-width: 760px)');

  // ------------------------------------------------------------------ geometry
  if (!('DecompressionStream' in window)) { fail('这个浏览器不能解压模型数据（缺少 DecompressionStream）。请用新版 Chrome、Safari 或 Firefox 打开。'); return; }
  function b64bytes(s) {
    const bin = atob(s); const n = bin.length; const out = new Uint8Array(n);
    for (let i = 0; i < n; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  let buf;
  try {
    const raw = b64bytes(document.getElementById('head-geometry').textContent.trim());
    buf = await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  } catch (e) { fail('模型数据解压失败：' + e.message); return; }

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true });
  } catch (e) { fail('无法启动 3D 显示（WebGL）：' + e.message); return; }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0xfbfcfb, 1);
  view.prepend(renderer.domElement);
  renderer.domElement.setAttribute('aria-label', '头部 3D 模型，拖动旋转，点零件看说明');
  renderer.domElement.tabIndex = 0;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 4, 4000);
  camera.up.set(0, 0, 1);
  camera.position.set(400, -380, 330);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.12;
  controls.screenSpacePanning = true;
  controls.minDistance = 30;
  controls.maxDistance = 2000;
  controls.target.set(30, 0, 128);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x9aa3a8, 1.9));
  const key = new THREE.DirectionalLight(0xffffff, 1.9); key.position.set(0.8, -0.6, 1.3); scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 0.8); fill.position.set(-1, 0.9, 0.4); scene.add(fill);
  const rim = new THREE.DirectionalLight(0xffffff, 0.45); rim.position.set(0.2, 0.3, -1); scene.add(rim);

  const objs = [];
  let triCount = 0;
  for (const [i, rec] of D.meshes.entries()) {
    const it = ITEM[rec.item];
    let geo; let wts = null;
    if (rec.tube) {
      const curve = new THREE.CatmullRomCurve3(rec.tube.map((p) => new THREE.Vector3(p[0], p[1], p[2])), false, 'centripetal');
      const segs = Math.max(16, Math.ceil(curve.getLength() / 0.8));
      const radial = 10;
      geo = new THREE.TubeGeometry(curve, segs, rec.r, radial, false);
      if (rec.blocks) {
        const n = geo.attributes.position.count; wts = new Float32Array(n);
        for (let k = 0; k < n; k++) wts[k] = Math.floor(k / (radial + 1)) / segs;
      }
    } else {
      geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(buf, rec.pos[0], rec.pos[1]), 3));
      const I = rec.idx[2] === 2 ? Uint16Array : Uint32Array;
      geo.setIndex(new THREE.BufferAttribute(new I(buf, rec.idx[0], rec.idx[1]), 1));
      geo.computeVertexNormals();
      if (rec.blocks) {
        const n = geo.attributes.position.count; wts = new Float32Array(n);
        if (rec.w) { const u8 = new Uint8Array(buf, rec.w[0], rec.w[1]); for (let k = 0; k < n; k++) wts[k] = u8[k] / 255; }
      }
    }
    geo.computeBoundingBox(); geo.computeBoundingSphere();
    triCount += geo.index ? geo.index.count / 3 : geo.attributes.position.count / 3;
    const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.62, metalness: it.cls === 'screw' ? 0.35 : 0.03, side: THREE.DoubleSide });
    if (it.id === 'cap_added') { mat.polygonOffset = true; mat.polygonOffsetFactor = -1; mat.polygonOffsetUnits = -2; }
    const mesh = new THREE.Mesh(geo, mat);
    const o = { i, rec, it, mesh, mat, wts, base: wts ? geo.attributes.position.array.slice() : null, bb0: geo.boundingBox.clone(), pickable: true, ghost: false };
    mesh.userData.o = o;
    scene.add(mesh);
    objs.push(o);
  }

  // ------------------------------------------------------------------ state
  const state = { mode: 'status', capGhost: true, v18Ghost: false, orig: false, filterNew: false, vis: {}, sel: null, selMesh: null, explode: 0, target: 0 };
  for (const it of D.items) state.vis[it.id] = !it.hidden;
  let dirty = true;

  // ------------------------------------------------------------------ explode
  const LIFT = new THREE.Vector3(...D.lift);
  const clamp01 = (t) => (t < 0 ? 0 : t > 1 ? 1 : t);
  const ease = (t) => { t = clamp01(t); return t * t * (3 - 2 * t); };
  function disp(name, t, out) {
    out.set(0, 0, 0);
    const b = D.blocks[name];
    if (!b) return out;
    const a = ease(t * 2); const c = ease(t * 2 - 1);
    if (b.lift) out.addScaledVector(LIFT, a);
    out.x += b.off[0] * c; out.y += b.off[1] * c; out.z += b.off[2] * c;
    return out;
  }
  const vA = new THREE.Vector3(); const vB = new THREE.Vector3();
  function applyExplode(t) {
    for (const o of objs) {
      if (o.rec.blocks) {
        disp(o.rec.blocks[0], t, vA); disp(o.rec.blocks[1], t, vB);
        const attr = o.mesh.geometry.attributes.position; const arr = attr.array; const b = o.base; const w = o.wts;
        const dx = vB.x - vA.x; const dy = vB.y - vA.y; const dz = vB.z - vA.z;
        for (let k = 0, n = w.length; k < n; k++) {
          const j = 3 * k; const s = w[k];
          arr[j] = b[j] + vA.x + dx * s; arr[j + 1] = b[j + 1] + vA.y + dy * s; arr[j + 2] = b[j + 2] + vA.z + dz * s;
        }
        attr.needsUpdate = true;
        o.mesh.geometry.computeBoundingBox(); o.mesh.geometry.computeBoundingSphere();
      } else {
        disp(o.rec.block, t, o.mesh.position);
      }
    }
    dirty = true;
  }

  // ------------------------------------------------------------------ look
  function classColor(it) { return CLS[it.cls].color; }
  function applyLook() {
    for (const o of objs) {
      const it = o.it;
      let color = o.rec.ccol || classColor(it);
      if (it.cls === 'v18' && state.orig && o.rec.color) color = o.rec.color;
      let opacity = 1; let ghost = false;
      if (state.mode === 'wiring') {
        if (it.focus) color = o.rec.wcol || color;
        else { ghost = true; opacity = (it.id === 'cap' || it.id === 'cap_added') ? 0.05 : 0.1; }
      } else if (state.filterNew && (it.change === 'unchanged' || it.change === 'replaced')) {
        ghost = true; opacity = 0.08;
      } else if (it.id === 'cap' && state.capGhost) {
        opacity = 0.26;
      } else if (it.cls === 'v18' && state.v18Ghost) {
        opacity = 0.38;
      } else if (it.cls === 'context') {
        opacity = 0.5;
      }
      if (ghost) color = GHOST;
      o.mat.color.set(color);
      const transparent = opacity < 1;
      if (o.mat.transparent !== transparent) o.mat.needsUpdate = true;
      o.mat.transparent = transparent;
      o.mat.opacity = opacity;
      o.mat.depthWrite = !transparent;
      const side = transparent ? THREE.FrontSide : THREE.DoubleSide;
      if (o.mat.side !== side) { o.mat.side = side; o.mat.needsUpdate = true; }
      o.mesh.renderOrder = transparent ? (ghost ? 3 : 2) : 0;
      const sel = state.sel === it.id;
      o.mat.emissive.set(sel ? (state.selMesh === o.i ? '#ff9f1c' : '#ffbf47') : '#000000');
      o.mat.emissiveIntensity = sel ? (state.selMesh === o.i ? 0.55 : 0.32) : 0;
      o.mesh.visible = !!state.vis[it.id];
      o.ghost = ghost;
      o.pickable = o.mesh.visible && !ghost;
    }
    dirty = true;
  }

  // ------------------------------------------------------------------ camera framing
  function boxAt(t, filter) {
    const box = new THREE.Box3(); const tmp = new THREE.Box3(); const d = new THREE.Vector3();
    for (const o of objs) {
      if (!o.mesh.visible || !filter(o)) continue;
      if (o.rec.blocks) {
        for (const name of o.rec.blocks) { tmp.copy(o.bb0).translate(disp(name, t, d)); box.union(tmp); }
      } else {
        tmp.copy(o.bb0).translate(disp(o.rec.block, t, d)); box.union(tmp);
      }
    }
    if (box.isEmpty()) box.set(new THREE.Vector3(-30, -46, 98), new THREE.Vector3(92, 46, 158));
    return box;
  }
  const framed = (o) => (state.mode === 'wiring' ? o.it.focus : !o.ghost && o.it.cls !== 'context' && !o.it.noframe);
  // Distance along `dir` at which every corner of `box` fits the frustum (with a margin), looking at the box centre.
  function fit(box, dir, margin = 0.9) {
    const c = box.getCenter(new THREE.Vector3());
    const f = dir.clone().normalize();
    const right = new THREE.Vector3().crossVectors(camera.up, f);
    if (right.lengthSq() < 1e-8) right.set(0, 1, 0).cross(f);
    right.normalize();
    const up = new THREE.Vector3().crossVectors(f, right).normalize();
    const tv = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * margin;
    const th = tv * camera.aspect;
    let dist = 0; const p = new THREE.Vector3();
    for (let k = 0; k < 8; k++) {
      p.set(k & 1 ? box.max.x : box.min.x, k & 2 ? box.max.y : box.min.y, k & 4 ? box.max.z : box.min.z).sub(c);
      const z = p.dot(f);
      dist = Math.max(dist, z + Math.abs(p.dot(right)) / th, z + Math.abs(p.dot(up)) / tv);
    }
    return { target: c, pos: c.clone().addScaledVector(f, dist), dist };
  }
  function fitsInView(box) {
    const p = new THREE.Vector3();
    for (let k = 0; k < 8; k++) {
      p.set(k & 1 ? box.max.x : box.min.x, k & 2 ? box.max.y : box.min.y, k & 4 ? box.max.z : box.min.z).project(camera);
      if (Math.abs(p.x) > 0.98 || Math.abs(p.y) > 0.98 || p.z > 1) return false;
    }
    return true;
  }
  let tween = null;
  function flyTo(pos, target, ms = 550) {
    tween = { p0: camera.position.clone(), t0: controls.target.clone(), p1: pos, t1: target, start: performance.now(), ms };
    dirty = true;
  }
  function setView(name, ms = 550) {
    const dir = new THREE.Vector3(...D.views[name]);
    const f = fit(boxAt(state.target, framed), dir, name === 'wiring' ? 0.82 : 0.9);
    if (ms === 0) { camera.position.copy(f.pos); controls.target.copy(f.target); controls.update(); dirty = true; return; }
    flyTo(f.pos, f.target, ms);
  }
  function refitIfNeeded() {
    const box = boxAt(state.target, framed);
    if (fitsInView(box)) return;
    const f = fit(box, camera.position.clone().sub(controls.target));
    flyTo(f.pos, f.target, 500);
  }
  function frameItem(id) {
    const dir = camera.position.clone().sub(controls.target);
    const f = fit(boxAt(state.explode, (o) => o.it.id === id), dir, 0.7);
    flyTo(f.target.clone().addScaledVector(dir.normalize(), Math.max(f.dist, 90)), f.target, 500);
  }

  // ------------------------------------------------------------------ labels (wiring view)
  const labelHost = $('#labels'); const leaders = $('#leaders');
  const labelEls = D.labels.map((l) => {
    const el = document.createElement('div');
    el.className = 'lab'; el.textContent = l.text; el.style.borderColor = l.color;
    labelHost.appendChild(el);
    return el;
  });
  const v3 = new THREE.Vector3(); const dv = new THREE.Vector3();
  function layoutLabels() {
    const on = state.mode === 'wiring';
    labelHost.hidden = !on; leaders.style.display = on ? '' : 'none';
    if (!on) return;
    const W = view.clientWidth; const H = view.clientHeight;
    const rows = D.labels.map((l, k) => {
      v3.set(l.at[0], l.at[1], l.at[2]).add(disp(l.block, state.explode, dv)).project(camera);
      const el = labelEls[k];
      return { k, l, el, x: (v3.x + 1) / 2 * W, y: (1 - v3.y) / 2 * H, w: el.offsetWidth, h: el.offsetHeight, behind: v3.z > 1 };
    }).sort((a, b) => a.y - b.y);
    const placed = []; let svg = '';
    for (const r of rows) {
      if (r.behind) { r.el.style.display = 'none'; continue; }
      r.el.style.display = '';
      const right = r.x < W * 0.6;
      let bx = right ? r.x + 22 : r.x - 22 - r.w;
      bx = Math.max(4, Math.min(W - r.w - 4, bx));
      let by = Math.max(4, Math.min(H - r.h - 4, r.y - r.h / 2));
      for (let guard = 0; guard < 30; guard++) {
        const hit = placed.find((p) => bx < p.x + p.w + 3 && bx + r.w + 3 > p.x && by < p.y + p.h + 3 && by + r.h + 3 > p.y);
        if (!hit) break;
        by = hit.y + hit.h + 3;
        if (by + r.h > H - 4) { by = Math.max(4, hit.y - r.h - 3); bx = right ? Math.max(4, bx - 12) : bx + 12; }
      }
      placed.push({ x: bx, y: by, w: r.w, h: r.h });
      r.el.style.transform = `translate(${bx.toFixed(1)}px, ${by.toFixed(1)}px)`;
      const ex = bx + r.w / 2 < r.x ? bx + r.w : bx; const ey = by + r.h / 2;
      svg += `<line x1="${r.x.toFixed(1)}" y1="${r.y.toFixed(1)}" x2="${ex.toFixed(1)}" y2="${ey.toFixed(1)}" stroke="${r.l.color}" stroke-width="1.4"/>`
           + `<circle cx="${r.x.toFixed(1)}" cy="${r.y.toFixed(1)}" r="3.6" fill="${r.l.color}" stroke="#fff" stroke-width="1.4"/>`;
    }
    leaders.setAttribute('viewBox', `0 0 ${W} ${H}`);
    leaders.innerHTML = svg;
  }

  // ------------------------------------------------------------------ panels
  const tabInfo = $('#tab-info'); const tabList = $('#tab-list'); const tabWiring = $('#tab-wiring');
  const panel = $('#panel'); const panelBody = $('#panel-body');
  const sheetBtn = $('#sheet-toggle');
  sheetBtn.setAttribute('aria-label', '展开或收起说明');
  function setSheet(open) {
    panel.classList.toggle('open', open);
    sheetBtn.setAttribute('aria-expanded', String(open));
    $('#sheet-label').textContent = open ? '下拉收起' : '上拉看说明';
  }
  sheetBtn.addEventListener('click', () => setSheet(!panel.classList.contains('open')));
  function selectTab(name, openSheet = true) {
    for (const b of $$('.tabs [role=tab]')) b.setAttribute('aria-selected', String(b.dataset.tab === name));
    tabInfo.hidden = name !== 'info'; tabList.hidden = name !== 'list'; tabWiring.hidden = name !== 'wiring';
    panelBody.scrollTop = 0;
    if (openSheet && mobileMQ.matches) setSheet(true);
  }
  for (const b of $$('.tabs [role=tab]')) {
    b.addEventListener('click', () => {
      selectTab(b.dataset.tab);
      if (b.dataset.tab === 'wiring' && state.mode !== 'wiring') setMode('wiring');
    });
  }

  function defaultInfo() {
    tabInfo.innerHTML = `
<h2>怎么看</h2>
<ul>
<li>拖动旋转，滚轮或双指缩放，右键拖动或双指拖动平移。</li>
<li>拖「拆开」：前一半是头盖连同 Pi、功放、扬声器整体竖直抬起。真实掀头盖就是这样，因为这些东西都装在头盖上。后一半各零件再分开。</li>
<li>点模型上的零件，这里会写它叫什么、干什么、怎么固定、是不是新的。头盖半透明时，点到的是里面的零件。</li>
<li>「部件列表」里可以单独隐藏零件，或者只看新增和改动的。</li>
<li>「功放接线」只突出功放、扬声器和它们的线，标出每根线插 Pi 的哪个针。</li>
</ul>
<h2>头里改了什么</h2>
<ul>
<li><b>头盖重打</b>：后脑缺口补平，头顶开出声孔，里面加扬声器围框和功放短柱，Pi 立柱加固。</li>
<li><b>扬声器</b>回到头里，在头顶内侧靠后，用打印压板和 2 颗 M2×6 压住，中间垫 1 mm 泡棉。</li>
<li><b>功放</b>挂在头顶内侧正中，2 颗 M2×6；5 根杜邦线插到 Pi；板背面焊一只 100 kΩ 增益电阻（GAIN 到 Vin，增益 3 dB）。</li>
<li><b>颈部 8 根线</b>改从脖子里进头，用 4 个打印卡扣压住：躯干 S12-horn-025、俯仰支架 S11-horn-040、下巴支架 H-jaw_support-03、Pi 的 E-pi-04。四个都在本页里；下面两个在头以下，勾"显示脖子"能看到它们旁边的线。</li>
<li><b>螺丝</b>：卡扣耳片 2.0 mm 厚，所以 S12-horn-025、S11-horn-040、E-pi-04 从 M2×6 换成 M2×8，H-jaw_support-03 从 M2.5×6 换成 M2.5×8；压板 2 颗 M2×6，功放 2 颗 M2×6。全机 75 → 79 颗。</li>
</ul>
<h2>打印文件状态（V1.9）</h2>
<ul>
<li>头盖、扬声器压板和 4 个线卡扣已切片发布：zhengxia_MicroDuck_V1.9_2-files.zip，橙色一盘 7 件。躯干卡扣网格检查报的 1 组重合面是两片极小的针状面，文件水密，按原样发布。</li>
<li>切片前要定：四个卡扣的形状（还没确认、没试打）。扬声器围框只有 0.2 mm 间隙，建议先试打一小块。</li>
<li>功放、扬声器、Pi、插头和螺丝包络仍是研究模型，不是打印件。</li>
</ul>
<h2>模型对齐检查</h2>
<ul>${D.alignment.map((s) => `<li>${rich(s)}</li>`).join('')}</ul>
<p class="fine">标 <span class="guess">推测</span> 的是研究里的估算或推断，没有实测。数据来自 guide/print/ext-v19/（V1.9 打印件、route-v19.json、README）、guide/extension-20261012-neck-audio/ 下的研究文件、HANDOFF-20261013.md 和 V1.8 装配指南数据。坐标：x 向前，y 向左（鸭子自己的左边），z 向上，单位 mm。生成日期 ${esc(D.built)}。</p>`;
  }

  function showInfo(id, meshIdx) {
    const it = ITEM[id];
    const c = CLS[it.cls];
    const sub = meshIdx != null && D.meshes[meshIdx].sub ? D.meshes[meshIdx].sub : null;
    const subs = it.meshes.length > 1 ? it.meshes.map((m) => D.meshes[m].sub).filter(Boolean) : [];
    tabInfo.innerHTML = `
<div class="info-head"><span class="sw" style="background:${D.meshes[it.meshes[0]].ccol || c.color}"></span><h2>${esc(it.name)}</h2></div>
<div class="badges"><span class="badge b-${it.change}">${esc(D.changes[it.change])}</span><span class="badge">${esc(c.label)}</span></div>
${sub ? `<p class="sub">点到的是：${rich(sub)}</p>` : ''}
<h3>作用</h3><p>${rich(it.role)}</p>
<h3>怎么固定</h3><p>${rich(it.fix)}</p>
${subs.length ? `<h3>包含</h3><ul>${subs.map((s) => `<li>${rich(s)}</li>`).join('')}</ul>` : ''}
${it.notes.length ? `<h3>要注意</h3><ul>${it.notes.map((n) => `<li>${rich(n)}</li>`).join('')}</ul>` : ''}
<h3>来源</h3><p class="src">${it.src.map(esc).join('；')}</p>
<div class="actions">
<button type="button" class="btn" id="act-frame">镜头对准它</button>
<button type="button" class="btn" id="act-hide">隐藏它</button>
<button type="button" class="btn" id="act-clear">取消选择</button>
</div>`;
    $('#act-frame').addEventListener('click', () => { if (!state.vis[id]) setVisible(id, true); frameItem(id); if (mobileMQ.matches) setSheet(false); });
    $('#act-hide').addEventListener('click', () => { setVisible(id, false); select(null); });
    $('#act-clear').addEventListener('click', () => select(null));
  }

  function select(id, meshIdx = null, fromList = false) {
    state.sel = id; state.selMesh = meshIdx;
    applyLook();
    for (const li of $$('#tab-list li')) li.classList.toggle('sel', li.dataset.item === id);
    if (id) { showInfo(id, meshIdx); selectTab('info', true); } else { defaultInfo(); }
    if (id && fromList) frameItem(id);
  }

  function buildList() {
    let html = `<div class="list-tools"><label class="chk"><input type="checkbox" id="f-new"> 只看新增和改动（其余变淡影）</label>`
             + `<button type="button" class="btn sm" id="show-all">全部显示</button></div>`;
    for (const c of D.classes) {
      const its = D.items.filter((i) => i.cls === c.id);
      if (!its.length) continue;
      html += `<div class="grp"><div class="grp-head"><span class="sw" style="background:${c.color}"></span><span>${esc(c.label)}</span><span class="cnt">${its.length} 项</span></div><ul>`;
      for (const it of its) {
        html += `<li data-item="${it.id}"><input type="checkbox" class="vis" data-item="${it.id}" aria-label="显示 ${esc(it.name)}"${state.vis[it.id] ? ' checked' : ''}>`
              + `<button type="button" class="nm" data-item="${it.id}">${esc(it.name)}</button><span class="badge b-${it.change}">${esc(D.changes[it.change])}</span></li>`;
      }
      html += '</ul></div>';
    }
    tabList.innerHTML = html;
    for (const cb of $$('input.vis', tabList)) cb.addEventListener('change', () => setVisible(cb.dataset.item, cb.checked));
    for (const b of $$('button.nm', tabList)) b.addEventListener('click', () => { if (!state.vis[b.dataset.item]) setVisible(b.dataset.item, true); select(b.dataset.item, null, true); });
    $('#f-new').addEventListener('change', (e) => { state.filterNew = e.target.checked; syncListDim(); applyLook(); });
    $('#show-all').addEventListener('click', () => {
      for (const it of D.items) if (!it.hidden) state.vis[it.id] = true;
      syncChecks(); applyLook();
    });
  }
  function syncListDim() {
    for (const li of $$('#tab-list li')) {
      const it = ITEM[li.dataset.item];
      li.classList.toggle('dim', state.filterNew && (it.change === 'unchanged' || it.change === 'replaced'));
    }
  }
  function syncChecks() {
    for (const cb of $$('input.vis', tabList)) cb.checked = !!state.vis[cb.dataset.item];
    $('#t-neck').checked = D.items.filter((i) => i.context).every((i) => state.vis[i.id]);
    const g = $('#w-gnd14'); if (g) g.checked = !!state.vis.gnd14;
  }
  function setVisible(id, on) {
    state.vis[id] = on;
    syncChecks(); applyLook();
  }

  function buildWiring() {
    const W = D.wiring;
    const pinsUsed = new Set(W.jumpers.map((j) => j.sig));
    const resistorPins = new Set(W.resistorPins || []);
    tabWiring.innerHTML = `
<p>功放（MAX98357A）从 Pi 排针取电和数字音频，用 5 根母对母杜邦线，两头都是插的。扬声器两根引线一头焊在扬声器上，一头拧进功放的螺丝端子。</p>
<button type="button" class="btn primary" id="w-mode">打开功放接线视图</button>
<h3>功放 → Pi（5 根）</h3>
${W.jumpers.map((j) => `<div class="wcard"><span class="sw" style="background:${j.color}"></span><div><b>${esc(j.sig)} → Pi ${j.pin} 号针</b><span class="m">${esc(j.fn)} · 模型线长 ${esc(j.len)}</span></div></div>`).join('')}
<p class="fine">页面上的线色只为区分，扩展文件没有规定真实线色。线长是模型中心线的长度；现成 10 cm 杜邦线每根会多出 30–50 mm。</p>
<h3>功放排针顺序（从 −y 到 +y）</h3>
<div class="pins">${W.headerOrder.map((p) => `<span class="${pinsUsed.has(p) ? '' : resistorPins.has(p) ? 'res' : 'off'}">${esc(p)}${resistorPins.has(p) && !pinsUsed.has(p) ? '（电阻）' : ''}</span>`).join('')}</div>
<p>GAIN 不插线：板背面焊一只 100 kΩ 电阻接到 Vin 的针尾，增益 3 dB（不接是 9 dB），满幅约 0.40 W。SD 不接，左右声道混成单声道<span class="guess">推测</span>。软件音量上限 −3 dBFS<span class="guess">推测</span>，这时约 0.20 W。</p>
<h3>扬声器 → 功放</h3>
${W.spk.map((s) => `<div class="wcard"><span class="sw" style="background:${s.color}"></span><div><b>扬声器焊盘 → 功放螺丝端子</b><span class="m">文件里叫 ${esc(s.name)}</span></div></div>`).join('')}
<p>扬声器那头焊在扬声器自己的 2 个焊盘上，功放那头拧进 2 针 3.5 mm 螺丝端子。可选在中间加一对 2 针 JST-PH。先拧端子，再把功放装上头盖。</p>
<p class="warn">没有记录：端子哪一口是 +、扬声器哪个焊盘是 +。按功放板和扬声器上的标记接。</p>
<h3>GND 为什么用 34 号</h3>
<p>14 号也是 GND，但它在摄像头后面，线要从插头下面钻过去，离下头壳只有 0.70 mm，还要和 12 号线挤同一条道。34 号（或 39 号）走得宽松。BCLK 必须接 12 号：GPIO18 是 Pi 唯一的 PCM 时钟脚。</p>
<label class="chk"><input type="checkbox" id="w-gnd14"> 显示备选：GND 走 14 号针</label>
<h3>Pi 排针还接了什么（参考）</h3>
<ul>
<li>1、3、5、9 号：IMU（BNO085）的 I²C 线。按 Pi 标准针脚，1 号是 3.3 V，3 号 SDA，5 号 SCL，9 号 GND。</li>
<li>2 号 5 V、6 号 GND：Pi 供电，来自 DFR1202 降压板。</li>
<li>8 号 TXD → OpenRB J12 第 3 脚 Rx（绿线）；10 号 RXD ← J12 第 4 脚 Tx（白线）。</li>
<li>其余针空着。</li>
</ul>
<p class="fine">来源：guide/print/ext-v19/route-v19.json（audioWires）、guide/print/ext-v19/README.md（Connection methods）、bringup/build/audio-bench/README.md（增益电阻）、audio/README.md（Amplifier header、Every connection method）、audio/wires.json、V1.8 装配指南 cables、HANDOFF-20261013.md。</p>`;
    $('#w-mode').addEventListener('click', () => setMode(state.mode === 'wiring' ? 'status' : 'wiring'));
    $('#w-gnd14').addEventListener('change', (e) => setVisible('gnd14', e.target.checked));
  }

  function buildLegend() {
    const host = $('#legend');
    if (state.mode === 'wiring') {
      const W = D.wiring;
      host.innerHTML = W.jumpers.map((j) => `<span class="chip"><span class="sw" style="background:${j.color}"></span>${esc(j.sig)}（Pi ${j.pin}）</span>`).join('')
        + `<span class="chip"><span class="sw" style="background:${W.spk[0].color}"></span><span class="sw" style="background:${W.spk[1].color}"></span>扬声器引线</span>`
        + `<span class="chip"><span class="sw" style="background:#69c17d"></span>功放、扬声器、Pi（浅绿）</span>`
        + `<span class="chip"><span class="sw" style="background:${GHOST}"></span>其他零件（淡影）</span>`;
    } else {
      host.innerHTML = D.classes.filter((c) => c.id !== 'context' || D.items.some((i) => i.cls === 'context' && state.vis[i.id]))
        .map((c) => `<span class="chip"><span class="sw" style="background:${c.color}"></span>${esc(c.label)}</span>`).join('')
        + `<span class="chip"><span class="sw" style="background:${D.capAdded}"></span>黄色：头盖上新加的材料</span>`;
    }
  }

  function setMode(mode) {
    state.mode = mode;
    for (const b of $$('[data-mode]')) b.setAttribute('aria-pressed', String(b.dataset.mode === mode));
    $('#mode-badge').hidden = mode !== 'wiring';
    const wm = $('#w-mode'); if (wm) wm.textContent = mode === 'wiring' ? '回到按状态上色' : '打开功放接线视图';
    buildLegend();
    applyLook();
    if (mode === 'wiring') {
      setExplodeTarget(0);
      selectTab('wiring', false);
      setView('wiring', 650);
    } else {
      setView('home', 550);
    }
  }

  // ------------------------------------------------------------------ controls wiring
  const slider = $('#explode'); const sliderOut = $('#explode-val'); const toggleBtn = $('#explode-toggle');
  function setExplodeTarget(t) {
    state.target = clamp01(t);
    slider.value = String(Math.round(state.target * 100));
    sliderOut.textContent = slider.value + '%';
    toggleBtn.textContent = state.target > 0.5 ? '一键合上' : '一键拆开';
    dirty = true;
  }
  slider.addEventListener('input', () => setExplodeTarget(Number(slider.value) / 100));
  slider.addEventListener('change', () => refitIfNeeded());
  toggleBtn.addEventListener('click', () => {
    setExplodeTarget(state.target > 0.5 ? 0 : 1);
    const dir = camera.position.clone().sub(controls.target);
    const f = fit(boxAt(state.target, framed), dir);
    flyTo(f.pos, f.target, 900);
  });
  for (const b of $$('[data-view]')) b.addEventListener('click', () => setView(b.dataset.view));
  $('#reset-view').addEventListener('click', () => setView(state.mode === 'wiring' ? 'wiring' : 'home'));
  for (const b of $$('[data-mode]')) b.addEventListener('click', () => { if (state.mode !== b.dataset.mode) setMode(b.dataset.mode); });
  $('#t-cap').addEventListener('change', (e) => { state.capGhost = e.target.checked; applyLook(); });
  $('#t-v18ghost').addEventListener('change', (e) => { state.v18Ghost = e.target.checked; applyLook(); });
  $('#t-orig').addEventListener('change', (e) => { state.orig = e.target.checked; applyLook(); });
  $('#t-neck').addEventListener('change', (e) => {
    for (const it of D.items) if (it.context) state.vis[it.id] = e.target.checked;
    syncChecks(); buildLegend(); applyLook();
  });

  // picking
  const raycaster = new THREE.Raycaster(); const ndc = new THREE.Vector2();
  let down = null;
  renderer.domElement.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; });
  renderer.domElement.addEventListener('pointerup', (e) => {
    if (!down) return;
    const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y); const dt = performance.now() - down.t;
    down = null;
    if (moved > 6 || dt > 700) return;
    const r = renderer.domElement.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(ndc, camera);
    const hits = raycaster.intersectObjects(objs.filter((o) => o.pickable).map((o) => o.mesh), false);
    const hit = hits.find((h) => !h.object.material.transparent) || hits[0];
    if (hit) select(hit.object.userData.o.it.id, hit.object.userData.o.i);
    else if (state.sel) select(null);
  });

  // ------------------------------------------------------------------ render loop
  function resize() {
    const w = Math.max(1, view.clientWidth); const h = Math.max(1, view.clientHeight);
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
    dirty = true;
  }
  new ResizeObserver(resize).observe(view);
  resize();

  let last = performance.now();
  function frame(now) {
    const dt = Math.min(0.1, (now - last) / 1000); last = now;
    if (Math.abs(state.target - state.explode) > 0.0005) {
      state.explode += (state.target - state.explode) * Math.min(1, dt * 6.5);
      if (Math.abs(state.target - state.explode) <= 0.0005) state.explode = state.target;
      applyExplode(state.explode);
    }
    if (tween) {
      const k = ease((now - tween.start) / tween.ms);
      camera.position.lerpVectors(tween.p0, tween.p1, k);
      controls.target.lerpVectors(tween.t0, tween.t1, k);
      if (k >= 1) tween = null;
      dirty = true;
    }
    if (controls.update()) dirty = true;
    if (dirty) { renderer.render(scene, camera); layoutLabels(); dirty = false; }
    requestAnimationFrame(frame);
  }

  buildList(); buildWiring(); buildLegend(); defaultInfo();
  applyExplode(0); applyLook();
  setView('home', 0);
  loading.hidden = true;
  requestAnimationFrame(frame);

  // Hooks for the headless probe (probe_head3d.mjs). Not used by the page itself.
  window.__head3d = {
    ready: true,
    meshes: objs.length,
    triangles: triCount,
    setExplode(v, instant = false) { setExplodeTarget(v); if (instant) { state.explode = state.target; applyExplode(state.explode); } },
    explode: () => state.explode,
    setMode,
    setView: (n) => setView(n, 0),
    select: (id) => select(id),
    state: () => ({ mode: state.mode, explode: state.explode, target: state.target, sel: state.sel, visible: objs.filter((o) => o.mesh.visible).length }),
    sample() {
      renderer.render(scene, camera);
      const gl = renderer.getContext(); const w = gl.drawingBufferWidth; const h = gl.drawingBufferHeight;
      const px = new Uint8Array(w * h * 4); gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px);
      let n = 0; for (let i = 0; i < px.length; i += 4) if (Math.abs(px[i] - 251) + Math.abs(px[i + 1] - 252) + Math.abs(px[i + 2] - 251) > 12) n++;
      return { w, h, nonBackground: n, fraction: n / (w * h) };
    },
    screenOf(id) {
      const box = boxAt(state.explode, (o) => o.it.id === id); const c = box.getCenter(new THREE.Vector3()).project(camera);
      const r = renderer.domElement.getBoundingClientRect();
      return { x: r.left + (c.x + 1) / 2 * r.width, y: r.top + (1 - c.y) / 2 * r.height };
    },
  };
})();

/* MicroDuck step-by-step assembly guide viewer.
 *
 * Runs inside the single HTML file produced by guide/build_guide.py. Expects:
 *   - globals THREE and OrbitControls (three.js r164.1, inlined by the bundler);
 *   - a data block with id guide-data:     gzip+base64 guide JSON (schemaVersion 1);
 *   - a data block with id guide-geometry: gzip+base64 binary; parts[].geom = [posOffset, posBytes, idxOffset, idxBytes].
 * Parts that still carry positionB64 / indexB64 are decoded directly (useful for hand-built test data).
 */
(() => {
'use strict';

const STATUS_LABEL = {
  assembled: 'Already assembled', printed: 'Printed', reprint: 'Reprint needed',
  'new-print': 'New print', purchased: 'Purchased', owned: 'Owned'
};
const PREP_KIND_LABEL = {
  fastener: 'Fastener', printed: 'Printed part', electronic: 'Electronics', tool: 'Tool', cable: 'Cable', other: 'Other'
};
const CABLE_KIND_LABEL = {
  dxl: 'DYNAMIXEL bus', 'power-20v': '12 V power', 'power-15v': '15 V power', 'power-7v': '7 V power', 'power-5v': '5 V power', ground: 'Ground', usb: 'USB', uart: 'UART link',
  i2c: 'I²C', i2s: 'I²S audio', speaker: 'Speaker', csi: 'Camera CSI ribbon', touch: 'Touch sensor wire'
};
const HIGHLIGHT = 0x1e7bf0;
const ADD_GLOW = 0.14;          // steady self-glow on parts added in this step; the hue stays the print colour
const ADD_GLOW_MOVING = 0.45;   // glow while a part travels along its approach
const MUTED_MIX = 0.6;          // parts from earlier chapters: print colour mixed this far toward the background
const MUTED_TO = 0xdfe3e8;
const SMALL_PART_MM = 15;       // added parts smaller than this (bounding radius) also get a locator box
const MAX_LOCATOR_BOXES = 6;    // more small parts than this in one step: outline only, no boxes
const MAX_PART_LABELS = 14;     // name tags drawn for the parts added in a step
// Screw colours by specification; assigned in order of first appearance so a spec keeps its colour on every step.
const SCREW_COLORS = ['#e8590c', '#2f9e44', '#7048e8', '#0c8599', '#c2255c', '#f08c00', '#1c7ed6', '#5c940d', '#862e9c', '#495057'];
const CTX_MODES = ['ghost', 'solid', 'hidden'];
const REF_ASPECT = 1.6;           // authored cameras are framed for a 16:10 viewer
const KIT_GAP_MM = 14;            // spacing between parts on an "Identify the parts" layout
const PARTS_SHARE = 0.62;         // timeline fraction spent placing parts when the step also drives screws
const HEX = /^#[0-9a-fA-F]{6}$/;
const reduceMotion = (() => { try { return matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; } })();
const narrowQuery = (() => { try { return matchMedia('(max-width: 860px)'); } catch (e) { return { matches: false }; } })();

/* ---------------------------------------------------------------- helpers */
const $ = (id) => document.getElementById(id);
function h(tag, props, ...kids) {
  const n = document.createElement(tag);
  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (v == null || v === false) continue;
      if (k === 'class') n.className = v;
      else if (k === 'text') n.textContent = v;
      else if (k.startsWith('on') && typeof v === 'function') n.addEventListener(k.slice(2), v);
      else if (typeof v === 'boolean') n[k] = v;
      else if (k.startsWith('--')) n.style.setProperty(k, v);
      else n.setAttribute(k, String(v));
    }
  }
  for (const c of kids.flat(Infinity)) {
    if (c == null || c === false) continue;
    n.append(c instanceof Node ? c : String(c));
  }
  return n;
}
const SVGNS = 'http://www.w3.org/2000/svg';
function icon(paths, cls) {
  const s = document.createElementNS(SVGNS, 'svg');
  s.setAttribute('viewBox', '0 0 24 24'); s.setAttribute('aria-hidden', 'true');
  if (cls) s.setAttribute('class', cls);
  for (const d of paths) { const p = document.createElementNS(SVGNS, 'path'); p.setAttribute('d', d); s.append(p); }
  return s;
}
const ICON_CHECK = ['M5 12.5l4.5 4.5L19 7.5'];
const ICON_CHEVRON = ['M6 9l6 6 6-6'];
const ICON_WARN = ['M12 3.5l9.5 16.5h-19z', 'M12 10v4.5', 'M12 17.6v.1'];
const ICON_CLOSE = ['M6 6l12 12M18 6L6 18'];
const ICON_PARTS = ['M4 4h7v7H4z', 'M13 4h7v7h-7z', 'M4 13h7v7H4z', 'M13 13h7v7h-7z'];
const ICON_SCREW = ['M8 4h8v4H8z', 'M10 8v11l2 2 2-2V8', 'M10 11h4M10 14h4M10 17h4'];
const SCREW_KIND_TEXT = { tap: 'Self-tapping (TAP), cuts its own thread in plastic', machine: 'Machine screw', 'machine-nut': 'Machine screw with nut' };
function screwDesc(s) {
  return [SCREW_KIND_TEXT[String(s.kind || '').toLowerCase()] || s.kind || '', s.nut ? 'nut: ' + s.nut : '', s.washer ? 'washer: ' + s.washer : ''].filter(Boolean).join(' · ');
}
const pad2 = (n) => String(n).padStart(2, '0');
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const colorOf = (c, fallback = '#9aa3ad') => (typeof c === 'string' && HEX.test(c) ? c : fallback);
const isVec3 = (v) => Array.isArray(v) && v.length === 3 && v.every((x) => typeof x === 'number' && Number.isFinite(x));
// An approach is one offset [dx,dy,dz] or a list of waypoints; either way the part ends seated at [0,0,0].
const toPath = (v) => {
  if (isVec3(v)) return [v, [0, 0, 0]];
  if (!Array.isArray(v) || !v.length || !v.every(isVec3)) return null;
  const pts = v.map((x) => x.slice());
  if (pts[pts.length - 1].some((x) => x !== 0)) pts.push([0, 0, 0]);
  return pts.length > 1 ? pts : null;
};
// Offset along a waypoint path at progress e (0 = first waypoint, 1 = seated), legs timed by their length.
function pathAt(path, e) {
  const lens = [];
  let total = 0;
  for (let k = 1; k < path.length; k++) { const l = Math.hypot(...path[k].map((x, j) => x - path[k - 1][j])); lens.push(l); total += l; }
  if (total <= 0) return path[path.length - 1];
  let d = e * total;
  for (let k = 0; k < lens.length; k++) {
    if (d <= lens[k] || k === lens.length - 1) {
      const t = lens[k] > 0 ? Math.min(1, d / lens[k]) : 1;
      return path[k].map((x, j) => x + (path[k + 1][j] - x) * t);
    }
    d -= lens[k];
  }
  return path[path.length - 1];
}
// Let the status text paint; a hidden tab gets no frames, so do not wait longer than 100 ms.
const nextFrame = () => new Promise((r) => { requestAnimationFrame(() => r()); setTimeout(r, 100); });
// Yield to the event loop without waiting for a frame, so a guide opened in a background tab keeps building.
const yieldTask = (() => {
  if (typeof MessageChannel !== 'function') return () => new Promise((r) => setTimeout(r, 0));
  const ch = new MessageChannel(); const queue = [];
  ch.port1.onmessage = () => { const r = queue.shift(); if (r) r(); };
  return () => new Promise((r) => { queue.push(r); ch.port2.postMessage(0); });
})();
const slug = (s) => String(s || 'guide').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'guide';
function fmtQty(q) {
  if (q == null || q === '') return '';
  return typeof q === 'number' ? '×' + q : String(q);
}
function statusPill(status) {
  if (!status) return null;
  return h('span', { class: 'status status-' + String(status).replace(/[^a-z-]/g, ''), text: STATUS_LABEL[status] || status });
}

/* A to-scale side view of one screw: 4 px per mm, head on the left. */
function screwIcon(s, color) {
  const k = 4;
  const d = s.diameterMm > 0 ? s.diameterMm : (parseFloat(String(s.spec).replace(/^M/, '')) || 2);
  const L = s.lengthMm > 0 ? s.lengthMm : 6;
  const hd = s.headDiameterMm > 0 ? s.headDiameterMm : d * 1.9;
  const hh = s.headHeightMm > 0 ? s.headHeightMm : d * 0.7;
  const w = (hh + L) * k + 2; const ht = hd * k + 2;
  const svg = document.createElementNS(SVGNS, 'svg');
  svg.setAttribute('viewBox', '0 0 ' + w + ' ' + ht); svg.setAttribute('width', String(w)); svg.setAttribute('height', String(ht));
  svg.setAttribute('class', 'screw-icon'); svg.setAttribute('aria-hidden', 'true');
  const rect = (x, y, rw, rh, fill) => { const r = document.createElementNS(SVGNS, 'rect'); for (const [a, v] of Object.entries({ x, y, width: rw, height: rh, fill, rx: 0.8 })) r.setAttribute(a, String(v)); svg.append(r); };
  rect(1, 1, hh * k, hd * k, color);
  rect(1 + hh * k, 1 + (hd - d) * k / 2, L * k, d * k, color);
  for (let x = 1 + hh * k + 3; x < 1 + (hh + L) * k - 1; x += 3) rect(x, 1 + (hd - d) * k / 2, 1, d * k, 'rgba(255,255,255,0.55)');
  return svg;
}

/* localStorage: per-viewer conveniences only; every access may throw. */
const store = {
  get(key, fallback) {
    try { const raw = window.localStorage.getItem(key); return raw == null ? fallback : JSON.parse(raw); } catch (e) { return fallback; }
  },
  set(key, value) { try { window.localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* unavailable: keep in memory */ } },
  remove(key) { try { window.localStorage.removeItem(key); } catch (e) { /* ignore */ } }
};

/* --------------------------------------------------------------- payloads */
function b64ToBytes(text) {
  const bin = atob(text);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
async function gunzip(bytes) {
  if (typeof DecompressionStream !== 'function') {
    throw new Error('This browser cannot unpack the guide (DecompressionStream missing). Use a current Chrome, Edge, Firefox or Safari 16.4+.');
  }
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  return new Response(stream).arrayBuffer();
}
async function readPayload(id) {
  const node = $(id);
  if (!node) return null;
  const text = node.textContent;
  node.remove();
  return gunzip(b64ToBytes(text.trim()));
}

/* ------------------------------------------------------------ guide model */
function prepareGuide(data) {
  if (!data || !Array.isArray(data.parts) || !Array.isArray(data.steps)) throw new Error('Guide data is missing parts or steps.');
  const parts = data.parts;
  const byKey = new Map();
  const byModule = new Map();
  parts.forEach((p, i) => {
    byKey.set(p.key, i);
    if (p.module) { if (!byModule.has(p.module)) byModule.set(p.module, []); byModule.get(p.module).push(i); }
  });
  const cables = Array.isArray(data.cables) ? data.cables : [];
  const cableById = new Map(cables.map((c, i) => [c.id, i]));
  const problems = [];
  const screws = (Array.isArray(data.screws) ? data.screws : []).filter((s, k) => {
    const ok = s && typeof s.step === 'string' && typeof s.spec === 'string' && isVec3(s.center) && isVec3(s.axis);
    if (!ok) problems.push('screw ' + k + ': needs step, spec, center and axis');
    return ok;
  });
  const specColor = new Map();
  for (const s of screws) if (!specColor.has(s.spec)) specColor.set(s.spec, SCREW_COLORS[specColor.size % SCREW_COLORS.length]);
  const screwsByStep = new Map();
  screws.forEach((s, k) => { if (!screwsByStep.has(s.step)) screwsByStep.set(s.step, []); screwsByStep.get(s.step).push(k); });
  const resolve = (list, where) => {
    const out = new Set();
    for (const ref of Array.isArray(list) ? list : []) {
      let hit = false;
      if (byKey.has(ref)) { out.add(byKey.get(ref)); hit = true; }
      if (byModule.has(ref)) { for (const i of byModule.get(ref)) out.add(i); hit = true; }
      if (!hit) problems.push(where + ': unknown part or module "' + ref + '"');
    }
    return out;
  };

  const chapters = (Array.isArray(data.chapters) ? data.chapters : []).map((c) => ({ id: c.id, title: c.title || c.id, summary: c.summary || '', steps: [] }));
  const chapterById = new Map(chapters.map((c) => [c.id, c]));
  for (const s of data.steps) {
    let ch = chapterById.get(s.chapter);
    if (!ch) {
      problems.push('step ' + s.id + ': unknown chapter "' + s.chapter + '"');
      ch = chapterById.get('__other');
      if (!ch) { ch = { id: '__other', title: 'Other steps', summary: '', steps: [] }; chapters.push(ch); chapterById.set(ch.id, ch); }
    }
    ch.steps.push(s);
  }
  const live = chapters.filter((c) => c.steps.length);
  live.forEach((c, i) => { c.index = i; });

  const steps = [];
  for (const ch of live) {
    const chapterCables = [];
    ch.steps.forEach((raw, k) => {
      const where = 'step ' + raw.id;
      const add = resolve(raw.add, where + ' add');
      const show = resolve(raw.show, where + ' show');
      const ctx = resolve(raw.context, where + ' context');
      for (const i of add) { show.delete(i); ctx.delete(i); }
      for (const i of show) ctx.delete(i);
      const approach = new Map();
      for (const [ref, vec] of Object.entries(raw.approach || {})) {
        const path = toPath(vec);
        if (!path) { problems.push(where + ' approach ' + ref + ': expected [dx,dy,dz] or a list of them'); continue; }
        const targets = resolve([ref], where + ' approach');
        for (const i of targets) if (add.has(i)) approach.set(i, path);
      }
      // A group moves a bench subassembly into place as one rigid body.
      const groupPath = raw.group ? toPath(raw.group.approach) : null;
      const group = raw.group && typeof raw.group.label === 'string' && groupPath ? { ...raw.group, path: groupPath } : null;
      if (raw.group && !group) problems.push(where + ' group: expected {label, approach: [dx,dy,dz] or a list of them}');
      if (group) for (const i of add) approach.set(i, groupPath);
      // A pose turns listed parts about an axis for this step (the jaw held open); with `from` it swings to `deg` as the step plays.
      let pose = null;
      if (raw.pose) {
        const pr = raw.pose;
        if (isVec3(pr.pivot) && isVec3(pr.axis) && Number.isFinite(pr.deg)) {
          pose = { set: resolve(pr.parts || [], where + ' pose'), pivot: pr.pivot, axis: pr.axis, deg: pr.deg,
            from: Number.isFinite(pr.from) ? pr.from : pr.deg };
        } else problems.push(where + ' pose: expected {parts, pivot, axis, deg[, from]}');
      }
      // A flex springs a part's two arms apart along Y while it moves in, then lets them snap back (the one-piece jaw
      // spread over the shell walls). Vertices beyond |y| ramp[1] move by the full spread, none inside ramp[0]. An optional
      // shift slides the whole part (and its riders) along Y by that amount at full spread, as a jaw held loosely does.
      let flex = null;
      if (raw.flex) {
        const fr = raw.flex;
        const ok2 = (v) => Array.isArray(v) && v.length === 2 && v.every(Number.isFinite);
        if (ok2(fr.ramp) && ok2(fr.spread) && ok2(fr.window)) {
          const riders = new Map();
          for (const [k, sgn] of Object.entries(fr.riders || {})) for (const i of resolve([k], where + ' flex rider')) riders.set(i, Math.sign(sgn));
          const shift = Number.isFinite(fr.shift) ? fr.shift : 0;
          flex = { set: resolve(fr.parts || [], where + ' flex'), riders, ramp: fr.ramp, spread: fr.spread, shift, window: fr.window };
        } else problems.push(where + ' flex: expected {parts, ramp: [a, b], spread: [-y, +y], window: [in, out], riders[, shift]}');
      }
      const hi = [];
      for (const id of Array.isArray(raw.cables) ? raw.cables : []) {
        if (cableById.has(id)) hi.push(cableById.get(id)); else problems.push(where + ': unknown cable "' + id + '"');
      }
      const faint = new Set(chapterCables.filter((c) => !hi.includes(c)));
      for (const c of hi) if (!chapterCables.includes(c)) chapterCables.push(c);
      const step = {
        raw, id: String(raw.id), title: raw.title || raw.id, chapter: ch, indexInChapter: k,
        add, show, ctx, approach, group, pose, flex, cables: hi, faintCables: faint,
        screws: screwsByStep.get(String(raw.id)) || [],
        number: steps.length + 1
      };
      step.search = [
        raw.title, ...(raw.instructions || []), ...(raw.checks || []), ...(raw.warnings || []),
        ...(raw.prepare || []).map((p) => p && p.item), ...[...add].map((i) => parts[i].name),
        ...hi.map((c) => cables[c].label), ...(screwsByStep.get(String(raw.id)) || []).map((k) => screws[k].spec), ch.title
      ].filter(Boolean).join(' \n ').toLowerCase();
      steps.push(step);
    });
  }
  const stepById = new Map(steps.map((s) => [s.id, s]));
  for (const [id, list] of screwsByStep) if (!stepById.has(id)) problems.push(list.length + ' screws name unknown step "' + id + '"');

  // The chapter that first installs each part: its "Identify the parts" page lists it, later chapters draw it muted.
  // Chapters marked intro: false only lay out the inventory, so they install nothing.
  const rawChapter = new Map((Array.isArray(data.chapters) ? data.chapters : []).map((c) => [c.id, c]));
  const inventoryOnly = (ch) => !!(rawChapter.get(ch.id) && rawChapter.get(ch.id).intro === false);
  // Bench steps (servo ID checks, the harness, the neck before it goes in) do not install anything on the robot yet.
  const introChapter = new Array(parts.length).fill(-1);
  for (const s of steps) if (!inventoryOnly(s.chapter) && !s.raw.bench) for (const i of s.add) if (introChapter[i] < 0) introChapter[i] = s.chapter.index;
  const pages = [];
  for (const ch of live) {
    const own = steps.filter((s) => s.chapter === ch);
    ch.stepList = own;
    // Kit: what goes on the desk for this chapter, i.e. every part it adds that is not already on the robot.
    // One entry per subassembly, otherwise one per distinct part (same name, colour and status = one entry ×N).
    const kit = []; const byName = new Map(); const claimed = new Set();
    for (const s of own) {
      const fresh = [...s.add].filter((i) => (introChapter[i] < 0 || introChapter[i] >= ch.index) && !claimed.has(i));
      if (s.group) {
        if (fresh.length) { kit.push({ label: s.group.label, parts: fresh, group: true, step: s }); fresh.forEach((i) => claimed.add(i)); }
        continue;
      }
      for (const i of fresh) {
        claimed.add(i);
        const p = parts[i]; const name = p.kit || p.name || p.key; const k = name + '|' + p.color + '|' + (p.status || '');
        if (byName.has(k)) byName.get(k).parts.push(i);
        else { const e = { label: name, parts: [i], group: false, step: s }; byName.set(k, e); kit.push(e); }
      }
    }
    ch.kit = kit;
    ch.screws = own.flatMap((s) => s.screws);
    // Loose fasteners and tools written as prepare items, summed by item text.
    const prep = new Map();
    for (const s of own) for (const it of s.raw.prepare || []) {
      if (!it || !it.item || (it.kind !== 'fastener' && it.kind !== 'tool')) continue;
      const e = prep.get(it.item) || { item: it.item, kind: it.kind, qty: 0, steps: [] };
      if (typeof it.qty === 'number') e.qty += it.qty; else if (it.qty) e.qtyText = String(it.qty);
      e.steps.push(s); prep.set(it.item, e);
    }
    ch.loose = [...prep.values()];
    const intro = !inventoryOnly(ch);
    if (intro && kit.length) pages.push({ kind: 'parts', id: 'parts-' + ch.id, chapter: ch, title: 'Identify the parts' });
    if (intro && (ch.screws.length || ch.loose.length)) pages.push({ kind: 'screws', id: 'screws-' + ch.id, chapter: ch, title: 'Prepare screws and tools' });
    for (const s of own) { s.kind = 'step'; pages.push(s); }
  }
  pages.forEach((pg, k) => { pg.page = k; });
  const pageById = new Map(pages.map((pg) => [pg.id, pg]));
  return { data, parts, byKey, cables, screws, specColor, chapters: live, steps, stepById, pages, pageById, introChapter, problems };
}

/* ----------------------------------------------------------------- viewer */
async function createViewer(container, guide, geoBuf, progress) {
  const { parts, cables } = guide;
  const canvas = h('canvas', { 'aria-label': '3D model of the current assembly step', role: 'img', tabindex: '0' });
  container.prepend(canvas);
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  } catch (e) {
    canvas.remove();
    throw new Error('WebGL is not available here, so the 3D view cannot be shown. The written steps still work.');
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0xeef1f4, 1);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 1, 8000);
  camera.up.set(0, 0, 1);                       // frame: x forward, y left, z up
  camera.position.set(400, 300, 260);
  scene.add(camera);
  const hemi = new THREE.HemisphereLight(0xffffff, 0xcfc9bf, 1.45);
  hemi.position.set(0, 0, 1);
  scene.add(hemi);
  const key = new THREE.DirectionalLight(0xffffff, 1.85);   // head light follows the camera
  key.position.set(-1.2, 1.6, 1.0);
  key.target.position.set(0, 0, -4);
  camera.add(key, key.target);
  const fill = new THREE.DirectionalLight(0xffffff, 0.55);
  fill.position.set(-0.6, -0.9, -0.5);
  scene.add(fill);

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.14;
  controls.screenSpacePanning = true;
  controls.minDistance = 8;
  controls.maxDistance = 4000;
  controls.zoomSpeed = 1.1;

  /* parts: build once, toggle per step */
  const n = parts.length;
  const meshes = new Array(n).fill(null);
  const mats = new Array(n);
  const centers = new Array(n);
  const radii = new Array(n).fill(0);
  const sceneBox = new THREE.Box3();
  const modelGroup = new THREE.Group();
  scene.add(modelGroup);
  let triangles = 0;
  let t0 = performance.now();
  for (let i = 0; i < n; i++) {
    const p = parts[i];
    let pos = null; let idx = null;
    if (Array.isArray(p.geom) && geoBuf) {
      const [po, pl, io, il] = p.geom;
      pos = new Float32Array(geoBuf, po, pl / 4);
      idx = new Uint32Array(geoBuf, io, il / 4);
    } else if (p.positionB64 && p.indexB64) {
      pos = new Float32Array(b64ToBytes(p.positionB64).buffer);
      idx = new Uint32Array(b64ToBytes(p.indexB64).buffer);
    }
    const color = new THREE.Color(colorOf(p.color));
    mats[i] = { color, solid: null, ghost: null, add: null, muted: null };
    if (pos && idx && pos.length >= 9 && idx.length >= 3) {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      geo.setIndex(new THREE.BufferAttribute(idx, 1));
      geo.computeVertexNormals();
      geo.computeBoundingBox();
      geo.computeBoundingSphere();
      // Source meshes are welded; flat shading keeps their planar faces crisp instead of pillow-shaded.
      // Some source meshes mix triangle windings; draw both sides so no shell renders as a hollow cage.
      mats[i].solid = new THREE.MeshStandardMaterial({ color, roughness: 0.6, metalness: 0.04, flatShading: true, side: THREE.DoubleSide });
      const mesh = new THREE.Mesh(geo, mats[i].solid);
      mesh.visible = false;
      mesh.userData.part = i;
      meshes[i] = mesh;
      modelGroup.add(mesh);
      centers[i] = geo.boundingBox.getCenter(new THREE.Vector3());
      radii[i] = geo.boundingSphere.radius;
      sceneBox.union(geo.boundingBox);
      triangles += idx.length / 3;
    } else if (Array.isArray(p.bounds) && isVec3(p.bounds[0]) && isVec3(p.bounds[1])) {
      const b = new THREE.Box3(new THREE.Vector3(...p.bounds[0]), new THREE.Vector3(...p.bounds[1]));
      centers[i] = b.getCenter(new THREE.Vector3());
      radii[i] = b.getSize(new THREE.Vector3()).length() / 2;
    } else {
      centers[i] = new THREE.Vector3();
    }
    if (performance.now() - t0 > 35) { progress(i + 1, n); await yieldTask(); t0 = performance.now(); }
  }
  progress(n, n);

  function material(i, kind) {
    const m = mats[i];
    if (kind === 'ghost') {
      if (!m.ghost) m.ghost = new THREE.MeshStandardMaterial({ color: m.color, roughness: 0.9, metalness: 0, transparent: true, opacity: 0.16, depthWrite: false, flatShading: true });
      return m.ghost;
    }
    if (kind === 'add') {
      if (!m.add) m.add = new THREE.MeshStandardMaterial({ color: m.color, roughness: 0.55, metalness: 0.04, emissive: m.color.clone().lerp(new THREE.Color(0xffffff), 0.35), emissiveIntensity: ADD_GLOW, flatShading: true, side: THREE.DoubleSide });
      return m.add;
    }
    if (kind === 'muted') {
      if (!m.muted) m.muted = new THREE.MeshStandardMaterial({ color: m.color.clone().lerp(new THREE.Color(MUTED_TO), MUTED_MIX), roughness: 0.85, metalness: 0, flatShading: true, side: THREE.DoubleSide });
      return m.muted;
    }
    return m.solid;
  }

  /* ground grid under the model */
  if (!sceneBox.isEmpty()) {
    const size = sceneBox.getSize(new THREE.Vector3());
    const extent = Math.ceil((Math.max(size.x, size.y) * 1.6) / 20) * 20 + 40;
    const grid = new THREE.GridHelper(extent, extent / 10, 0xc3cad2, 0xdbe0e6);
    grid.rotation.x = Math.PI / 2;               // GridHelper lies in XZ; rotate into the XY plane (z up)
    const c = sceneBox.getCenter(new THREE.Vector3());
    grid.position.set(Math.round(c.x / 10) * 10, Math.round(c.y / 10) * 10, sceneBox.min.z - 0.5);
    grid.material.transparent = true; grid.material.opacity = 0.75; grid.material.depthWrite = false;
    grid.renderOrder = -1;
    scene.add(grid);
  }

  /* cables: tubes built once */
  const cableGroup = new THREE.Group();
  scene.add(cableGroup);
  const cableObjs = cables.map((c, ci) => {
    const pts = (Array.isArray(c.path) ? c.path : []).filter(isVec3).map((v) => new THREE.Vector3(...v));
    if (pts.length < 2) return null;
    const curve = new THREE.CatmullRomCurve3(pts, false, 'centripetal');
    const len = curve.getLength();
    const segs = clamp(Math.round(len / 1.2), 24, 800);
    const r = typeof c.radius === 'number' && c.radius > 0 ? c.radius : 0.9;
    const color = new THREE.Color(colorOf(c.color, '#444c55'));
    const hiMat = new THREE.MeshStandardMaterial({ color, roughness: 0.45, metalness: 0, emissive: color, emissiveIntensity: 0.12 });
    const faintMat = new THREE.MeshStandardMaterial({ color, roughness: 0.6, transparent: true, opacity: 0.3, depthWrite: false });
    const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, segs, r, 10, false), hiMat);
    const capGeo = new THREE.SphereGeometry(r * 1.9, 16, 12);
    const capA = new THREE.Mesh(capGeo, hiMat); capA.position.copy(pts[0]);
    const capB = new THREE.Mesh(capGeo, hiMat); capB.position.copy(pts[pts.length - 1]);
    const pick = new THREE.Mesh(new THREE.TubeGeometry(curve, Math.max(16, Math.round(segs / 3)), Math.max(r * 3, 3.2), 6, false), hiMat);
    pick.userData.cable = ci;
    const group = new THREE.Group();
    group.add(tube, capA, capB);
    group.visible = false;
    cableGroup.add(group);
    return { group, tube, caps: [capA, capB], pick, hiMat, faintMat, ends: [pts[0], pts[pts.length - 1]], mid: curve.getPointAt(0.5), len, state: 'off' };
  });

  /* screws: head + shank, built once; the head seat sits on `center` and the shank runs along `axis` */
  const { screws, specColor } = guide;
  const screwGroup = new THREE.Group();
  scene.add(screwGroup);
  const yUp = new THREE.Vector3(0, 1, 0);
  const geoCache = new Map();
  const cyl = (r1, r2, len, seg) => {
    const k = [r1, r2, len, seg].map((x) => x.toFixed(2)).join('/');
    if (!geoCache.has(k)) geoCache.set(k, new THREE.CylinderGeometry(r1, r2, len, seg));
    return geoCache.get(k);
  };
  const installedMat = new THREE.MeshStandardMaterial({ color: 0x8d949c, roughness: 0.35, metalness: 0.7 });
  const specMats = new Map();
  for (const [spec, c] of specColor) specMats.set(spec, new THREE.MeshStandardMaterial({ color: new THREE.Color(c), roughness: 0.4, metalness: 0.3, emissive: new THREE.Color(c), emissiveIntensity: 0.25 }));
  const stepNumber = new Map(guide.steps.map((s) => [s.id, s.number]));
  const screwObjs = screws.map((s, k) => {
    const axis = new THREE.Vector3(...s.axis).normalize();
    const d = s.diameterMm > 0 ? s.diameterMm : (parseFloat(String(s.spec).replace(/^M/, '')) || 2);
    const L = s.lengthMm > 0 ? s.lengthMm : 6;
    const hd = s.headDiameterMm > 0 ? s.headDiameterMm : d * 1.9;
    const hh = s.headHeightMm > 0 ? s.headHeightMm : d * 0.7;
    const head = new THREE.Mesh(cyl(hd / 2, hd / 2, hh, 20), installedMat);
    head.position.set(0, -hh / 2, 0);
    const shank = new THREE.Mesh(cyl(d * 0.46, d * 0.34, L, 12), installedMat);
    shank.position.set(0, L / 2, 0);
    const g = new THREE.Group();
    g.add(head, shank);
    g.quaternion.setFromUnitVectors(yUp, axis);
    const home = new THREE.Vector3(...s.center);
    g.position.copy(home);
    g.visible = false;
    g.userData.screw = k;
    screwGroup.add(g);
    const keys = [s.throughPart, s.intoPart].filter((x) => guide.byKey.has(x)).map((x) => guide.byKey.get(x));
    return { g, head, shank, axis, home, L, hh, q0: g.quaternion.clone(), label: null, keys, through: guide.byKey.get(s.throughPart),
      into: guide.byKey.get(s.intoPart),
      step: stepNumber.get(s.step) || Infinity };
  });
  const screwAnchors = [];
  // A screw through a posed part (the jaw horn screws) turns with it; `back` pulls it out along its axis and `off`
  // carries it with its part along that part's approach path.
  function placeScrew(o, back, off) {
    o.g.position.copy(o.home).addScaledVector(o.axis, -back);
    o.g.quaternion.copy(o.q0);
    if (poseNow && o.through != null && poseNow.set.has(o.through)) {
      const q = poseQuat(poseNow.angle);
      o.g.position.sub(poseNow.pivot).applyQuaternion(q).add(poseNow.pivot);
      o.g.quaternion.premultiply(q);
    }
    if (off) { o.g.position.x += off[0]; o.g.position.y += off[1]; o.g.position.z += off[2]; }
  }
  function setScrewState(k, state, number) {
    const o = screwObjs[k];
    o.g.visible = state !== 'off';
    placeScrew(o, 0);
    const m = state === 'current' ? specMats.get(screws[k].spec) : installedMat;
    o.head.material = m; o.shank.material = m;
    if (o.label) { o.label.remove(); o.label = null; }
    if (state === 'current' && number != null) {
      o.label = h('div', { class: 'screw-label', '--c': specColor.get(screws[k].spec), text: String(number), title: screws[k].spec });
      labelsEl.append(o.label);
      screwAnchors.push({ el: o.label, point: o.home.clone().addScaledVector(o.axis, -(o.hh + 1.2)), obj: o });
    }
  }
  // `list` is drawn in its spec colour (numbered when asked); screws from steps before `before` stay grey when their part shows.
  function showScrews(list, before, numbered) {
    screwAnchors.length = 0;
    const cur = new Set(list);
    screwObjs.forEach((o, k) => {
      if (cur.has(k)) return;
      // A finished screw shows only on a solid part; on a ghosted context part it would float in mid-air.
      const visibleOwner = o.keys.length === 0 || o.keys.some((i) => role[i] === 'show' || role[i] === 'add' || (role[i] === 'ctx' && ctxMode === 'solid'));
      setScrewState(k, o.step < before && visibleOwner ? 'installed' : 'off');
    });
    list.forEach((k, j) => setScrewState(k, 'current', numbered ? j + 1 : null));
  }

  /* part name tags */
  let partLabelsOn = true;
  const partAnchors = [];
  function clearPartLabels() { for (const a of partAnchors) a.el.remove(); partAnchors.length = 0; }
  function showPartLabels(step) {
    clearPartLabels();
    if (!partLabelsOn) return;
    if (step.group) {
      const box = new THREE.Box3();
      for (const i of step.add) if (meshes[i]) box.union(meshes[i].geometry.boundingBox);
      if (!box.isEmpty()) {
        const el = h('div', { class: 'part-label', text: step.group.label });
        labelsEl.append(el); partAnchors.push({ el, point: box.getCenter(new THREE.Vector3()), part: [...step.add][0] });
      }
      return;
    }
    const list = [...step.add].filter((i) => meshes[i]).sort((a, b) => radii[b] - radii[a]).slice(0, MAX_PART_LABELS);
    for (const i of list) {
      const el = h('div', { class: 'part-label', text: parts[i].name || parts[i].key });
      labelsEl.append(el); partAnchors.push({ el, point: centers[i], part: i });
    }
  }

  /* pose: parts turned about an axis for one step (the jaw held open) */
  let poseNow = null;           // {set, pivot, axisV, from, deg, angle}
  const qTmp = new THREE.Quaternion();
  const poseQuat = (deg) => qTmp.setFromAxisAngle(poseNow.axisV, THREE.MathUtils.degToRad(deg));
  const vTmp = new THREE.Vector3();
  // Place part i at approach offset `off` ([dx,dy,dz] or null), turned by the current pose when it belongs to it.
  function placePart(i, off) {
    const mesh = meshes[i];
    if (!mesh) return;
    mesh.quaternion.identity();
    if (off) mesh.position.set(off[0], off[1], off[2]); else mesh.position.set(0, 0, 0);
    if (poseNow && poseNow.set.has(i) && poseNow.angle !== 0) {
      const q = poseQuat(poseNow.angle);
      mesh.quaternion.copy(q);
      // x' = R (x - p) + p + off  ->  position = off + p - R p
      vTmp.copy(poseNow.pivot).applyQuaternion(q);
      mesh.position.add(poseNow.pivot).sub(vTmp);
    }
  }
  /* flex: a part's arms sprung apart for one step */
  let flexNow = null;
  const flexBase = new Map();   // part index -> its undeformed vertex positions
  // Spread fraction at eased progress e: rises over [0, in], held, released over [out, 1] as the part snaps home.
  const flexAt = (f, e) => (e <= 0 || e >= 1 ? 0 : e < f.window[0] ? e / f.window[0] : e <= f.window[1] ? 1 : (1 - e) / (1 - f.window[1]));
  function bendPart(i, a) {
    const mesh = meshes[i];
    if (!mesh) return;
    const pos = mesh.geometry.attributes.position;
    let base = flexBase.get(i);
    if (!base) { if (!a) return; base = pos.array.slice(); flexBase.set(i, base); }
    const [r0, r1] = flexNow ? flexNow.ramp : [0, 1];
    const [sn, sp] = flexNow ? flexNow.spread : [0, 0];
    const sh = flexNow ? flexNow.shift : 0;
    for (let k = 0; k < pos.count; k++) {
      const y = base[3 * k + 1], ay = Math.abs(y);
      const w = ay <= r0 ? 0 : ay >= r1 ? 1 : (ay - r0) / (r1 - r0);
      pos.array[3 * k + 1] = y + ((y < 0 ? -sn : sp) * w + sh) * a;
    }
    pos.needsUpdate = true;
  }
  function setFlex(step) {
    for (const [i, base] of flexBase) { meshes[i].geometry.attributes.position.array.set(base); meshes[i].geometry.attributes.position.needsUpdate = true; }
    flexNow = step && step.flex ? step.flex : null;
  }
  function setPose(step) {
    poseNow = step && step.pose ? { set: step.pose.set, pivot: new THREE.Vector3(...step.pose.pivot),
      axisV: new THREE.Vector3(...step.pose.axis).normalize(), from: step.pose.from, deg: step.pose.deg, angle: step.pose.deg } : null;
  }

  /* step state */
  let ctxMode = 'ghost';
  let current = null;           // the step on screen; null on a chapter page
  let page = null;              // the step or chapter page on screen
  let pageChapter = -1;         // chapter index of the page; earlier chapters are drawn muted
  let role = new Array(n).fill('off');
  let camTween = null;
  let currentView = null;
  let dirty = true;
  const arrows = new THREE.Group();
  scene.add(arrows);
  const boxes = new Map();
  const outlines = new Map();
  // Added parts get a screen-constant blue silhouette: an inverted hull pushed out along the computed vertex normals.
  const outlineWidth = { value: 1 };
  const outlineMat = new THREE.MeshBasicMaterial({ color: HIGHLIGHT, side: THREE.BackSide });
  outlineMat.onBeforeCompile = (shader) => {
    shader.uniforms.outlineWidth = outlineWidth;
    shader.vertexShader = 'uniform float outlineWidth;\n' + shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n\ttransformed += normalize( normal ) * outlineWidth;');
  };
  outlineMat.customProgramCacheKey = () => 'guide-outline';

  function setPartRole(i, r) {
    const mesh = meshes[i];
    role[i] = r;
    if (!mesh) return;
    mesh.position.set(0, 0, 0);
    mesh.quaternion.identity();
    const box = boxes.get(i);
    if (box) box.visible = false;
    const hull = outlines.get(i);
    if (hull) hull.visible = false;
    if (r === 'off' || (r === 'ctx' && ctxMode === 'hidden')) { mesh.visible = false; return; }
    mesh.visible = true;
    mesh.renderOrder = 0;
    if (r === 'add') {
      const m = material(i, 'add');
      m.opacity = 1; m.emissiveIntensity = ADD_GLOW; if (m.transparent) { m.transparent = false; m.needsUpdate = true; }
      mesh.material = m;
      let b = boxes.get(i);
      const fewSmall = current && !current.group && [...current.add].filter((j) => radii[j] < SMALL_PART_MM).length <= MAX_LOCATOR_BOXES;
      if (!b && radii[i] < SMALL_PART_MM && fewSmall) {
        b = new THREE.Box3Helper(mesh.geometry.boundingBox.clone().expandByScalar(1.5), new THREE.Color(HIGHLIGHT));
        b.material.transparent = true; b.material.opacity = 0.7; b.material.depthWrite = false; b.material.depthTest = false;
        b.renderOrder = 9;
        mesh.add(b); boxes.set(i, b);
      }
      if (b) b.visible = fewSmall;
      let o = outlines.get(i);
      if (!o) { o = new THREE.Mesh(mesh.geometry, outlineMat); o.raycast = () => {}; mesh.add(o); outlines.set(i, o); }
      o.visible = true;
    } else if (r === 'ctx' && ctxMode === 'ghost') {
      mesh.material = material(i, 'ghost');
      mesh.renderOrder = 1;
    } else if (r === 'show' && pageChapter >= 0 && guide.introChapter[i] < pageChapter) {
      mesh.material = material(i, 'muted');
    } else {
      mesh.material = material(i, 'solid');
    }
  }
  function setOutline(i, on) {
    const mesh = meshes[i];
    if (!mesh) return;
    let o = outlines.get(i);
    if (!o && on) { o = new THREE.Mesh(mesh.geometry, outlineMat); o.raycast = () => {}; mesh.add(o); outlines.set(i, o); }
    if (o) o.visible = on;
  }

  function setCableState(ci, s) {
    const o = cableObjs[ci];
    if (!o) return;
    o.state = s;
    o.group.visible = s !== 'off';
    const m = s === 'faint' ? o.faintMat : o.hiMat;
    o.tube.material = m;
    o.tube.renderOrder = s === 'faint' ? 2 : 0;
    for (const cap of o.caps) cap.visible = s === 'hi';
  }

  function clearArrows() {
    for (const a of [...arrows.children]) {
      arrows.remove(a);
      a.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
    }
  }
  function buildArrows(step) {
    clearArrows();
    const entries = [...step.approach];
    let groupCentre = null;
    if (step.group) {
      // One arrow for the whole subassembly, from its combined centre.
      const box = new THREE.Box3();
      for (const i of step.add) if (meshes[i]) box.union(meshes[i].geometry.boundingBox);
      if (!box.isEmpty()) { groupCentre = box.getCenter(new THREE.Vector3()); entries.splice(0, entries.length, [[...step.add][0], step.group.path]); }
    }
    for (const [i, path] of entries) {
      if (!meshes[i]) continue;
      const c = groupCentre || centers[i];
      // One arrow per leg of the path, pointing the way the part travels; only the last leg ends in a head.
      for (let k = 0; k + 1 < path.length; k++) {
        const a = new THREE.Vector3(...path[k]);
        const b = new THREE.Vector3(...path[k + 1]);
        const dir = b.clone().sub(a);
        const len = dir.length();
        if (len < 0.5) continue;
        const last = k + 2 === path.length;
        const head = last ? Math.min(8, len * 0.3) : 0.001;
        const arrow = new THREE.ArrowHelper(dir.normalize(), c.clone().add(a), len, HIGHLIGHT, head, last ? head * 0.55 : 0.001);
        arrow.traverse((o) => {
          if (o.material) { o.material.depthTest = false; o.material.transparent = true; o.material.opacity = 0.75; }
          o.renderOrder = 10;
        });
        arrows.add(arrow);
      }
    }
  }

  /* cameras */
  const v1 = new THREE.Vector3();
  function hfov() { return 2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect); }
  function fitDistance(radius) {
    const f = Math.min(THREE.MathUtils.degToRad(camera.fov), hfov());
    return radius / Math.sin(f / 2);
  }
  function focusSphere(step, which) {
    const box = new THREE.Box3();
    const sets = which === 'add' && step.add.size ? [step.add] : [step.add, step.show];
    for (const set of sets) for (const i of set) {
      if (meshes[i]) box.union(meshes[i].geometry.boundingBox);
      else if (radii[i]) box.expandByPoint(centers[i]);
    }
    for (const ci of step.cables) if (cableObjs[ci]) for (const e of cableObjs[ci].ends) box.expandByPoint(e);
    if (box.isEmpty()) box.copy(sceneBox.isEmpty() ? new THREE.Box3(new THREE.Vector3(-50, -50, -50), new THREE.Vector3(50, 50, 50)) : sceneBox);
    return box.getBoundingSphere(new THREE.Sphere());
  }
  function stepView(step) {
    const cam = step.raw.camera;
    if (cam && isVec3(cam.position) && isVec3(cam.target)) {
      const pos = new THREE.Vector3(...cam.position);
      const target = new THREE.Vector3(...cam.target);
      if (camera.aspect < REF_ASPECT) {
        // Narrow viewer: back off only as far as needed to keep the added parts in frame.
        const dir = pos.clone().sub(target);
        const d = dir.length();
        const sphere = focusSphere(step, 'add');
        const need = fitDistance(sphere.radius) * 0.95 + sphere.center.distanceTo(target);
        const d2 = Math.max(d, Math.min(d * (REF_ASPECT / camera.aspect), need));
        if (d > 0 && d2 > d) pos.copy(target).add(dir.multiplyScalar(d2 / d));
      }
      return { pos, target };
    }
    const sphere = focusSphere(step, 'all');
    const dir = new THREE.Vector3(1, 0.9, 0.7).normalize();
    const d = fitDistance(Math.max(sphere.radius, 10)) * 1.08;
    return { pos: sphere.center.clone().add(dir.multiplyScalar(d)), target: sphere.center.clone() };
  }
  function flyTo(view, instant) {
    if (instant || reduceMotion) {
      camTween = null;
      camera.position.copy(view.pos); controls.target.copy(view.target); controls.update();
      dirty = true;
      return;
    }
    camTween = { t0: performance.now(), dur: 650, fromPos: camera.position.clone(), fromTarget: controls.target.clone(), toPos: view.pos.clone(), toTarget: view.target.clone() };
  }
  controls.addEventListener('start', () => { camTween = null; hideHint(); });
  controls.addEventListener('change', () => { dirty = true; });

  /* step timeline: 0 = parts back along their approach and screws out, 1 = everything seated */
  let tl = null;
  const onProgress = [];
  function buildTimeline(step) {
    const items = [...step.add].filter((i) => meshes[i]).map((i) => ({ i, path: step.approach.get(i) || null }));
    const ks = step.screws.slice();
    const posed = step.pose ? [...step.pose.set].filter((i) => meshes[i] && role[i] !== 'off' && !step.add.has(i)) : [];
    const swing = !!(step.pose && step.pose.from !== step.pose.deg);
    const stagger = items.length > 1 && !step.group;
    const w = stagger ? 0.55 : 1;
    items.forEach((it, k) => { it.a = stagger ? (k * (1 - w)) / (items.length - 1) : 0; it.w = w; });
    const moving = items.length || swing;
    const share = moving ? (ks.length ? PARTS_SHARE : 1) : 0;
    const dur = (moving ? (stagger ? 1700 : 1100) : 0) + (ks.length ? 1000 : 0);
    const riding = new Map(items.filter((it) => it.path).map((it) => [it.i, it]));
    tl = { items, ks, posed, swing, share, dur, riding, p: 1, playing: false, t0: 0, from: 0 };
  }
  function applyProgress(p) {
    if (!tl) return;
    tl.p = p;
    const pp = tl.share ? clamp(p / tl.share, 0, 1) : 1;
    // A swinging pose turns over the whole parts phase, after any path has brought its parts in.
    if (poseNow) poseNow.angle = tl.swing ? poseNow.from + (poseNow.deg - poseNow.from) * ease(pp) : poseNow.deg;
    const fa = flexNow ? flexAt(flexNow, ease(pp)) : 0;
    if (flexNow) for (const i of flexNow.set) bendPart(i, fa);
    for (const it of tl.items) {
      const t = clamp((pp - it.a) / it.w, 0, 1); const e = ease(t);
      const mesh = meshes[it.i]; const m = mesh.material;
      it.off = it.path ? pathAt(it.path, e) : null;
      if (it.off && flexNow && flexNow.riders.has(it.i)) {
        const sg = flexNow.riders.get(it.i);
        it.off = [it.off[0], it.off[1] + (sg * (sg < 0 ? flexNow.spread[0] : flexNow.spread[1]) + flexNow.shift) * fa, it.off[2]];
      }
      if (it.path) placePart(it.i, it.off);
      else {
        placePart(it.i, null);
        const fade = e < 1; if (m.transparent !== fade) { m.transparent = fade; m.needsUpdate = true; } m.opacity = fade ? e : 1;
      }
      if (m === mats[it.i].add) m.emissiveIntensity = ADD_GLOW + (ADD_GLOW_MOVING - ADD_GLOW) * (1 - e);
    }
    for (const i of tl.posed) placePart(i, null);
    const sp = tl.share < 1 ? clamp((p - tl.share) / (1 - tl.share), 0, 1) : 1;
    const e = ease(sp);
    for (const k of tl.ks) placeScrew(screwObjs[k], (screwObjs[k].L + 10) * (1 - e));
    // Screws already in ride with their part while it moves (a bench subassembly lowered as a group) or turns with a pose.
    screwObjs.forEach((o, k) => {
      if (!o.g.visible || tl.ks.includes(k)) return;
      const ride = tl.riding.get(o.through) || tl.riding.get(o.into);
      if (ride || (poseNow && o.through != null && poseNow.set.has(o.through))) placeScrew(o, 0, ride ? ride.off : null);
    });
    for (const f of onProgress) f(p, tl.playing);
    dirty = true;
  }
  function play(from) {
    if (!tl || !tl.dur) return;
    if (reduceMotion) { tl.playing = false; applyProgress(1); return; }
    tl.from = from >= 1 ? 0 : from; tl.t0 = performance.now(); tl.playing = true;
    applyProgress(tl.from);
  }
  function tickTimeline(now) {
    const t = clamp((now - tl.t0) / Math.max(1, tl.dur * (1 - tl.from)), 0, 1);
    if (t >= 1) tl.playing = false;
    applyProgress(tl.from + (1 - tl.from) * t);
  }

  /* chapter pages: the parts laid out on the bench, or the finished chapter with all its screws */
  let kitSlots = [];
  let kitFocus = -1;
  function clearScene() {
    tl = null;
    poseNow = null;
    setFlex(null);
    for (let i = 0; i < n; i++) setPartRole(i, 'off');
    cableObjs.forEach((o, ci) => setCableState(ci, 'off'));
    selectedCable = -1; hoverCable = -1;
    refreshCableLabels(); clearArrows(); clearPartLabels(); closePartCard();
    screwAnchors.length = 0;
    screwObjs.forEach((o, k) => setScrewState(k, 'off'));
  }
  function layoutKit(ch) {
    const slots = ch.kit.map((e, k) => {
      const shown = (e.group ? e.parts : e.parts.slice(0, 1)).filter((i) => meshes[i]);
      const box = new THREE.Box3();
      for (const i of shown) box.union(meshes[i].geometry.boundingBox);
      return { k, e, shown, box, size: box.isEmpty() ? new THREE.Vector3() : box.getSize(new THREE.Vector3()) };
    }).filter((sl) => sl.shown.length);
    // Shelf packing on the bench: rows run along +y (screen right from the front camera), largest parts in the back row.
    const order = slots.slice().sort((a, b) => Math.max(b.size.x, b.size.y) - Math.max(a.size.x, a.size.y));
    const area = order.reduce((acc, sl) => acc + (sl.size.x + KIT_GAP_MM) * (sl.size.y + KIT_GAP_MM), 0);
    const rowW = Math.max(Math.sqrt(area) * 1.5, ...order.map((sl) => sl.size.y));
    const rows = [[]]; let x = 0; let y = 0; let depth = 0;
    for (const sl of order) {
      if (y > 0 && y + sl.size.y > rowW) { rows[rows.length - 1].w = y - KIT_GAP_MM; x += depth + KIT_GAP_MM; y = 0; depth = 0; rows.push([]); }
      sl.slot = new THREE.Vector3(x + sl.size.x / 2, y + sl.size.y / 2, sl.size.z / 2);
      rows[rows.length - 1].push(sl);
      y += sl.size.y + KIT_GAP_MM; depth = Math.max(depth, sl.size.x);
    }
    rows[rows.length - 1].w = y - KIT_GAP_MM;
    const total = x + depth;
    const base = sceneBox.isEmpty() ? new THREE.Vector3() : sceneBox.getCenter(new THREE.Vector3()).setZ(sceneBox.min.z);
    for (const row of rows) for (const sl of row) {
      sl.slot.add(new THREE.Vector3(base.x - total / 2, base.y - row.w / 2, base.z));
      sl.offset = sl.slot.clone().sub(sl.box.getCenter(new THREE.Vector3()));
    }
    return slots;
  }
  function showKitLabels() {
    clearPartLabels();
    if (!partLabelsOn) return;
    // A phone-sized view has no room for names: it shows the row numbers of the list instead.
    const compact = canvas.clientWidth < 600;
    for (const sl of kitSlots) {
      const e = sl.e;
      const text = compact ? String(sl.k + 1) : e.label + (!e.group && e.parts.length > 1 ? ' ×' + e.parts.length : '');
      const el = h('div', { class: 'part-label' + (compact ? ' num' : '') + (sl.k === kitFocus ? ' focus' : ''), text, title: e.label });
      const c = sl.box.getCenter(new THREE.Vector3());
      labelsEl.append(el); partAnchors.push({ el, point: c.setZ(sl.box.max.z + 1), part: sl.shown[0], slot: sl.k });
    }
  }
  function viewOf(box, dir, margin) {
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const d = fitDistance(Math.max(sphere.radius, 10)) * margin;
    return { pos: sphere.center.clone().add(new THREE.Vector3(...dir).normalize().multiplyScalar(d)), target: sphere.center.clone() };
  }

  /* labels and picking */
  const labelsEl = $('labels');
  const anchors = [];           // {el, point}
  let partCard = null;          // {el, point, part}
  let hoverCable = -1;
  let selectedCable = -1;
  let hoverEls = [];
  const onCableSelect = [];

  function clearEndLabels() { for (const el of hoverEls) el.remove(); hoverEls = []; anchors.length = 0; }
  function showEndLabels(ci, hoverPoint) {
    clearEndLabels();
    const keep = [];
    const add = (ci2, point) => {
      const c = cables[ci2]; const o = cableObjs[ci2];
      if (!o) return;
      const dot = colorOf(c.color, '#444c55');
      const mk = (roleText, text, pt) => {
        const el = h('div', { class: 'end-label', '--dot': dot }, h('span', { class: 'end-role', text: roleText }), text || '—');
        labelsEl.append(el); hoverEls.push(el); keep.push({ el, point: pt });
      };
      mk('From', c.from, o.ends[0]);
      mk('To', c.to, o.ends[1]);
      const name = h('div', { class: 'hover-label', text: (c.label || c.id) + (c.lengthMM ? ' · ' + c.lengthMM + ' mm' : '') });
      labelsEl.append(name); hoverEls.push(name); keep.push({ el: name, point: point || o.mid });
    };
    if (ci >= 0) add(ci, hoverPoint);
    anchors.push(...keep);
    positionLabels();
  }
  function refreshCableLabels() {
    if (hoverCable >= 0) showEndLabels(hoverCable);
    else if (selectedCable >= 0) showEndLabels(selectedCable);
    else clearEndLabels();
  }
  function closePartCard() { if (partCard) { partCard.el.remove(); partCard = null; } }
  function openPartCard(i, point) {
    closePartCard();
    const p = parts[i];
    const close = h('button', { class: 'pc-close', type: 'button', 'aria-label': 'Close part label', onclick: () => { closePartCard(); dirty = true; } }, icon(ICON_CLOSE));
    const roleText = { add: 'Installed in this step', show: 'Already installed', ctx: 'Context only', off: '' }[role[i]] || '';
    const el = h('div', { class: 'part-card', role: 'dialog', 'aria-label': 'Part: ' + (p.name || p.key) },
      h('div', { class: 'pc-name', text: p.name || p.key }),
      h('div', { class: 'pc-row' }, h('span', { class: 'swatch', '--c': colorOf(p.color) }), statusPill(p.status), roleText ? h('span', { class: 'pc-meta', text: roleText }) : null),
      h('div', { class: 'pc-meta', text: [p.module ? 'Module ' + p.module : '', 'Key ' + p.key].filter(Boolean).join(' · ') }),
      close);
    labelsEl.parentElement.append(el);
    partCard = { el, point: point.clone(), part: i };
    positionLabels();
  }
  function project(point, out) {
    v1.copy(point).project(camera);
    const w = canvas.clientWidth; const hgt = canvas.clientHeight;
    out.x = (v1.x + 1) / 2 * w; out.y = (1 - v1.y) / 2 * hgt; out.ok = v1.z > -1 && v1.z < 1;
    return out;
  }
  const scr = { x: 0, y: 0, ok: false };
  function positionLabels() {
    for (const a of screwAnchors) {
      project(a.obj.g.position.clone().addScaledVector(a.obj.axis, -(a.obj.hh + 1.2)), scr);
      a.el.style.display = scr.ok ? '' : 'none';
      a.el.style.transform = 'translate(' + Math.round(scr.x) + 'px,' + Math.round(scr.y) + 'px) translate(-50%,-50%)';
    }
    // Part names: centred on the part, then pushed down past any name already placed so none overlap.
    const tags = [];
    for (const a of partAnchors) {
      const m = meshes[a.part];
      project(m ? a.point.clone().add(m.position) : a.point, scr);
      a.el.style.display = scr.ok ? '' : 'none';
      if (!scr.ok) continue;
      if (a.w === undefined) { a.w = a.el.offsetWidth; a.h = a.el.offsetHeight; }
      tags.push({ a, x: scr.x - a.w / 2, y: scr.y - a.h / 2 });
    }
    tags.sort((p, q) => p.y - q.y);
    const placed = [];
    for (const t of tags) {
      for (let k = 0; k < 10; k++) {
        const hit = placed.find((r) => t.x < r.x + r.a.w + 3 && t.x + t.a.w + 3 > r.x && t.y < r.y + r.a.h + 2 && t.y + t.a.h + 2 > r.y);
        if (!hit) break;
        t.y = hit.y + hit.a.h + 2;
      }
      placed.push(t);
      t.a.el.style.transform = 'translate(' + Math.round(t.x) + 'px,' + Math.round(t.y) + 'px)';
    }
    for (const a of anchors) {
      project(a.point, scr);
      a.el.style.display = scr.ok ? '' : 'none';
      a.el.style.transform = 'translate(' + Math.round(scr.x) + 'px,' + Math.round(scr.y - 8) + 'px) translate(-50%,-100%)';
    }
    if (partCard) {
      project(partCard.point, scr);
      const w = canvas.clientWidth; const hgt = canvas.clientHeight;
      const cw = partCard.el.offsetWidth; const chh = partCard.el.offsetHeight;
      let x = scr.x + 12; let y = scr.y - chh - 12;
      if (x + cw > w - 8) x = scr.x - cw - 12;
      if (y < 56) y = scr.y + 12;
      x = clamp(x, 8, Math.max(8, w - cw - 8)); y = clamp(y, 8, Math.max(8, hgt - chh - 8));
      partCard.el.style.transform = 'translate(' + Math.round(x) + 'px,' + Math.round(y) + 'px)';
      partCard.el.style.visibility = scr.ok ? 'visible' : 'hidden';
    }
  }

  const raycaster = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  function setRay(ev) {
    const rect = canvas.getBoundingClientRect();
    ndc.set(((ev.clientX - rect.left) / rect.width) * 2 - 1, -((ev.clientY - rect.top) / rect.height) * 2 + 1);
    raycaster.setFromCamera(ndc, camera);
  }
  function activePicks() { return cableObjs.filter((o) => o && o.state === 'hi').map((o) => o.pick); }
  function pickCable() {
    const picks = activePicks();
    if (!picks.length) return null;
    for (const p of picks) p.updateMatrixWorld();
    const hit = raycaster.intersectObjects(picks, false)[0];
    return hit ? { ci: hit.object.userData.cable, point: hit.point, distance: hit.distance } : null;
  }
  function pickPart() {
    const solid = []; const ghost = [];
    for (let i = 0; i < n; i++) {
      const m = meshes[i];
      if (!m || !m.visible) continue;
      (m.material === mats[i].ghost ? ghost : solid).push(m);
    }
    const hit = raycaster.intersectObjects(solid, false)[0] || raycaster.intersectObjects(ghost, false)[0];
    return hit ? { i: hit.object.userData.part, point: hit.point, distance: hit.distance } : null;
  }
  function selectCable(ci, point) {
    selectedCable = ci;
    refreshCableLabels();
    if (ci >= 0 && point) { anchors[anchors.length - 1].point = point; }
    for (const f of onCableSelect) f(ci);
    dirty = true;
  }
  let down = null;
  canvas.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; });
  canvas.addEventListener('pointerup', (e) => {
    if (!down) return;
    const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y);
    const quick = performance.now() - down.t < 700;
    down = null;
    if (moved > 6 || !quick) return;
    setRay(e);
    const c = pickCable();
    const p = pickPart();
    if (c && (!p || c.distance <= p.distance + 4)) { closePartCard(); selectCable(c.ci === selectedCable ? -1 : c.ci, c.point); return; }
    if (p) { selectCable(-1); openPartCard(p.i, p.point); dirty = true; return; }
    closePartCard(); selectCable(-1);
  });
  let hoverQueued = null;
  canvas.addEventListener('pointermove', (e) => {
    if (e.pointerType !== 'mouse' || e.buttons) return;
    if (hoverQueued) { hoverQueued = e; return; }
    hoverQueued = e;
    requestAnimationFrame(() => {
      const ev = hoverQueued; hoverQueued = null;
      setRay(ev);
      const c = pickCable();
      const ci = c ? c.ci : -1;
      canvas.style.cursor = ci >= 0 ? 'pointer' : '';
      if (ci !== hoverCable) { hoverCable = ci; refreshCableLabels(); dirty = true; }
    });
  });
  canvas.addEventListener('pointerleave', () => { if (hoverCable !== -1) { hoverCable = -1; canvas.style.cursor = ''; refreshCableLabels(); } });

  /* hint */
  const hint = $('viewer-hint');
  let hintTimer = setTimeout(hideHint, 9000);
  function hideHint() { if (hint) hint.classList.add('fade'); clearTimeout(hintTimer); }

  /* resize + loop */
  function resize() {
    const w = Math.max(1, container.clientWidth); const hgt = Math.max(1, container.clientHeight);
    renderer.setSize(w, hgt, false);
    camera.aspect = w / hgt;
    camera.updateProjectionMatrix();
    if (kitSlots.length) showKitLabels();
    dirty = true;
  }
  const ro = new ResizeObserver(() => resize());
  ro.observe(container);
  resize();

  function loop(now) {
    requestAnimationFrame(loop);
    if (camTween) {
      const t = clamp((now - camTween.t0) / camTween.dur, 0, 1); const e = ease(t);
      camera.position.lerpVectors(camTween.fromPos, camTween.toPos, e);
      controls.target.lerpVectors(camTween.fromTarget, camTween.toTarget, e);
      if (t >= 1) camTween = null;
      dirty = true;
    }
    if (controls.update()) dirty = true;
    if (tl && tl.playing) tickTimeline(now);
    if (dirty) {
      dirty = false;
      // about 2.5 px at the orbit target, in mm
      outlineWidth.value = 2.5 * 2 * camera.position.distanceTo(controls.target) * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) / Math.max(1, canvas.clientHeight);
      renderer.render(scene, camera);
      positionLabels();
      frames++;
    }
  }
  let frames = 0;

  /* warm-up: upload every buffer once behind the loading screen, so later steps do not hitch */
  for (const m of meshes) if (m) m.visible = true;
  for (const o of cableObjs) if (o) o.group.visible = true;
  camera.position.copy(sceneBox.isEmpty() ? new THREE.Vector3(300, 300, 200) : sceneBox.getCenter(new THREE.Vector3()).add(new THREE.Vector3(1, 0.9, 0.7).normalize().multiplyScalar(fitDistance(sceneBox.getBoundingSphere(new THREE.Sphere()).radius))));
  controls.target.copy(sceneBox.isEmpty() ? new THREE.Vector3() : sceneBox.getCenter(new THREE.Vector3()));
  controls.update();
  renderer.render(scene, camera);
  for (const m of meshes) if (m) m.visible = false;
  for (const o of cableObjs) if (o) o.group.visible = false;
  requestAnimationFrame(loop);

  /* public API */
  return {
    triangles,
    showStep(step, opts = {}) {
      const changed = step !== page;
      current = step; page = step; pageChapter = step.chapter.index;
      kitSlots = []; kitFocus = -1;
      closePartCard();
      setPose(step);
      setFlex(step);
      for (let i = 0; i < n; i++) {
        const r = step.add.has(i) ? 'add' : step.show.has(i) ? 'show' : step.ctx.has(i) ? 'ctx' : 'off';
        setPartRole(i, r);
      }
      const hi = new Set(step.cables);
      // An earlier cable of this chapter stays as a faint trace only while the parts at both of its ends are on screen.
      const seen = [];
      for (let i = 0; i < n; i++) if (meshes[i] && role[i] !== 'off' && !(role[i] === 'ctx' && ctxMode === 'hidden')) seen.push(meshes[i].geometry.boundingBox);
      const anchored = (o) => o && o.ends.every((e) => seen.some((b) => b.distanceToPoint(e) < 12));
      cableObjs.forEach((o, ci) => setCableState(ci, hi.has(ci) ? 'hi' : step.faintCables.has(ci) && anchored(o) ? 'faint' : 'off'));
      selectedCable = -1; hoverCable = -1;
      refreshCableLabels();
      buildArrows(step);
      showScrews(step.screws, step.number, true);
      showPartLabels(step);
      currentView = stepView(step);
      if (changed || opts.resetCamera) flyTo(currentView, !!opts.instant);
      buildTimeline(step);
      if (opts.animate === false || !tl.dur) applyProgress(1); else play(0);
      dirty = true;
    },
    showKit(ch, opts = {}) {
      const changed = page !== ch.kit;
      current = null; page = ch.kit; pageChapter = ch.index; kitFocus = -1;
      clearScene();
      kitSlots = layoutKit(ch);
      const box = new THREE.Box3();
      for (const sl of kitSlots) {
        for (const i of sl.shown) { setPartRole(i, 'kit'); meshes[i].position.copy(sl.offset); }
        box.union(sl.box.clone().translate(sl.offset));
      }
      showKitLabels();
      if (!box.isEmpty()) currentView = viewOf(box, [1, 0, 1.15], 1.0);
      if (changed && currentView) flyTo(currentView, !!opts.instant);
      for (const f of onProgress) f(1, false);
      dirty = true;
    },
    focusKit(k) {
      const sl = kitSlots.find((x) => x.k === k);
      if (!sl) return;
      kitFocus = k;
      for (const x of kitSlots) for (const i of x.shown) setOutline(i, x === sl);
      showKitLabels();
      const box = sl.box.clone().translate(sl.offset);
      const sphere = box.getBoundingSphere(new THREE.Sphere());
      const dir = camera.position.clone().sub(controls.target).normalize();
      flyTo({ pos: sphere.center.clone().addScaledVector(dir, fitDistance(Math.max(sphere.radius * 2.2, 22))), target: sphere.center.clone() }, false);
      dirty = true;
    },
    showChapterScrews(ch, opts = {}) {
      const changed = page !== ch.screws;
      current = null; page = ch.screws; pageChapter = ch.index;
      clearScene();
      const last = ch.stepList[ch.stepList.length - 1];
      const box = new THREE.Box3();
      for (let i = 0; i < n; i++) {
        if (!(last.add.has(i) || last.show.has(i))) continue;
        setPartRole(i, 'show');
        if (guide.introChapter[i] === ch.index && meshes[i]) box.union(meshes[i].geometry.boundingBox);
      }
      const first = ch.stepList[0].number;
      showScrews(ch.screws, first, false);
      for (const k of ch.screws) box.expandByPoint(screwObjs[k].home);
      if (!box.isEmpty()) currentView = viewOf(box, [1, 0.9, 0.7], 1.08);
      if (changed && currentView) flyTo(currentView, !!opts.instant);
      for (const f of onProgress) f(1, false);
      dirty = true;
    },
    play() { if (tl) play(tl.p >= 1 ? 0 : tl.p); },
    pause() { if (tl) tl.playing = false; },
    pullApart() { if (tl) { tl.playing = false; applyProgress(0); } },
    seat() { if (tl) { tl.playing = false; applyProgress(1); } },
    scrub(p) { if (tl) { tl.playing = false; applyProgress(clamp(p, 0, 1)); } },
    hasTimeline() { return !!(tl && tl.dur); },
    onProgress(f) { onProgress.push(f); },
    replay() { if (current) { closePartCard(); play(0); } },
    resetView() { if (current) currentView = stepView(current); if (currentView) flyTo(currentView, false); },
    flipSide() {
      const t = controls.target; const d = camera.position.clone().sub(t);
      flyTo({ pos: t.clone().add(new THREE.Vector3(-d.x, -d.y, d.z)), target: t.clone() }, false);
    },
    setContextMode(mode) {
      if (!CTX_MODES.includes(mode)) return;
      ctxMode = mode;
      if (current) { for (let i = 0; i < n; i++) if (role[i] === 'ctx') setPartRole(i, 'ctx'); showScrews(current.screws, current.number, true); applyProgress(tl ? tl.p : 1); }
      dirty = true;
    },
    setPartLabels(on) { partLabelsOn = !!on; if (current) showPartLabels(current); else if (kitSlots.length) showKitLabels(); dirty = true; },
    focusScrews(list) {
      if (!list.length) return;
      const box = new THREE.Box3();
      for (const k of list) box.expandByPoint(screwObjs[k].home);
      const sphere = box.getBoundingSphere(new THREE.Sphere());
      const r = Math.max(sphere.radius * 1.8, 18);
      const dir = camera.position.clone().sub(controls.target).normalize();
      flyTo({ pos: sphere.center.clone().addScaledVector(dir, fitDistance(r)), target: sphere.center.clone() }, false);
      for (const k of list) { const o = screwObjs[k]; if (o.label) { o.label.classList.remove('pulse'); void o.label.offsetWidth; o.label.classList.add('pulse'); } }
      dirty = true;
    },
    focusPart(i) {
      if (!meshes[i] || !meshes[i].visible) return false;
      selectCable(-1);
      const p = centers[i].clone().add(meshes[i].position);
      openPartCard(i, p);
      dirty = true;
      return true;
    },
    selectCable(ci) { closePartCard(); selectCable(ci === selectedCable ? -1 : ci, null); },
    onCableSelect(f) { onCableSelect.push(f); },
    stats() {
      const vis = meshes.filter((m) => m && m.visible);
      return {
        meshes: meshes.filter(Boolean).length,
        visibleParts: vis.length,
        visibleTriangles: vis.reduce((a, m) => a + m.geometry.index.count / 3, 0),
        addedParts: [...(current ? current.add : [])].length,
        ghostParts: vis.filter((m) => m.material === mats[m.userData.part].ghost).length,
        cablesHighlighted: cableObjs.filter((o) => o && o.state === 'hi').length,
        cablesFaint: cableObjs.filter((o) => o && o.state === 'faint').length,
        locatorBoxes: [...boxes.values()].filter((b) => b.visible && b.parent.visible).length,
        screwsCurrent: current ? current.screws.length : 0,
        screwsVisible: screwObjs.filter((o) => o.g.visible).length,
        partLabels: partAnchors.length,
        outlined: [...outlines.values()].filter((o) => o.visible && o.parent.visible).length,
        animating: !!(tl && tl.playing),
        progress: tl ? +tl.p.toFixed(3) : null,
        kitSlots: kitSlots.length,
        frames,
        drawCalls: renderer.info.render.calls,
        renderedTriangles: renderer.info.render.triangles,
        camera: { position: camera.position.toArray().map((x) => +x.toFixed(1)), target: controls.target.toArray().map((x) => +x.toFixed(1)) },
        contextMode: ctxMode
      };
    },
    debugPick(clientX, clientY) {
      setRay({ clientX, clientY });
      const c = pickCable(); const p = pickPart();
      return { cable: c ? cables[c.ci].id : null, part: p ? parts[p.i].key : null };
    },
    projectPart(i) {
      if (!meshes[i]) return null;
      const rect = canvas.getBoundingClientRect();
      project(centers[i].clone().add(meshes[i].position), scr);
      return { x: rect.left + scr.x, y: rect.top + scr.y, ok: scr.ok };
    },
    projectCable(ci) {
      const o = cableObjs[ci]; if (!o) return null;
      const rect = canvas.getBoundingClientRect();
      project(o.mid, scr);
      return { x: rect.left + scr.x, y: rect.top + scr.y, ok: scr.ok };
    }
  };
}

/* --------------------------------------------------------------------- UI */
async function main() {
  const status = $('viewer-status');
  const setStatus = (text, isError) => { status.hidden = !text; status.textContent = text || ''; status.classList.toggle('error', !!isError); };
  setStatus('Unpacking the guide…');
  await nextFrame();

  const jsonBuf = await readPayload('guide-data');
  if (!jsonBuf) throw new Error('No guide data is embedded in this file.');
  const data = JSON.parse(new TextDecoder().decode(jsonBuf));
  const guide = prepareGuide(data);
  if (guide.problems.length) console.warn('Guide data references that could not be resolved:\n' + guide.problems.join('\n'));
  if (!guide.steps.length) throw new Error('The guide has no steps.');

  const storeKey = 'mdguide:' + slug(data.title);
  const done = new Set(Object.keys(store.get(storeKey + ':done', {}) || {}).filter((id) => guide.stepById.has(id)));
  const ticks = store.get(storeKey + ':checks', {}) || {};
  let ctxMode = store.get('mdguide:context-mode', 'ghost');
  if (!CTX_MODES.includes(ctxMode)) ctxMode = 'ghost';
  let viewer = null;
  let current = null;
  const total = guide.steps.length;

  /* header + sidebar */
  document.title = data.title || 'Assembly guide';
  $('guide-title').textContent = data.title || 'Assembly guide';
  $('guide-subtitle').textContent = [data.subtitle, data.revision ? 'Revision ' + data.revision : ''].filter(Boolean).join(' · ');
  $('side-count').textContent = total + (total === 1 ? ' step' : ' steps');
  $('side-foot').textContent = [data.revision ? 'Revision ' + data.revision : '', data.units ? 'Units: ' + data.units : '', 'Frame: ' + (data.frame || 'x forward, y left, z up')].filter(Boolean).join(' · ');

  const toc = $('toc');
  const linkById = new Map();
  const chapterEls = new Map();
  const expanded = new Set();
  for (const ch of guide.chapters) {
    const listId = 'chap-' + ch.index;
    const count = h('span', { class: 'chap-count' });
    const btn = h('button', { class: 'chap-btn', type: 'button', 'aria-expanded': 'false', 'aria-controls': listId, title: ch.summary || ch.title },
      h('span', { class: 'chap-num', text: pad2(ch.index + 1) }), h('span', { class: 'chap-title', text: ch.title }), count, icon(ICON_CHEVRON));
    const list = h('ol', { class: 'steps', id: listId, hidden: true });
    for (const pg of guide.pages.filter((x) => x.kind !== 'step' && x.chapter === ch)) {
      const a = h('a', { class: 'step-link page-link', href: '#' + encodeURIComponent(pg.id) },
        h('span', { class: 'step-num page-num' }, icon(pg.kind === 'parts' ? ICON_PARTS : ICON_SCREW)), h('span', { class: 'step-name', text: pg.title }));
      a.addEventListener('click', () => { if (narrowQuery.matches) closeDrawer(); });
      linkById.set(pg.id, a);
      list.append(h('li', { class: 'page-li' }, a));
    }
    for (const s of ch.steps) {
      const step = guide.stepById.get(String(s.id));
      const a = h('a', { class: 'step-link', href: '#' + encodeURIComponent(step.id) },
        h('span', { class: 'step-num', text: pad2(step.number) }), h('span', { class: 'step-name', text: step.title }), icon(ICON_CHECK, 'step-check'));
      a.addEventListener('click', () => { if (narrowQuery.matches) closeDrawer(); });
      linkById.set(step.id, a);
      list.append(h('li', null, a));
    }
    btn.addEventListener('click', () => { setExpanded(ch, !expanded.has(ch.id)); });
    const sec = h('section', { class: 'chap' }, btn, list);
    chapterEls.set(ch.id, { sec, btn, list, count });
    toc.append(sec);
  }
  function setExpanded(ch, open) {
    const e = chapterEls.get(ch.id);
    if (open) expanded.add(ch.id); else expanded.delete(ch.id);
    e.btn.setAttribute('aria-expanded', String(open));
    e.list.hidden = !open;
  }
  function refreshProgress() {
    let n = 0;
    for (const s of guide.steps) {
      const d = done.has(s.id);
      if (d) n++;
      linkById.get(s.id).classList.toggle('done', d);
    }
    for (const ch of guide.chapters) {
      const k = ch.steps.filter((s) => done.has(String(s.id))).length;
      const c = chapterEls.get(ch.id).count;
      c.textContent = k + '/' + ch.steps.length;
      c.classList.toggle('complete', k === ch.steps.length);
    }
    $('done-count').textContent = n + ' of ' + total + ' done';
    $('done-bar').style.width = (total ? (100 * n) / total : 0) + '%';
    if (current) {
      const d = done.has(current.id);
      $('done-btn').setAttribute('aria-pressed', String(d));
      $('done-text').textContent = d ? 'Done' : 'Mark done';
      const badge = document.querySelector('.step-meta .badge-done');
      if (badge) badge.hidden = !d;
    }
  }
  function saveDone() { const o = {}; for (const id of done) o[id] = true; store.set(storeKey + ':done', o); }
  $('reset-progress').addEventListener('click', () => {
    if (!done.size && !Object.keys(ticks).length) return;
    if (!window.confirm('Clear all done marks and ticked checks for this guide on this device?')) return;
    done.clear();
    for (const k of Object.keys(ticks)) delete ticks[k];
    store.remove(storeKey + ':done'); store.remove(storeKey + ':checks');
    if (current) renderStep(current);
    refreshProgress();
  });

  /* search */
  $('search').addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase();
    let any = false;
    for (const ch of guide.chapters) {
      let hits = 0;
      for (const s of ch.steps) {
        const step = guide.stepById.get(String(s.id));
        const match = !q || step.search.includes(q);
        linkById.get(step.id).parentElement.hidden = !match;
        if (match) hits++;
      }
      const e2 = chapterEls.get(ch.id);
      e2.sec.hidden = hits === 0;
      if (q && hits) setExpanded(ch, true);
      if (!q) setExpanded(ch, current && current.chapter === ch);
      any = any || hits > 0;
    }
    $('toc-empty').hidden = any;
  });

  /* drawer */
  const body = document.body;
  function openDrawer() {
    body.classList.add('drawer-open'); $('scrim').hidden = false; $('menu-btn').setAttribute('aria-expanded', 'true');
    const a = current && linkById.get(current.id);
    setTimeout(() => { (a || $('search')).focus({ preventScroll: false }); if (a) a.scrollIntoView({ block: 'center' }); }, 60);
  }
  function closeDrawer() {
    if (!body.classList.contains('drawer-open')) return;
    body.classList.remove('drawer-open'); $('scrim').hidden = true; $('menu-btn').setAttribute('aria-expanded', 'false');
    if ($('sidebar').contains(document.activeElement)) $('menu-btn').focus();
  }
  $('menu-btn').addEventListener('click', () => (body.classList.contains('drawer-open') ? closeDrawer() : openDrawer()));
  $('drawer-close').addEventListener('click', closeDrawer);
  $('scrim').addEventListener('click', closeDrawer);
  if (narrowQuery.addEventListener) narrowQuery.addEventListener('change', () => { if (!narrowQuery.matches) closeDrawer(); });

  /* step panel */
  const stepBody = $('step-body');
  function section(title, count, ...content) {
    return h('section', { class: 'sec' }, h('h3', { class: 'sec-title' }, title, count ? h('span', { class: 'sec-count', text: count }) : null), ...content);
  }
  let cableButtons = new Map();
  let wiringView = null;
  const ICON_EXPAND = ['M14 4h6v6', 'M20 4l-7 7', 'M10 20H4v-6', 'M4 20l7-7'];
  function wiringOptions(w, extra) {
    const pinText = w.pinText || {};
    return Object.assign({
      overviewLabels: 'always',
      text: { step: 'Step through the wires', exitStep: 'Show all wires' },
      pinLabel: (pin, m) => pinText[m.id + '.' + pin.id] || (pin.label === pin.name ? pin.label : pin.label + ' · ' + pin.name),
    }, extra);
  }
  // Large view: a full-viewport modal dialog that renders the same bench at the window's width, with the
  // overview fitted to the visible height; the dialog body scrolls vertically for the step bar, close-ups and
  // pin details.
  let bigWiring = null;
  let bigWiringView = null;
  function dropBigWiring() {
    if (bigWiringView) { try { bigWiringView.destroy(); } catch (_) { /* already gone */ } bigWiringView = null; }
  }
  function closeBigWiring() {
    if (bigWiring && bigWiring.dlg.open) bigWiring.dlg.close(); else dropBigWiring();
  }
  function ensureBigWiring() {
    if (bigWiring) return bigWiring;
    const title = h('h2', { class: 'wo-title', id: 'wiring-large-title' });
    const holder = h('div', { class: 'wiring-holder wo-holder' });
    const caption = h('p', { class: 'wiring-caption wo-caption' });
    const close = h('button', { class: 'nav-btn wo-close', type: 'button', 'aria-label': 'Close large wiring view',
      onclick: () => closeBigWiring() }, icon(ICON_CLOSE), h('span', { text: 'Close' }));
    const dlg = h('dialog', { class: 'wiring-large', 'aria-labelledby': 'wiring-large-title' },
      h('div', { class: 'wo-head' }, title, close),
      h('div', { class: 'wo-body' }, holder, caption));
    dlg.addEventListener('close', () => {
      dropBigWiring();
      holder.textContent = '';
      document.documentElement.classList.remove('wiring-large-open');
      const back = bigWiring.opener; bigWiring.opener = null;
      if (back && document.contains(back)) back.focus({ preventScroll: true });
    });
    document.body.append(dlg);
    bigWiring = { dlg, title, holder, caption, close, opener: null };
    return bigWiring;
  }
  function fitHeight(o) {
    const body = o.dlg.querySelector('.wo-body');
    const stage = o.holder.querySelector('.wk-stage');
    const top = stage ? stage.getBoundingClientRect().top - body.getBoundingClientRect().top + body.scrollTop : 72;
    const padBottom = parseFloat(getComputedStyle(body).paddingBottom) || 0;
    return Math.max(320, body.clientHeight - top - padBottom - 4);
  }
  function openBigWiring(w, opener) {
    const o = ensureBigWiring();
    dropBigWiring();
    o.holder.textContent = '';
    o.title.textContent = w.title || 'Wiring drawing';
    o.caption.textContent = w.caption || '';
    o.caption.hidden = !w.caption;
    o.opener = opener || null;
    document.documentElement.classList.add('wiring-large-open');
    if (!o.dlg.open) { if (typeof o.dlg.showModal === 'function') o.dlg.showModal(); else o.dlg.setAttribute('open', ''); }
    o.dlg.querySelector('.wo-body').scrollTop = 0;
    try {
      const opts = wiringOptions(w, { keyboard: true });
      // wiring-kit reads options.maxHeight on every layout, so a getter keeps the overview inside the visible
      // dialog body (below the title bar and chips) when the window is resized.
      Object.defineProperty(opts, 'maxHeight', { enumerable: true, get: () => fitHeight(o) });
      bigWiringView = window.WiringKit.render(o.holder, JSON.parse(JSON.stringify(w.bench)), opts);
    } catch (err) {
      o.holder.append(h('p', { class: 'empty-note', text: 'The wiring drawing failed to render: ' + (err && err.message || err) }));
    }
    o.close.focus({ preventScroll: true });
  }
  // A step's `wiring` field is a wiring-kit bench (window.WiringKit, inlined by build_guide.py): an interactive
  // drawing of pads, wires and far ends with a wire-by-wire mode. Markers come from wiring.pinText.
  function wiringSection(w) {
    const holder = h('div', { class: 'wiring-holder' });
    const large = window.WiringKit ? h('button', { class: 'nav-btn wiring-large-btn', type: 'button',
      title: 'Show this drawing across the whole window', onclick: (e) => openBigWiring(w, e.currentTarget) },
    icon(ICON_EXPAND), h('span', { text: 'Open large view' })) : null;
    const sec = section(w.title || 'Wiring drawing', null, large, holder, w.caption ? h('p', { class: 'wiring-caption', text: w.caption }) : null);
    if (!window.WiringKit) {
      holder.append(h('p', { class: 'empty-note', text: 'The wiring drawing could not load in this browser.' }));
      return { sec, mount() {} };
    }
    return {
      sec,
      mount() {
        try {
          wiringView = window.WiringKit.render(holder, JSON.parse(JSON.stringify(w.bench)), wiringOptions(w, { keyboard: false, maxHeight: 900 }));
        } catch (err) {
          holder.textContent = '';
          holder.append(h('p', { class: 'empty-note', text: 'The wiring drawing failed to render: ' + (err && err.message || err) }));
        }
      },
    };
  }
  function dropWiring() {
    if (wiringView) { try { wiringView.destroy(); } catch (_) { /* already gone */ } wiringView = null; }
    closeBigWiring();
  }
  function renderStep(step) {
    const raw = step.raw;
    const ch = step.chapter;
    dropWiring();
    stepBody.textContent = '';
    cableButtons = new Map();
    const badge = h('span', { class: 'badge-done', hidden: !done.has(step.id) }, icon(ICON_CHECK), 'Done');
    stepBody.append(
      h('div', { class: 'step-eyebrow', text: 'Chapter ' + pad2(ch.index + 1) + ' · ' + ch.title }),
      h('h2', { class: 'step-title', id: 'step-title', tabindex: '-1', text: step.title }),
      h('div', { class: 'step-meta' }, h('span', { text: 'Step ' + step.number + ' of ' + total }), badge)
    );
    if (step.indexInChapter === 0 && ch.summary) {
      stepBody.append(h('div', { class: 'chapter-intro' }, h('strong', { text: 'About this chapter' }), ch.summary));
    }
    const warnings = (raw.warnings || []).filter(Boolean);
    if (warnings.length) {
      stepBody.append(h('div', { class: 'callouts' }, warnings.map((w) =>
        h('div', { class: 'callout', role: 'note' }, icon(ICON_WARN), h('div', null, h('strong', { text: 'Caution' }), h('p', { text: w }))))));
    }
    // A step's `links`: the detailed bench pages (BRINGUP.html, Chinese, with photos and wiring views) and related guide
    // steps. External pages open in a new tab; '#step-id' links move within this guide.
    const links = (raw.links || []).filter((l) => l && l.href && l.label);
    if (links.length) {
      stepBody.append(section('Detailed pages', String(links.length), h('ul', { class: 'link-list' }, links.map((l) =>
        h('li', null, h('a', Object.assign({ class: 'link-row', href: l.href },
          l.external ? { target: '_blank', rel: 'noopener' } : {}),
        h('span', { class: 'link-label', text: l.label + (l.external ? ' ↗' : '') }),
        l.note ? h('span', { class: 'link-note', text: l.note }) : null))))));
    }
    if (step.group) {
      const first = [...step.add][0];
      stepBody.append(section('Installed in this step', '1',
        h('div', { class: 'chips' }, h('button', { class: 'chip', type: 'button', title: 'Show ' + step.group.label + ' in the 3D view',
          onclick: () => { if (viewer && first !== undefined) viewer.focusPart(first); } },
        h('span', { class: 'swatch', '--c': colorOf(guide.parts[first] && guide.parts[first].color) }),
        h('span', { class: 'chip-name', text: step.group.label + ' (' + step.add.size + ' parts)' })))));
    } else if (step.add.size) {
      stepBody.append(section('Installed in this step', String(step.add.size),
        h('div', { class: 'chips' }, [...step.add].map((i) => {
          const p = guide.parts[i];
          return h('button', { class: 'chip', type: 'button', title: 'Show ' + (p.name || p.key) + ' in the 3D view',
            onclick: () => { if (viewer) viewer.focusPart(i); } },
          h('span', { class: 'swatch', '--c': colorOf(p.color) }), h('span', { class: 'chip-name', text: p.name || p.key }), statusPill(p.status));
        }))));
    }
    if (step.screws.length) {
      const bySpec = new Map();
      step.screws.forEach((k, j) => { const s = guide.screws[k]; if (!bySpec.has(s.spec)) bySpec.set(s.spec, []); bySpec.get(s.spec).push({ k, n: j + 1 }); });
      stepBody.append(section('Screws in this step', String(step.screws.length),
        h('ul', { class: 'screw-list' }, [...bySpec].map(([spec, list]) => {
          const s = guide.screws[list[0].k];
          const where = [...new Set(list.map((x) => guide.screws[x.k].where).filter(Boolean))];
          const tools = [...new Set(list.map((x) => guide.screws[x.k].tool).filter(Boolean))];
          const notes = [...new Set(list.map((x) => guide.screws[x.k].note).filter(Boolean))];
          return h('li', null, h('button', { class: 'screw-row', type: 'button', title: 'Show these screws in the 3D view',
            onclick: () => { if (viewer) viewer.focusScrews(list.map((x) => x.k)); } },
          screwIcon(s, guide.specColor.get(spec)),
          h('span', { class: 'screw-main' },
            h('span', { class: 'screw-spec', text: spec }),
            h('span', { class: 'screw-where', text: 'Markers ' + list.map((x) => x.n).join(', ') + (where.length ? ' · ' + where.join('; ') : '') }),
            tools.length ? h('span', { class: 'screw-where', text: 'Tool: ' + tools.join('; ') }) : null,
            notes.length ? h('span', { class: 'screw-where', text: notes.join(' ') }) : null),
          h('span', { class: 'screw-qty', text: '×' + list.length })));
        }))));
    }
    const prep = (raw.prepare || []).filter((p) => p && p.item);
    if (prep.length) {
      stepBody.append(section('Prepare', null, h('ul', { class: 'prep-list' }, prep.map((p) =>
        h('li', null, h('span', { class: 'qty', text: fmtQty(p.qty) || '—' }),
          h('div', { class: 'prep-main' },
            h('div', { class: 'prep-item' }, p.item, p.kind ? h('span', { class: 'kind-tag', text: PREP_KIND_LABEL[p.kind] || p.kind }) : null),
            p.note ? h('div', { class: 'prep-note', text: p.note }) : null))))));
    }
    const wiring = raw.wiring && raw.wiring.bench ? wiringSection(raw.wiring) : null;
    if (wiring) { stepBody.append(wiring.sec); wiring.mount(); }
    const ins = (raw.instructions || []).filter(Boolean);
    if (ins.length) stepBody.append(section('Assemble', null, h('ol', { class: 'instructions' }, ins.map((t) => h('li', null, h('span', { text: t }))))));
    const imgs = (raw.images || []).filter((im) => im && typeof im.src === 'string' && /^data:image\//.test(im.src));
    if (imgs.length) {
      stepBody.append(section('Reference photos', null, h('div', { class: 'figures' }, imgs.map((im) =>
        h('button', { class: 'figure-btn', type: 'button', onclick: () => openLightbox(im) },
          h('img', { src: im.src, alt: im.caption || 'Reference photo', loading: 'lazy' }), im.caption ? h('span', { text: im.caption }) : null)))));
    }
    if (step.cables.length) {
      stepBody.append(section('Cables in this step', String(step.cables.length), h('ul', { class: 'cable-list' }, step.cables.map((ci) => {
        const c = guide.cables[ci];
        const btn = h('button', { class: 'cable-btn', type: 'button', 'aria-pressed': 'false', onclick: () => { if (viewer) viewer.selectCable(ci); } },
          h('span', { class: 'cable-line', '--c': colorOf(c.color, '#444c55') }),
          h('span', { class: 'cable-main' },
            h('span', { class: 'cable-name', text: c.label || c.id }),
            h('span', { class: 'cable-route', text: ' · ' + (CABLE_KIND_LABEL[c.kind] || c.kind || 'cable') }),
            h('div', { class: 'cable-route', text: (c.from || '?') + ' → ' + (c.to || '?') + (c.lengthMM ? ' · ' + c.lengthMM + ' mm' : '') }),
            c.note ? h('div', { class: 'cable-note', text: c.note }) : null));
        cableButtons.set(ci, btn);
        return h('li', null, btn);
      }))));
    }
    const checks = (raw.checks || []).filter(Boolean);
    if (checks.length) {
      const state = Array.isArray(ticks[step.id]) ? ticks[step.id] : [];
      const statusEl = h('p', { class: 'check-status', 'aria-live': 'polite' });
      const items = checks.map((t, k) => {
        const input = h('input', { type: 'checkbox', checked: !!state[k] });
        const label = h('label', { class: 'check' + (state[k] ? ' ticked' : '') }, input, h('span', { text: t }));
        input.addEventListener('change', () => {
          const arr = Array.isArray(ticks[step.id]) ? ticks[step.id] : [];
          arr[k] = input.checked;
          ticks[step.id] = arr;
          label.classList.toggle('ticked', input.checked);
          store.set(storeKey + ':checks', ticks);
          updateChecks();
        });
        return h('li', null, label);
      });
      function updateChecks() {
        const arr = Array.isArray(ticks[step.id]) ? ticks[step.id] : [];
        const k = checks.filter((_, j) => arr[j]).length;
        statusEl.textContent = k === checks.length ? 'All checks passed. Mark the step done to continue.' : k + ' of ' + checks.length + ' checked';
        statusEl.classList.toggle('all', k === checks.length);
        $('done-btn').classList.toggle('ready', k === checks.length && !done.has(step.id));
      }
      stepBody.append(section('Check before moving on', null, h('ul', { class: 'checks' }, items), statusEl));
      updateChecks();
    } else {
      $('done-btn').classList.remove('ready');
    }
    if (!warnings.length && !step.add.size && !prep.length && !ins.length && !checks.length && !step.cables.length) {
      stepBody.append(h('p', { class: 'empty-note', text: 'No written instructions for this step.' }));
    }
  }

  /* chapter pages */
  let kitButtons = [];
  function renderChapterPage(pg) {
    const ch = pg.chapter;
    stepBody.textContent = '';
    kitButtons = [];
    const firstStep = ch.stepList[0];
    stepBody.append(
      h('div', { class: 'step-eyebrow', text: 'Chapter ' + pad2(ch.index + 1) + ' · ' + ch.title }),
      h('h2', { class: 'step-title', id: 'step-title', tabindex: '-1', text: pg.title }),
      h('div', { class: 'step-meta' }, h('span', { text: 'Before step ' + firstStep.number }))
    );
    if (ch.summary && pg === guide.pages.find((x) => x.chapter === ch)) {
      stepBody.append(h('div', { class: 'chapter-intro' }, h('strong', { text: 'About this chapter' }), ch.summary));
    }
    if (pg.kind === 'parts') {
      const counts = new Map();
      for (const e of ch.kit) {
        const st = e.group ? 'subassembly' : guide.parts[e.parts[0]].status || 'other';
        counts.set(st, (counts.get(st) || 0) + (e.group ? 1 : e.parts.length));
      }
      stepBody.append(h('p', { class: 'page-lead', text: 'Put these on the desk before you start. Match the shape first, then the colour. Tap a row to find the part in the 3D view.' }),
        h('p', { class: 'kit-summary', text: [...counts].map(([st, c]) => c + ' ' + (st === 'subassembly' ? (c === 1 ? 'subassembly' : 'subassemblies') : (STATUS_LABEL[st] || st).toLowerCase())).join(' · ') }));
      const cards = ch.kit.map((e, k) => {
        const p = guide.parts[e.parts[0]];
        const where = e.group ? e.parts.length + ' parts · placed in step ' + e.step.number : 'Step ' + e.step.number;
        const btn = h('button', { class: 'kit-card', type: 'button', 'aria-pressed': 'false', title: 'Show ' + e.label + ' in the 3D view',
          onclick: () => { for (const b of kitButtons) b.setAttribute('aria-pressed', String(b === btn)); if (viewer) viewer.focusKit(k); } },
        h('span', { class: 'kit-n', text: String(k + 1) }),
        h('span', { class: 'kit-swatch', '--c': colorOf(p.color) }),
        h('span', { class: 'kit-main' }, h('span', { class: 'kit-name', text: e.label }),
          h('span', { class: 'kit-meta' }, e.group ? null : statusPill(p.status), h('span', { text: where }))),
        h('span', { class: 'kit-qty', text: '×' + (e.group ? 1 : e.parts.length) }));
        kitButtons.push(btn);
        return btn;
      });
      stepBody.append(section('Parts for this chapter', String(ch.kit.length), h('div', { class: 'kit-list' }, cards)));
      return;
    }
    const bySpec = new Map();
    for (const k of ch.screws) { const sp = guide.screws[k].spec; if (!bySpec.has(sp)) bySpec.set(sp, []); bySpec.get(sp).push(k); }
    if (bySpec.size) {
      stepBody.append(h('p', { class: 'page-lead', text: 'Count each size into its own cup before you start. The 3D view shows where every screw in this chapter goes, coloured by size.' }));
      stepBody.append(section('Screws', String(ch.screws.length), h('ul', { class: 'screw-list' }, [...bySpec].map(([spec, ks]) => {
        const s0 = guide.screws[ks[0]];
        const perStep = new Map();
        for (const k of ks) { const st = guide.stepById.get(guide.screws[k].step); perStep.set(st, (perStep.get(st) || 0) + 1); }
        return h('li', null, h('div', { class: 'screw-row static' }, screwIcon(s0, guide.specColor.get(spec)),
          h('span', { class: 'screw-main' }, h('span', { class: 'screw-spec', text: spec }),
            screwDesc(s0) ? h('span', { class: 'screw-where', text: screwDesc(s0) }) : null,
            h('span', { class: 'screw-steps' }, [...perStep].map(([st, c]) => h('a', { href: '#' + encodeURIComponent(st.id), text: 'Step ' + st.number + ' ×' + c })))),
          h('span', { class: 'screw-qty', text: '×' + ks.length })));
      }))));
    }
    const loose = (kind, title) => {
      const list = ch.loose.filter((x) => x.kind === kind);
      if (!list.length) return;
      stepBody.append(section(title, null, h('ul', { class: 'prep-list' }, list.map((x) =>
        h('li', null, h('span', { class: 'qty', text: x.qtyText || (x.qty ? '×' + x.qty : '—') }),
          h('div', { class: 'prep-main' }, h('div', { class: 'prep-item', text: x.item }),
            h('div', { class: 'prep-note' }, [...new Set(x.steps)].map((st, j) => [j ? ', ' : 'Step ', h('a', { href: '#' + encodeURIComponent(st.id), text: String(st.number) })]))))))));
    };
    loose('fastener', bySpec.size ? 'Other fasteners' : 'Fasteners');
    loose('tool', 'Tools');
  }

  /* legend */
  function renderLegend(step) {
    const legend = $('legend');
    const ids = [...step.cables, ...step.faintCables];
    legend.textContent = '';
    if (!step.cables.length) { legend.hidden = true; return; }
    const kinds = [];
    for (const ci of ids) { const k = guide.cables[ci].kind || 'other'; if (!kinds.includes(k)) kinds.push(k); }
    const given = new Map((Array.isArray(data.legend) ? data.legend : []).map((l) => [l.kind, l]));
    legend.append(h('span', { class: 'legend-title', text: 'Cables' }));
    for (const k of kinds) {
      const g = given.get(k);
      const first = ids.map((ci) => guide.cables[ci]).find((c) => (c.kind || 'other') === k);
      legend.append(h('span', { class: 'legend-item' }, h('span', { class: 'legend-swatch', '--c': colorOf(g && g.color, colorOf(first && first.color, '#444c55')) }),
        (g && g.label) || CABLE_KIND_LABEL[k] || k));
    }
    legend.hidden = false;
  }

  /* lightbox */
  const lightbox = $('lightbox');
  function openLightbox(im) {
    $('lightbox-img').src = im.src; $('lightbox-img').alt = im.caption || 'Reference photo';
    $('lightbox-caption').textContent = im.caption || '';
    if (typeof lightbox.showModal === 'function') lightbox.showModal(); else lightbox.setAttribute('open', '');
  }
  $('lightbox-close').addEventListener('click', () => { if (lightbox.close) lightbox.close(); else lightbox.removeAttribute('open'); });
  lightbox.addEventListener('click', (e) => { if (e.target === lightbox && lightbox.close) lightbox.close(); });

  /* navigation */
  function stepFromHash() {
    const raw = location.hash.replace(/^#/, '');
    if (!raw) return null;
    let id = raw;
    try { id = decodeURIComponent(raw); } catch (e) { /* keep raw */ }
    return guide.pageById.get(id) || null;
  }
  const timelineEl = $('timeline');
  function showInViewer(pg, opts) {
    if (!viewer) return;
    if (pg.kind === 'parts') viewer.showKit(pg.chapter, opts);
    else if (pg.kind === 'screws') viewer.showChapterScrews(pg.chapter, opts);
    else viewer.showStep(pg, opts);
    timelineEl.hidden = !(pg.kind === 'step' && viewer.hasTimeline());
  }
  function go(pg, opts = {}) {
    if (!pg) return;
    const changed = pg !== current;
    current = pg;
    const isStep = pg.kind === 'step';
    for (const [id, a] of linkById) { if (id === pg.id) a.setAttribute('aria-current', 'step'); else a.removeAttribute('aria-current'); }
    if (changed) {
      setExpanded(pg.chapter, true);
      const a = linkById.get(pg.id);
      if (a && !narrowQuery.matches) a.scrollIntoView({ block: 'nearest' });
    }
    $('crumbs').textContent = 'Chapter ' + pad2(pg.chapter.index + 1) + ' / ' + pg.chapter.title;
    $('step-of').textContent = isStep ? 'Step ' + pg.number + ' of ' + total : 'Chapter preparation';
    $('top-progress').textContent = isStep ? pg.number + ' / ' + total : 'Prep';
    $('page-id').textContent = '#' + pg.id;
    $('prev-btn').disabled = pg.page === 0;
    $('next-btn').disabled = pg.page === guide.pages.length - 1;
    $('done-btn').style.visibility = isStep ? '' : 'hidden';
    document.querySelector('.viewer-tools .seg').hidden = !isStep;
    if (isStep) { renderStep(pg); renderLegend(pg); } else { dropWiring(); renderChapterPage(pg); $('legend').hidden = true; $('done-btn').classList.remove('ready'); }
    refreshProgress();
    $('panel-scroll').scrollTop = 0;
    $('announcer').textContent = isStep ? 'Step ' + pg.number + ' of ' + total + ': ' + pg.title : pg.chapter.title + ': ' + pg.title;
    store.set(storeKey + ':last', pg.id);
    showInViewer(pg, { instant: !!opts.instant });
  }
  function goPage(i) {
    const s = guide.pages[clamp(i, 0, guide.pages.length - 1)];
    if (!s || s === current) return;
    location.hash = '#' + encodeURIComponent(s.id);
  }
  window.addEventListener('hashchange', () => { const s = stepFromHash(); if (s) go(s); });
  $('page-id').addEventListener('click', () => {
    const url = location.href.split('#')[0] + '#' + encodeURIComponent(current.id);
    const done = () => { const b = $('page-id'); b.classList.add('copied'); b.textContent = 'copied #' + current.id; setTimeout(() => { b.classList.remove('copied'); b.textContent = '#' + current.id; }, 1500); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, () => prompt('Link to this page', url));
    else prompt('Link to this page', url);
  });
  $('prev-btn').addEventListener('click', () => goPage(current.page - 1));
  $('next-btn').addEventListener('click', () => goPage(current.page + 1));
  $('done-btn').addEventListener('click', () => {
    if (!current) return;
    if (done.has(current.id)) done.delete(current.id); else done.add(current.id);
    saveDone();
    $('done-btn').classList.remove('ready');
    refreshProgress();
  });
  document.addEventListener('keydown', (e) => {
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    const t = e.target;
    const typing = t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));
    if (e.key === 'Escape') { closeDrawer(); return; }
    if (typing && !(t.type === 'checkbox')) return;
    if (bigWiring && bigWiring.dlg.open) {
      // Arrow keys step through wires in the large view; wiring-kit handles them itself when focus is inside it.
      const st = bigWiringView && !bigWiring.holder.contains(document.activeElement) ? bigWiringView.state.step : null;
      if (st !== null && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) { e.preventDefault(); bigWiringView.setStep(st + (e.key === 'ArrowRight' ? 1 : -1)); }
      return;
    }
    if (lightbox.open) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); goPage(current.page + 1); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); goPage(current.page - 1); }
  });

  /* viewer tools */
  const segButtons = [...document.querySelectorAll('.seg button')];
  function setCtxMode(mode) {
    ctxMode = mode;
    for (const b of segButtons) b.setAttribute('aria-pressed', String(b.dataset.mode === mode));
    store.set('mdguide:context-mode', mode);
    if (viewer) viewer.setContextMode(mode);
  }
  for (const b of segButtons) b.addEventListener('click', () => setCtxMode(b.dataset.mode));
  setCtxMode(ctxMode);
  let labelsOn = store.get('mdguide:part-labels', true) !== false;
  const labelsBtn = $('labels-btn');
  function setLabels(on) {
    labelsOn = on;
    labelsBtn.setAttribute('aria-pressed', String(on));
    store.set('mdguide:part-labels', on);
    if (viewer) viewer.setPartLabels(on);
  }
  labelsBtn.addEventListener('click', () => setLabels(!labelsOn));
  setLabels(labelsOn);
  $('flip-btn').addEventListener('click', () => { if (viewer) viewer.flipSide(); });
  const tlRange = $('tl-range'); const tlPlay = $('tl-play');
  $('tl-play').addEventListener('click', () => { if (viewer) viewer.play(); });
  $('tl-apart').addEventListener('click', () => { if (viewer) viewer.pullApart(); });
  $('tl-seat').addEventListener('click', () => { if (viewer) viewer.seat(); });
  tlRange.addEventListener('input', () => { if (viewer) viewer.scrub(Number(tlRange.value) / 1000); });
  $('reset-btn').addEventListener('click', () => { if (viewer) viewer.resetView(); });

  /* first step: hash, then the last visited step, then the first */
  const lastId = store.get(storeKey + ':last', null);
  const first = stepFromHash() || (lastId && guide.pageById.get(lastId)) || guide.pages[0];
  if (!stepFromHash()) history.replaceState(null, '', '#' + encodeURIComponent(first.id));
  go(first, { instant: true });

  /* 3D */
  try {
    setStatus('Building the 3D model…');
    await nextFrame();
    const geoBuf = await readPayload('guide-geometry');
    viewer = await createViewer($('viewer'), guide, geoBuf, (i, n) => setStatus('Building the 3D model… ' + i + ' of ' + n + ' parts'));
    viewer.setContextMode(ctxMode);
    viewer.setPartLabels(labelsOn);
    viewer.onCableSelect((ci) => { for (const [k, b] of cableButtons) b.setAttribute('aria-pressed', String(k === ci)); });
    viewer.onProgress((p, playing) => {
      tlRange.value = String(Math.round(p * 1000));
      tlPlay.querySelector('span').textContent = playing ? 'Playing' : p >= 1 ? 'Replay' : 'Play';
    });
    showInViewer(current, { instant: true });
    setStatus('');
  } catch (err) {
    console.warn(err);
    setStatus(err && err.message ? err.message : 'The 3D view could not be built.', true);
  }

  window.guideViewer = {
    get step() { return current && current.id; },
    steps: guide.steps.map((s) => s.id),
    pages: guide.pages.map((s) => s.id),
    problems: guide.problems,
    stats: () => (viewer ? viewer.stats() : null),
    debugPick: (x, y) => (viewer ? viewer.debugPick(x, y) : null),
    projectPart: (key) => (viewer && guide.byKey.has(key) ? viewer.projectPart(guide.byKey.get(key)) : null),
    projectCable: (id) => { const i = guide.cables.findIndex((c) => c.id === id); return viewer && i >= 0 ? viewer.projectCable(i) : null; },
    ready: !!viewer
  };
  document.documentElement.dataset.guideReady = viewer ? '3d' : 'text';
}

main().catch((err) => {
  console.error(err);
  const box = $('fatal');
  box.hidden = false;
  box.textContent = 'The guide could not load: ' + (err && err.message ? err.message : String(err));
  const status = $('viewer-status');
  if (status) { status.textContent = 'Unavailable'; status.classList.add('error'); }
});
})();

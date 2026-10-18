// Headless check of HEAD-3D.html at desktop and phone width.
// Usage: node probe_head3d.mjs <HEAD-3D.html> <out-dir>
// Checks: console errors, WebGL canvas not empty, explode slider (real input event + animation), wiring view labels,
// part picking by a real click, horizontal overflow, input font sizes. Saves screenshots and report.json.
import { launch } from '../../../bringup/build/probe/cdp.mjs';
import fs from 'node:fs';
import path from 'node:path';

const PAGE = path.resolve(process.argv[2]);
const OUT = path.resolve(process.argv[3]);
fs.mkdirSync(OUT, { recursive: true });
const views = [
  { name: 'desk', width: 1280, height: 860, deviceScaleFactor: 1, mobile: false },
  { name: 'mob', width: 390, height: 844, deviceScaleFactor: 2, mobile: true },
];
const LAYOUT = `(() => {
  const W = innerWidth, wide = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    let p = el.parentElement, clipped = false;
    while (p && p !== document.body) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') { clipped = true; break; } p = p.parentElement; }
    if (!clipped && r.right > W + 1) wide.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + '.' + [...el.classList].join('.') + ' ' + Math.round(r.right));
  }
  const inputs = [...document.querySelectorAll('input,textarea,select')];
  const small = inputs.filter(e => parseFloat(getComputedStyle(e).fontSize) < 16).map(e => (e.id || e.className || e.type) + ' ' + getComputedStyle(e).fontSize);
  return { scrollW: document.documentElement.scrollWidth, W, wide: wide.slice(0, 8), inputs: inputs.length, small };
})()`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const b = await launch({ profile: path.join(OUT, '.profile'), extraArgs: ['--enable-unsafe-swiftshader', '--use-angle=swiftshader'] });
const report = [];
async function shot(name) {
  const r = await b.page('Page.captureScreenshot', { format: 'png' });
  const file = path.join(OUT, name + '.png');
  fs.writeFileSync(file, Buffer.from(r.data, 'base64'));
  return file;
}
for (const v of views) {
  await b.page('Emulation.setDeviceMetricsOverride', v);
  await b.page('Emulation.setTouchEmulationEnabled', { enabled: v.mobile });
  await b.page('Page.navigate', { url: 'file://' + PAGE });
  await b.waitFor(`!!(window.__head3d && window.__head3d.ready)`, 90000);
  await sleep(1500);
  const rec = { view: v.name };
  rec.layout = await b.eval(LAYOUT);
  rec.meshes = await b.eval('window.__head3d.meshes');
  rec.triangles = await b.eval('window.__head3d.triangles');
  rec.sample0 = await b.eval('window.__head3d.sample()');
  rec.shot0 = await shot(`${v.name}-explode0`);

  // explode slider: a real input event on the range, then the animation must move the parts
  await b.eval(`(() => { const s = document.getElementById('explode'); s.value = '100'; s.dispatchEvent(new Event('input', { bubbles: true })); s.dispatchEvent(new Event('change', { bubbles: true })); })()`);
  await sleep(250);
  rec.explodeMid = await b.eval('window.__head3d.explode()');
  await sleep(2600);
  rec.explodeEnd = await b.eval('window.__head3d.explode()');
  rec.sliderLabel = await b.eval(`document.getElementById('explode-val').textContent`);
  rec.sample100 = await b.eval('window.__head3d.sample()');
  rec.shot100 = await shot(`${v.name}-explode100`);

  // half way: the cap assembly lifted as one unit
  await b.eval(`window.__head3d.setExplode(0.5, true)`);
  await b.eval(`window.__head3d.setView('home')`);
  await sleep(600);
  rec.shot50 = await shot(`${v.name}-explode50`);

  // wiring view
  await b.eval(`window.__head3d.setExplode(0, true)`);
  await b.eval(`document.querySelector('[data-mode=wiring]').click()`);
  await sleep(1600);
  rec.wiringState = await b.eval('window.__head3d.state()');
  rec.labels = await b.eval(`[...document.querySelectorAll('#labels .lab')].filter(e => e.style.display !== 'none' && e.offsetParent !== null).map(e => e.textContent)`);
  rec.sampleWiring = await b.eval('window.__head3d.sample()');
  rec.layoutWiring = await b.eval(LAYOUT);
  rec.shotWiring = await shot(`${v.name}-wiring`);
  await b.eval(`document.querySelector('[data-mode=status]').click()`);
  await sleep(900);

  // pick a part with a real click (amplifier centre; the translucent cap must let the click through)
  const pt = await b.eval(`window.__head3d.screenOf('amp')`);
  await b.click(pt.x, pt.y);
  await sleep(500);
  rec.clickAt = pt;
  rec.picked = await b.eval('window.__head3d.state().sel');
  rec.infoTitle = await b.eval(`(document.querySelector('#tab-info h2') || {}).textContent || ''`);
  rec.panelOpen = await b.eval(`document.getElementById('panel').classList.contains('open')`);
  rec.shotPick = await shot(`${v.name}-picked`);

  // part list with the "new or changed only" filter
  await b.eval(`document.querySelector('[data-tab=list]').click()`);
  await sleep(200);
  await b.eval(`(() => { const f = document.getElementById('f-new'); f.checked = true; f.dispatchEvent(new Event('change', { bubbles: true })); })()`);
  await sleep(500);
  rec.layoutList = await b.eval(LAYOUT);
  rec.shotList = await shot(`${v.name}-list-filter`);
  report.push(rec);
}
const problems = b.consoleProblems();
await b.close();
fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify({ report, problems }, null, 1));
for (const r of report) {
  const lay = [r.layout, r.layoutWiring, r.layoutList];
  const over = lay.some((l) => l.scrollW > l.W + 1 || l.wide.length);
  const small = lay.some((l) => l.small.length);
  const bad = over || small || r.sample0.fraction < 0.02 || r.sample100.fraction < 0.02 || r.explodeEnd < 0.99 || !(r.explodeMid > 0 && r.explodeMid < 1) || r.picked !== 'amp' || r.labels.length < 5;
  console.log(`${bad ? 'FAIL' : 'ok  '} ${r.view} meshes=${r.meshes} tris=${r.triangles} fill0=${r.sample0.fraction.toFixed(3)} fill100=${r.sample100.fraction.toFixed(3)} fillWiring=${r.sampleWiring.fraction.toFixed(3)}`
    + ` explode mid=${r.explodeMid.toFixed(3)} end=${r.explodeEnd.toFixed(3)} label=${r.sliderLabel} labels=${r.labels.length} picked=${r.picked} panelOpen=${r.panelOpen}`
    + ` scrollW=${lay.map((l) => l.scrollW + '/' + l.W).join(',')} inputs=${r.layout.inputs} small=${JSON.stringify(lay.flatMap((l) => l.small))} wide=${JSON.stringify(lay.flatMap((l) => l.wide))}`);
}
console.log('console problems:', JSON.stringify(problems).slice(0, 2000));

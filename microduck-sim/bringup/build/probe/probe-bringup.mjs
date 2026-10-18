// Probe BRINGUP.html at desktop and phone width: overflow, input font size, images, overlay dots, wiring views. Saves screenshots.
import { launch } from './cdp.mjs';
import fs from 'node:fs';
import path from 'node:path';

const PAGE = process.argv[2];
const OUT = process.argv[3];
const ONLY = process.argv[4] ? process.argv[4].split(',') : null;
fs.mkdirSync(OUT, { recursive: true });
const states = [];
for (let i = 0; i <= 13; i++) states.push({ name: `step${i}`, q: `?tab=steps&step=${i}` });
for (const t of ['parts', 'head', 'cad', 'log']) states.push({ name: t, q: `?tab=${t}` });
const views = [
  { name: 'desk', width: 1280, height: 900, deviceScaleFactor: 1, mobile: false },
  { name: 'mob', width: 390, height: 844, deviceScaleFactor: 2, mobile: true },
];
const b = await launch({ profile: path.join(OUT, '.profile') });
const report = [];
const CHECK = `(() => {
  const W = innerWidth, wide = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    let p = el.parentElement, clipped = false;
    while (p && p !== document.body) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') { clipped = true; break; } p = p.parentElement; }
    if (!clipped && r.right > W + 1) wide.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + '.' + [...el.classList].join('.') + ' ' + Math.round(r.right));
  }
  const vis = el => el.offsetParent !== null || getComputedStyle(el).position === 'fixed';
  const small = [...document.querySelectorAll('input,textarea,select')].filter(vis).filter(e => parseFloat(getComputedStyle(e).fontSize) < 16).map(e => (e.id || e.dataset.r || e.type) + ' ' + getComputedStyle(e).fontSize);
  const broken = [...document.querySelectorAll('img')].filter(vis).filter(i => !i.complete || i.naturalWidth === 0).map(i => i.alt || i.src.slice(0, 40));
  const figs = [...document.querySelectorAll('figure.ov')].filter(vis).map(f => ({ part: f.dataset.part, marks: JSON.parse(f.dataset.marks || '[]').length, dots: f.querySelectorAll('.dot').length }));
  const missing = figs.filter(f => f.dots < f.marks);
  const wk = [...document.querySelectorAll('.wkhost')].filter(vis).map(h => { const g = h.querySelector('svg .wk-labels'); return { bench: h.dataset.bench, svgs: h.querySelectorAll('svg').length, h: Math.round(h.getBoundingClientRect().height), pills: g ? g.querySelectorAll('.wk-label:not(.wk-title):not(.wk-block-label)').length : 0, titles: g ? g.querySelectorAll('.wk-title').length : 0 }; });
  const dotOverlap = [];
  for (const host of document.querySelectorAll('.ovimg')) {
    if (!vis(host)) continue;
    const ds = [...host.querySelectorAll('.dot')].map(d => d.getBoundingClientRect());
    for (let i = 0; i < ds.length; i++) for (let j = i + 1; j < ds.length; j++) {
      const a = ds[i], c = ds[j];
      const ox = Math.min(a.right, c.right) - Math.max(a.left, c.left), oy = Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top);
      if (ox > 4 && oy > 4) dotOverlap.push((host.closest('figure')?.dataset.part || host.parentElement.id) + ' ' + i + '/' + j);
    }
  }
  return { scrollW: document.documentElement.scrollWidth, W, wide: wide.slice(0, 8), small, broken, missing, wk, dotOverlap: dotOverlap.slice(0, 10), h: document.documentElement.scrollHeight };
})()`;
for (const v of views) {
  await b.page('Emulation.setDeviceMetricsOverride', v);
  await b.page('Emulation.setTouchEmulationEnabled', { enabled: v.mobile });
  for (const s of states) {
    if (ONLY && !ONLY.includes(s.name)) continue;
    await b.page('Page.navigate', { url: 'file://' + PAGE + s.q });
    await b.waitFor(`document.readyState === 'complete' && !!document.querySelector('.tab.on')`);
    await new Promise(r => setTimeout(r, 700));
    const m = await b.eval(CHECK);
    const { cssContentSize } = await b.page('Page.getLayoutMetrics');
    const h = Math.min(Math.ceil(cssContentSize.height), 9000);
    const shot = await b.page('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: 0, y: 0, width: v.width, height: h, scale: v.mobile ? 1 : 1 } });
    const file = path.join(OUT, `${v.name}-${s.name}.png`);
    fs.writeFileSync(file, Buffer.from(shot.data, 'base64'));
    report.push({ view: v.name, state: s.name, ...m });
  }
}
const problems = b.consoleProblems();
await b.close();
fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify({ report, problems }, null, 1));
for (const r of report) {
  const bad = r.scrollW > r.W + 1 || r.wide.length || r.small.length || r.broken.length || r.missing.length || r.dotOverlap.length || r.wk.some(w => !w.svgs);
  console.log(`${bad ? 'FAIL' : 'ok  '} ${r.view} ${r.state} scrollW=${r.scrollW}/${r.W} h=${r.h}` + (r.wide.length ? ' wide=' + r.wide.join('|') : '') + (r.small.length ? ' small=' + r.small.join('|') : '') + (r.broken.length ? ' broken=' + r.broken.join('|') : '') + (r.missing.length ? ' missing=' + JSON.stringify(r.missing) : '') + (r.dotOverlap.length ? ' overlap=' + r.dotOverlap.join('|') : '') + (r.wk.length ? ' wk=' + JSON.stringify(r.wk) : ''));
}
console.log('console problems:', JSON.stringify(problems).slice(0, 1500));

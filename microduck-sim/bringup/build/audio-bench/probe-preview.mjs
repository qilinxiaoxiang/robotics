// Probe preview.html at desktop and phone width: page overflow, input font size, broken images, overlay dots,
// wiring view, then full-page screenshots. Same checks as ../probe/probe-bringup.mjs (CHECK copied from it at build time).
// Usage: node probe-preview.mjs <out-dir>
import { launch } from '../probe/cdp.mjs';
import fs from 'node:fs';
import path from 'node:path';

const PAGE = path.join(import.meta.dirname, 'preview.html');
const OUT = process.argv[2];
fs.mkdirSync(OUT, { recursive: true });
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
  const wk = [...document.querySelectorAll('.wkhost')].filter(vis).map(h => ({ bench: h.dataset.bench, svgs: h.querySelectorAll('svg').length, h: Math.round(h.getBoundingClientRect().height) }));
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
const EXTRA = `(() => {
  const dots = [...document.querySelectorAll('.ovimg .dot')].map(d => { const r = d.getBoundingClientRect(), h = d.closest('.ovimg').getBoundingClientRect();
    return { fig: d.closest('figure').querySelector('figcaption')?.textContent.slice(0, 18), n: d.textContent, x: +(((r.left + r.width / 2) - h.left) / h.width).toFixed(3), y: +(((r.top + r.height / 2) - h.top) / h.height).toFixed(3), inside: r.left >= h.left - 1 && r.right <= h.right + 1 && r.top >= h.top - 1 && r.bottom <= h.bottom + 1 }; });
  const wires = [...document.querySelectorAll('.wkhost svg path, .wkhost svg line, .wkhost svg polyline')].length;
  const cmdOverflow = [...document.querySelectorAll('.cmd')].filter(c => c.getBoundingClientRect().right > innerWidth + 1).length;
  const figs = [...document.querySelectorAll('#s13 figure')].map(f => Math.round(f.getBoundingClientRect().width));
  return { dots, wires, cmdOverflow, figs };
})()`;
for (const v of views) {
  await b.page('Emulation.setDeviceMetricsOverride', v);
  await b.page('Emulation.setTouchEmulationEnabled', { enabled: v.mobile });
  await b.page('Page.navigate', { url: 'file://' + PAGE });
  await b.waitFor(`document.readyState === 'complete' && !!document.querySelector('#s13 .stephead')`);
  await new Promise(r => setTimeout(r, 900));
  const m = await b.eval(CHECK);
  const x = await b.eval(EXTRA);
  const { cssContentSize } = await b.page('Page.getLayoutMetrics');
  const h = Math.ceil(cssContentSize.height);
  // Full page in slices of at most 4000 CSS px.
  const files = [];
  for (let y = 0, k = 0; y < h; y += 4000, k++) {
    const shot = await b.page('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: 0, y, width: v.width, height: Math.min(4000, h - y), scale: 1 } });
    const file = path.join(OUT, `${v.name}-${k}.png`);
    fs.writeFileSync(file, Buffer.from(shot.data, 'base64'));
    files.push(path.basename(file));
  }
  report.push({ view: v.name, ...m, ...x, files });
}
const problems = b.consoleProblems();
await b.close();
fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify({ report, problems }, null, 1));
for (const r of report) {
  const bad = r.scrollW > r.W + 1 || r.wide.length || r.small.length || r.broken.length || r.missing.length || r.dotOverlap.length || r.wk.some(w => !w.svgs) || r.cmdOverflow || r.dots.some(d => !d.inside);
  console.log(`${bad ? 'FAIL' : 'ok  '} ${r.view} scrollW=${r.scrollW}/${r.W} h=${r.h}` + (r.wide.length ? ' wide=' + r.wide.join('|') : '') + (r.small.length ? ' small=' + r.small.join('|') : '') + (r.broken.length ? ' broken=' + r.broken.join('|') : '') + (r.missing.length ? ' missing=' + JSON.stringify(r.missing) : '') + (r.dotOverlap.length ? ' overlap=' + r.dotOverlap.join('|') : '') + ' wk=' + JSON.stringify(r.wk) + ' wires=' + r.wires + ' cmdOverflow=' + r.cmdOverflow + ' figs=' + r.figs.join(',') + ' files=' + r.files.join(','));
}
console.log('console problems:', JSON.stringify(problems).slice(0, 1500));

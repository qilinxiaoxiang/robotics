// Probe wiring.html at 1280 px and 390 px: horizontal overflow, input font size, broken images, tables, external tags,
// console problems, and wiring-kit's own bench check (missing endpoints, pin reuse, overvoltage, shorts) on every bench.
// Run: node probe_page.mjs [profileDir]   (headless Chrome via ../../../bringup/build/probe/cdp.mjs). Screenshots go to shots/.
import { launch } from '../../../bringup/build/probe/cdp.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'shots');
fs.mkdirSync(OUT, { recursive: true });
const PAGE = path.join(HERE, 'wiring.html');
const views = [
  { name: 'desk', width: 1280, height: 900, deviceScaleFactor: 1, mobile: false },
  { name: 'mob', width: 390, height: 844, deviceScaleFactor: 1, mobile: true },
];
const CHECK = `(() => {
  const W = innerWidth, wide = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width && r.right > W + 1) wide.push(el.tagName.toLowerCase() + '.' + [...el.classList].join('.') + ' ' + Math.round(r.right));
  }
  const small = [...document.querySelectorAll('input,textarea,select,button')].filter(e => parseFloat(getComputedStyle(e).fontSize) < 16).map(e => e.tagName + ' ' + getComputedStyle(e).fontSize);
  const broken = [...document.querySelectorAll('img')].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.alt);
  const benches = [...document.querySelectorAll('.wkhost')].map(h => h.id + ':' + h.querySelectorAll('svg').length + 'svg');
  return { scrollW: document.documentElement.scrollWidth, W, wide: wide.slice(0, 8), small, broken, benches,
           tables: document.querySelectorAll('table').length, ext: [...document.querySelectorAll('script[src],link[href],img[src^="http"]')].length,
           h: document.documentElement.scrollHeight };
})()`;
const ISSUES = `(() => {
  const out = {};
  for (const s of document.querySelectorAll('script:not([src])')) {
    const m = s.textContent.match(/WiringKit\\.render\\(document\\.getElementById\\("([^"]+)"\\),([\\s\\S]*),\\{text:/);
    if (!m) continue;
    const bench = JSON.parse(m[2]);
    out[m[1]] = (WiringKit.checkBench(bench) || []).map(i => (i.code || i.type) + ' ' + (i.wire || i.pin || i.message || JSON.stringify(i)).toString().slice(0, 120));
  }
  return out;
})()`;
const b = await launch({ profile: process.argv[2] || path.join(OUT, '.profile') });
const report = [];
let issues = null;
for (const v of views) {
  await b.page('Emulation.setDeviceMetricsOverride', v);
  await b.page('Page.navigate', { url: 'file://' + PAGE });
  await b.waitFor(`document.readyState === 'complete' && [...document.images].every(i => i.complete)`);
  await new Promise((r) => setTimeout(r, 800));
  const m = await b.eval(CHECK);
  if (!issues) issues = await b.eval(ISSUES);
  const { cssContentSize } = await b.page('Page.getLayoutMetrics');
  const h = Math.min(Math.ceil(cssContentSize.height), 16000);
  const shot = await b.page('Page.captureScreenshot', { format: 'jpeg', quality: 70, captureBeyondViewport: true, clip: { x: 0, y: 0, width: v.width, height: h, scale: 1 } });
  const file = path.join(OUT, `${v.name}-wiring.jpg`);
  fs.writeFileSync(file, Buffer.from(shot.data, 'base64'));
  report.push({ view: v.name, file, ...m });
}
const problems = b.consoleProblems();
await b.close();
fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify({ date: new Date().toISOString(), report, issues, problems }, null, 1));
for (const r of report) {
  const bad = r.scrollW > r.W + 1 || r.small.length || r.broken.length || r.tables || r.ext;
  console.log(`${bad ? 'FAIL' : 'ok  '} ${r.view} scrollW=${r.scrollW}/${r.W} h=${r.h} benches=${r.benches.join(',')} tables=${r.tables} ext=${r.ext}`
    + (r.wide.length ? ' wide=' + r.wide.join('|') : '') + (r.small.length ? ' small=' + r.small.join('|') : '') + (r.broken.length ? ' broken=' + r.broken.join('|') : ''));
}
console.log('wiring-kit issues:', JSON.stringify(issues));
console.log('console problems:', JSON.stringify(problems).slice(0, 1500));

// Probe A7Z-PINS.html and A7Z-ANTENNA.html at 1280 px and 390 px: horizontal overflow, small inputs/buttons,
// broken images, <table> elements, console problems. Saves full-page screenshots in shots/.
// Run: node probe_pages.mjs   (uses ../build/probe/cdp.mjs and the installed Google Chrome, headless)
import { launch } from '../build/probe/cdp.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'shots');
const PAGES = ['A7Z-PINS.html', 'A7Z-ANTENNA.html'].map((p) => path.join(HERE, '..', p));
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
  return { scrollW: document.documentElement.scrollWidth, W, wide: wide.slice(0, 8), small, broken,
           tables: document.querySelectorAll('table').length, imgs: document.querySelectorAll('img').length,
           svgs: document.querySelectorAll('svg').length, ext: [...document.querySelectorAll('script[src],link[href]')].length,
           h: document.documentElement.scrollHeight };
})()`;
const b = await launch({ profile: path.join(OUT, '.profile') });
const report = [];
for (const v of views) {
  await b.page('Emulation.setDeviceMetricsOverride', v);
  for (const p of PAGES) {
    await b.page('Page.navigate', { url: 'file://' + p });
    await b.waitFor(`document.readyState === 'complete' && [...document.images].every(i => i.complete)`);
    await new Promise((r) => setTimeout(r, 600));
    const m = await b.eval(CHECK);
    const { cssContentSize } = await b.page('Page.getLayoutMetrics');
    const h = Math.min(Math.ceil(cssContentSize.height), 30000);
    const shot = await b.page('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: 0, y: 0, width: v.width, height: h, scale: 1 } });
    const file = path.join(OUT, `${v.name}-${path.basename(p, '.html')}.png`);
    fs.writeFileSync(file, Buffer.from(shot.data, 'base64'));
    report.push({ view: v.name, page: path.basename(p), file, ...m });
  }
}
const problems = b.consoleProblems();
await b.close();
fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify({ date: new Date().toISOString(), report, problems }, null, 1));
for (const r of report) {
  const bad = r.scrollW > r.W + 1 || r.small.length || r.broken.length || r.tables || r.ext;
  console.log(`${bad ? 'FAIL' : 'ok  '} ${r.view} ${r.page} scrollW=${r.scrollW}/${r.W} h=${r.h} imgs=${r.imgs} svgs=${r.svgs} tables=${r.tables} ext=${r.ext}`
    + (r.wide.length ? ' wide=' + r.wide.join('|') : '') + (r.small.length ? ' small=' + r.small.join('|') : '') + (r.broken.length ? ' broken=' + r.broken.join('|') : ''));
}
console.log('console problems:', JSON.stringify(problems).slice(0, 1500));

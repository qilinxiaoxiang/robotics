// Probe the full-guide export (team/microduck-build.html + its geometry script) over HTTP, as the page host serves it.
// Checks that the CSP lets the geometry script load, all parts build, a step in chapter 1 and chapter 11 draws,
// and there is no horizontal overflow at 1280 px and 390 px. Screenshots and report.json in team/shots/.
// Run: node probe_guide.mjs   (headless Chrome via ../build/probe/cdp.mjs; starts a local static server)
import { launch } from '../build/probe/cdp.mjs';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TEAM = path.join(HERE, 'team');
const OUT = path.join(TEAM, 'shots');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript' };
const srv = http.createServer((req, res) => {
  const f = path.join(TEAM, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!f.startsWith(TEAM) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(0);
const base = `http://127.0.0.1:${srv.address().port}/microduck-build.html`;
const views = [
  { name: 'desk', width: 1280, height: 900, deviceScaleFactor: 1, mobile: false },
  { name: 'mob', width: 390, height: 844, deviceScaleFactor: 1, mobile: true },
];
const b = await launch({ profile: path.join(OUT, '.profile') });
const report = [];
for (const v of views) {
  await b.page('Emulation.setDeviceMetricsOverride', v);
  for (const step of ['', 'bp-cap']) {
    await b.page('Page.navigate', { url: base + (step ? '#' + step : '') });
    await b.waitFor(`document.documentElement.dataset.guideReady`, 120000);
    await new Promise((r) => setTimeout(r, 2500));
    const m = await b.eval(`(() => ({ ready: document.documentElement.dataset.guideReady, stats: window.guideViewer.stats() || { meshes: 0 }, hash: location.hash, title: document.title,
      status: (document.getElementById('status') || {}).textContent || '', scrollW: document.documentElement.scrollWidth, W: innerWidth,
      chapters: document.querySelectorAll('[data-chapter], .chapter').length }))()`);
    const shot = await b.page('Page.captureScreenshot', { format: 'png' });
    const file = path.join(OUT, `guide-${v.name}-${step || 'start'}.png`);
    fs.writeFileSync(file, Buffer.from(shot.data, 'base64'));
    report.push({ view: v.name, step: step || 'start', file, ...m });
  }
}
const problems = b.consoleProblems();
await b.close(); srv.close();
fs.writeFileSync(path.join(OUT, 'guide-report.json'), JSON.stringify({ date: new Date().toISOString(), report, problems }, null, 1));
let bad = problems.length > 0;
for (const r of report) {
  const fail = r.ready !== '3d' || r.scrollW > r.W + 1 || r.stats.meshes < 170 || !r.stats.visibleParts;
  bad ||= fail;
  console.log(fail ? 'FAIL' : 'ok  ', r.view, r.step, r.hash, 'meshes', r.stats.meshes, 'visible', r.stats.visibleParts, 'scrollW', r.scrollW, '/', r.W);
}
if (problems.length) console.log('console problems:', problems.slice(0, 5));
process.exit(bad ? 1 : 0);

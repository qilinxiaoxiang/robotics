// Builds preview.html: section.html shown alone, with the bring-up template's CSS and the parts of its script
// that the section uses (part chips, photo overlays, wiring view, command boxes, records).
// Nothing in ../template.html or ../build.mjs is changed; both are read as text.
// Usage: node build_preview.mjs
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const HERE = import.meta.dirname;
const BUILD = path.resolve(HERE, '..');
const PARTS_DIR = path.resolve(BUILD, '../parts');
const WK = '/Users/xiangzheng/code/wiring-kit';
const ESBUILD = path.join(WK, 'node_modules/.bin/esbuild');
const OUT = path.join(HERE, 'preview.html');
const USED_PARTS = ['max98357a_3006', 'speaker_cms_30204_18sp', 'pi_zero_w'];

const template = fs.readFileSync(path.join(BUILD, 'template.html'), 'utf8');
const buildSrc = fs.readFileSync(path.join(BUILD, 'build.mjs'), 'utf8');
const between = (s, a, b) => {
  const i = s.indexOf(a), j = s.indexOf(b, i + a.length);
  if (i < 0 || j < 0) throw new Error(`marker not found: ${a} .. ${b}`);
  return s.slice(i, j);
};

// 1. Template CSS (first <style> block) with the wiring-kit CSS in place of its marker.
let css = between(template, '<style>', '</style>').slice('<style>'.length);
if (!css.includes('/*WK_CSS*/')) throw new Error('template CSS has no /*WK_CSS*/ marker');
css = css.replace('/*WK_CSS*/', fs.readFileSync(path.join(WK, 'dist/wiring-kit.css'), 'utf8'));

// 2. Template script blocks the section needs.
const fullDialog = (template.match(/<dialog id="wkfull"[\s\S]*?<\/dialog>/) || [])[0];
if (!fullDialog) throw new Error('template has no #wkfull dialog');
const tplJS = between(template, '/* ---------- part chips ---------- */', '/* ---------- part dialog ---------- */')
  + between(template, '/* ---------- wiring ---------- */', '/* ---------- steps ---------- */')
  + between(template, '/* ---------- commands ---------- */', '/* ---------- records ---------- */');

// 3. Parts: the Chinese text maps are read from build.mjs so the preview cannot drift from the real page.
const literal = name => {
  const start = buildSrc.indexOf(`const ${name} = {`);
  if (start < 0) throw new Error(`build.mjs no longer defines ${name}`);
  const end = buildSrc.indexOf('\n};\n', start);
  return Function(`return (${buildSrc.slice(start + `const ${name} = `.length, end + 2)});`)();
};
const ZH = literal('ZH'), CONN_ZH = literal('CONN_ZH'), PHOTO_SRC = literal('PHOTO_SRC');
const piZh = n => n === '3V3 power' ? '3.3 V 电源' : n === '5V power' ? '5 V 电源' : n === 'Ground' ? 'GND 地线' : n;
const QUALITY = { 'photos/pi_zero_w-top-header-adafruit3708.jpg': 85 };
const cache = path.join(HERE, '.photo-cache');
fs.rmSync(cache, { recursive: true, force: true });
fs.mkdirSync(cache);
const dossier = JSON.parse(fs.readFileSync(path.join(PARTS_DIR, 'parts.json'), 'utf8'));
const PARTS = {};
for (const id of USED_PARTS) {
  const p = dossier.parts.find(x => x.id === id);
  if (!p) throw new Error(`parts.json has no ${id}`);
  const out = path.join(cache, path.basename(p.photo).replace(/\.\w+$/, '.jpg'));
  execFileSync('python3', [path.join(BUILD, 'shrink.py'), path.join(PARTS_DIR, p.photo), out, '900', String(QUALITY[p.photo] ?? 72)], { cwd: BUILD, stdio: 'inherit' });
  const cz = CONN_ZH[id] || {};
  const host = new URL(p.photo_page_url || p.photo_source_url).hostname.replace(/^www\./, '');
  PARTS[id] = {
    zh: ZH[id].zh, short: ZH[id].short, use: ZH[id].use, source: ZH[id].source || '',
    name: p.product_name, mfr: p.manufacturer, mpn: p.manufacturer_pn, dk: p.digikey_pn || '', url: p.product_url,
    img: `data:image/jpeg;base64,${fs.readFileSync(out).toString('base64')}`, w: p.photo_px[0], h: p.photo_px[1],
    photoSrc: PHOTO_SRC[host] || host,
    conns: (p.connectors || []).filter(c => c.label !== 'M2.5').map(c => ({ label: c.label, zh: cz[c.label] ?? c.label, x: c.x, y: c.y })),
    pins: (p.pins || []).map(q => ({ pin: q.pin, name: q.label || q.name, zhname: id === 'pi_zero_w' ? piZh(q.name) : (q.label || q.name), row: q.row || '', x: q.x, y: q.y })),
  };
}
fs.rmSync(cache, { recursive: true, force: true });

// 4. The wiring bench (same module benches.ts would import).
const tmp = path.join(HERE, '.bench.mjs');
execFileSync(ESBUILD, [path.join(HERE, 'bench-entry.ts'), '--bundle', '--platform=node', '--format=esm', '--log-level=warning', `--outfile=${tmp}`], { stdio: 'inherit' });
let benches;
try { benches = execFileSync(process.execPath, [tmp, PARTS_DIR], { maxBuffer: 64 << 20 }).toString(); }
finally { fs.rmSync(tmp, { force: true }); }
JSON.parse(benches);

// 5. Section with its images inlined.
let section = fs.readFileSync(path.join(HERE, 'section.html'), 'utf8');
section = section.replace(/src="audio-bench\/img\/([^"]+)"/g, (m, f) => {
  const file = path.join(HERE, 'img', f);
  const type = f.endsWith('.png') ? 'image/png' : 'image/jpeg';
  return `src="data:${type};base64,${fs.readFileSync(file).toString('base64')}"`;
});
if (/src="(?!data:)/.test(section)) throw new Error('section.html has an image that is not under audio-bench/img/');
section = section.replace('<section class="step" id="s13"', '<section class="step on" id="s13"');

const esc = s => s.replace(/<\/(script)/gi, '<\\/$1');
const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>功放台架预览</title>
<style>${css}
.pvbar{max-width:1160px;margin:0 auto;padding:12px 16px 0;color:var(--muted);font-size:14px}
</style></head>
<body>
<div class="pvbar">预览：台架联调页的第 13 步，单独显示。插进 BRINGUP 页后由 build.mjs 生成。</div>
<main><div class="stepsgrid wide"><div id="steps">
${section}
</div></div></main>
${fullDialog}
<script>${esc(fs.readFileSync(path.join(WK, 'dist/wiring-kit.js'), 'utf8'))}</script>
<script>
const BENCHES = ${esc(benches)};
const PARTS = ${esc(JSON.stringify(PARTS))};
</script>
<script>
(function(){
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function openPart(){}
// {{u}} as on the real page, with the default user name.
const walker=document.createTreeWalker($('#steps'),NodeFilter.SHOW_TEXT);let n;
while((n=walker.nextNode()))if(n.nodeValue.includes('{{u}}'))n.nodeValue=n.nodeValue.split('{{u}}').join('duck');
${esc(tplJS)}
renderWiringIn($('#s13'));
const s=$('#s13'),head=document.createElement('div');head.className='stephead';
const lab=document.createElement('label');lab.className='donebox';lab.innerHTML='<input type="checkbox"> 这一步做完了';
const no=s.querySelector('.stepno');head.appendChild(no.cloneNode(true));head.appendChild(lab);no.replaceWith(head);
})();
</script>
</body></html>
`;
fs.writeFileSync(OUT, html);
console.log(`wrote ${OUT} (${(fs.statSync(OUT).size / 1024).toFixed(0)} KB), parts ${Object.keys(PARTS).join(', ')}, benches ${Object.keys(JSON.parse(benches)).join(', ')}`);

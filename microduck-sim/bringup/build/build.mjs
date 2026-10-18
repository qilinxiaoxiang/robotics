// Builds ../BRINGUP.html: one self-contained page (no network fetches).
// Inputs: template.html, benches.ts (wiring benches; guide-benches.ts copies the step 11 UART drawing from
// ../../guide/data/guide-data.json with Chinese text), ../parts/parts.json + photos, wiring-kit dist.
// Usage: node build.mjs
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const HERE = import.meta.dirname;
const ROOT = path.resolve(HERE, '..');
const PARTS_DIR = path.join(ROOT, 'parts');
const WK = '/Users/xiangzheng/code/wiring-kit';
const ESBUILD = path.join(WK, 'node_modules/.bin/esbuild');
const OUT = path.join(ROOT, 'BRINGUP.html');

// 1. Benches: bundle benches.ts next to this file (it resolves ../parts from its own location) and run it.
const tmpBundle = path.join(HERE, '.benches.mjs');
execFileSync(ESBUILD, [path.join(HERE, 'benches.ts'), '--bundle', '--platform=node', '--format=esm', '--log-level=warning', `--outfile=${tmpBundle}`], { stdio: 'inherit' });
let benches;
try { benches = execFileSync(process.execPath, [tmpBundle], { maxBuffer: 64 << 20 }).toString(); }
finally { fs.rmSync(tmpBundle, { force: true }); }
JSON.parse(benches);

// 2. Parts: compact records with Chinese text and data-URI photos.
const dossier = JSON.parse(fs.readFileSync(path.join(PARTS_DIR, 'parts.json'), 'utf8'));
const ZH = {
  pi_zero_w: { zh: '树莓派 Raspberry Pi Zero W', short: '主电脑', use: '机器人的主电脑。运行 Linux，连 Wi-Fi，读摄像头和 IMU，通过 USB 给 OpenRB 发命令。',
    source: '自己已有的板子，不是从 DigiKey 买的。DigiKey 的同款货号是 2648-SC0020-ND。' },
  camera_module_3_wide: { zh: '摄像头 Camera Module 3 Wide', short: '广角摄像头', use: '头上的摄像头。1200 万像素，对角 120 度广角。' },
  camera_cable_sc1892: { zh: '摄像头排线 SC1892', short: '15 针转 22 针', use: '宽头 15 针接摄像头，窄头 22 针接 Pi Zero。摄像头自带的线插不进 Pi Zero，所以换成这根。' },
  bno085_4754: { zh: '姿态传感器 BNO085（IMU）', short: '测倾斜和转动', use: '测量身体的倾斜和转动，通过 I2C 告诉 Pi。走路保持平衡要用它。' },
  stemma_qt_cable_4397: { zh: 'STEMMA QT 转杜邦插孔线 4397', short: 'IMU 到 Pi 的线', use: '一头是插 IMU 的白色小插头，另一头是 4 个插孔套，直接套在 Pi 的针上，不用焊。' },
  max98357a_3006: { zh: '功放 MAX98357A', short: '数字功放', use: '把 Pi 输出的数字音频（I2S）放大，推动喇叭。' },
  speaker_cms_30204_18sp: { zh: '喇叭 CMS-30204-18SP', short: '30 × 20 mm 喇叭', use: '8 欧姆、1 W 的小喇叭。背面只有两个焊盘，没有引线。' },
  usb_pd_5991: { zh: 'USB-C 取电板 Adafruit 5991', short: '从充电器取固定电压', use: '向 USB-C 充电器要一个固定电压，从螺丝端子输出。第 6 步在桌上拨到 5 V 临时试舵机；第 12 步起只拨 15 V 一个开关（5V 也开着会变成 5 V；改了开关要拔掉 USB-C 再插；9 V 走路会掉电），装在机器人背后转换盒的最下层，喂两块 XL4015 降压板。' },
  xl4015_robotis: { zh: '降压板 XL4015（OMX-AI 套件的 DC converter）', short: '15 V 降到 7 V / 5 V', use: '两块，平躺在背后转换盒里：#1 在最上层，调到 7.40 V（7 V 线；舵机 Shutdown 52），给 OpenRB 和全部舵机；#2 在中间层，调到 5.00 V，给 Pi。两个蓝色多圈旋钮：OUT 在左、IN 在右、旋钮朝下时，右边挨着 XL4015 芯片的应该是调电压，左边挨着 LM358 的应该是调限流（按布局推断，用万用表拧一拧确认）。',
    source: 'ROBOTIS OMX-AI 套件里带的（三套里拿两块，第三块留在 OMX-F 机械臂上），不是从 DigiKey 买的。' },
  usb_cable_4472: { zh: 'USB-A 转 USB-C 线 4472', short: '15 cm 数据线', use: '以后连接 Pi 和 OpenRB（Pi 那头还要一个 OTG 转接头）。你的 Mac 有 USB-A 口的话，今天也可以用它连 OpenRB。' },
  openrb_150: { zh: '舵机控制板 OpenRB-150', short: '舵机控制板', use: 'Mac（以后是 Pi）通过 USB-C 连它，它再通过三芯线控制舵机，同时给舵机供电。',
    source: 'ROBOTIS OMX-AI 套件里带的，不是从 DigiKey 买的。' },
  xl330_m288_t: { zh: '舵机 DYNAMIXEL XL330-M288-T', short: '关节舵机', use: '每个关节一个，机器人上共 15 个。用三芯线串成一串，电源和数据走同一根线。',
    source: 'ROBOTIS OMX-AI 套件里带的，不是从 DigiKey 买的。' },
  dfr1202: { zh: '降压模块 DFRobot DFR1202', short: '12 V 降到 5 V', use: '不用：10 月 14 日起舵机用 XL4015 给的 7 V，Pi 用另一块 XL4015 给的 5 V。只有焊盘。' },
  xt30_fit0586: { zh: 'XT30 电源插头 FIT0586', short: '可拔开的电源插头', use: '10 月 13 日起不用：电源线直接拧在螺丝端子上，断电就拔 USB-C 线。尾部是焊杯。' },
  fuse_0251010_10a: { zh: '保险丝 10 A（Littelfuse 251 系列）', short: '保险丝', use: '原计划放在 5 V 输出后、舵机总支路的主保险丝。10 月 11 日起整个机器人不用保险丝。' },
  fuse_0251003_3a: { zh: '保险丝 3 A（Littelfuse 251 系列）', short: '保险丝', use: '原计划 8 路舵机支路和 Pi 支路各一个。10 月 11 日起整个机器人不用保险丝。' },
  fuse_0251005_5a: { zh: '保险丝 5 A（Littelfuse 251 系列）', short: '保险丝', use: '原计划放在电源输入端的总保险丝。10 月 11 日起整个机器人不用保险丝。' },
  fuse_0251500_0p5a: { zh: '保险丝 0.5 A（Littelfuse 251 系列）', short: '保险丝', use: '原计划给声音支路的保险丝。10 月 11 日起整个机器人不用保险丝。' },
};
const CONN_ZH = {
  pi_zero_w: { microSD: 'microSD 卡槽', 'mini-HDMI': 'mini-HDMI 视频口（今天不用）', USB: 'USB 数据口（不是电源口）', 'PWR IN': 'PWR IN 电源口（插充电器）',
    'CAMERA 22-pin': '摄像头接口（22 针）', 'GPIO 2x20': '40 针排针（GPIO）', RUN: 'RUN 焊盘（不用）', TV: 'TV 焊盘（不用）', ACT: 'ACT 绿灯（工作指示）' },
  camera_module_3_wide: { 'CSI 15-pin FPC': '排线接口（15 针，在背面）', lens: '镜头（先撕掉保护膜）', 'Camera Module 3 Wide': '板上印字：确认是 Wide 版', '15-15 cable': '自带排线：插不进 Pi Zero，要换掉' },
  camera_cable_sc1892: { '15-pin, 1 mm (wide end)': '宽头 15 针：插摄像头', '22-pin, 0.5 mm (narrow end)': '窄头 22 针：插 Pi', 'Standard - Mini | 200mm': '线上印字：Standard - Mini 200mm' },
  bno085_4754: { 'STEMMA QT left': 'STEMMA QT 插座（左）', 'STEMMA QT right': 'STEMMA QT 插座（右），和左边的一样' },
  stemma_qt_cable_4397: { 'JST SH 4-pin, 1 mm pitch': '白色小插头：插 IMU', 'blue = SDA': '蓝线：SDA 数据', 'black = GND': '黑线：GND 地线', 'red = 3.3 V': '红线：3.3 V 电源', 'yellow = SCL': '黄线：SCL 时钟' },
  max98357a_3006: { '-': '喇叭端子 −（螺丝端子）', '+': '喇叭端子 +（螺丝端子）' },
  speaker_cms_30204_18sp: { '+': '焊盘 +', '-': '焊盘 −' },
  usb_pd_5991: { 'USB-C': 'USB-C 输入口：接充电器', 'STEMMA QT': 'STEMMA QT 插座（不用）', '5V / 6': '开关 6：5 V', '9V / 5': '开关 5：9 V', '12V / 4': '开关 4：12 V',
    '15V / 3': '开关 3：15 V', '18V / 2': '开关 2：18 V', '20V / 1': '开关 1：20 V', '+': '输出端子 +', '-': '输出端子 −', ISet: 'ISet 电流跳线（出厂连着，要 1.25 A）',
    'D-': 'D− 焊盘（不用）', 'D+': 'D+ 焊盘（不用）', OFF: 'OFF 焊盘（不用）', 'green LED': '绿灯：端子有电时亮', 'LED jumper': 'LED 跳线（不用动）' },
  usb_cable_4472: { 'USB-C': 'USB-C 头：插 OpenRB', 'USB-A': 'USB-A 头：插电脑' },
  xl4015_robotis: { 'IN+': 'IN+ 输入 +（15 V 红线）', 'IN-': 'IN− 输入 −（黑线）', 'OUT+': 'OUT+ 输出 +', 'OUT-': 'OUT− 输出 −',
    'trim L': '蓝色旋钮（靠电感）', 'trim R': '蓝色旋钮（靠芯片）', 'R LED': 'R 红灯：限流在起作用时亮' },
  openrb_150: { J1: 'J1：USB-C 口', '-': '电源端子 −', '+': '电源端子 +', JP1: 'JP1：供电跳线', J11: '舵机口 J11', J9: '舵机口 J9', J8: '舵机口 J8', J10: '舵机口 J10',
    RESET: 'RESET 复位按钮', PWR: 'PWR 绿灯：板子通电', DXL: 'DXL 红灯：舵机口有电', USER: 'USER 橙灯（程序控制）', F1: 'F1：USB 保险丝 500 mA', J6: 'J6：Arduino 排针（不用）', J7: 'J7：Arduino 排针（不用）' },
  xl330_m288_t: { 'Left TTL port': '舵机线插口（左）', 'Right TTL port': '舵机线插口（右），和左边的一样' },
  dfr1202: { VIN: '输入 + 焊盘', GND: '地焊盘（输入输出共用）', VOUT: '输出 5 V 焊盘' },
  xt30_fit0586: { 'F cup 1': '母头焊杯 1', 'F cup 2': '母头焊杯 2', 'M cup 1': '公头焊杯 1', 'M cup 2': '公头焊杯 2', 'XT30U-F': '母头外壳印字' },
  fuse: { lead: '金属引线（不分方向）', '2A (photo example)': '本体印着电流值（照片里是 2 A 的样品）' },
};
const PHOTO_SRC = {
  'adafruit.com': 'Adafruit 产品页', 'learn.adafruit.com': 'Adafruit 教程页', 'raspberrypi.com': 'Raspberry Pi 产品资料', 'datasheets.raspberrypi.com': 'Raspberry Pi 产品资料',
  'pip.raspberrypi.com': 'Raspberry Pi 产品资料', 'robotis.us': 'ROBOTIS 产品页', 'dfrobot.com': 'DFRobot 产品页', 'sameskydevices.com': 'Same Sky（原 CUI Devices）产品页',
  'mrsdprojects.ri.cmu.edu': 'Littelfuse 251 系列数据手册',
};
const piZh = n => n === '3V3 power' ? '3.3 V 电源' : n === '5V power' ? '5 V 电源' : n === 'Ground' ? 'GND 地线' : n;

// Photos are downscaled and re-encoded by shrink.py (Pillow), run from this folder with absolute paths.
const cache = path.join(HERE, '.photo-cache');
fs.rmSync(cache, { recursive: true, force: true });
fs.mkdirSync(cache);
const KEEP_PNG = new Set(['photos/camera_cable_sc1892_rev2_drawing.png']); // line drawing: PNG is smaller and sharper
const QUALITY = { 'photos/pi_zero_w-top-header-adafruit3708.jpg': 85, 'photos/openrb_150_top.png': 85 }; // pin-level detail
function photoURI(rel) {
  const file = path.join(PARTS_DIR, rel);
  if (KEEP_PNG.has(rel)) return `data:image/png;base64,${fs.readFileSync(file).toString('base64')}`;
  const out = path.join(cache, path.basename(rel).replace(/\.\w+$/, '.jpg'));
  execFileSync('python3', [path.join(HERE, 'shrink.py'), file, out, '900', String(QUALITY[rel] ?? 72)], { cwd: HERE, stdio: 'inherit' });
  return `data:image/jpeg;base64,${fs.readFileSync(out).toString('base64')}`;
}
const PHOTOS = [];
const photoIndex = new Map();
const PARTS = {};
for (const p of dossier.parts) {
  const z = ZH[p.id];
  if (!z) throw new Error(`no Chinese text for part ${p.id}`);
  const cz = CONN_ZH[p.id] ?? (p.id.startsWith('fuse_') ? CONN_ZH.fuse : {});
  if (!photoIndex.has(p.photo)) { photoIndex.set(p.photo, PHOTOS.length); PHOTOS.push(photoURI(p.photo)); }
  const host = new URL(p.photo_page_url || p.photo_source_url).hostname.replace(/^www\./, '');
  const conns = (p.connectors || []).filter(c => c.label !== 'M2.5').map(c => {
    if (!(c.label in cz)) throw new Error(`no Chinese label for ${p.id} connector ${c.label}`);
    return { label: c.label, zh: cz[c.label], x: c.x, y: c.y };
  });
  const pins = (p.pins || []).map(q => ({ pin: q.pin, name: q.label || q.name, zhname: p.id === 'pi_zero_w' ? piZh(q.name) : (q.label || q.name), row: q.row || '', x: q.x, y: q.y }));
  PARTS[p.id] = {
    zh: z.zh, short: z.short, use: z.use, source: z.source || '',
    name: p.product_name, mfr: p.manufacturer, mpn: p.manufacturer_pn, dk: p.digikey_pn || '', url: p.product_url,
    img: photoIndex.get(p.photo), w: p.photo_px[0], h: p.photo_px[1], photoSrc: p.photo_credit_zh || PHOTO_SRC[host] || host, conns, pins,
  };
}
fs.rmSync(cache, { recursive: true, force: true });

// 3. Store each board drawing once; modules point at it as "@svg:N" and the page restores them.
const benchObj = JSON.parse(benches);
// Ship only the benches the page shows; a drawing removed from the template must not linger in the data.
const shown = new Set([...fs.readFileSync(path.join(HERE, 'template.html'), 'utf8').matchAll(/data-bench="([^"]+)"/g)].map(m => m[1]));
for (const k of Object.keys(benchObj)) if (!shown.has(k)) delete benchObj[k];
for (const k of shown) if (!benchObj[k]) throw new Error(`template shows bench ${k} but benches.ts does not build it`);
const SVGS = [];
const svgIndex = new Map();
for (const b of Object.values(benchObj)) for (const m of b.modules) {
  const svg = m.drawing?.svg;
  if (typeof svg !== 'string') continue;
  if (!svgIndex.has(svg)) { svgIndex.set(svg, SVGS.length); SVGS.push(svg); }
  m.drawing.svg = `@svg:${svgIndex.get(svg)}`;
}

// 4. Assemble.
const esc = s => s.replace(/<\/(script)/gi, '<\\/$1');
let html = fs.readFileSync(path.join(HERE, 'template.html'), 'utf8');
// Step 13 images (audio-bench/img) and the step 12 power picture (power-diagram/power.png) are inlined as data URIs.
html = html.replace(/src="(audio-bench\/img|power-diagram)\/([^"]+)"/g, (m, dir, f) =>
  `src="data:image/${f.endsWith('.png') ? 'png' : 'jpeg'};base64,${fs.readFileSync(path.join(HERE, dir, f)).toString('base64')}"`);
const put = (marker, value) => {
  if (!html.includes(marker)) throw new Error(`template marker missing: ${marker}`);
  html = html.split(marker).join(value);
};
const guideData = JSON.parse(fs.readFileSync(path.join(HERE, '../../guide/data/guide-data.json'), 'utf8'));
const uartItem = guideData.steps.find(s => s.id === 'uart-wires')?.prepare?.[0]?.item ?? '';
const uartMM = /(\d+) mm each/.exec(uartItem);
if (!uartMM) throw new Error('guide step uart-wires no longer states the UART wire length as "<n> mm each"');
put('{{UART_MM}}', uartMM[1]);
// Amplifier wire cut lengths come from the build guide, so both pages always give the same numbers.
const guideItem = (stepId, re, what) => {
  const items = (guideData.steps.find(s => s.id === stepId)?.prepare ?? []).map(p => p.item);
  for (const it of items) { const m = re.exec(it); if (m) return m; }
  throw new Error(`guide step ${stepId} no longer states ${what}`);
};
const amp = guideItem('wire-list', /LRC (\d+), BCLK (\d+), DIN (\d+), GND (\d+) and Vin (\d+) mm/, 'the five amplifier wire lengths');
['LRC', 'BCLK', 'DIN', 'GND', 'VIN'].forEach((k, i) => put(`{{AMP_${k}_MM}}`, amp[i + 1]));
put('/*WK_CSS*/', fs.readFileSync(path.join(WK, 'dist/wiring-kit.css'), 'utf8'));
put('/*WK_JS*/', esc(fs.readFileSync(path.join(WK, 'dist/wiring-kit.js'), 'utf8')));
put('/*BENCHES*/null', esc(JSON.stringify(benchObj)));
put('/*SVGS*/null', esc(JSON.stringify(SVGS)));
put('/*PHOTOS*/null', esc(JSON.stringify(PHOTOS)));
put('/*PARTS*/null', esc(JSON.stringify(PARTS)));
fs.writeFileSync(OUT, html);
console.log(`wrote ${OUT} (${(fs.statSync(OUT).size / 1024).toFixed(0)} KB), ${Object.keys(PARTS).length} parts, ${PHOTOS.length} photos, ${SVGS.length} drawings, benches: ${Object.keys(benchObj).join(', ')}`);

// Chinese copies of the assembly guide's wiring benches for the bring-up page.
// Geometry (board drawings, pin positions, placements, routing endpoints) is read from the guide's own
// build output, guide/data/guide-data.json, so the guide stays the single source. This file only:
//  1. picks a source bench (a guide step's wiring.bench) and optionally keeps a subset of its modules and wire groups;
//  2. replaces the English text (module titles, pin names and notes, wire captions, group labels) with Chinese;
//  3. adds Chinese marker text (pinText) for every wired pin.
// The build fails if the guide renames or adds a pin, wire, group or module that has no Chinese text here,
// so a changed guide cannot silently show English or stale captions.
import fs from 'node:fs';
import path from 'node:path';
import type { Bench, Module, Pin, Wire } from '/Users/xiangzheng/code/wiring-kit/src/model';

const GUIDE_DATA = path.resolve(import.meta.dirname, '../../guide/data/guide-data.json');

type Text = { title: string; subtitle?: string; short?: string };
type PinZh = { name: string; note?: string };
interface Spec {
  source: string;                       // guide step id whose wiring.bench is copied
  modules?: string[];                   // keep only these modules (default: all)
  groups?: string[];                    // keep only wires in these groups (default: all)
  modulesZh: Record<string, Text>;
  pinsZh: Record<string, PinZh>;        // 'module.pin'
  groupsZh: Record<string, string>;
  wiresZh: Record<string, { label: string; note?: string }>;
  pinText: Record<string, string>;      // marker text beside each wired pin
}

// ---- shared Chinese text -----------------------------------------------------------------------------
const ORB_TEXT: Text = { title: 'OpenRB-150，USB-C 口朝上', short: 'OpenRB', subtitle: 'ROBOTIS OpenRB-150 舵机控制板（902-0183-000），元件面朝上' };
// Steps 11 and 12 draw the Pi turned round (header at the bottom) so the Pi lead and the UART pair reach their pins without crossing.
const PI_TURNED: Text = { title: 'Pi Zero W（转了 180°：排针在下，microSD 卡槽在右）', short: 'Pi', subtitle: 'Raspberry Pi Zero W，排针在下；这里用 2、6、8、10 号针' };

const ORB_PINS: Record<string, PinZh> = {
  'orb.Tx': { name: '印着 Tx 的孔', note: '焊白线，白线另一头插 Pi 10 号针。' },
  'orb.Rx': { name: '印着 Rx 的孔', note: '焊绿线，绿线另一头插 Pi 8 号针。' },
  'orb.V': { name: '印着 V 的孔：不用', note: '不接任何线。' },
  'orb.G': { name: '印着 G 的孔：不用', note: '不接任何线。' },
  'orb.JPV': { name: 'JP1 供电跳线的 VIN(DXL) 一侧', note: '从螺丝端子供电时，跳线帽套在这一侧。用 USB 供电时套在另一侧 +5V。' },
  'orb.n': { name: '螺丝端子 −（左边螺丝）', note: '7 V 黑线拧在这里，来自 XL4015 #1 的 OUT−（第 12 步）。一个螺丝只拧一根线。' },
  'orb.p': { name: '螺丝端子 +（右边螺丝）', note: '7 V 红线拧在这里，来自 XL4015 #1 的 OUT+（第 12 步）。一个螺丝只拧一根线。' },
};
// Pi pins in the full 40-pin drawing: "Pi pin 8 (8 GPIO 14)" -> "Pi 8 号针（GPIO 14）".
function piPinZh(pin: Pin): PinZh | undefined {
  const m = /^Pi pin (\d+) \(\d+ (.+)\)$/.exec(pin.name);
  if (!m) return undefined;
  return { name: `Pi ${m[1]} 号针（${m[2]}）`, note: pin.note === 'Not used by this connection.' ? '这里不用这根针。' : undefined };
}
// ---- the guide-derived bench on the page --------------------------------------------------------------------
const SPECS: Record<string, Spec> = {
  // Step 11: only the two UART wires soldered into J12; the converter is not on the bench yet.
  uart: {
    source: 'uart-wires', modules: ['orb', 'pi'], groups: ['uart'],
    modulesZh: { orb: ORB_TEXT, pi: { ...PI_TURNED, subtitle: 'Raspberry Pi Zero W，排针在下；这一步只用 8、10 号针' } },
    pinsZh: {
      ...ORB_PINS,
      'pi.8': { name: 'Pi 8 号针（GPIO14 TXD）', note: '绿线：Pi 从这里发数据，到 OpenRB J12 焊盘 3（印着 Rx）。' },
      'pi.10': { name: 'Pi 10 号针（GPIO15 RXD）', note: '白线：Pi 在这里收数据，来自 OpenRB J12 焊盘 4（印着 Tx）。' },
      'pi.2': { name: 'Pi 2 号针（5V）', note: '第 12 步红杜邦线（来自 XL4015 #2 的 OUT+，5 V）的母头插这里。这一步不用。' },
      'pi.6': { name: 'Pi 6 号针（GND）', note: '第 12 步黑杜邦线（来自 XL4015 #2 的 OUT−）的母头插这里。这一步不用。' },
    },
    groupsZh: { uart: 'OpenRB ↔ Pi 的两根线' },
    wiresZh: {
      tx: { label: '绿线，{uartMM} mm：OpenRB 印着 Rx 的孔 → Pi 8 号针', note: '一头焊进孔里，另一头是杜邦插头，插在针上。' },
      rx: { label: '白线，{uartMM} mm：OpenRB 印着 Tx 的孔 → Pi 10 号针', note: '一头焊进孔里，另一头是杜邦插头，插在针上。' },
    },
    pinText: { 'orb.Rx': 'Rx 孔：绿线', 'orb.Tx': 'Tx 孔：白线', 'pi.8': '8 号针：绿线', 'pi.10': '10 号针：白线' },
  },
  // Step 12: the whole power chain from the guide's chapter-3 bench (5991 at 15 V, XL4015 #1 at 7.40 V (the 7 V rail), #2 at 5 V) plus
  // the UART pair, so the page shows exactly the guide's wires.
  power7: {
    source: 'bench-test',
    modulesZh: {
      orb: ORB_TEXT,
      pi: PI_TURNED,
      pd: { title: 'Adafruit 5991 取电板（15 V）', short: '5991', subtitle: '只拨开关 3（15V），ISet 不剪；在盒子最下面一层，USB-C 口朝左（机器人的左边），螺丝端子朝右' },
      xl1: { title: '#1（上）7.40 V', short: '#1（上）7.40 V', subtitle: 'OMX-AI 套件的降压板，给舵机；从背后看在盒子最上面一层，平躺：IN 在右，OUT 在左，元件朝你，旋钮在下边' },
      xl2: { title: '#2（中）5.00 V', short: '#2（中）5.00 V', subtitle: 'OMX-AI 套件的降压板，给 Pi；从背后看在盒子中间一层，平躺：IN 在右，OUT 在左，元件朝你，旋钮在下边' },
    },
    pinsZh: {
      ...ORB_PINS,
      'pi.2': { name: 'Pi 2 号针（5V）', note: '红杜邦线的母头，来自 XL4015 #2 的 OUT+。只能是 5 V。' },
      'pi.6': { name: 'Pi 6 号针（GND）', note: '黑杜邦线的母头，来自 XL4015 #2 的 OUT−。' },
      'pi.8': { name: 'Pi 8 号针（GPIO14 TXD）', note: '绿线：Pi 从这里发数据，到 OpenRB J12 焊盘 3（印着 Rx）。' },
      'pi.10': { name: 'Pi 10 号针（GPIO15 RXD）', note: '白线：Pi 在这里收数据，来自 OpenRB J12 焊盘 4（印着 Tx）。' },
      'pd.P': { name: '5991 螺丝端子 +（图里下面的螺丝，旁边印着 ⊕）', note: '15 V 红线到 XL4015 #2 的 IN+。一个螺丝一根线。' },
      'pd.N': { name: '5991 螺丝端子 −（图里上面的螺丝）', note: '15 V 黑线到 XL4015 #2 的 IN−。' },
      'pd.SW15': { name: '开关 3，印着 15V', note: '只有这一个拨到 ON。其余 5 个关着：5V 也开着时它要 5 V；6 个全关时它要充电器的最高电压（小米是 20 V）。不要用 9V：2026-10-15 用 9 V 时第一条走路指令后半秒内整机掉电。板子只在插上 USB-C 时读开关，改了要拔掉再插。' },
      'pd.USB': { name: 'USB-C 输入口', note: '插充电器的线。第 12 步调电压和通电时才插。' },
      'xl1.INP': { name: '#1 IN+（图里 IN 端子下面的螺丝）', note: '一根红线：从 #2 IN+ 接过来的 15 V。' },
      'xl1.INN': { name: '#1 IN−（图里 IN 端子上面的螺丝）', note: '一根黑线：从 #2 IN− 接过来的。' },
      'xl1.OUTP': { name: '#1 OUT+（图里 OUT 端子下面的螺丝）', note: '空着量到 7.35 到 7.45 V（目标 7.40 V）以后，才拧上去 OpenRB 的红线。' },
      'xl1.OUTN': { name: '#1 OUT−（图里 OUT 端子上面的螺丝）', note: '去 OpenRB 的黑线。' },
      'xl2.INP': { name: '#2 IN+（图里 IN 端子下面的螺丝）', note: '两根红线：5991 来的 15 V，和接到 #1 IN+ 的那根。' },
      'xl2.INN': { name: '#2 IN−（图里 IN 端子上面的螺丝）', note: '两根黑线：5991 来的，和接到 #1 IN− 的那根。' },
      'xl2.OUTP': { name: '#2 OUT+（图里 OUT 端子下面的螺丝）', note: '空着量到 4.95 到 5.10 V 以后，才拧上去 Pi 的红杜邦线。' },
      'xl2.OUTN': { name: '#2 OUT−（图里 OUT 端子上面的螺丝）', note: '去 Pi 的黑杜邦线。' },
    },
    groupsZh: { uart: 'OpenRB ↔ Pi 的两根信号线', feed: '15 V：5991 → #2 IN → #1 IN', servo: '7 V：#1 OUT → OpenRB 端子', pi: '5 V：#2 OUT → Pi 2、6 号针' },
    wiresZh: {
      tx: { label: '绿线，{uartMM} mm：OpenRB 印着 Rx 的孔 → Pi 8 号针', note: '第 11 步焊好的。' },
      rx: { label: '白线，{uartMM} mm：OpenRB 印着 Tx 的孔 → Pi 10 号针', note: '第 11 步焊好的。' },
      f15p: { label: '15 V 红线：5991 + → #2 IN+', note: '22 AWG 实心线，两头剥 6 mm。盒子里从最下层和中间层右边的窗口绕出去再绕回来。' },
      f15n: { label: '15 V 黑线：5991 − → #2 IN−', note: '22 AWG 实心线，和红线并排。' },
      l15p: { label: '15 V 红线：#2 IN+ → #1 IN+', note: '和上一根红线挤在 #2 IN+ 同一个螺丝下；从中间层和最上层右边的窗口绕。' },
      l15n: { label: '15 V 黑线：#2 IN− → #1 IN−', note: '和上一根黑线挤在 #2 IN− 同一个螺丝下。' },
      s7p: { label: '7 V 红线：#1 OUT+ → OpenRB 端子 +', note: '22 AWG 实心线；从 OUT 端子往左出最上层左边的窗口、绕回来，在板子和盖子之间往下走到两层之间的缝，穿过前板的过线口 P1 进背包。' },
      s7n: { label: '7 V 黑线：#1 OUT− → OpenRB 端子 −', note: '22 AWG 实心线，和红线一起走。' },
      pip: { label: '红杜邦线：#2 OUT+ → Pi 2 号针', note: '从背包经过线口 P1 进盒子，从中间层左边的窗口绕一圈，走在大线圈外侧，不压线圈；公头剪掉，剥 10 mm，拧成股再对折，拧进螺丝。' },
      pin: { label: '黑杜邦线：#2 OUT− → Pi 6 号针', note: '同样做法。' },
    },
    pinText: {
      'orb.Rx': 'Rx 孔：绿线', 'orb.Tx': 'Tx 孔：白线', 'orb.p': '端子 +：7 V 红线', 'orb.n': '端子 −：7 V 黑线',
      'pi.8': '8 号针：绿线', 'pi.10': '10 号针：白线', 'pi.2': '2 号针：5 V 红', 'pi.6': '6 号针：黑',
      'pd.P': '5991 +（下，红）', 'pd.N': '5991 −（上，黑）',
      'xl1.INP': '#1 IN+（下，红）', 'xl1.INN': '#1 IN−（上，黑）', 'xl1.OUTP': '#1 OUT+（下）7.40 V', 'xl1.OUTN': '#1 OUT−（上）',
      'xl2.INP': '#2 IN+（下，红）', 'xl2.INN': '#2 IN−（上，黑）', 'xl2.OUTP': '#2 OUT+（下）5.00 V', 'xl2.OUTN': '#2 OUT−（上）',
    },
  },
};

type BenchOut = Bench & { pinText: Record<string, string>; source: string };

// Cut length of each UART wire, as the guide's uart-wires step states it ("Jumper wire, green and white (any two colours), 425 mm each").
// Chinese captions write {uartMM} so they follow the guide when the route changes.
export function uartCutMM(data: any): number {
  const step = data.steps.find((s: any) => s.id === 'uart-wires');
  const m = /(\d+) mm each/.exec(step?.prepare?.[0]?.item ?? '');
  if (!m) throw new Error('guide step uart-wires no longer states the UART wire length as "<n> mm each"');
  return Number(m[1]);
}

function derive(key: string, spec: Spec, data: any): BenchOut {
  const step = data.steps.find((s: any) => s.id === spec.source);
  const src: Bench | undefined = step?.wiring?.bench;
  if (!src) throw new Error(`guide step ${spec.source} has no wiring.bench`);
  const fail = (msg: string) => { throw new Error(`bench ${key} (guide step ${spec.source}): ${msg}`); };
  const bench: Bench = JSON.parse(JSON.stringify(src));
  const keepM = new Set(spec.modules ?? bench.modules.map(m => m.id));
  for (const id of keepM) if (!bench.modules.some(m => m.id === id)) fail(`module ${id} is gone`);
  const keepG = new Set(spec.groups ?? bench.groups.map(g => g.id));
  for (const id of keepG) if (!bench.groups.some(g => g.id === id)) fail(`group ${id} is gone`);
  bench.modules = bench.modules.filter(m => keepM.has(m.id));
  bench.placements = bench.placements.filter(p => keepM.has(p.module));
  bench.groups = bench.groups.filter(g => keepG.has(g.id));
  bench.wires = bench.wires.filter(w => keepG.has(w.group));
  const used = new Set<string>();
  for (const w of bench.wires) for (const end of [w.from, w.to]) {
    if (!keepM.has(end.split('.')[0])) fail(`wire ${w.id} leaves the kept modules (${end})`);
    used.add(end);
  }

  const seenPins = new Set<string>();
  for (const m of bench.modules as Module[]) {
    const t = spec.modulesZh[m.id];
    if (!t) fail(`no Chinese title for module ${m.id}`);
    m.title = t.title;
    if (t.subtitle !== undefined) m.subtitle = t.subtitle;
    if (t.short !== undefined) m.short = t.short;
    for (const p of m.pins) {
      const ref = `${m.id}.${p.id}`;
      seenPins.add(ref);
      const z = spec.pinsZh[ref] ?? (m.id === 'pi' ? piPinZh(p) : undefined);
      if (!z) fail(`no Chinese text for pin ${ref} ("${p.name}")`);
      if (p.note && z.note === undefined) fail(`no Chinese note for pin ${ref} ("${p.note}")`);
      p.name = z.name;
      if (z.note !== undefined) p.note = z.note; else delete p.note;
    }
  }
  for (const ref of Object.keys(spec.pinsZh)) {
    const [mid] = ref.split('.');
    if (keepM.has(mid) && !seenPins.has(ref)) fail(`Chinese text names pin ${ref}, which the guide bench no longer has`);
  }
  for (const g of bench.groups) {
    const z = spec.groupsZh[g.id];
    if (!z) fail(`no Chinese label for group ${g.id}`);
    g.label = z;
  }
  const wireIds = new Set(bench.wires.map(w => w.id));
  for (const w of bench.wires as Wire[]) {
    const z = spec.wiresZh[w.id];
    if (!z) fail(`no Chinese caption for wire ${w.id} ("${w.label}")`);
    if (w.note && z.note === undefined) fail(`no Chinese note for wire ${w.id}`);
    w.label = z.label.replace(/\{uartMM\}/g, () => String(uartCutMM(data)));
    if (z.note !== undefined) w.note = z.note; else delete w.note;
  }
  for (const id of Object.keys(spec.wiresZh)) if (!wireIds.has(id)) fail(`Chinese caption for wire ${id}, which the guide bench no longer has`);
  for (const ref of used) if (!spec.pinText[ref]) fail(`no Chinese marker text for wired pin ${ref}`);
  for (const ref of Object.keys(spec.pinText)) if (!used.has(ref)) fail(`marker text for ${ref}, which no kept wire uses`);
  return { ...bench, pinText: spec.pinText, source: spec.source };
}

export function guideBenches(): Record<string, BenchOut> {
  const data = JSON.parse(fs.readFileSync(GUIDE_DATA, 'utf8'));
  const out: Record<string, BenchOut> = {};
  for (const [key, spec] of Object.entries(SPECS)) out[key] = derive(key, spec, data);
  return out;
}

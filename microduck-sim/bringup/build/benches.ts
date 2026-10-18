// Builds the wiring benches for the bring-up page (JSON on stdout).
// Board drawings come from official Fritzing parts in ../parts/fritzing (Adafruit and Fritzing, CC BY-SA)
// or, for the OpenRB-150 which has no Fritzing part, from its product photo with pins placed at the
// photo coordinates recorded in ../parts/parts.json.
import fs from 'node:fs';
import path from 'node:path';
import { fromFritzing } from '/Users/xiangzheng/code/wiring-kit/src/fritzing';
import type { Bench, Module, Pin } from '/Users/xiangzheng/code/wiring-kit/src/model';
import { guideBenches } from './guide-benches';
import { audioBenches } from './audio-bench/bench-audio';

const PARTS = path.resolve(import.meta.dirname, '../parts');
const FZ = path.join(PARTS, 'fritzing');
const read = (f: string) => fs.readFileSync(path.join(FZ, f), 'utf8');
const dossier = JSON.parse(fs.readFileSync(path.join(PARTS, 'parts.json'), 'utf8'));
const part = (id: string) => dossier.parts.find((p: { id: string }) => p.id === id);

const PI_NAMES = ['3V3', '5V', 'GPIO2 SDA', '5V', 'GPIO3 SCL', 'GND', 'GPIO4', 'GPIO14 TXD', 'GND', 'GPIO15 RXD',
  'GPIO17', 'GPIO18 PCM CLK', 'GPIO27', 'GND', 'GPIO22', 'GPIO23', '3V3', 'GPIO24', 'GPIO10 MOSI', 'GND',
  'GPIO9 MISO', 'GPIO25', 'GPIO11 SCLK', 'GPIO8 CE0', 'GND', 'GPIO7 CE1', 'ID_SD', 'ID_SC', 'GPIO5', 'GND',
  'GPIO6', 'GPIO12', 'GPIO13', 'GND', 'GPIO19 PCM FS', 'GPIO16', 'GPIO26', 'GPIO20 PCM DIN', 'GND', 'GPIO21 PCM DOUT'];

function pi(): Module {
  const pins: Record<string, Partial<Pin>> = {};
  PI_NAMES.forEach((n, i) => {
    const gnd = n === 'GND', pwr = n === '3V3' || n === '5V';
    pins[`connector${i}`] = {
      label: String(i + 1), name: n, role: gnd ? 'ground' : pwr ? 'power' : 'signal',
      voltage: gnd ? undefined : n === '5V' ? 5 : 3.3, multi: gnd || pwr,
    };
  });
  return fromFritzing({
    fzp: read('pi_zero_w__Raspberry_Pi_Zero_1.fzp'), svg: read('pi_zero_w__raspberrypi_zero_1_breadboard.svg'),
    id: 'pi', title: 'Raspberry Pi Zero W', subtitle: '树莓派主板，40 针排针', short: 'Pi', pins,
  });
}

function imu(): Module {
  return fromFritzing({
    fzp: read('bno085_4754__part.adafruit_bb7246dc1f9fb642b554dfdbcf82e47c_1.fzp'),
    svg: read('bno085_4754__svg.breadboard.adafruit_82b2a6c2d868cc0647847d952bef1335_1_breadboard.svg'),
    id: 'imu', title: 'Adafruit BNO085 IMU', subtitle: '姿态传感器，DigiKey 1528-4754-ND', short: 'IMU',
    digikey: '1528-4754-ND',
    pins: {
      connector25: { label: 'GND', name: 'STEMMA QT 插座 GND', role: 'ground' },
      connector26: { label: 'VIN', name: 'STEMMA QT 插座 VIN', role: 'power', voltage: 3.3, maxVoltage: 5.5, note: '3 到 5 V 都行' },
      connector27: { label: 'SDA', name: 'STEMMA QT 插座 SDA', role: 'signal', voltage: 3.3 },
      connector28: { label: 'SCL', name: 'STEMMA QT 插座 SCL', role: 'signal', voltage: 3.3 },
    },
  });
}

function pd5991(): Module {
  return fromFritzing({
    fzp: read('usb_pd_5991__part.Adafruit-_21826482517ac24b21d6a931a0c70033_1.fzp'),
    svg: read('usb_pd_5991__svg.breadboard.Adafruit-_21826482517ac24b21d6a931a0c70033_1_breadboard.svg'),
    id: 'pd', title: 'Adafruit 5991 USB-C 取电板', subtitle: 'DigiKey 1528-5991-ND', short: '5991',
    digikey: '1528-5991-ND',
    filter: c => c.id === 'connector101' || c.id === 'connector102',
    pins: {
      connector102: { label: '+', name: '输出 +（拨到 5V 时为 5 V）', role: 'power', voltage: 5 },
      connector101: { label: '−', name: '输出 −', role: 'ground' },
    },
  });
}

// OpenRB-150: product photo as the drawing. Arduino MKR footprint, about 25 mm wide; height from the photo aspect.
function openrb(): Module {
  const p = part('openrb_150');
  const [pw, ph] = p.photo_px ?? [204, 488];
  const w = 25, h = +(w * ph / pw).toFixed(2);
  // The page replaces this token with the part photo it already carries, so the image is stored once.
  const href = '@part-photo:openrb_150';
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${w}mm" height="${h}mm" viewBox="0 0 ${pw} ${ph}">`
    + `<image width="${pw}" height="${ph}" href="${href}" xlink:href="${href}"/></svg>`;
  const at = (name: string) => p.connectors.find((c: { label: string; name: string }) => c.label === name || c.name === name);
  const plus = at('+'), minus = at('-');
  return {
    id: 'rb', title: 'ROBOTIS OpenRB-150', subtitle: '舵机控制板（OMX-AI 套件自带）', short: 'OpenRB',
    drawing: { kind: 'svg', svg }, width: w, height: h,
    pins: [
      { id: 'plus', label: '+', name: '电源端子 +', role: 'power', voltage: 5, maxVoltage: 12.6, x: plus.x * w, y: plus.y * h },
      { id: 'minus', label: '−', name: '电源端子 −', role: 'ground', x: minus.x * w, y: minus.y * h },
    ],
  };
}

const benches: Record<string, Bench> = {
  // IMU SDA/SCL on pins 7 (GPIO4) and 13 (GPIO27): software I2C bus 3 (i2c-gpio), since 2026-10-13.
  imu: {
    modules: [pi(), imu()],
    placements: [{ module: 'pi', x: 0, y: 34 }, { module: 'imu', x: 82, y: 0 }],
    groups: [{ id: 'power', label: '电源', color: '#d7263d' }, { id: 'i2c', label: '信号', color: '#1f6fd1' }],
    wires: [
      { id: 'red', from: 'pi.connector0', to: 'imu.connector26', color: 'red', group: 'power', label: '红：Pi 1 号针 → IMU 的 VIN' },
      { id: 'black', from: 'pi.connector8', to: 'imu.connector25', color: 'black', group: 'power', label: '黑：Pi 9 号针 → IMU 的 GND' },
      { id: 'blue', from: 'pi.connector6', to: 'imu.connector27', color: 'blue', group: 'i2c', label: '蓝：Pi 7 号针 → IMU 的 SDA' },
      { id: 'yellow', from: 'pi.connector12', to: 'imu.connector28', color: 'yellow', group: 'i2c', label: '黄：Pi 13 号针 → IMU 的 SCL' },
    ],
  },
  power: {
    modules: [pd5991(), openrb()],
    placements: [{ module: 'pd', x: 0, y: 30 }, { module: 'rb', x: 50, y: 0 }],
    groups: [{ id: 'power', label: '电源', color: '#d7263d' }],
    wires: [
      { id: 'plus', from: 'pd.connector102', to: 'rb.plus', color: 'red', group: 'power', label: '红线：5991 的 + → OpenRB 的 +' },
      { id: 'minus', from: 'pd.connector101', to: 'rb.minus', color: 'black', group: 'power', label: '黑线：5991 的 − → OpenRB 的 −' },
    ],
  },
};
// Step 11: Chinese copy of the assembly guide's UART bench (geometry read from guide-data.json).
const guide = guideBenches();
for (const k of Object.keys(guide)) if (k in benches) throw new Error(`bench key ${k} used twice`);
// Step 13: amplifier bench (audio-bench/bench-audio.ts).
const audio = audioBenches(PARTS);
for (const k of Object.keys(audio)) if (k in benches || k in guide) throw new Error(`bench key ${k} used twice`);
process.stdout.write(JSON.stringify({ ...benches, ...guide, ...audio }));

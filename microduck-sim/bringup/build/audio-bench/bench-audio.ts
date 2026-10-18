// Wiring bench for the amplifier bench test (BRINGUP step 13, "功放：焊 5 根线"). The five wires are soldered
// into the amplifier (2026-10-13, no header); their far ends are jumper sleeves on the Pi pins.
// Same Fritzing drawings as benches.ts (Adafruit and Fritzing, CC BY-SA). Differs from the "amp" bench in
// benches.ts in one wire: GND goes to Pi pin 34, because pin 6 carries the DFR1202 Pi ground (step 12) and
// pin 14 is kept for the optional UART ground (step 11).
// Usage from benches.ts:  import { audioBenches } from './audio-bench/bench-audio';  ...audioBenches(PARTS)
import fs from 'node:fs';
import path from 'node:path';
import { fromFritzing } from '/Users/xiangzheng/code/wiring-kit/src/fritzing';
import type { Bench, Module, Pin } from '/Users/xiangzheng/code/wiring-kit/src/model';

const PI_NAMES = ['3V3', '5V', 'GPIO2 SDA', '5V', 'GPIO3 SCL', 'GND', 'GPIO4', 'GPIO14 TXD', 'GND', 'GPIO15 RXD',
  'GPIO17', 'GPIO18 PCM CLK', 'GPIO27', 'GND', 'GPIO22', 'GPIO23', '3V3', 'GPIO24', 'GPIO10 MOSI', 'GND',
  'GPIO9 MISO', 'GPIO25', 'GPIO11 SCLK', 'GPIO8 CE0', 'GND', 'GPIO7 CE1', 'ID_SD', 'ID_SC', 'GPIO5', 'GND',
  'GPIO6', 'GPIO12', 'GPIO13', 'GND', 'GPIO19 PCM FS', 'GPIO16', 'GPIO26', 'GPIO20 PCM DIN', 'GND', 'GPIO21 PCM DOUT'];

// pinText: short Chinese marker text beside each wired pin (read by the page's markerLabel for big drawings).
export function audioBenches(partsDir: string): Record<string, Bench & { pinText: Record<string, string> }> {
  const FZ = path.join(partsDir, 'fritzing');
  const read = (f: string) => fs.readFileSync(path.join(FZ, f), 'utf8');

  const pins: Record<string, Partial<Pin>> = {};
  PI_NAMES.forEach((n, i) => {
    const gnd = n === 'GND', pwr = n === '3V3' || n === '5V';
    pins[`connector${i}`] = {
      label: String(i + 1), name: n, role: gnd ? 'ground' : pwr ? 'power' : 'signal',
      voltage: gnd ? undefined : n === '5V' ? 5 : 3.3, multi: gnd || pwr,
    };
  });
  const pi: Module = fromFritzing({
    fzp: read('pi_zero_w__Raspberry_Pi_Zero_1.fzp'), svg: read('pi_zero_w__raspberrypi_zero_1_breadboard.svg'),
    id: 'pi', title: 'Raspberry Pi Zero W', subtitle: '树莓派主板，40 针排针', short: 'Pi', pins,
  });
  const amp: Module = fromFritzing({
    fzp: read('max98357a_3006__part.adafruit_9a4ae3187ff9cf8dabbd6d3535bb2380_7.fzp'),
    svg: read('max98357a_3006__svg.breadboard.adafruit_9a4ae3187ff9cf8dabbd6d3535bb2380_9_breadboard.svg'),
    id: 'amp', title: 'Adafruit MAX98357A 功放', subtitle: '功放，DigiKey 1528-1696-ND', short: '功放',
    digikey: '1528-1696-ND',
    pins: {
      connector14: { label: 'Vin', name: 'Vin（5 V）', role: 'power', voltage: 5, maxVoltage: 5.5, multi: true },
      connector15: { label: 'GND', name: 'GND', role: 'ground' },
      connector19: { label: 'BCLK', name: 'BCLK', role: 'signal', voltage: 3.3, maxVoltage: 5.5 },
      connector20: { label: 'LRC', name: 'LRC', role: 'signal', voltage: 3.3, maxVoltage: 5.5 },
      connector18: { label: 'DIN', name: 'DIN', role: 'signal', voltage: 3.3, maxVoltage: 5.5 },
      // GAIN is left unconnected (default 9 dB gain, no resistor since 2026-10-14); the volume ceiling is in ALSA softvol.
      connector17: { label: 'GAIN', name: 'GAIN：空着（不接 = 9 dB）', role: 'signal', voltage: 5, maxVoltage: 5.5 },
    },
  });

  return {
    amp_bench: {
      modules: [pi, amp],
      placements: [{ module: 'pi', x: 0, y: 40 }, { module: 'amp', x: 20, y: 0 }],
      groups: [{ id: 'power', label: '电源', color: '#d7263d' }, { id: 'i2s', label: '声音信号', color: '#7d4cc2' }],
      pinText: {
        'pi.pin_4': '4 号针 5 V', 'pi.pin_34': '34 号针 GND', 'pi.pin_12': '12 号针', 'pi.pin_35': '35 号针', 'pi.pin_40': '40 号针',
        'amp.VIN': 'Vin', 'amp.GND': 'GND', 'amp.BCLK': 'BCLK', 'amp.LRCLK': 'LRC', 'amp.DIN': 'DIN', 'amp.GAIN': 'GAIN（空）',
      },
      wires: [
        { id: 'vin', from: 'pi.connector3', to: 'amp.connector14', color: 'red', group: 'power', label: 'Pi 4 号针（5 V）→ 功放 Vin' },
        { id: 'gnd', from: 'pi.connector33', to: 'amp.connector15', color: 'black', group: 'power', label: 'Pi 34 号针 → 功放 GND' },
        { id: 'bclk', from: 'pi.connector11', to: 'amp.connector19', color: 'green', group: 'i2s', label: 'Pi 12 号针 → 功放 BCLK' },
        { id: 'lrc', from: 'pi.connector34', to: 'amp.connector20', color: 'purple', group: 'i2s', label: 'Pi 35 号针 → 功放 LRC' },
        { id: 'din', from: 'pi.connector39', to: 'amp.connector18', color: 'orange', group: 'i2s', label: 'Pi 40 号针 → 功放 DIN' },
      ],
    },
  };
}

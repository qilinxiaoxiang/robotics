# Amplifier bench step (MAX98357A five soldered wires, Pi audio)

A self-contained step for the bring-up page: solder five wires straight into the Adafruit 3006 MAX98357A
breakout (no header, no GAIN resistor since 2026-10-14), wire it to the Pi Zero W, set up I2S audio and a software
volume ceiling, and play a short low-volume test. Chinese page text, bench work before the amplifier goes into the head.

Problem it advances: the head audio needs the speaker (CMS-30204-18SP, 8 Ω, 1 W rated) protected from the
amplifier's default 9 dB gain (about 1.6 W at full scale). The protection is the ALSA softvol ceiling `max_dB -6.0`
(0.4 W at full scale, the same as the former 100 kΩ 3 dB hardware setting). Evidence that would change the plan:
the ALSA ceiling not reading −6.00 dB on the real Pi, or a program that opens `hw:MAX98357A` directly.
`../template.html` owns the live text; `section.html` is regenerated from it.

## Files

- `section.html`: the step as a fragment (`<section class="step" id="s13" data-wide="1">`), same classes as the
  sections in `../template.html`, plus a small `#s13`-scoped `<style>` block. Images are referenced as
  `audio-bench/img/...`.
- `img/`: drawings and photos used by the section.
  - `endview.html` → `endview.png`: side view along the pin row (wire in from the front, solder on the back, tail
    1 mm). The resistor drawings (`underside`, `leadform-1..4`, the YAGEO photo) are in `../retired-20261014/`.
  - `max98357a_3006_back.jpg`: crop of Adafruit's product photo of the board back
    (https://cdn-shop.adafruit.com/1200x900/3006-06.jpg). It was saved by the web-fetch tool while checking the
    back silkscreen, then cropped. Adafruit photo, used as a private reference like the other product photos.
  - Render a drawing: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu
    --hide-scrollbars --screenshot=$PWD/X.png --window-size=W,H --force-device-scale-factor=2 "file://$PWD/X.html"`
    with W×H = 640×900 (underside), 670×430 (endview), 400×300 (leadform).
- `bench-audio.ts`: `audioBenches(partsDir)` returns the wiring bench `amp_bench` (Pi pins 4, 34, 12, 35, 40 to
  amp Vin, GND, BCLK, LRC, DIN) with short Chinese pin labels (`pinText`).
- `bench-entry.ts`: prints that bench as JSON for the preview build.
- `build_preview.mjs`: builds `preview.html`. It reads the template's CSS, the script blocks the section needs,
  and the Chinese part text maps from `../build.mjs` as text, so the preview follows those files without
  changing them.
- `preview.html`: the step on its own page (generated, self-contained).
- `probe-preview.mjs`: renders `preview.html` at 1280 px and 390 px with the same checks as
  `../probe/probe-bringup.mjs` (page overflow, input font size, broken images, overlay dots, wiring view) and
  saves full-page screenshots.

```
node build_preview.mjs
node probe-preview.mjs <output-dir>
```

## Inserting the step into BRINGUP.html

1. `../template.html`: paste `section.html` after the `s12` section, inside `#steps`. It becomes 第 13 步.
2. `../benches.ts`: `import { audioBenches } from './audio-bench/bench-audio';` and merge `...audioBenches(PARTS)`
   into the printed object, with the same duplicate-key check used for the guide benches.
3. `../build.mjs`: inline the section images before writing the page, for example after the template is read:
   ```js
   html = html.replace(/src="audio-bench\/img\/([^"]+)"/g, (m, f) =>
     `src="data:image/${f.endsWith('.png') ? 'png' : 'jpeg'};base64,${fs.readFileSync(path.join(HERE, 'audio-bench/img', f)).toString('base64')}"`);
   ```
4. Template follow-ups that the section implies (not done here because the template is owned elsewhere):
   - `LABELS` (export): add `amp_r_alone: '电阻单独量 (kΩ)'` and `amp_r_incircuit: '焊好后 GAIN 到 Vin (kΩ)'`
     so the two new record inputs reach the exported log.
   - `USED` (pin map): the amp ground moves from pin 14 to pin 34.
   - Step 7, `FLOW` and `GROUPS` still say the amplifier cannot be connected today; point them at step 13.
     Step 7's `amp` bench still shows ground on pin 14.
5. Rebuild and run `../probe/probe-bringup.mjs` (extend its state list to step 13).

## Sources (checked 2026-10-13)

- Adafruit product page, https://www.adafruit.com/product/3006: the board ships with a pre-soldered terminal
  block; only the header needs soldering.
- Adafruit learn guide, https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp:
  `/pinouts` (pin names, gain options, SD/MODE), `/assembly` (header soldering),
  `/raspberry-pi-wiring` (Vin→5V, GND→GND, DIN→GPIO21, BCLK→GPIO18, LRCLK→GPIO19),
  `/raspberry-pi-usage` (manual setup: blacklist check, `/etc/asound.conf` with dmix and softvol,
  `dtparam=audio=on` commented out, `dtoverlay=max98357a` in `/boot/firmware/config.txt`; it also recommends
  Adafruit's own installer `i2samp.py`, https://github.com/adafruit/Raspberry-Pi-Installer-Scripts).
- MAX98357A/MAX98357B datasheet 19-6779 Rev 7, Adafruit-hosted copy
  https://cdn-shop.adafruit.com/product-files/3006/MAX98357A-MAX98357B.pdf (the analog.com copy timed out):
  gain table (GAIN to VDD through 100 kΩ = 3 dB, unconnected = 9 dB), output level = input dBFS + 2.1 dB + gain,
  SD_MODE pulldown.
- Raspberry Pi overlay README,
  https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/overlays/README:
  `max98357a` overlay, `no-sdmode` parameter, default SD_MODE pin GPIO4. Card name `MAX98357A` comes from the
  overlay's `simple-audio-card,name`.
- Board geometry: Adafruit EAGLE files, https://github.com/adafruit/Adafruit-MAX98357-I2S-Amp-Breakout
  (`Adafruit MAX98357 Breakout.brd`): 17.78 × 19.05 mm board, 1.57 mm thick, header row 2.54 mm from the edge,
  GAIN net only to U1 pin 2 and the header, R1 1 MΩ from VDD to SD_MODE.
- YAGEO MFR datasheet (local copy above, Apr 2024 V.4): MFR-25 body 6.3 × 2.4 mm, 0.55 mm leads, resistance to
  soldering heat 260 °C for 10 s immersed to 3 mm from the body.
- Same Sky CMS-30204-18X datasheet, https://www.sameskydevices.com/product/resource/cms-30204-18x.pdf: 8 Ω, 1.0 W
  rated, 1.2 W max, hand soldering 360 to 380 °C for 3 ± 1 s.

## Numbers used on the page

- Full scale at 9 dB: 2.1 + 9 = 11.1 dBV = 3.59 Vrms → 1.61 W into 8 Ω (the amp clips first; the datasheet gives
  1.4 W at 1% THD with 5 V). At 3 dB: 5.1 dBV = 1.80 Vrms → 0.40 W. With the −3 dB softvol ceiling: 0.20 W; if
  the resistor joint opens (back to 9 dB): 0.81 W, still under 1 W.
- softvol `min_dB -54.0`, `max_dB -3.0`, 256 steps: 51 dB / 255 = exactly 0.20 dB per step, so 50% → value 128 →
  −28.40 dB and 100% → 255 → −3.00 dB.

## Differences from Adafruit's manual setup

1. `dtoverlay=max98357a,no-sdmode`: without it the overlay drives GPIO4 (pin 7) as SD_MODE; SD stays unconnected
   here and the board's 1 MΩ pull-up selects (L+R)/2.
2. `card MAX98357A` instead of `card 0`: the HDMI card can take index 0.
3. softvol `min_dB`/`max_dB`: the ceiling. It must be in place when the control is first created, because
   `alsactl` restores a saved user control with its old range; the page's trouble item covers removing
   `/var/lib/alsa/asound.state`.

## Open items and uncertainties

- Underside depth: header tails about 1.5 mm (assumed for the roboclub right-angle header; brand unknown) grow to
  about 4 mm with the resistor, heat-shrink and Kapton. Head placement must be checked against 4 mm; the page
  defers to the head assembly instructions.
- The in-circuit GAIN-to-Vin reading is not quantified; the page uses the out-of-circuit 99.0 to 101.0 kΩ reading,
  leg-to-pin continuity and neighbour short checks as the pass criteria. The 3 dB gain itself is not measured
  electrically.
- The ALSA configuration and expected outputs were not run on a Pi from here. `amixer` line wording, `aplay -l`
  device strings, the `speaker-test` banner and the `config.txt` line numbers may differ; the page labels them as
  "类似" or names only the values that matter.
- No photo of the right-angle header exists in the repo; it is drawn (schematic plastic shape).
- Lead length for the speaker (about 50 mm, 40 to 60 mm) follows the head study; the final length is set by the
  head layout.

# A7Z bench pages

Two standalone Chinese pages for the MicroDuck head computer change from the Raspberry Pi Zero W to the Radxa Cubie A7Z.
The Pi pages (`../BRINGUP.html`, built from `../build/`) are unchanged.

- `../A7Z-PINS.html`: Dupont wires on the A7Z 40-pin header (anchors `#changes #count #flags #power #imu #uart #audio #touch #check #software #twi0`).
- `../A7Z-WIRES.html`: one-picture summary, Pi Zero W pin -> A7Z pin for each wire, click a pin, wire or row to show only that wire (builder `build_a7z_wires.py`, probe `node probe_wires.mjs`).
- `../A7Z-ANTENNA.html`: AC019 FPC antenna in the head cap (sections in assembly order: `#parts #stick #mount #clip #plug #check`; the IPEX plug goes on after the cap wire clip, as in guide/content/steps.py).

## Build

```
/tmp/microduck-cad-venv/bin/python render_cad_views.py   # CAD renders -> img/cad_*.png (only when the head geometry changes)
python3 build_a7z_pages.py                               # both HTML pages, images embedded as data URIs
node probe_pages.mjs                                     # headless Chrome at 1280 and 390 px -> shots/, shots/report.json
```

`photos.py` holds the marked Radxa photos and the marked XIAO ESP32-S3 pinout crop (`sources/xiao-esp32s3-front-pinout-crop.png`, from
Seeed's `XIAO_ESP32-S3_front_pinout.png` on the XIAO ESP32S3 getting-started wiki, read 2026-10-15) (pixel coordinates read on the source photos and checked on `shots/check_*.png`).

## Final pin map (2026-10-15)

Inner row (odd): 1 IMU red 3.3 V, 3 IMU blue SDA (TWI7), 5 IMU yellow SCL (TWI7), 7 UART green (A7Z TX to OpenRB Rx),
9 IMU black GND, 11 UART white (A7Z RX from OpenRB Tx), 17 touch board 3.3 V (XIAO 3V3), 25 touch GND, 29 touch SCL
(XIAO D5), 31 touch SDA (XIAO D4), 35 amplifier LRC, 39 amplifier GND. 17 wires in all (12 inner, 5 edge; D-013).
Edge row (even): 2 5 V lead red, 4 amplifier Vin, 6 5 V lead black, 12 amplifier BCLK (method pending Shawn), 40 amplifier DIN.
8 and 10 stay empty (debug console). The camera board covers edge-row pins 10 to 34 (coordinating session's CAD check).

## Sources (checked 2026-10-15)

- Radxa docs, Cubie A7Z, local copies in `../../guide/print/a7z-head/sources/`: `radxa-a7z-pin-gpio.md` (pin table;
  "进入 `rsetup` 的 `Overlay` -> `Manage overlays` 勾选 `Enable TWI7` 选项，勾选后重启系统"; UART4 is `/dev/ttyAS4`, TWI7 is `/dev/i2c-7`),
  `radxa-a7z-uart-debug.md` (UART0_TX Pin8, UART0_RX Pin10, 115200), `radxa-a7z-antenna.md` / `radxa-a7z-ante.md`
  (AC019 双频 FPC 天线, 1 代 IPEX, 42mm × 11.9mm, 线缆长度 50mm, Wi-Fi 2.4GHz / 5GHz; "提供 1 个天线接口用于外接天线，以增强无线通信性能"),
  `a7z-hardware-info.md` (antenna socket position, green power LED), photos `a7z-top.png`, `a7z-bottom.png`.
- Radxa Cubie A7Z schematic V1.11: page 13 J16 VBUS -> FB2 (60R 3A) -> VCC5V0_SYS; page 14 J11 pins 2/4 VCC5V0_SYS,
  pin 1 DCDC1, 8/10 CPUX-TX/RX, 12 I2S0-BCLK, 35 I2S0-LRCK, 40 I2S0-DOUT0; page 12 USB 3.1 port VBUS through U4.
- Header logic level, pins 7/11 (PB0/PB1) and 3/5 (TWI7, PJ23/PJ22), schematic V1.11: page 14 J11 nets `PB0` (pin 7) and
  `PB1` (pin 11) run straight to the A733 balls AE1/AE2 on page 7 (no series part, no level shifter anywhere in the
  schematic). The A733 symbol has no VCC-PB pin; its supply pins are VCC-PC/PD/PE/PG/PH/PJ/PK/PL/PM, VCC18-PF and
  VCC-IO, so PB is on VCC-IO (same as the A523 family: mainline `sun55i-a527-cubie-a5e.dts` has
  `vcc-pb-supply = <&reg_cldo3>;	/* via VCC-IO */`). Page 4: SWOUT2 "3.3V with ON/OFF" feeds VCC-CARD, VCC-PH, VCC-IO.
  Page 7: ball 1L6 VCC-PJ is wired to VCC33-LCD (SWOUT1 "3.3V with ON/OFF"), and TWI7_SCK/SDA have 2.2K pull-ups
  (R30, R215) to VCC33-LCD. Radxa's GPIO page tests input by connecting "the PB7 pin to the GND or 3.3V pin".
  Result: both UART2 and TWI7 header pins are 3.3 V logic.
- radxa-pkg/radxa-overlays (GitHub, main, `arch/arm64/boot/dts/allwinner/overlays/`), copies in `sources/`:
  `sun60iw2p1-twi7.dtso` (title "Enable TWI7", "On Radxa Cubie A7Z this is SDA pin 3 & SCL pin 5."),
  `sun60iw2p1-uart2.dtso` (title "Enable UART2", "On Radxa Cubie A7Z, TX is pin 7 and RX is pin 11."),
  `sun60iw2p1-i2s0-2ch.dtso` (title "Enable I2S0", 2-channel dummy sound card, "This overlay is only for demonstration
  purpose."; A7Z pins 36 mclk, 12 bclk, 35 lrck, 38 din0, 40 dout0),
  `sun60iw2p1-twi0.dtso` (title "Enable TWI0", but `compatible = "radxa,cm-a7-rpi-cm5-io"` only, pins PG8/PG9; added
  2026-08-05 in "feat: add CM-A7 RPi CM5 IO overlays"). On the A7Z, schematic V1.11 page 14 puts pins 29/31 on PB2/PB3
  (Radxa pin table: TWI0-SCK/TWI0-SDA alternate functions) and pin 17 on DCDC1 with pin 1.
- CAD: `../../guide/print/a7z-head/build_a7z_head.py`, `checks.json` (antenna x 64 to 75.9 mm, y -21 to +21 mm, coax
  36 of 50 mm, clip clear of antenna and coax), `../../guide/print/world/camera_board.stl` (coax to camera board 3.8 mm,
  computed 2026-10-15).
- Wire colours, flags and wording: `../build/template.html` steps 4, 11, 12, 13. Backpack 5 V: `DECISIONS.md` D-010.

## Not verified

- No stock overlay enables TWI0 on A7Z pins 29/31 (PB2/PB3). Decision (coordinating session, 2026-10-15): the page marks
  it pending (`#twi0`); a custom overlay (TWI0 on PB2/PB3, fallback i2c-gpio on the same pins, 100 kHz, internal pull-ups
  on both sides) is written and verified at bench acceptance, and only then added to the page.

- UART2 device name `/dev/ttyAS2` is inferred from UART4 = `/dev/ttyAS4`; the page asks for `ls /dev/ttyAS*`.
- The ssh host `radxa@cubie-a7z.local` is inferred from the doc prompt `radxa@cubie-a7z`.
- Speaker output through the Enable I2S0 dummy card is untested on the A7Z; the page marks it pending.
- Pin 12 BCLK connection method (short single female header socket) awaits Shawn's confirmation.

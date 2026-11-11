# Head wiring simplification: handoff (2026-11-11)

Goal: cut the bundle of wires that runs from the MicroDuck head down the neck to the A7Z in the saddle backpack, ideally to one USB cable like the official Pollen duck. Nothing has been built, ordered or flashed. This file is the whole state of the discussion; start here.

## Current wiring (authoritative sources)

- Pin map: `microduck-sim/bringup/A7Z-PINS.html` (19 Dupont wires on the A7Z 40-pin header). Read it, not the overlays, for wire counts.
- From the torso (8, unchanged by any plan): 5 V red 2 / black 6; IMU 1, 3, 5, 9; UART 7 (A7Z TX), 11 (A7Z RX).
- From the head, across the neck (11, plus 1 optional):
  - Amp MAX98357A (5): Vin 4, BCLK 12, LRC 35, GND 39, DIN 40.
  - Touch board XIAO ESP32-S3 (4): 3V3 17, GND 25, SCL 29, SDA 31 (TWI0, I2C slave 0x2A).
  - Ear mics INMP441 x2 (2): GND 34, SD 38. Their SCK/WS/VDD share the amp and touch lines on a 25-hole mini breadboard on the back of the camera.
  - Optional back-of-head mic (1): SD to pin 10, not plugged.
- Camera: U20CAM, its own USB cable to the A7Z USB-C through a USB-A to C adapter. The camera has a Molex PicoBlade 1.25 mm 5-pin socket on its board.
- Overlays: `guide/firmware/pi/duck-i2s0-din3.dts`, `duck-twi0-touch.dts`.
- Touch firmware: `guide/extension-20261015-touch/firmware/touch_xiao/touch_main.cpp`. Pads L1 D0 (GPIO1), R1 D1 (GPIO2), L2 D2 (GPIO3), R2 D3 (GPIO4), M D8 (GPIO7); I2C slave on D4 SDA / D5 SCL. Arduino framework.

## Why the official duck has few wires (earlier session, 2026-11-09)

Session "Micro Duck USB线路由" looked at Pollen's photos: not retouched, thin short black wires at the neck. Pollen's servos daisy-chain on one 3-pin bus, and its main board (Radxa Zero 3) location is unpublished. Our extra wires come from putting the A7Z on the back while camera, mics, amp and touch sit in the head. Hollow-shaft routing and flex PCBs were judged not applicable at this size (FPC dislikes twisting; a soft multi-core cable suits the turning neck better).

## Related fault records (`microduck-sim/FAULTS.json`)

- `head-camera-usb-drop`: closed 2026-11-09. Cause confirmed by Shawn: the camera USB plug at the A7Z worked loose when the body lurched; fixed with a new adapter packed from below (commit cca120b7). Evidence it holds: the 2026-11-06 seepick runs (turns and 4 falls, camera kept working). The adapter model was not named; `CURRENT-STATE.json` `parts_a7z_extensions.usb_a_to_c_adapter` says so. This was the main precondition for plan B (every device would ride one USB plug).
- `touch-twi0-jam`: OK, but hypothesis H1 (weak-pull-up I2C sharing a long bundle with a ~3 MHz I2S clock) is still open. Plan B keeps I2C and I2S inside the head, which removes that risk.

## Plan A: head adapter board (no software change)

One small head board collects the amp, mics and XIAO; one latching multi-core cable (JST both ends) runs to a matching board on the A7Z header. Distinct signals: 5 V, GND (pins 39/25/34 merge), BCLK, LRC, amp DIN, mic SD, SCL, SDA; 3V3 made on the board. Minimum 8 wires, 9 with the back mic. Gain: one locking plug instead of 11 loose Dupont plugs, softer cable, no breadboard. Same pins, overlays and audio chain. Does not reach "one USB".

## Plan B: one USB cable across the neck (preferred direction under discussion)

- In the head: a USB 2.0 hub (WCH CH334) with two downstream devices: the camera (via its PicoBlade socket, dropping the USB-A plug and adapter) and the XIAO.
- The XIAO becomes a USB audio device (UAC) plus touch. Amp and mics wire to XIAO pins inside the head; the A7Z sees an ordinary USB sound card. Touch data rides the same USB link, so pins 29/31 and I2C across the neck go away.
- Neck: one 4-core USB cable (5 V, GND, D+, D-). Header keeps only the 8 torso wires.
- Bandwidth: USB 2.0 480 Mbps; audio + touch about 2 Mbps; the XIAO is a 12 Mbps full-speed device behind the hub.

### XIAO pin budget (paper check, 11 signal pins D0-D10)

- Touch 5, unchanged: D0, D1, D2, D3, D8 (touch needs GPIO1-14; XIAO D0-D5 = GPIO1-6, D8-D10 = GPIO7-9, D6/D7 = GPIO43/44).
- Audio 5: BCLK, LRCK (shared by amp and all mics), DOUT to amp, DIN for the two ear mics (one set L, one R on the same line), DIN for the back mic. Proposed D4, D5, D6, D7, D9 (D4/D5 freed from I2C). Spare: D10.
- Conflict to keep in mind: `CURRENT-STATE.json` records a planned beak contact film (Velostat, in cart, not ordered; the round FSR was rejected) read on XIAO ADC D9/D10. With it the budget is 12 > 11; choose between back mic and beak film, or use an ESP32-S3 module on a custom board.

### Certain vs uncertain

- Hardware, certain: ESP32-S3 has native full-speed USB device and two I2S controllers.
- Firmware, the real unknown (all our own code, no example exists):
  1. Espressif `usb_device_uac` (esp-iot-solution) supports ESP32-S2/S3/P4, up to 4 mic and 8 speaker channels; its example shows only 2 mic channels. Reading two I2S data lines (ear pair + back) into one 4-channel stream is ours to write; whether the second I2S peripheral can run as a slave on shared clocks is unverified.
  2. UAC plus a touch interface (CDC serial or HID) in one composite device: the component has `skip_tinyusb_init` for building composites, but no UAC+CDC example.
  3. Arduino's TinyUSB build lacks UAC (arduino-esp32 issue #12053), so the firmware moves to ESP-IDF and `touch_main.cpp` is rewritten.
- Driver, low risk: A7Z uses stock Linux `snd-usb-audio` and `cdc_acm`. Check the Radxa kernel has them when the A7Z is online (e.g. `modinfo snd-usb-audio cdc_acm` or `zcat /proc/config.gz | grep -E 'SND_USB_AUDIO|USB_ACM'`). The A7Z was offline on 2026-11-09.
- Power, unchecked: amp peaks at several hundred mA on 5 V (today from header pin 4). The A7Z USB port's current limit is unknown; if too low, keep 2 separate power wires for the amp. Earlier estimate (not measured): about 1 A total, 28 AWG at 0.6 m round trip drops about 0.13 V.
- Unchecked: whether the XIAO ESP32-S3 exposes USB D+/D- anywhere except its USB-C connector (believed not; check the Seeed pinout). If not, a XIAO cannot be surface-mounted onto a carrier board and still carry USB.

### Fallbacks, by failure point

- Composite fails: 4-port hub (Adafruit 5997) with two XIAOs: one UAC only, one touch only over Arduino USB serial (known to work). Still one USB across the neck.
- Three-mic merge fails: two ear mics only (stereo on one line, the case the example covers); the back mic is optional.
- UAC unstable: audio stays on I2S wires to the A7Z (about 7 wires: BCLK, LRCK, DOUT, 2 x DIN, amp 5 V and GND); USB carries camera and touch. Still removes I2C from the neck and the camera adapter.

### Software that changes with plan B (all in microduck-sim)

- Recording: `namecall.py` and the recording scripts in `guide/firmware/mac/namecall-20261029/` read `hw:0,0` 4-channel today; move to the USB card and remap channels.
- Playback: `duck_sound.py`; reapply the -3 dB softvol ceiling (D-012) on the new card, never higher.
- Touch: `walk_wired.py` reads touch over I2C; move to the USB interface.
- Firmware: XIAO rewritten as USB composite. Overlays for TWI0 and I2S0 DIN3 retired.
- Name call re-acceptance against `guide/firmware/mac/namecall-20261029/REQUIREMENTS.json` (same mics, new capture path; levels may differ from training data).

## Build route

1. Bench test with no PCB and nothing on the robot touched: the loose XIAO ESP32-S3 in the RoboClub XIAO drawer (`roboclub/INVENTORY.md`, 2026-10-20) plus an Adafruit CH334F mini hub (2-port 5999: 24 x 20 mm, 2.2 g, $4.50; downstream on 4-pin solder pads). Hub pads to XIAO via a short USB-C plug lead. Amp and mics wire to XIAO pins, clocks split on a breadboard. Acceptance: A7Z (or a Mac first) enumerates one UAC device with 2 then 4 mic channels plus speaker, and a touch interface, in one composite; record and play at the same time. The hub is not owned yet (not in `parts_a7z_extensions`), so it is not a design input until in hand.
2. Custom head board after step 1 passes, made and assembled by JLCPCB: CH334 hub, ESP32-S3 (a XIAO if it can carry USB on a carrier, else an ESP32-S3-MINI-1 module, about 15 x 20 mm, 30+ pins, which also solves the pin budget), MAX98357A chip on board, latching JST (1.0 or 1.25 mm) sockets for mics, speaker and touch pads, a PicoBlade socket for the camera. Show Shawn a concept picture and signal list before CAD or layout; an approved concept goes into a `DESIGN-CONTRACT.json` before any geometry.

## Board-joining terms explained to Shawn

Fly wires between pads (test only), pin headers through holes soldered underneath (amp module), castellated edge holes soldered flat onto a carrier (XIAO style). "Putting the chip on the board" means using a bare ESP32-S3 or a module on our own PCB instead of a finished XIAO, so all pins are available.

## Sources

- Espressif UAC component docs: https://docs.espressif.com/projects/esp-iot-solution/zh_CN/latest/usb/usb_device/usb_device_uac.html
- Component registry: https://components.espressif.com/components/espressif/usb_device_uac
- arduino-esp32 issue #12053 (no UAC in Arduino TinyUSB): https://github.com/espressif/arduino-esp32/issues/12053
- Adafruit CH334F 2-port hub: https://adafruit.com/product/5999 and guide https://learn.adafruit.com/adafruit-ch334f-mini-4-port-usb-hub-breakout
- CH334F at LCSC: https://www.lcsc.com/product-detail/C5187527.html
- CH334 datasheet extract: https://www.compel.ru/infosheet/WCH/CH334Q

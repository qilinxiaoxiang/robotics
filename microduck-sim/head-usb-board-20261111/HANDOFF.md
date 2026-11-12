# Head wiring simplification: handoff (2026-11-11)

Goal: cut the bundle of wires that runs from the MicroDuck head down the neck to the A7Z in the saddle backpack, ideally to one USB cable like the official Pollen duck. Nothing has been built, ordered or flashed. This file is the whole state of the discussion; start here.

## Current wiring (authoritative sources)

- Pin map: `microduck-sim/bringup/A7Z-PINS.html` (20 Dupont wires on the A7Z 40-pin header, corrected 2026-11-11). The page is a guide, not the authority: what is fitted and plugged now is in `microduck-sim/CURRENT-STATE.json` (`a7z_audio_capture`, `a7z_touch_bus`, `parts_a7z_extensions`); check the page against it before quoting a count.
- From the torso (8, unchanged by any plan): 5 V red 2 / black 6; IMU 1, 3, 5, 9; UART 7 (A7Z TX), 11 (A7Z RX).
- From the head, across the neck (12):
  - Amp MAX98357A (5): Vin 4, BCLK 12, LRC 35, GND 39, DIN 40.
  - Touch board XIAO ESP32-S3 (4): 3V3 17, GND 25, SCL 29, SDA 31 (TWI0, I2C slave 0x2A).
  - Ear mics INMP441 x2 (2): GND 34, SD 38. Their SCK/WS/VDD share the amp and touch lines on a 25-hole mini breadboard on the back of the camera.
  - Back-of-head mic INMP441 (1): SD to pin 10, fitted and working since 2026-10-29 (ALSA ch2; `CURRENT-STATE.json` `a7z_audio_capture`). Corrected 2026-11-11: this line said "optional, not plugged", which was wrong and was repeated to Shawn; he rejected it. All three microphones are in use, so any plan must carry three mic channels (two I2S data lines) or state plainly that it removes a working function.
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

## Investigation results (2026-11-11, four parallel research agents; sources in their reports, not all re-opened)

Shawn's questions: can a head PCB carry a CSI socket for the Radxa CSI camera; do two USB cables need a 1-to-2 adapter; how to cut wires inside and out of the head with only ordinary soldering; can a PCB be ordered fast. Constraint: board in hand and fitted by late November 2026.

- CSI: rejected. CSI ends at the A733, so a head board can only pass it through and a ribbon still crosses the neck. The owned Radxa Camera 13M 214 has a 150 mm 31-pin 0.3 mm ribbon; the exit-to-header path is 158-198 mm (`bringup/a7z/head-sweep-v2.json`, `head-wire-lengths.json`), and flat FFC does not tolerate neck yaw. A CSI-to-USB bridge (Infineon CX3, 121-ball BGA, own firmware, no ISP) is weeks of work; the U20CAM already is that bridge.
- Two USB devices need a hub (Adafruit 5999 CH334F, 24 x 20 x 5 mm, $4.50), never a passive split. A7Z ports per Radxa docs: USB 3.1 port (camera today) limits downstream current to about 1 A; the USB 2.0 port is device-mode by default and needs an overlay to host. Not verified on the board (A7Z offline 2026-11-11, so the `snd-usb-audio` / `cdc_acm` check is also still open).
- Plan B full (ESP32-S3 as UAC + touch composite): too risky for this deadline. No complete public example; the closest public attempt had a working mic and an unfixed crackling speaker; our capture is 4 channels, 48 kHz, S32_LE (`record_calls.sh`, `namecall.py`), the width with an open issue in `usb_device_uac`. The XIAO exposes USB D+/D- only on its USB-C connector. Amp peaks near 650 mA would share the ~1 A port with camera and hub.
- No ready-made USB audio board near 25 x 35 mm with stereo mics and an amp was found; any would change the mics and force spotter retraining.
- 18-021 gives no fab route (course submits to JLCPCB without ordering; final project is a fixed shield). Fab for a bare 2-layer board ordered 2026-11-13: OSH Park Super Swift about $34, door about 11-21 to 11-24; JLCPCB about $25-40, door about 11-18 to 11-21, 35 % duty prepaid. Assembled hub + MCU board from JLCPCB: about 11-23 to 11-26, no slack.
- Head space (agent voxel check, wires not modelled, inference): a flat board up to 40 x 20 x 5 or 30 x 20 x 6 mm fits at z 132-140 on the right half; an upright 30 x 20 board fits behind the camera where the breadboard is. About 34 wires are inside the head today.

Recommended to Shawn (awaiting his word, nothing designed or ordered): Plan A as a passive collector board. Amp module and XIAO solder onto the board by their header pins; each mic gets one 5-pin through-hole socket; I2C pull-ups (2.2 k) sit on the board, which is the deferred `touch-twi0-jam` fix; 3V3 comes from the XIAO regulator. Neck: one latching 8-core cable (9 with the back mic: 5 V, GND, BCLK, LRC, amp DIN, mic SD, SCL, SDA) plus the camera's factory 30 cm USB cable. No software change. Plan B stays a later bench experiment.

### Shawn's reply (2026-11-11) and the revised direction

Shawn rejected Plan A: "还是要8根线 那不就跟没做一样吗也少不了几根呀". Eight cores is the floor for any passive board (eight distinct signals), so the goal is again one USB cable across the neck, and the open question is only which chip turns audio into USB with the least unproven firmware. The "crackling speaker" above is a third party's ESP32-S3 USB sound card attempt (atomic14 blog), not the duck; the duck's own audio is fine (Shawn: "现在声音很好").

Lead found the same day, not yet tested: public RP2040 firmware that already is a USB sound card with INMP441 mics and an I2S DAC (github.com/denisgav/pico-usb-headset, github.com/denisgav/rpi_usb_sound_card: `stereo_microphone_i2s`, `stereo_speaker`; TinyUSB, Pico SDK). RoboClub stock has Raspberry Pi Pico boards and 2 XIAO RP2040 (`roboclub/INVENTORY.md`). Candidate head layout: CH334F hub with three downstream devices: camera, an RP2040 as USB sound card (two ear mics + amp; this firmware covers two mic channels only, so the working back mic would be lost unless a third channel is added: open problem, not an accepted loss), the existing XIAO sending touch over Arduino USB serial. Unverified: mic and speaker in one device at the same time on that firmware, 48 kHz capture, MAX98357A as the DAC, total current against the ~1 A port, A7Z drivers. Silicon Labs CP2615 (USB to I2S bridge, 48 kHz 16/24-bit stereo both ways) was looked at and set aside: marked not for new designs. First step is a bench test on a Mac with a club Pico before any PCB.

### RP2040 firmware read from source (2026-11-11, no hardware used)

Shawn's objection: a bench test with new microphones means buying them and soldering their headers, which takes long; what can be known without it. Read from the public source of github.com/denisgav/pico-usb-headset, example `examples/usb_headset_16b_24b` (`tusb_config.h`, `usb_descriptors.h`, `main.c`), and `common/src/i2s/audio_i2s_rx_32b.pio` of github.com/denisgav/rpi_usb_sound_card:

- Known from source: one USB device carries speaker and microphone together (UAC2 headset, two streaming interfaces); maximum rate 48000; 16-bit and 24-bit-in-4-byte formats; the README lists INMP441 as a supported I2S microphone; speaker and microphone each use their own I2S instance, with clocks made by the RP2040.
- Not provided: the headset example sends 1 microphone channel over USB (`CFG_TUD_AUDIO_FUNC_1_N_CHANNELS_TX 1`); the separate `usb_microphone_i2s_stereo` example sends 2. The duck needs 3 (two ears on one data line, the back microphone on a second). The receive program samples one data pin (`in pins, 1`). Our change: sample two adjacent data pins on the same clock and declare 4 USB channels (3 used, same layout as today's ch0/ch1/ch2). This is firmware work of ours, not something a bench test with new microphones would tell us.
- The DAC the author used is a PCM5102a; MAX98357A is not named. Both take plain I2S; MAX98357A needs no master clock. Inference, not tested.
- Repository facts: last push 2024-08-31, 20 stars, no licence file reported by the GitHub API (matters only if the firmware is published in the public duck repository).

What needs hardware, and which: (1) the changed firmware enumerating with 4 capture channels and 2 playback channels: a bare Pico from the RoboClub drawer on a Mac, nothing soldered; (2) A7Z side (USB host on the second port or through a hub, `snd-usb-audio` in its kernel): a read-only check on the robot when it is online; (3) real sound through the real microphones and amp: the head's own parts, whose leads are Dupont plugs on the breadboard and can be moved to a Pico and back without soldering. No spare microphones are required for any of these. The main gap is therefore the three-channel firmware change and the carrier board's design and delivery time, not an unknown about the microphones.

## Board-joining terms explained to Shawn

Fly wires between pads (test only), pin headers through holes soldered underneath (amp module), castellated edge holes soldered flat onto a carrier (XIAO style). "Putting the chip on the board" means using a bare ESP32-S3 or a module on our own PCB instead of a finished XIAO, so all pins are available.

## Sources

- Espressif UAC component docs: https://docs.espressif.com/projects/esp-iot-solution/zh_CN/latest/usb/usb_device/usb_device_uac.html
- Component registry: https://components.espressif.com/components/espressif/usb_device_uac
- arduino-esp32 issue #12053 (no UAC in Arduino TinyUSB): https://github.com/espressif/arduino-esp32/issues/12053
- Adafruit CH334F 2-port hub: https://adafruit.com/product/5999 and guide https://learn.adafruit.com/adafruit-ch334f-mini-4-port-usb-hub-breakout
- CH334F at LCSC: https://www.lcsc.com/product-detail/C5187527.html
- CH334 datasheet extract: https://www.compel.ru/infosheet/WCH/CH334Q

## 2026-11-12: concept approved, schematic draft 1

Shawn approved the one-USB board concept ("对 开始画"); load-bearing facts are in `DESIGN-CONTRACT.json`. Draft 1 of the schematic is generated from `sch/netlist.py` by `sch/gen_sch.py` into `sch/build/head_usb_board.sch` (64 parts, 45 nets; `sch_lint.py` PASS, `sch/check_netlist.py` PASS; picture `sch/build/head_usb_board.png` from `sch/render_svg.py`). Symbols only, no footprints yet; not imported into Fusion (Fusion had the 18-021 board open).

Choices in draft 1:
- Hub CH334F on its own internal 3.3 V regulator, 12 MHz crystal with no load capacitors, RESET#, PSELF, OVCUR#, PWREN#, LEDs and ports 3 and 4 open (WCH datasheet V3.0 section 6; Adafruit breakout does the same). Port 1 to the RP2040 through 27 ohm, port 2 to the camera.
- RP2040 per the Raspberry Pi minimal design (W25Q16JV flash, 1 k on QSPI_SS to a BOOT pad, 15 pF + 1 k crystal circuit). GPIO: 4/5 touch I2C0 (2.2 k pull-ups to 3V3), 10/11 mic SCK/WS, 12 ears SD, 13 back SD, 18/19/20 amp BCLK/LRC/DIN, 0 debug TX pad, 25 LED.
- Amp MAX98357A on 5 V with SD_MODE 1 M to 5 V and GAIN open, the same as the Adafruit 3006 module now fitted ((L+R)/2, 9 dB); ferrite beads and 220 pF on the outputs as on that module; speaker on a 2-position screw terminal (the leads are bare ends in the module's terminal today).
- Microphones and touch on 2.54 mm sockets and pins so the existing Dupont ends plug in unchanged: three 1x5 sockets (3V3, GND, SCK, WS, SD), one pin for the back SD lead (female end today), 1x3 pins for the XIAO's GND/SCL/SDA (female ends) and one socket for its 3V3 (male end). Lead ends are read from the wiring page source (`bringup/a7z/build_a7z_solder.py`), not yet confirmed on the robot.
- Camera and uplink on two 5-pin PicoBlade headers with the camera's order (V, D-, D+, G, G), so the camera's present cable becomes the neck cable; the camera then needs a short double-ended 1.25 mm lead (not owned).

Open before layout: which end of the camera socket is pin 1 (unpublished; board silk reads V M P G G); a 12 MHz crystal with 10 pF load at JLCPCB for the RP2040 (the basic part C9002 is 20 pF); AP2112K and W25Q16JV pinouts were written from memory and need their datasheets; the INMP441 modules' own pull-downs; PIO pin-order needs of the firmware; A7Z USB host, drivers and port current; fit of the outline with 2.54 mm headers.

Sources read 2026-11-12 (by two research agents, quotes in their reports): WCH CH334/335 datasheet V3.0 (wch-ic.com/downloads/CH334DS1_PDF.html); Adafruit-CH334F-Breakout-PCB; Raspberry Pi hardware-design-with-rp2040.pdf and Minimal-KiCAD.zip; rp2040-datasheet.pdf; MAX98357A datasheet 19-6779 Rev 7; Adafruit MAX98357 breakout schematic; INMP441 DS-INMP441-00 Rev 1.1; JLCPCB part pages (CH334F C5187527, RP2040 C2040, W25Q16JVUXIQ C2843335, MAX98357AETE+T C910544, AP2112K-3.3 C51118, PicoBlade 53047-0510 C471412 / 53261-0571 C17256390), all Extended library, in stock that day.

## 2026-11-12: head space check (parts only, wires not modelled)

`space_check.py` (run on the Mac mini, 8 s; result `space-check.json`) voxelises the guide's head part meshes at HOME (guide revision guide-20261101-v140-backpack, 0.5 mm grid) with the amp module removed, and grows the largest free rectangle from the breadboard's place on the camera back (slab x 51.6 to 62.9, 11.3 mm thick, board upright in the y-z plane). Sanity: with zero clearance the plug zone it finds (y -27.5 to 2.0, z 130.5 to 145.5) contains the breadboard's 20 x 15 mm and its plug rows, which are on the robot today.
- Board body, 1 mm clearance to every part: 30 x 30 mm free (y -29.0 to 1.0, z 115.5 to 145.5).
- Where straight-back Dupont plugs (16 mm behind the board) also clear every part: only the top band, 27.5 x 13.5 mm (y -26.5 to 1.0, z 131.5 to 145.0); below z 131.5 parts sit behind the board.
- The camera lead in its present position changes neither number.
Consequence for layout: 2.54 mm headers go in the top 13.5 mm band (5 rows x 10 columns possible, about 21 positions needed); chips and the two PicoBlade headers go below it on the same face, with side-entry PicoBlade parts because nothing can plug straight back there. Thickness budget 11.3 mm: PCB 1.6 + socket 8.5 = 10.1. Not covered: wires (about 34 in the head today), head poses other than HOME, and the cap being lowered on.

## 2026-11-12: board layout draft 1 (KiCad + Freerouting on the Mac mini)

Tool choice: KiCad 10.0.8 (`~/Applications/KiCad/KiCad.app` on the Mac mini, installed without sudo) builds the board from `sch/netlist.py`, Freerouting 2.5.0 routes it, `kicad-cli pcb drc` judges it. Reason: 0.4 mm pitch QFN-56 and USB in 30 x 30 mm are beyond the two-layer router written for 18-021, and Fusion's AUTO does not run through the bridge. Cost: this board is not editable in Fusion. One command: `sh pcb/run.sh all 80` (place, plane vias, route, rule check, picture; about 40 s), then `python3 pcb/check_drc.py`.

Result (`pcb/build/board.kicad_pcb`, picture `pcb/build/board.png`): 30 x 30 mm, 4 layers (front, GND plane, +3V3 plane, back), all 64 parts on the rear face, 45 nets, 0 unconnected, 0 rule errors at JLCPCB-level limits (track/space min 0.1 mm, default 0.15/0.13, via 0.5/0.3, edge 0.3). Waived: 7 courtyard overlaps between the 2.54 mm headers, which stand on one 2.54 mm grid like a multi-row header. Warnings not cleaned: 201 silkscreen overlaps (reference texts).

Placement follows a depth probe behind the board's rear face (same voxel grid as `space_check.py`): over 30 mm free in the top band (board y < 13.5), 4 to 5 mm under the band on the left half, 9 to 10 mm on the right half. So every part that takes a plug is in the band (three 1x5 sockets, back-SD pin, touch pins and socket, speaker screw terminal, and both PicoBlade headers as the vertical 53047-0510); below the band only parts up to about 1.3 mm tall. The outline 30 x 30 is larger than the contract's 30 x 20 target and still needs Shawn's word in `DESIGN-CONTRACT.json`.

How the build works, and what failed first (all in `pcb/gen_pcb.py` comments):
- The native `freerouting-cli` 2.5.0 dies on this board (UnsupportedFeatureError ComponentOutline) and hangs; `run.sh` runs the jar (sha256 matches the release) on Homebrew openjdk 27 with an 8 minute limit.
- KiCad keeps constraints and net classes in the `.kicad_pro`, not the board; without it `kicad-cli drc` judged against 0.2 mm defaults. `write_project()` writes it.
- Freerouting does not drop vias from surface pads to a plane. `plane_fanout()` gives every GND and +3V3 surface pad its own via (78 vias, in the pad for exposed pads), and the router's copy of the board puts each such pad on a private, already-complete net so it routes signals only.
- Signals stay off the inner layers only when the planes are present in the router's copy (one anchor pin per plane). Without planes it routed on them and cut them into islands; with wire keep-outs it placed no vias.
- Plane clearance 0.2 mm (KiCad's default 0.5 merged the header holes into a slot that isolated part of the 3V3 plane). The router's outline is 0.2 mm inside the real one (edge rule). Segments it necks below 0.1 mm are widened to 0.1 mm before the rule check.

Research agent results folded in (sources in the chat report of 2026-11-12): AP2112K-3.3 pinout 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT (Diodes DS39724); W25Q16JVUXIQ pinout as drawn, exposed pad may float (Winbond rev H; the Pico leaves it open, so does this board); crystal pads 1 and 3 are the crystal, 2 and 4 ground (YXC, matches the KiCad footprint); CH334F exposed pad 2.6 mm and MAX98357A T1633 pad match the chosen footprints. Crystal choice: YXC X322512MMB4SI, C50430, 10 pF load, for both chips (RP2040 with 2 x 15 pF and 1 k as in the Raspberry Pi guide; CH334F with no capacitors); its ESR is 80 ohm max against the guide's 50, so the 1 k value is unproven. Screw terminal C557685 (Xinya XY308-2.54-2P, matches the footprint). 1x5 sockets: 8.5 mm C50950, or 5.7 mm C2913789 (insertion depth for a 6 mm pin not confirmed).

Not done, in order of risk:
1. USB data lines are routed as ordinary single tracks. The camera and uplink pairs carry 480 Mbit/s and need to be routed as matched 90 ohm pairs side by side over the ground plane before ordering; the stackup's track width for 90 ohm has to come from JLCPCB's calculator for the chosen 4-layer stack.
2. Camera socket pin 1 end (board silk reads V M P G G) still unknown; J_CAM and J_UP pin order depends on it.
3. Speaker terminal wire-entry side: read from the footprint outline only (KiCad convention puts entry on the +y side, toward the low parts); check against the maker drawing.
4. No silkscreen labels for the builder (which plug goes where), no mounting feature (how the board is held on the camera back), no fiducials.
5. Manufacturing files (Gerber, BOM with LCSC numbers, placement file), firmware, A7Z-side checks: not started.

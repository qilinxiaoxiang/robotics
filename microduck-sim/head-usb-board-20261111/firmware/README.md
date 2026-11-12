# MicroDuck head USB board firmware (RP2040)

Status on 2026-11-12: the firmware builds and passes its host-side checks. **It has never run on hardware.** No board
exists yet, so nothing electrical is verified: not enumeration, not sound in either direction, not the touch bridge.
Read "What is not verified" before relying on any statement here.

The board (`../sch/netlist.py`) puts a CH334F hub, a bare RP2040, a MAX98357A amplifier and sockets for three INMP441
microphones and the touch XIAO in the head, so that one USB cable crosses the neck. This firmware makes the RP2040 one
USB composite device:

- **USB Audio Class 2 sound card.** Capture: 4 channels, 48 kHz, 16 bit (ch0 left ear, ch1 right ear, ch2 back
  microphone, ch3 always zero: the channel order the A7Z's I2S capture has today, `a7z_audio_capture` in
  `../../CURRENT-STATE.json`). Playback: 2 channels, 48 kHz, 16 bit, sent to the amplifier, which plays (L+R)/2.
  No volume or mute control is exposed, so the level stays where the A7Z's ALSA configuration puts it.
- **CDC-ACM serial port** that forwards the touch board's readings as text lines (format below).

## Pins (from `../sch/netlist.py`)

- GPIO4 SDA, GPIO5 SCL: I2C0 master at 100 kHz to the touch XIAO (slave 0x2A, its firmware unchanged)
- GPIO10 SCK, GPIO11 WS: microphone clocks, made by the RP2040 (3.072 MHz, 48 kHz, 64 SCK per frame)
- GPIO12 SD of both ear microphones (left and right slots), GPIO13 SD of the back microphone (left slot)
- GPIO18 BCLK, GPIO19 LRC, GPIO20 DIN: MAX98357A
- GPIO25 LED, GPIO0 debug UART TX (115200 baud, test pad TP6)

## Build

Edit on the MacBook, build on the Mac mini. From this folder on the MacBook:

    sh tools/sync_build.sh               # mirror to the Mac mini, build, run both checks, copy build/ back
    sh tools/sync_build.sh sh tools/build.sh clean     # the same from scratch

On the build host itself: `sh tools/build.sh` (or `sh tools/build.sh clean`). The first run fetches the dependencies
into `.deps/` (ignored by git, nothing is vendored): Pico SDK 2.1.1 with its TinyUSB submodule, and the Arm GNU
Toolchain 14.2.rel1 tarball from developer.arm.com, checked against its published SHA-256. The tarball is used because
the Homebrew `arm-none-eabi-gcc` formula has no C library and the `gcc-arm-embedded` cask needs sudo. A toolchain
already on `PATH` that has newlib is used instead. CMake 3.13 or newer and a host C compiler are needed; the SDK builds
`pioasm` and `picotool` itself.

Outputs in `build/`: `head_usb.uf2` (flash this), `head_usb.elf`, `build.log`, `warnings.txt`,
`descriptor-check.json`, `pio-check.json`.

Warnings: the project's own sources compile with `-Wall -Wextra -Wshadow -Wconversion` and give none. The one line in
`warnings.txt` is from the macOS linker while the SDK builds its host tool `picotool`
(`ld: warning: ignoring duplicate libraries`); it does not concern the firmware.

## Checks that run without hardware

- `tools/check_descriptors.py build/head_usb.elf --uf2 build/head_usb.uf2` reads the linked descriptor tables out of
  the ELF and asserts 4 capture channels, 2 playback channels, 48000 Hz, 16 bit, exactly one CDC port, endpoint sizes
  and the UF2 layout. Plain Python.
- `tools/test_pio.py --build build` runs the assembled PIO opcodes (from the headers `pioasm` generated) in a
  hand-written cycle model against models of the INMP441 and MAX98357A, and decodes the result with the firmware's own
  C conversion code compiled for the host. It checks clock rates, 64 clocks per frame, the datasheet timing limits,
  MSB-first data one clock after the word-select edge, 24 bits in a 32-bit slot, channel order, and that a stalled FIFO
  does not shift the word order. Two controls confirm the test fails when the alignment or the sample point is wrong.

These show the logic and the timing budget on paper. They are models written by the same author as the firmware, not
measurements.

## Flashing

The RP2040 has no firmware when the board arrives; its ROM bootloader takes a UF2 file over USB.

1. Connect the board's uplink socket J_UP to a computer (the RP2040 sits behind the on-board hub, so the hub must
   work for this route).
2. Hold the BOOT pad (TP1) to the GND pad next to it (TP2) with tweezers and, while holding, apply power (plug the
   cable in) or tap the RUN pad (TP5) to GND and let it go. Release BOOT after a second.
3. A USB drive named `RPI-RP2` appears. Copy `build/head_usb.uf2` onto it. The drive disappears and the board restarts
   into the firmware; the LED blinks slowly once a host has configured it (fast while it has no host).

Later updates use the same steps. If the drive never appears, the hub or the RP2040's USB wiring is the first suspect;
the SWD pads (TP3 SWCLK, TP4 SWDIO) take a debug probe and do not depend on USB.

## Serial port: line format

One text line per event, ASCII, ending in `\n`. The first character says what the line is.

- `T <48 hex digits>`: one touch read, every 20 ms. The digits are the 24 bytes exactly as they came from the XIAO
  at I2C address 0x2A: uint32 little-endian sequence number, then the raw counts of L1, R1, L2, R2, M
  (`../../guide/extension-20261015-touch/firmware/touch_xiao/touch_main.cpp`). The bytes are not interpreted on the
  board, so a block that arrives shifted by one byte behind a 0x55 filler (`a7z_touch_bus` in the state file) reaches
  the host as it is and the host's existing two-alignment decode still applies.
  Example: `T d20400005456000058590000c05d0000a8610000bc660000`
- `E <reason>`: that poll failed; reason is `timeout`, `nack` or `short`. One `E` line replaces the `T` line.
- `S key=value ...`: status, sent in answer to `?`: `version`, `mic` and `spk` (frames passed to and from USB),
  `resync`, `underrun`, `drop`, `repeat` (see "Known limits"), `peak=<left>,<right>,<back>` (largest absolute sample
  of each microphone since the previous `?`, 0 to 32767; it works with no capture stream open), `gain`.
- `# text`: a remark, for example the result of a command.

Commands from the host, one per line:

- `RS`, `RD`, `HD`, `HC`: written to the XIAO as two bytes, the same bytes the A7Z writes to 0x2A today (`RS` restarts
  the XIAO). Answer: `# RS sent` or `# RS failed`.
- `?`: status line. `G0` to `G8`: microphone gain shift (below).

Smallest change on the A7Z side (`walk_wired.py` reads 24 bytes from `/dev/i2c-0` and passes them to `touch_decode`):
replace the two bus functions, keep `touch_decode`, `TouchPads` and the restart logic. Sketch, not run anywhere yet:

    def open_touch_serial(port):                 # port: an opened serial port object with a short read timeout
        def read():
            while True:
                line = port.readline()
                if line[:2] == b"T ":
                    return bytes.fromhex(line[2:50].decode())
                if line[:2] == b"E " or not line:
                    raise OSError(line.decode(errors="replace").strip() or "no touch line")
        return read                              # restart: port.write(b"RS\n")

## What changes for audio on the A7Z

- The sound card is a new ALSA card (USB) with its own name and index; scripts that open `hw:0,0` must name the new
  card. The playback softvol ceiling has to be set up again on this card.
- Capture is S16_LE instead of S32_LE. With gain shift 0 each sample is the top 16 bits of the microphone's 24-bit
  word, the same value as the old S32 sample shifted right by 16. Levels far below full scale lose resolution
  compared with the old format; `G1` to `G8` multiply by 2 to 256 before the cut to 16 bits (saturating). The gain
  setting is not stored: it returns to 0 at power-up.
- The name-call spotter was trained on audio from the old capture path; it needs its acceptance run again.

## Design in short

- clk_sys is set to 61.44 MHz (12 MHz crystal x 128 / 25). Both PIO programs then use an integer divider of 10 and
  two PIO cycles per bit clock: 3.072 MHz, exactly 64 x 48 kHz, with no fractional-divider jitter. The INMP441 wants
  an SCK period of at least 312 ns (here 325.5 ns) and the MAX98357A recovers its clock from BCLK.
- `src/i2s_mic.pio` drives SCK and WS and samples both data lines on the same clock (`in pins, 2`).
  `src/i2s_spk.pio` drives BCLK, LRC and DIN. Both are original to this project.
- Each state machine is served by two DMA channels that chain to each other and wrap in a 16 KiB ring, with no
  interrupt handler. The USB side reads and writes the rings and looks at the DMA address.
- Core 0 runs USB and audio. Core 1 runs the touch I2C polling (a jammed bus can hold a read to its timeout) and the
  debug UART, so neither can delay the audio packets served every millisecond.

## Known limits (by design, before any hardware)

- **Crystal start-up.** The board's 12 MHz crystal is the YXC X322512MMB4SI (LCSC C50430): 10 pF load, 80 ohm
  maximum ESR. The Raspberry Pi oscillator circuit it sits in is tuned for the ABM8-272-T3 at 50 ohm, so start-up may
  be slower or marginal. `boards/microduck_head_usb.h` sets `PICO_XOSC_STARTUP_DELAY_MULTIPLIER` to 64 (the SDK's
  knob for slow-starting crystals; the wait before the clock is used grows from about 1 ms to about 64 ms). A longer
  wait does not help a crystal that never starts: see bench check 1. The same header selects the flash boot stage
  `boot2_w25q080` for the W25Q16JV (`PICO_BOOT_STAGE2_CHOOSE_W25Q080`), 2 MB, SPI clock divider 2.
- **Playback has no rate feedback to the host.** The board's crystal and the host's clock differ by some parts per
  million. The firmware keeps about 8 ms queued and drops or repeats one frame when the queue drifts 3 ms
  (`drop` and `repeat` in the status line). If that is audible, the fix is a UAC2 feedback endpoint.
- The capture side has no such problem: it is an asynchronous endpoint and sends what the microphones produced.
- The configuration descriptor asks for 100 mA, because Linux refuses a device behind a bus-powered hub that asks for
  more. The amplifier's real peaks are higher; whether the A7Z port and the cable carry them is a hardware question.
- USB IDs are the pid.codes vendor ID 0x1209 with its test product ID 0x0001, which is for private testing only.

## What is not verified

Everything that needs a board. In particular:

- that the RP2040's crystal starts (80 ohm ESR part in a circuit tuned for 50 ohm; the firmware waits about 64 ms
  for it), and that the board enumerates through the CH334F, and is accepted by `snd-usb-audio` and `cdc_acm` on the A7Z or by
  macOS;
- that the DMA channel pairs hand over cleanly (every 22 s for the microphones, 44 s for the amplifier);
- real microphone data: the INMP441 datasheet gives no SD output delay; the model passes for 0 to 285 ns; long ear
  leads and two microphones sharing one line are not modelled;
- real sound from the MAX98357A, start and stop noises, and the drop/repeat behaviour over minutes;
- capture and playback together, and audio together with the camera on the same hub;
- the touch bridge against the real XIAO, including its known bus jams and the `RS` recovery;
- supply behaviour at amplifier peaks.

## First three bench checks when a board exists

Start `python3 tools/live_meter.py <serial port>` first in checks 2 and 3: it shows microphone levels and pad counts
as they change, so each tap or touch is seen at once.

1. **Power, clocks, enumeration.** On the first power-up, measure the crystal oscillator starting: scope XIN/XOUT
   (a low-capacitance probe, or watch for the debug UART banner and the 3.072 MHz clocks instead, which only appear
   once the crystal runs). If it fails to start, lower R5 from 1 k. Note that the USB bootloader itself needs the
   crystal, so a board whose `RPI-RP2` drive never appears may have this fault. Then flash as above. Expect on the debug UART (TP6, 115200):
   `microduck head usb 0.1.0, clk_sys 61440000 Hz`. On the host: one hub, behind it one device 1209:0001 with a sound
   card (4 inputs, 2 outputs, 48000 Hz) and one serial port. With a logic analyser or scope and no microphones
   plugged in: GPIO10 and GPIO18 at 3.072 MHz, GPIO11 and GPIO19 at 48.000 kHz, 64 clocks per frame.
2. **Microphones and touch.** Plug the three microphones and the XIAO. In the live meter, tap each microphone in turn:
   only its bar should jump (L, R, B). Touch each pad: its count rises (rest counts are 22100 to 26300 on the robot
   today), `seq` keeps advancing, `err` stays 0. Then record 10 s (`arecord -D <card> -c 4 -r 48000 -f S16_LE`):
   the file should be 3.84 MB within a few hundred bytes per million, ch3 all zero, and the `resync` counter 0.
3. **Playback, alone and with capture.** Play a quack through the new card while the 10 s recording runs. Listen for
   clicks at start and end and during the sound; afterwards `underrun` should be 0 and `drop`/`repeat` should have
   grown by at most a few per second. Leave both streams running for 2 minutes and read the counters again; in the
   recording, the quack should appear on all three microphone channels.

## Files

- `src/main.c` (core 0 loop, CDC port), `src/audio.c`, `src/audio.h`, `src/audio_convert.h` (sample conversion, also
  compiled by the host test), `src/i2s_mic.pio`, `src/i2s_spk.pio`, `src/touch.c`, `src/touch_format.c`, `src/touch.h`
- `src/usb_descriptors.c`, `src/usb_descriptors.h`, `src/usb_audio.c`, `src/tusb_config.h` (adapted from TinyUSB)
- `boards/microduck_head_usb.h` (pins, flash, crystal start-up wait), `CMakeLists.txt`
- `tools/fetch_deps.sh`, `tools/build.sh`, `tools/sync_build.sh`, `tools/check_descriptors.py`, `tools/test_pio.py`,
  `tools/host_shim.c`, `tools/live_meter.py`

## Licences

- The four USB files named above are adapted from the TinyUSB example `examples/device/uac2_headset`
  (MIT, copyright Ha Thach and Jerzy Kasenberg); each keeps the MIT notice with the original copyright lines.
- Everything else in this folder is original work for this project. Its file headers name the BSD 3-Clause licence,
  the licence of the Pico SDK it builds on. The repository has no licence file of its own on 2026-11-12, so this is a
  proposal for the repository owner to confirm or change; no third-party term depends on it. The two PIO programs and
  the DMA scheme were written from the RP2040, INMP441 and MAX98357A datasheets.
- No code from github.com/denisgav/pico-usb-headset or rpi_usb_sound_card is used: those repositories carry no
  licence. They were read earlier only to learn that the approach is possible (`../HANDOFF.md`).
- The Pico SDK (BSD 3-Clause), TinyUSB (MIT) and the Arm GNU Toolchain are fetched at build time into `.deps/`.

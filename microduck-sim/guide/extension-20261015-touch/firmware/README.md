# Touch readout firmware and bench test

- `touch_xiao/touch_main.cpp`: XIAO ESP32-S3 firmware. Five pads at 50 Hz (L1 D0, R1 D1, L2 D2, R2 D3, M D8), USB serial lines `T,<ms>,<L1>,<R1>,<L2>,<R2>,<M>`, and an I2C slave at 0x2A on D4/D5 (24-byte block: sequence, then the five counts, uint32 LE). The I2C side is untested until the A7Z overlay for pins 29/31 exists.
- `flash.sh`: compile and flash over USB-C (`arduino-cli`, core `esp32:esp32` 3.3.12, Homebrew `universal-ctags`).
- `touch_bench.py`: acceptance item 2 of `../PLAN.md` (fingertip delta at least 5x resting noise, no cross-trigger). Run with `~/.venvs/touch/bin/python touch_bench.py --pads L1`; it writes `touch_bench_<time>.json` here.

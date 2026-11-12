#!/bin/sh
# Build on the build host (the Mac mini) and run both host-side checks. From the MacBook use tools/sync_build.sh.
#   sh tools/build.sh          incremental
#   sh tools/build.sh clean    configure and build from scratch
# Output: build/head_usb.uf2, build/build.log (full compiler output), build/warnings.txt (every warning line),
#         build/descriptor-check.json, build/pio-check.json
set -eu

HERE=$(cd "$(dirname "$0")/.." && pwd)
cd "$HERE"

sh tools/fetch_deps.sh

TC_BIN="$HERE/.deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin"
if [ -x "$TC_BIN/arm-none-eabi-gcc" ]; then
    PATH="$TC_BIN:$PATH"
    export PATH
fi

if [ "${1:-}" = "clean" ]; then
    cmake -E rm -rf "$HERE/build"
fi
mkdir -p "$HERE/build"

cmake -S "$HERE" -B "$HERE/build" -DCMAKE_BUILD_TYPE=Release -DPICO_SDK_PATH="$HERE/.deps/pico-sdk" \
    > "$HERE/build/configure.log" 2>&1 || { cat "$HERE/build/configure.log"; exit 1; }
cmake --build "$HERE/build" -j 8 > "$HERE/build/build.log" 2>&1 || { tail -60 "$HERE/build/build.log"; exit 1; }

grep -n -i "warning" "$HERE/build/build.log" > "$HERE/build/warnings.txt" || true
echo "build ok: $(ls -l "$HERE/build/head_usb.uf2" | awk '{print $5}') bytes head_usb.uf2, $(wc -l < "$HERE/build/warnings.txt" | tr -d ' ') warning lines (build/warnings.txt)"
arm-none-eabi-size "$HERE/build/head_usb.elf"

python3 tools/check_descriptors.py build/head_usb.elf --uf2 build/head_usb.uf2 --json build/descriptor-check.json
python3 tools/test_pio.py --build build --json build/pio-check.json

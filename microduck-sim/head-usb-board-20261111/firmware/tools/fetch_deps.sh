#!/bin/sh
# Fetch the build dependencies into firmware/.deps (ignored by git). Nothing here is vendored into the repository.
#   pico-sdk 2.1.1 (BSD-3-Clause) with its TinyUSB submodule (MIT)
#   Arm GNU Toolchain 14.2.rel1 for arm-none-eabi (official tarball, no installer and no sudo; the Homebrew
#   arm-none-eabi-gcc formula ships without newlib and the gcc-arm-embedded cask is a .pkg that needs sudo)
# Run on the build host (the Mac mini): sh tools/fetch_deps.sh
set -eu

HERE=$(cd "$(dirname "$0")/.." && pwd)
DEPS="$HERE/.deps"
SDK_TAG=2.1.1
SDK_COMMIT=bddd20f928ce76142793bef434d4f75f4af6e433
TC_VER=14.2.rel1
TC_NAME="arm-gnu-toolchain-$TC_VER-darwin-arm64-arm-none-eabi"
TC_SHA256=c7c78ffab9bebfce91d99d3c24da6bf4b81c01e16cf551eb2ff9f25b9e0a3818
TC_URL="https://developer.arm.com/-/media/Files/downloads/gnu/$TC_VER/binrel/$TC_NAME.tar.xz"

mkdir -p "$DEPS"

if [ ! -f "$DEPS/pico-sdk/lib/tinyusb/src/tusb.h" ]; then
    if [ ! -d "$DEPS/pico-sdk/.git" ]; then
        git clone --depth 1 --branch "$SDK_TAG" https://github.com/raspberrypi/pico-sdk.git "$DEPS/pico-sdk"
    fi
    git -C "$DEPS/pico-sdk" submodule update --init --depth 1 lib/tinyusb
fi
GOT=$(git -C "$DEPS/pico-sdk" rev-parse HEAD)
if [ "$GOT" != "$SDK_COMMIT" ]; then
    echo "pico-sdk is at $GOT, expected $SDK_COMMIT" >&2
    exit 1
fi

if command -v arm-none-eabi-gcc >/dev/null 2>&1 && [ -n "$(arm-none-eabi-gcc -print-file-name=nosys.specs | grep /)" ]; then
    echo "toolchain: using arm-none-eabi-gcc on PATH"
elif [ ! -x "$DEPS/$TC_NAME/bin/arm-none-eabi-gcc" ]; then
    case "$(uname -s)-$(uname -m)" in
        Darwin-arm64) ;;
        *) echo "install an arm-none-eabi toolchain with newlib for this host and put it on PATH" >&2; exit 1 ;;
    esac
    curl -fL --retry 3 -o "$DEPS/$TC_NAME.tar.xz" "$TC_URL"
    echo "$TC_SHA256  $DEPS/$TC_NAME.tar.xz" | shasum -a 256 -c -
    tar -xf "$DEPS/$TC_NAME.tar.xz" -C "$DEPS"
fi

echo "deps ready in $DEPS"

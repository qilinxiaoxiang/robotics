#!/usr/bin/env bash
# Compile-check the A1/A2 bridge and the guide bridge against the official OpenRB-150 core in a Linux arm64 container
# (the core's macOS toolchain is x86-only). Needs a running Docker daemon (for example `colima start`).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
GUIDE_FW="$(cd "$HERE/../../../firmware" && pwd)"
docker run --rm -v "$HERE:/fw:ro" -v "$GUIDE_FW:/orig:ro" debian:bookworm-slim bash -c '
set -e
apt-get update -qq >/dev/null && apt-get install -y -qq curl ca-certificates >/dev/null
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=/usr/local/bin sh >/dev/null
URL=https://raw.githubusercontent.com/ROBOTIS-GIT/OpenRB-150/master/package_openrb_index.json
arduino-cli core update-index --additional-urls $URL >/dev/null
arduino-cli core install OpenRB-150:samd@0.2.1 --additional-urls $URL >/dev/null
arduino-cli lib install "Dynamixel2Arduino@0.8.1" >/dev/null
for s in /fw/openrb_uart_bridge_j12 /fw/openrb_uart_bridge_a1a2 /orig/openrb_uart_bridge; do
  n=$(basename $s); cp -r $s /tmp/$n
  echo "== $n"; arduino-cli compile -b OpenRB-150:samd:OpenRB-150 /tmp/$n
done'

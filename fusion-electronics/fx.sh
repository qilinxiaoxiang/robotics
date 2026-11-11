#!/bin/sh
# Send a Python file to the Fusion ClaudeBridge add-in and print its output.
# Exits non-zero when Fusion raised, a dialog was open before or appeared after the call, the call
# exceeded FX_TIMEOUT (default 10 s, screenshot saved), Fusion's windows cannot be read, or the
# file contains an EAGLE ADD without name@library. Implementation: fusion.py run.
exec python3 "$(cd "$(dirname "$0")" && pwd)/fusion.py" run "$1"

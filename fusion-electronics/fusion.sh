#!/bin/sh
# Entry point kept for callers; the logic and its failure handling live in fusion.py.
exec python3 "$(cd "$(dirname "$0")" && pwd)/fusion.py" "$@"

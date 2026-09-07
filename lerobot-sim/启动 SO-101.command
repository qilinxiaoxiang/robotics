#!/bin/zsh
set -eu
cd "${0:A:h}"
if curl --silent --fail http://127.0.0.1:8766/api/state >/dev/null; then
  open -a "Google Chrome" http://127.0.0.1:8766
  exit 0
fi
if [[ ! -x .venv/bin/python ]]; then
  uv sync --frozen --python 3.12
fi
.venv/bin/python download_model.py
(sleep 2; open -a "Google Chrome" http://127.0.0.1:8766) &
exec .venv/bin/python server.py

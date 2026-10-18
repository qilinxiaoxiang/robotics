import json,subprocess
from pathlib import Path
p=Path(__file__).resolve().parent
a=json.loads((p/"command.json").read_text())["argv"]
raise SystemExit(subprocess.call(a))

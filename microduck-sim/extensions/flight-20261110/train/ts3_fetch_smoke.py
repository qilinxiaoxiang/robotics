"""Copy one save of a Mac mini anchor smoke (train/ts3_anchor_smoke.sh, /tmp/ts3_anchor_<tag>/anch/model_<iter>.onnx)
into ckpt/smk_<tag>_<iter>/ (walk61.onnx + stand61.onnx) on the MacBook and in the Mac mini mirror. The MacBook copy
is written under the gate lock, because every gate batch mounts ckpt/ (gate_lock.py).

  python3 train/ts3_fetch_smoke.py <tag> <iter>
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))
from gate_lock import gate_lock  # noqa: E402

tag, it = sys.argv[1], int(sys.argv[2])
name = f"smk_{tag}_{it}"
mirror = "code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110/train/ckpt"
src = f"/tmp/ts3_anchor_{tag}/anch/model_{it}.onnx"
subprocess.run(["ssh", "-o", "ConnectTimeout=15", "mac-mini",
                f"mkdir -p {mirror}/{name} && cp {src} {mirror}/{name}/walk61.onnx && cp {src} {mirror}/{name}/stand61.onnx"], check=True)
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(["scp", "-q", "-o", "ConnectTimeout=15", f"mac-mini:{src}", f"{tmp}/m.onnx"], check=True)
    with gate_lock(f"fetch {name}"):
        d = T / "ckpt" / name
        d.mkdir(parents=True, exist_ok=True)
        for f in ("walk61.onnx", "stand61.onnx"):
            shutil.copyfile(f"{tmp}/m.onnx", d / f)
print(name)

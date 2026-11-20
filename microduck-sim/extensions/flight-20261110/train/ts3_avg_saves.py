"""Round 3, 2026-11-20: average the weights of several saves of one student run and export the result.

  <microduck_rl venv python> train/ts3_avg_saves.py <tag> <dst dir under ckpt> <iter> <iter> [...]
  e.g. cd microduck_rl && .venv/bin/python ../extensions/flight-20261110/train/ts3_avg_saves.py s3AB s3ABm4_160 100 120 140 160

Reads ckpt/<tag>_<iter>/model_<iter>.pt, takes the plain mean of every floating-point tensor of the student (integer
buffers must be equal in all saves), exports ONNX with the same code as the worker (recurrent.export_onnx,
check_onnx) and copies the metadata of the last save's ONNX (joint order, defaults, state keys, gain_flag_col), so
the eval harness treats it like any save. Writes ckpt/<dst>/walk61.onnx, stand61.onnx and avg.pt. No training, no
simulation: a file conversion.
"""
import shutil
import sys
from pathlib import Path

import onnx
import torch

T = Path(__file__).resolve().parent
sys.path.insert(0, str((T / "../../../microduck_rl/cmu/finetune/flight").resolve()))
import recurrent as rc  # noqa: E402

tag, dst, its = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3:]]
cks = [torch.load(T / "ckpt" / f"{tag}_{i}" / f"model_{i}.pt", map_location="cpu", weights_only=False) for i in its]
sds = [c["student"] for c in cks]
assert all(s.keys() == sds[0].keys() for s in sds)
avg, spread = {}, {}
for k in sds[0]:
    if sds[0][k].is_floating_point():
        st = torch.stack([s[k] for s in sds])
        avg[k] = st.mean(0)
        spread[k] = float((st - avg[k]).norm() / (avg[k].norm() * len(sds) ** 0.5 + 1e-12))
    else:
        assert all(torch.equal(s[k], sds[0][k]) for s in sds), k
        avg[k] = sds[0][k].clone()
a = cks[-1]["args"]
student = rc.Student(a["core"], avg["mean"], avg["div"], d=a["hidden"], layers=a["layers"])
student.load_state_dict(avg)
student.eval()
out = T / "ckpt" / dst
out.mkdir(parents=True, exist_ok=True)
p = out / "walk61.onnx"
rc.export_onnx(student, str(p))
src = onnx.load(str(T / "ckpt" / f"{tag}_{its[-1]}" / "walk61.onnx"))
m = onnx.load(str(p))
del m.metadata_props[:]
for e in src.metadata_props:
    x = m.metadata_props.add()
    x.key, x.value = e.key, e.value
onnx.save(m, str(p))
d = rc.check_onnx(student, str(p))
assert d < 1e-3, d
shutil.copyfile(p, out / "stand61.onnx")
torch.save(dict(student=avg, spec=cks[-1]["spec"], iter=its[-1], args=a, averaged=its), out / "avg.pt")
big = sorted(spread.items(), key=lambda kv: -kv[1])[:3]
print(f"{dst}: mean of saves {its}; ONNX vs torch {d:.1e}; relative spread of the saves around the mean, "
      f"median {sorted(spread.values())[len(spread) // 2]:.3f}, largest {[(k, round(v, 3)) for k, v in big]}; "
      f"metadata keys {len(m.metadata_props)} incl. gain_flag_col "
      f"{[e.value for e in m.metadata_props if e.key == 'gain_flag_col']}", flush=True)

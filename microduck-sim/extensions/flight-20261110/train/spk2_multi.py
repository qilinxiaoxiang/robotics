"""Several seeing_pack_check.py runs in one process (spk2 checks on Modal: one import and one CUDA start for all).

Mounted into the spk2chk container at microduck_rl-grasp/cmu/grasp/ by spk2_check_modal.py.
  python spk2_multi.py '[["--scale", "0.10", "--cases", "fq2", "--out", "/tmp/a.json"], ...]'
Each list is one seeing_pack_check.py command line; a failed run is printed and the next one starts; each run writes its
--out file after every case, so a run killed at the deadline keeps its finished cases.
"""
import json
import sys
import time
import traceback

sys.path.insert(0, "/root/microduck_rl-grasp/cmu/grasp")
import seeing_pack_check as C  # noqa: E402

for j in json.loads(sys.argv[1]):
    t0 = time.time()
    sys.argv = ["seeing_pack_check.py"] + j
    try:
        C.main()
        print(f"[spk2multi] done {j[-1]} in {time.time() - t0:.0f} s", flush=True)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        print(f"[spk2multi] FAILED {j[-1]} after {time.time() - t0:.0f} s", flush=True)

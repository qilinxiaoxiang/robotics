"""Score a spotter .npz (single or ensemble) on the held-out set train_mochi.py keeps out of training and write the report.

  python3 eval_mochi.py --mono16 <folder of 16 kHz .npy recordings> --set <mochi_set folder> \
      [--model models/mochi_own.npz] [--out results/mochi_own.json]

Held out: the last quarter of live_141734's calls, the live_073135 table calls, the eight 10/29 RoboClub calls
(calls_221619), the real negatives in mochi_labels.json heldout_negative_spans, and the synthetic speech of the set.
"""
import argparse
import glob
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import ownkws as ok  # noqa: E402
import train_mochi as tm  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mono16", required=True)
    ap.add_argument("--set", required=True)
    ap.add_argument("--model", default=ok.MODEL_DEFAULT)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "mochi_own.json"))
    a = ap.parse_args()
    model = ok.OwnModel(a.model)
    lab = json.load(open(os.path.join(HERE, "mochi_labels.json")))
    mono = {os.path.basename(p)[:-4]: np.load(p) for p in glob.glob(os.path.join(a.mono16, "*.npy"))}
    ev = tm.events(mono["live_141734"], *lab["call_spans"]["live_141734"])
    test_ev = [("live_141734", s, e) for s, e in ev[int(round(len(ev) * 0.75)):]]
    test_ev += [("live_073135", t, t + 0.6) for t in lab["calls_heldout"]["live_073135"]]
    test_ev += [("calls_221619", s, s + lab.get("word_len_s", 0.65)) for s in lab["word_starts"]["calls_221619"]]
    res, extra, _ = tm.evaluate(model, mono, test_ev, dict(lab, scan_files=[]), argparse.Namespace(set=a.set))
    report = dict(made=time.strftime("%Y-%m-%d %H:%M"), model=os.path.relpath(a.model, HERE),
                  members=len(model.members) if model.members else 1, threshold=model.threshold,
                  heldout_calls=len(test_ev), heldout=res, extra=extra)
    json.dump(report, open(a.out, "w"), indent=1, default=float)
    for t in sorted(res, key=float):
        r = res[t]
        print(f"P {t}: calls {r['recall']} {r['per_file']} | synthetic speech {r['fa_per_h']}/h | "
              f"held-out real false {r['heldout_real_false_n']} {r['heldout_real_false']}")


if __name__ == "__main__":
    main()

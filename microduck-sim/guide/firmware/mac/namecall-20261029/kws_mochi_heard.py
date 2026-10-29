"""What the keyword model itself hears when someone says "Mochi": decode the mochi_set.py positives with the same
transducer (encoder, decoder, joiner of the KWS model) as a plain streaming recogniser, modified beam search, and print
its words and BPE tokens. The keyword variants in kws_mochi_eval.py (v5-v7) are taken from this list.

  nice -n 19 pet/.venv/bin/python kws_mochi_heard.py --set DIR > results/kws_mochi_heard.txt
"""
import argparse
import collections
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import namecall as nc  # noqa: E402
import kws_mochi_eval as ev  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--model", default=nc.find_kws_model())
    a = ap.parse_args()
    import sherpa_onnx
    one = lambda s: sorted(glob.glob(os.path.join(a.model, f"{s}-*.int8.onnx")))[0]
    rec = sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=os.path.join(a.model, "tokens.txt"), encoder=one("encoder"), decoder=one("decoder"), joiner=one("joiner"),
        num_threads=1, decoding_method="modified_beam_search", max_active_paths=8)
    rows = [r for r in ev.load_set(a.set) if r["kind"] in ("pos", "pos_zh") and r["rate"] is None]
    words = collections.Counter()
    for r in rows:
        d = nc.Decimate3()
        x = r["sig"][: len(r["sig"]) - len(r["sig"]) % nc.BLOCK]
        y = np.concatenate([d(x[i:i + nc.BLOCK]) for i in range(0, len(x), nc.BLOCK)]).astype(np.float32)
        y = np.concatenate([np.zeros(16000, np.float32), y, np.zeros(32000, np.float32)])
        s = rec.create_stream()
        s.accept_waveform(16000, y)
        s.input_finished()
        while rec.is_ready(s):
            rec.decode_stream(s)
        res = rec.get_result_all(s)
        print(f"{r['accent']} {r['voice'][:12]:12s} {r['text']:18s} -> {res.text!r:32s} [{' '.join(res.tokens)}]")
        words.update(res.text.split())
    print("word counts:", words.most_common(40))


if __name__ == "__main__":
    main()

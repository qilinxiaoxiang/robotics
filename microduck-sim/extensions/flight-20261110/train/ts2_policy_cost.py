"""Cost of one policy call: a recurrent walk61.onnx (obs + state_in, state fed back) against a plain 61-input
walk61.onnx, onnxruntime on one CPU thread with the session options of walk_brain.session_options().

  <python with onnxruntime> train/ts2_policy_cost.py <recurrent walk61.onnx> <plain walk61.onnx> [--calls 3000]
  -> one JSON line: per file median / p90 / p99 / max ms per call, and the ratio of the medians

A few seconds of one core. It measures the machine it runs on; nothing here is an A7Z figure.
"""
import argparse
import json
import platform
import time

import numpy as np
import onnxruntime as ort


def bench(path, calls):
    so = ort.SessionOptions()
    so.intra_op_num_threads = 1
    so.inter_op_num_threads = 1
    sess = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])
    ins = sess.get_inputs()
    rng = np.random.default_rng(0)
    obs = rng.normal(0, 0.3, (calls + 200, 1, 61)).astype(np.float32)
    st = np.zeros(tuple(ins[1].shape), np.float32) if len(ins) > 1 else None
    ms = []
    for i in range(calls + 200):
        feed = {ins[0].name: obs[i]}
        if st is not None:
            feed[ins[1].name] = st
        t = time.perf_counter()
        res = sess.run(None, feed)
        dt = time.perf_counter() - t
        if st is not None:
            st = res[1]
        if i >= 200:  # 200 warm-up calls
            ms.append(dt * 1000)
    ms = np.array(ms)
    return dict(file=path, inputs=[(i.name, list(i.shape)) for i in ins], calls=calls,
                median_ms=round(float(np.median(ms)), 4), p90_ms=round(float(np.percentile(ms, 90)), 4),
                p99_ms=round(float(np.percentile(ms, 99)), 4), max_ms=round(float(ms.max()), 4))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("recurrent")
    ap.add_argument("plain")
    ap.add_argument("--calls", type=int, default=3000)
    a = ap.parse_args()
    r, p = bench(a.recurrent, a.calls), bench(a.plain, a.calls)
    print(json.dumps(dict(machine=platform.node(), cpu=platform.processor() or platform.machine(), onnxruntime=ort.__version__,
                          recurrent=r, plain=p, ratio_median=round(r["median_ms"] / p["median_ms"], 2),
                          ratio_p99=round(r["p99_ms"] / p["p99_ms"], 2))))

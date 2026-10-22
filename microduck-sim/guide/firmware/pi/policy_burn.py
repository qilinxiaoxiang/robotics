#!/usr/bin/env python3
"""Policy-shaped CPU load for the closed-head soak: runs one 61-input policy with onnxruntime at a fixed rate, the way
the brain does in stand61 or walk61 (one intra-op thread, one run per tick), without touching servos or the IMU.

The brain's own soak in monitor mode only reads the bus; the resets and the loop slow-down were seen with a policy
running (2026-10-19, 2026-10-21). This gives the soak that load for the whole hour. a7z_cpu_compare.py starts it with
`--burn` and ends it when the measurement window opens, so the window measures the real brain alone.

  ~/.venvs/duck-policy/bin/python ~/duck/policy_burn.py [--model .../stand61.onnx] [--hz 50] [--threads 1] [--report-s 60]

Prints one line per report period: runs done, mean and p90 run time (ms), achieved rate. Ends on SIGTERM or Ctrl-C.
"""
import argparse, os, signal, time

MODELS = os.path.expanduser("~/rt/microduck-sim/hardware-design-20260912/whole-robot-20260912/runtime-overlay/models")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default=os.path.join(MODELS, "stand61.onnx"))
    ap.add_argument("--hz", type=float, default=50.0)
    ap.add_argument("--threads", type=int, default=1, help="intra- and inter-op threads (the brain uses 1)")
    ap.add_argument("--report-s", type=float, default=60.0)
    ap.add_argument("--runs", type=int, default=None, help="stop after N runs (tests); default: run until a signal")
    a = ap.parse_args(argv)
    import numpy as np
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.intra_op_num_threads = a.threads
    so.inter_op_num_threads = a.threads
    sess = ort.InferenceSession(a.model, so, providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    shape = [d if isinstance(d, int) and d > 0 else 1 for d in inp.shape]
    x = np.zeros(shape, dtype=np.float32)
    stop = []
    for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(s, lambda sig, frame: stop.append(sig))
    period = 1.0 / a.hz
    print(f"# policy_burn {os.path.basename(a.model)} input {inp.name} {shape} at {a.hz:g} Hz, {a.threads} thread(s), pid {os.getpid()}", flush=True)
    t_next = time.monotonic()
    t_rep = t_next + a.report_s
    n = total = 0
    ms = []
    while not stop and (a.runs is None or total < a.runs):
        t0 = time.perf_counter()
        sess.run(None, {inp.name: x})
        ms.append((time.perf_counter() - t0) * 1000.0)
        n += 1
        total += 1
        t_next += period
        now = time.monotonic()
        if now >= t_rep:
            ms.sort()
            span = a.report_s - (t_rep - now)
            print(f"{time.strftime('%H:%M:%S')} runs {n} mean {sum(ms) / len(ms):.2f} ms p90 {ms[int(0.9 * (len(ms) - 1))]:.2f} ms "
                  f"rate {n / max(span, 1e-6):.1f}/s", flush=True)
            n, ms = 0, []
            t_rep += a.report_s
        if t_next > now:
            time.sleep(t_next - now)
        else:
            t_next = now  # fell behind (the board throttled): do not try to catch up in a burst
    print(f"# policy_burn end after {total} runs{' (signal %s)' % stop[0] if stop else ''}", flush=True)


if __name__ == "__main__":
    main()

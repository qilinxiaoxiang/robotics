"""Cost of a sherpa-onnx keyword spotter on this CPU, to decide whether namecall.py may run one on the A7Z.

Streams the model's own test clips (16 kHz) plus 20 s of noise through sherpa_onnx.KeywordSpotter with one thread,
in 20 ms chunks as namecall.py would, and reports the real-time factor (CPU seconds per audio second). The A7Z estimate
scales that by the published single-core ratios (an M1 Pro performance core is about 4x a Cortex-A76 at 2.0 GHz, and the
A7Z runs its clusters at 416 MHz once the thermal governor trips, CURRENT-STATE a7z_closed_head_thermal_and_resets).

  pet/.venv/bin/python kws_bench.py --model DIR --keywords DIR/test_wavs/test_keywords.txt --out results/kws_bench.json
"""
import argparse, glob, json, os, platform, time, wave

import numpy as np
import sherpa_onnx

A76_VS_M1PRO = 4.0        # single-core speed ratio M1 Pro : Cortex-A76 at 2.0 GHz (Geekbench 6 class figures, estimate)
A7Z_MHZ_COOL, A7Z_MHZ_HOT = 2000.0, 416.0


def read16k(path):
    with wave.open(path) as w:
        assert w.getframerate() == 16000 and w.getsampwidth() == 2
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if w.getnchannels() > 1:
            x = x.reshape(-1, w.getnchannels()).mean(axis=1)
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--int8", action="store_true", default=True)
    ap.add_argument("--keywords", default=None, help="keywords file (default: the model's keywords.txt)")
    a = ap.parse_args()
    tag = ".int8" if a.int8 else ""
    f = lambda stem: glob.glob(os.path.join(a.model, f"{stem}-*{tag}.onnx"))[0]
    kws = sherpa_onnx.KeywordSpotter(tokens=os.path.join(a.model, "tokens.txt"), encoder=f("encoder"),
                                     decoder=f("decoder"), joiner=f("joiner"),
                                     keywords_file=a.keywords or os.path.join(a.model, "keywords.txt"),
                                     num_threads=a.threads)
    clips = [read16k(p) for p in sorted(glob.glob(os.path.join(a.model, "test_wavs", "*.wav")))]
    rng = np.random.default_rng(0)
    audio = np.concatenate(clips + [0.01 * rng.standard_normal(16000 * 20).astype(np.float32)])
    s = kws.create_stream()
    hop = 320  # 20 ms
    hits, t_cpu, t_wall = [], time.process_time(), time.perf_counter()
    for i in range(0, len(audio) - hop, hop):
        s.accept_waveform(16000, audio[i:i + hop])
        while kws.is_ready(s):
            kws.decode_stream(s)
            r = kws.get_result(s)
            if r:
                hits.append((round(i / 16000, 2), r))
                kws.reset_stream(s)
    cpu, wall = time.process_time() - t_cpu, time.perf_counter() - t_wall
    sec = len(audio) / 16000
    rtf = cpu / sec
    res = dict(host=platform.node(), cpu=platform.processor() or platform.machine(), threads=a.threads, int8=a.int8,
               audio_s=round(sec, 1), cpu_s=round(cpu, 3), wall_s=round(wall, 3), rtf_cpu=round(rtf, 4),
               hits=hits,
               a7z_estimate=dict(method="rtf x A76_VS_M1PRO x (2000 MHz / clock)", a76_vs_m1pro=A76_VS_M1PRO,
                                 rtf_a76_2000mhz=round(rtf * A76_VS_M1PRO, 3),
                                 rtf_a76_416mhz_throttled=round(rtf * A76_VS_M1PRO * A7Z_MHZ_COOL / A7Z_MHZ_HOT, 3),
                                 budget_fraction_of_one_core=0.25))
    print(json.dumps(res, indent=1))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()

"""Stand61 oscillation summary of one tick log (robot or sim): per contiguous stand61 run, the dominant frequency and rms of
the leg actions and the trunk gyro, plus the fast (above ~2 Hz) leg-action rms. Same windows as churn_replay.py."""
import json, os, sys
import numpy as np
sys.argv, ARGS = sys.argv[:1], sys.argv[1:]
__file__ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "churn_replay.py")
exec(open(__file__).read().split("for path in sys.argv[1:]")[0])


def summary(path, skip=25):
    out = []
    for s in segments(path):
        s = s[skip:]
        if len(s) < 100:
            continue
        a = np.array([r["action"] for r in s])[:, LEGS]; g = np.array([r["gyro_body"] for r in s])
        f = np.fft.rfftfreq(len(a), 0.02)
        def peak(x):
            x = x - x.mean(0); P = (np.abs(np.fft.rfft(x, axis=0)) ** 2).sum(1); P[f < 0.5] = 0
            return float(f[int(np.argmax(P))]), float(np.sqrt(np.mean(x ** 2)))
        fa, ra = peak(a); fg, rg = peak(g)
        out.append(dict(dur=round(s[-1]["t"] - s[0]["t"], 1), act_hz=round(fa, 1), act_rms_mrad=round(ra * 1000, 1),
                        fast_act_mrad=round(rms_fast(np.array([r["action"] for r in s])) * 1000, 1),
                        gyro_hz=round(fg, 1), gyro_rms_mrad_s=round(rg * 1000, 1)))
    return out


if __name__ == "__main__":
    for p in ARGS:
        print(os.path.basename(p), json.dumps(summary(p)))

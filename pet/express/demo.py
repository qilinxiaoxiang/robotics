"""Evidence for the expressive layer.

  pet/.venv/bin/python -m pet.express.demo --body duck      # sim clip + strip (MuJoCo, as-built duck, stand61),
                                                            # tilt table, channel plots, variation, calls audio
  pet/.venv/bin/python -m pet.express.demo --body arm       # channel plots and variation on the OMX-F card
  pet/.venv/bin/python -m pet.express.demo --body vacuum    # channel plots, top-down strip, variation
  pet/.venv/bin/python -m pet.express.demo --body all       # all three plus the same-intent comparison

The duck simulation runs in ~/.venvs/microduck-dyn (pet/express/duck_sim.py re-executes itself there). Everything
lands in pet/express/out/.
"""
import argparse
import json
import os
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from . import Affect, Expressor, Target, acknowledge, content_idle  # noqa: E402
from .channels import load_card  # noqa: E402
from .spring import step_metrics  # noqa: E402
from .takes import SOCIAL_TAKES  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
CARDS = {"duck": "duck.json", "arm": "omx_arm.json", "vacuum": "vacuum.json"}
GAZE = {"duck": "head_yaw", "arm": "base", "vacuum": "heading"}
COLORS = {"quick_snap": "#2a6fdb", "curious_turn": "#d1495b", "double_take": "#edae49", "groggy": "#6c757d",
          "glance": "#00798c", "startle": "#3d348b", "settle": "#cccccc"}


def card(body):
    return load_card(os.path.join(HERE, "cards", CARDS[body]))


def five_calls(seed=7, gap=3.5):
    """The same schedule duck_sim.py --clip uses: five calls from alternating sides, idle in between."""
    rng = np.random.default_rng(seed + 1000)
    sched = []
    for i in range(5):
        side = 1 if i % 2 == 0 else -1
        yaw, pitch = side * float(rng.uniform(0.5, 1.25)), float(rng.uniform(0.1, 0.35))
        tc = 0.5 + i * gap
        sched.append((tc, acknowledge(Target(yaw, pitch), 0.8, 0.7, Affect(0.6, 0.6))))
        sched.append((tc + gap * 0.7, content_idle(affect=Affect(0.6, 0.4))))
    return sched, 0.5 + 5 * gap


def plot_channels(body, tl, path, title):
    outs = tl["outputs"]
    t = tl["t"]
    keys = [k for k in outs if np.ptp(outs[k]) > 1e-4]
    fig, ax = plt.subplots(len(keys) + 1, 1, figsize=(11, 1.5 * (len(keys) + 1) + 0.6), sharex=True)
    for h in tl["takes"]:
        for a in ax:
            a.axvspan(h["t"], h["t"] + 0.02, color=COLORS.get(h["take"], "k"), alpha=0.9)
        ax[0].text(h["t"] + 0.05, 0.92, h["take"], color=COLORS.get(h["take"], "k"), fontsize=8,
                   transform=ax[0].get_xaxis_transform(), va="top")
    for a_name, col in (("ATTEND.yaw", "#222"), ("ORIENT.yaw", "#999"), ("GESTURE.tilt", "#d1495b"),
                        ("POSTURE.height", "#00798c")):
        ax[0].plot(t, tl["axes"][a_name], color=col, lw=1.2, label=a_name)
    ax[0].set_ylabel("semantic")
    ax[0].legend(fontsize=7, ncol=4, loc="lower left")
    for a, k in zip(ax[1:], keys):
        a.plot(t, outs[k], lw=1.3, color="#2a6fdb")
        a.set_ylabel(k, fontsize=8)
        lim = card(body)["channels"]["outputs"][k]["limit"]
        for v in lim:
            if np.isfinite(v) and abs(v) < 3:
                a.axhline(v, color="#bbb", lw=0.6, ls="--")
    for e in tl["events"]:
        for a in ax:
            a.axvline(e["t_abs"], color="#edae49", lw=1.0, ls=":")
        ax[0].text(e["t_abs"], 0.05, f"{e['kind']} x{e['pitch']:.2f}", fontsize=7, color="#a07000",
                   transform=ax[0].get_xaxis_transform())
    ax[-1].set_xlabel("s")
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def variation(body, seed=3, n=300):
    """n name calls in bursts of 1-6 (5-40 s apart within a burst, 60-200 s between bursts), mixed affect:
    take counts, latency / overshoot / arrival distributions on the gaze output, call pitch and length, and the
    consecutive-identity check."""
    rng = np.random.default_rng(seed)
    ex = Expressor(card(body), seed=seed)
    gaze = GAZE[body]
    rows, t = [], 0.0
    while len(rows) < n:
        t += float(rng.uniform(60, 200))
        for _ in range(int(rng.integers(1, 7))):
            a = Affect(float(rng.uniform(-0.2, 0.9)), float(rng.choice([rng.uniform(0.05, 0.3), rng.uniform(0.3, 1.0)])))
            tgt = Target(float(rng.choice([-1, 1]) * rng.uniform(0.4, 1.2)), float(rng.uniform(0.0, 0.35)))
            ex.state = {k: 0.0 for k in ex.state}  # head home before each call
            ex.perf = None
            intent = acknowledge(tgt, float(rng.uniform(0.4, 1.0)), float(rng.uniform(0.3, 1.0)), a)
            tl = ex.run([(t, intent)], t + 3.0, t0=t)
            h = tl["takes"][0]
            y = tl["outputs"][gaze]
            final = y[-1]
            m = step_metrics(tl["t"], tl["axes"]["ATTEND.yaw"] - (tl["axes"]["ATTEND.yaw"][0]), 0.0,
                             tgt.yaw * h["params"].get("amp", 1.0), t)
            peak = float(np.max(np.sign(final) * y)) if abs(final) > 0.3 else 0.0
            rows.append(dict(take=h["take"], novelty=h["novelty"], arousal=a.arousal, latency=m["latency"],
                             arrival=h["arrival"], overshoot=m["overshoot"],
                             out_overshoot=max(0.0, peak / abs(final) - 1.0) if abs(final) > 0.3 and h["take"] != "glance" else None,
                             calls=[(e["pitch"], e["stretch"]) for e in h["events"]],
                             sig=(h["take"], round(h["params"]["latency"], 4), round(h["params"]["wn"], 4))))
            t += float(rng.uniform(5, 40))
    rows = rows[:n]
    ident = sum(1 for a, b in zip(rows, rows[1:]) if a["sig"] == b["sig"])
    same_take = sum(1 for a, b in zip(rows, rows[1:]) if a["take"] == b["take"])
    counts = {k: sum(r["take"] == k for r in rows) for k in SOCIAL_TAKES}

    def dist(key):
        v = np.array([r[key] for r in rows if r[key] is not None], float)
        return dict(n=int(v.size), median=round(float(np.median(v)), 3), p10=round(float(np.percentile(v, 10)), 3),
                    p90=round(float(np.percentile(v, 90)), 3), min=round(float(v.min()), 3), max=round(float(v.max()), 3))

    pitches = [c[0] for r in rows for c in r["calls"]]
    stretches = [c[1] for r in rows for c in r["calls"]]
    res = dict(body=body, n=len(rows), take_counts=counts, consecutive_identical=ident, consecutive_same_take=same_take,
               latency_s=dist("latency"), arrival_s=dist("arrival"), overshoot_frac=dist("overshoot"),
               calls=dict(n=len(pitches), pitch_p10_p90=[round(float(np.percentile(pitches, q)), 3) for q in (10, 90)],
                          stretch_p10_p90=[round(float(np.percentile(stretches, q)), 3) for q in (10, 90)],
                          distinct_pitch=len(set(pitches))),
               by_take={k: dict(latency_med=round(float(np.median([r["latency"] for r in rows if r["take"] == k and r["latency"] is not None] or [np.nan])), 3),
                                overshoot_med=round(float(np.median([r["overshoot"] for r in rows if r["take"] == k] or [np.nan])), 3))
                        for k in SOCIAL_TAKES})
    fig, ax = plt.subplots(1, 4, figsize=(14, 3.2))
    for k in SOCIAL_TAKES:
        sel = [r for r in rows if r["take"] == k]
        if not sel:
            continue
        ax[0].hist([r["latency"] for r in sel if r["latency"] is not None], bins=np.linspace(0, 1.4, 29), alpha=0.6,
                   color=COLORS[k], label=f"{k} ({len(sel)})")
        ax[1].hist([r["overshoot"] for r in sel], bins=np.linspace(0, 0.4, 21), alpha=0.6, color=COLORS[k])
        ax[2].scatter([r["arousal"] for r in sel], [r["arrival"] for r in sel], s=8, color=COLORS[k])
    ax[0].set_xlabel("gaze latency to 10 % of the move (s)")
    ax[0].legend(fontsize=7)
    ax[1].set_xlabel("gaze overshoot (fraction of the move)")
    ax[2].set_xlabel("arousal")
    ax[2].set_ylabel("arrival (s)")
    ax[3].scatter(pitches, stretches, s=8, color="#a07000")
    ax[3].set_xlabel("call pitch factor")
    ax[3].set_ylabel("call length factor")
    fig.suptitle(f"{body}: {len(rows)} name calls, {ident} consecutive identical, {same_take} consecutive same take",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, f"{body}_variation.png"), dpi=110)
    plt.close(fig)
    json.dump(res, open(os.path.join(OUT, f"{body}_variation.json"), "w"), indent=1)
    return res


def vacuum_strip(tl, path):
    """Top-down frames of the vacuum: heading arrow, drive displacement, ring LED brightness."""
    t, hd, dv, led = tl["t"], tl["outputs"]["heading"], tl["outputs"]["drive"], tl["outputs"]["ring_led"]
    x = np.cumsum(dv * np.cos(hd)) * 0.02
    y = np.cumsum(dv * np.sin(hd)) * 0.02
    calls = [h["t"] for h in tl["takes"]][:3]
    offs = (0.0, 0.3, 0.6, 0.9, 1.3, 2.0)
    fig, ax = plt.subplots(len(calls), len(offs), figsize=(2 * len(offs), 2 * len(calls)))
    for i, tc in enumerate(calls):
        for j, o in enumerate(offs):
            k = int(np.argmin(np.abs(t - (tc + o))))
            a = ax[i, j]
            a.add_patch(plt.Circle((x[k], y[k]), 0.17, color=plt.cm.YlOrBr(0.15 + 0.8 * led[k]), ec="#333"))
            a.arrow(x[k], y[k], 0.15 * np.cos(hd[k]), 0.15 * np.sin(hd[k]), width=0.012, color="#222")
            a.set_xlim(x[k] - 0.3, x[k] + 0.3)
            a.set_ylim(y[k] - 0.3, y[k] + 0.3)
            a.set_aspect("equal")
            a.set_xticks([])
            a.set_yticks([])
            a.set_title(f"t {tc + o:.1f}  {tl['takes'][i]['take'] if j == 0 else ''}", fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def same_intent(path):
    """One intent, one take, one seed on all three bodies: the semantic motion is identical, the outputs differ."""
    intent = acknowledge(Target(0.9, 0.25), 0.8, 0.8, Affect(0.6, 0.7))
    fig, ax = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
    tls = {}
    for col, body in zip(("#2a6fdb", "#d1495b", "#00798c"), ("duck", "arm", "vacuum")):
        tl = tls[body] = Expressor(card(body), seed=21).run([(0.3, intent, "quick_snap")], 3.0)
        for i, (axis_k, lab) in enumerate((("gaze", "gaze actuator"), ("posture", "posture actuator"),
                                            ("gesture", "gesture actuator"))):
            k = {"duck": ("head_yaw", "neck_pitch", "head_roll"), "arm": ("base", "shoulder", "wrist_roll"),
                 "vacuum": ("heading", "drive", "heading")}[body][i]
            ax[i + 1].plot(tl["t"], tl["outputs"][k], color=col, label=f"{body}: {k}")
            ax[i + 1].set_ylabel(lab, fontsize=8)
            ax[i + 1].legend(fontsize=7)
        for e in tl["events"]:
            ax[0].axvline(e["t_abs"], color=col, ls=":")
            ax[0].text(e["t_abs"], 0.1 + 0.25 * ("duck", "arm", "vacuum").index(body),
                       {"duck": "quack", "arm": "gripper clack", "vacuum": "beep + LED"}[body], color=col, fontsize=8,
                       transform=ax[0].get_xaxis_transform())
    for a_name in ("ATTEND.yaw", "POSTURE.height", "GESTURE.tilt"):
        ax[0].plot(tls["duck"]["t"], tls["duck"]["axes"][a_name], label=a_name)
    ax[0].plot(tls["arm"]["t"], tls["arm"]["axes"]["ORIENT.yaw"], label="ORIENT.yaw (arm, vacuum; the duck's stays 0 "
               "below its 1.2 rad threshold)")
    ax[0].legend(fontsize=7, ncol=4)
    ax[0].set_ylabel("semantic axes")
    ax[-1].set_xlabel("s")
    fig.suptitle("acknowledge(owner at +0.9 rad, warmth 0.8, energy 0.8), take quick_snap, seed 21, on three bodies",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def duck_audio(events):
    from .voice import CallPicker, find_calls, read_wav, render_call, write_wav
    files = find_calls()
    if not files:
        return None
    pick = CallPicker(files, np.random.default_rng(5))
    os.makedirs(os.path.join(OUT, "audio"), exist_ok=True)
    fig, ax = plt.subplots(1, len(events), figsize=(3 * len(events), 2.6), squeeze=False)
    out = []
    for i, e in enumerate(events):
        f = pick.pick()
        x, rate = read_wav(f)
        y = render_call(x, e["pitch"], e["stretch"], e["gain_db"])
        path = os.path.join(OUT, "audio", f"call_{i + 1}.wav")
        write_wav(path, y, rate)
        ax[0, i].specgram(y, NFFT=512, Fs=rate, noverlap=384, cmap="magma")
        ax[0, i].set_ylim(0, 6000)
        ax[0, i].set_title(f"call {i + 1}: {os.path.basename(f)}\npitch x{e['pitch']:.2f} length x{e['stretch']:.2f}",
                           fontsize=7)
        out.append(dict(source=os.path.relpath(f, os.path.join(HERE, "..", "..")), pitch=e["pitch"],
                        stretch=e["stretch"], gain_db=e["gain_db"], seconds=round(len(y) / rate, 3)))
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "duck_calls_spectrogram.png"), dpi=100)
    plt.close(fig)
    return out


def tilt_report():
    rows_md = ["| set | calls | trunk tilt median / p95 / max (deg) | head latency median (s) | joint lag (s) | "
               "tracking rms (rad) | EMA saturated ticks | falls |", "|---|---|---|---|---|---|---|---|"]
    lines = []
    data = {}
    for tag in ("", "_stress"):
        p = os.path.join(OUT, f"duck_tilt{tag}.json")
        if not os.path.exists(p):
            continue
        r = json.load(open(p))
        data[tag or "real"] = r
        lines.append(f"\n**{'Real' if not tag else 'Stress'} condition**: {r['volt']} V servo rail, "
                     f"{r['drop'] * 100:.0f} % servo read drops, {r['n']} calls per set, {r['gap_s']} s apart.\n")
        lines += rows_md
        for name, v in r["takes"].items():
            rows = v["rows"]
            tm = np.array([x["tilt_max_deg"] for x in rows])
            lat = [x["head_latency_s"] for x in rows if x["head_latency_s"] is not None]
            lines.append(f"| {name} | {len(rows)} | {np.median(tm):.2f} / {np.percentile(tm, 95):.2f} / {tm.max():.2f} | "
                         f"{np.median(lat):.2f} | {np.median([x['track_lag_s'] for x in rows]):.2f} | "
                         f"{np.median([x['track_rms_rad'] for x in rows]):.3f} | {v['head_cmd_saturated_ticks']} | "
                         f"{sum(x['fell'] for x in rows)} |")
    if not data:
        return None
    txt = ("# Duck trunk tilt per take under stand61\n\nAs-built MuJoCo duck (saddle mass manifest), stand61 at zero "
           "command, head commands through walk_brain.Brain's own head path (EMA pre-inverted by pet/express/duck.py). "
           "Tilt = largest change of trunk roll/pitch from the 0.6 s before the call, over the 2.3 s response. "
           "Baseline = today's path: the target pose stepped in and smoothed by HEAD_ALPHA 0.2. "
           "Servo rail and read-drop values come from microduck-sim/CURRENT-STATE.json, whose entries were stale on "
           "2026-10-26 (robot offline); the stress condition brackets them. Regenerate with "
           "`~/.venvs/microduck-dyn/bin/python pet/express/duck_sim.py --tilt`.\n" + "\n".join(lines) + "\n")
    open(os.path.join(OUT, "duck_tilt_table.md"), "w").write(txt)
    r = data.get("real")
    if r:
        fig, ax = plt.subplots(figsize=(10, 3.4))
        names = list(r["takes"])
        ax.boxplot([[x["tilt_max_deg"] for x in r["takes"][k]["rows"]] for k in names], tick_labels=names)
        ax.set_ylabel("trunk tilt max per call (deg)")
        ax.set_title(f"duck under stand61, {r['volt']} V, {r['drop'] * 100:.0f} % drops, {r['n']} calls per set",
                     fontsize=10)
        plt.setp(ax.get_xticklabels(), rotation=20, fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, "duck_tilt.png"), dpi=110)
        plt.close(fig)
    return txt


def run_body(body, args):
    os.makedirs(OUT, exist_ok=True)
    sched, until = five_calls()
    tl = Expressor(card(body), seed=7).run(sched, until)
    plot_channels(body, tl, os.path.join(OUT, f"{body}_5_calls_channels.png"),
                  f"{body}: five name calls (acknowledge, warmth 0.8, energy 0.7, valence 0.6, arousal 0.6), seed 7")
    v = variation(body)
    print(f"{body}: takes {[h['take'] for h in tl['takes']]}; variation {v['take_counts']}, "
          f"consecutive identical {v['consecutive_identical']}/{v['n'] - 1}")
    if body == "vacuum":
        vacuum_strip(tl, os.path.join(OUT, "vacuum_strip.png"))
    if body == "duck":
        if not args.no_sim:
            py = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
            subprocess.run([py, os.path.join(HERE, "duck_sim.py"), "--clip"], check=True)
            if args.tilt or not os.path.exists(os.path.join(OUT, "duck_tilt.json")):
                subprocess.run([py, os.path.join(HERE, "duck_sim.py"), "--tilt"], check=True)
        calls = json.load(open(os.path.join(OUT, "duck_calls.json")))
        audio = duck_audio([e for c in calls["calls"] for e in c["events"]])
        if audio:
            json.dump(audio, open(os.path.join(OUT, "duck_calls_audio.json"), "w"), indent=1)
        tilt_report()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--body", choices=("duck", "arm", "vacuum", "all"), default="all")
    ap.add_argument("--no-sim", action="store_true", help="duck: reuse out/duck_calls.json, skip MuJoCo")
    ap.add_argument("--tilt", action="store_true", help="duck: rerun the tilt table (about 1 min)")
    args = ap.parse_args()
    bodies = ("duck", "arm", "vacuum") if args.body == "all" else (args.body,)
    for b in bodies:
        run_body(b, args)
    same_intent(os.path.join(OUT, "same_intent_3_bodies.png"))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())

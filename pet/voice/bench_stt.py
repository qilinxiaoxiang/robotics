"""STT benchmark on the synthetic clips: latency and error rate per backend and model -> out/stt_bench.json + .md.

    nice -n 10 pet/.venv/bin/python -m pet.voice.bench_stt [--threads 4]

For every clip in out/clips/index.json (made by synth.py) each local model transcribes the 16 kHz clip, and the
chosen model also transcribes what listen.py segments out of the 4-channel robot-format version (the whole chain
the robot will use). ElevenLabs is tried on the first clip only; an error (401 today) is recorded and the backend is
skipped. English is scored by word error rate (lower-cased, punctuation stripped, word-level edit distance) and
Chinese by character error rate (punctuation and spaces stripped). Latency is the decode time of a clip already in
memory, after one warm-up decode, median and max over the clips.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import statistics
import sys
import time
from pathlib import Path

from . import stt
from .listen import ROBOT_FS, utterances, wav_blocks

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
CLIPS = OUT / "clips"
_PUNCT = re.compile(r"[^\w\s一-鿿]")


def norm(text: str, lang: str) -> list[str]:
    t = _PUNCT.sub(" ", text.lower())
    if lang == "zh":
        return [c for c in t if not c.isspace()]
    return t.split()


def edit_distance(a: list, b: list) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def error_rate(ref: str, hyp: str, lang: str) -> float:
    r, h = norm(ref, lang), norm(hyp, lang)
    return edit_distance(r, h) / max(1, len(r))


def score(rows: list[dict]) -> dict:
    by = {}
    for lang in ("en", "zh", "all"):
        sel = [r for r in rows if lang == "all" or r["lang"] == lang]
        if not sel:
            continue
        errs = sum(r["errors"] for r in sel)
        units = sum(r["units"] for r in sel)
        lat = [r["latency_s"] for r in sel]
        by[lang] = {"clips": len(sel), "error_rate": round(errs / max(1, units), 3), "exact": sum(r["exact"] for r in sel),
                    "latency_median_s": round(statistics.median(lat), 3), "latency_max_s": round(max(lat), 3)}
    return by


def run_local(model: str, index: list[dict], threads: int) -> dict:
    be = stt.LocalSTT(model, threads=threads)
    be.transcribe(CLIPS / index[0]["wav"])          # warm-up
    rows = []
    for c in index:
        r = be.transcribe(CLIPS / c["wav"])
        ref, hyp = c["text"], r["text"]
        rl = norm(ref, c["lang"])
        rows.append({"id": c["id"], "lang": c["lang"], "ref": ref, "hyp": hyp, "lang_out": r["lang"],
                     "errors": edit_distance(rl, norm(hyp, c["lang"])), "units": len(rl),
                     "exact": int(norm(ref, c["lang"]) == norm(hyp, c["lang"])), "latency_s": r["latency_s"],
                     "seconds": r["seconds"]})
    return {"backend": f"local:{model}", "load_s": round(be.load_s, 2), "threads": threads, "rows": rows,
            "score": score(rows)}


def run_chain(model: str, index: list[dict], threads: int) -> dict:
    """robot-format WAV -> listen.py -> the local model: the chain as it will run on the A7Z stream."""
    be = stt.get_backend("local", model)
    rows = []
    for c in index:
        p = CLIPS / c["robot_wav"]
        t0 = time.monotonic()
        utts = list(utterances(wav_blocks(p), ROBOT_FS, source=p.name))
        seg_s = time.monotonic() - t0
        hyp = ""
        lat = 0.0
        if utts:
            r = be.transcribe(utts[0])
            hyp, lat = r["text"], r["latency_s"]
        rl = norm(c["text"], c["lang"])
        rows.append({"id": c["id"], "lang": c["lang"], "ref": c["text"], "hyp": hyp, "utterances": len(utts),
                     "utt_seconds": round(utts[0].seconds, 2) if utts else 0.0, "segment_s": round(seg_s, 3),
                     "errors": edit_distance(rl, norm(hyp, c["lang"])), "units": len(rl),
                     "exact": int(rl == norm(hyp, c["lang"])), "latency_s": lat})
    return {"backend": f"chain:listen+local:{model}", "rows": rows, "score": score(rows),
            "segmented": sum(1 for r in rows if r["utterances"] == 1)}


def run_eleven(index: list[dict]) -> dict:
    be = stt.ElevenLabsSTT()
    first = be.transcribe(CLIPS / index[0]["wav"])
    if first.get("error"):
        return {"backend": "elevenlabs", "error": first["error"], "tried": index[0]["id"], "rows": [], "score": {}}
    rows = []
    for c in index:
        r = be.transcribe(CLIPS / c["wav"])
        rl = norm(c["text"], c["lang"])
        rows.append({"id": c["id"], "lang": c["lang"], "ref": c["text"], "hyp": r["text"], "lang_out": r["lang"],
                     "errors": edit_distance(rl, norm(r["text"], c["lang"])), "units": len(rl),
                     "exact": int(rl == norm(r["text"], c["lang"])), "latency_s": r["latency_s"],
                     "seconds": r["seconds"], "error": r.get("error")})
    return {"backend": "elevenlabs", "rows": rows, "score": score(rows)}


def markdown(res: dict) -> str:
    lines = [f"# STT benchmark {res['date']}", "",
             f"Host: {res['host']} ({res['cpu']}), {res['threads']} threads, {len(res['clips'])} synthetic clips "
             f"(macOS say: Samantha en, Tingting zh). Error rate: WER for English, CER for Chinese.", ""]
    for b in res["backends"]:
        if b.get("error"):
            lines.append(f"- **{b['backend']}**: {b['error']} (tried {b['tried']}); not scored.")
            continue
        s = b["score"]
        lines.append(f"- **{b['backend']}**" + (f" (load {b['load_s']} s)" if b.get("load_s") else "") + ": " + "; ".join(
            f"{lang} {v['error_rate']:.1%} error, {v['exact']}/{v['clips']} exact, latency median {v['latency_median_s']} s "
            f"max {v['latency_max_s']} s" for lang, v in s.items()))
    lines += ["", f"Chosen local default: **{res['chosen']}** ({res['why']})", "", "## Per clip (chosen model)", ""]
    chosen = next(b for b in res["backends"] if b["backend"] == f"local:{res['chosen']}")
    for r in chosen["rows"]:
        mark = "ok " if r["exact"] else "ERR"
        lines.append(f"- {mark} {r['id']} {r['latency_s']:.2f} s  ref `{r['ref']}`  hyp `{r['hyp']}`")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--threads", type=int, default=stt.THREADS)
    ap.add_argument("--models", default="sense-voice,whisper-base")
    a = ap.parse_args(argv)
    index = json.loads((CLIPS / "index.json").read_text())
    models = [m for m in a.models.split(",") if m]
    backends = [run_local(m, index, a.threads) for m in models]
    backends.append(run_eleven(index))
    ok = [b for b in backends if b["backend"].startswith("local:")]
    best = min(ok, key=lambda b: (b["score"]["all"]["error_rate"], b["score"]["all"]["latency_median_s"]))
    chosen = best["backend"].split(":", 1)[1]
    why = (f"lowest overall error {best['score']['all']['error_rate']:.1%} at median {best['score']['all']['latency_median_s']} s; "
           + ", ".join(f"{b['backend']} {b['score']['all']['error_rate']:.1%} / {b['score']['all']['latency_median_s']} s"
                       for b in ok if b is not best))
    backends.append(run_chain(chosen, index, a.threads))
    res = {"date": time.strftime("%Y-%m-%d %H:%M"), "host": platform.node(), "cpu": platform.machine(),
           "threads": a.threads, "clips": [c["id"] for c in index], "backends": backends, "chosen": chosen, "why": why}
    OUT.mkdir(exist_ok=True)
    (OUT / "stt_bench.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    md = markdown(res)
    (OUT / "stt_bench.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())

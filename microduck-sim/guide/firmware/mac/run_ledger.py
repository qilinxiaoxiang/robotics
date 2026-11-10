#!/usr/bin/env python3
"""Run ledger: every action the robot does after each power-on, with its outcome and full trajectory, from the
brain's own tick logs. Nothing is recorded by hand.

The brain (walk_wired.py) writes one row per 50 Hz tick to ~/duck-logs/duck_wired_log_<suffix>.jsonl on the A7Z
and, since 2026-11-10, one line per brain start to duck_wired_log_<suffix>.meta.jsonl (code and policy hashes,
arguments, gains). This tool copies both off the robot (rsync only: logs are never parsed on the A7Z), cuts each
settled log into actions and writes:

  ~/duck-walks/episodes.jsonl                one record per action (live data on the Mac mini, outside git)
  ~/duck-walks/episodes/<log>/<id>.jsonl.gz  the action's tick rows unchanged (goals, positions, currents, IMU,
                                             commands), 1 s before and after included
  ~/duck-walks/ledger-runs.jsonl             one record per ingest: time, status, logs, actions, error
  <summary>                                  runs.html: success rate per action and day, changes, scorecard, health

  run_ledger.py tick [--host a7z]   copy new logs, cut settled ones, feed the scorecard, write the page (launchd)
  run_ledger.py cut LOG...          cut local logs (.jsonl or .jsonl.gz) into the episode ledger
  run_ledger.py page                rewrite the page only

Action kinds (from the brain mode and the command it was given): stand (open-loop ramp, KP 400), balance
(stand61 at zero command), walk (forward or arc), turn (in place), bend (groundpick), pick (seepick), sit, kick,
getup (the recover sequence after a fall). Outcomes:
  fell       tilt over 45 deg during the action or within 1 s after it
  guard      a guard ended it: walk_wired's 3.0 rad action or 30 deg tilt stop (3 of the last 10 ticks over the
             limit before the switch) or a servo hardware fault
  incomplete the action ran but did not finish its job: a bend that never reached its done phase, a pick that
             ended without the jaw holding, a get-up that gave up
  ok         none of these
Actions that start lying (tilt over 45 deg) are kept with outcome "started_fallen" and left out of the rates.
"""
import argparse
import collections
import glob
import gzip
import hashlib
import html
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))  # microduck-sim
DATA = os.path.expanduser(os.environ.get("DUCK_LEDGER_DATA", "~/duck-walks"))
RAW = os.path.join(DATA, "raw")
EPI_DIR = os.path.join(DATA, "episodes")
EPISODES = os.path.join(DATA, "episodes.jsonl")
RUNS = os.path.join(DATA, "ledger-runs.jsonl")
STATE = os.path.join(DATA, "ledger-state.json")
PAGE = os.path.expanduser(os.environ.get(
    "DUCK_LEDGER_PAGE", os.path.join(ROOT, "microduck-simulator", "app", "public", "runs", "index.html")))
SCORE_DIR = os.path.join(HERE, "scorecard-20261109")

FALL_DEG, GUARD_TILT_DEG, GUARD_ACTION = 45.0, 30.0, 3.0
GP_DONE, SP_DONE = 0.98, 0.98
MERGE_GAP_S, PAD_S, MIN_BALANCE_S = 0.5, 1.0, 1.0
SETTLE_S = 180  # a log not grown for this long belongs to a finished brain run
REPLAYABLE = ("walk", "turn", "balance", "stand", "bend")  # brain_sim_check --cmd-replay covers these commands


def tilt(gb):
    return math.degrees(math.acos(max(-1.0, min(1.0, -gb[2])))) if gb else 0.0


def open_log(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path, errors="replace")


def rows_of(path):
    with open_log(path) as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and "t" in r and "mode" in r:
                yield r


def kind_of(r):
    m = r.get("mode")
    c = r.get("cmd") or {}
    if m == "walk":
        if r.get("getup") not in (None, "up", "rearmed"):
            return "getup"
        vx, vy, vth = (abs(float(c.get(k, 0) or 0)) for k in ("vx", "vy", "vtheta"))
        if vx > 1e-3 or vy > 1e-3:
            return "walk"
        if vth > 1e-3:
            return "turn"
        return "balance"
    return {"stand": "stand", "groundpick": "bend", "seepick": "pick", "sit": "sit", "kick": "kick"}.get(m)


def segments(rows):
    """[(kind, [rows])] of contiguous same-kind ticks; gaps under MERGE_GAP_S of another kind are absorbed."""
    segs = []
    for r in rows:
        k = kind_of(r)
        if segs and segs[-1][0] == k:
            segs[-1][1].append(r)
        else:
            segs.append([k, [r]])
    out = []
    for k, rs in segs:  # a short blip between two runs of the same kind joins them (hold-to-walk rewrites)
        if out and len(out) >= 2 and out[-2][0] == k and out[-1][1][-1]["t"] - out[-1][1][0]["t"] < MERGE_GAP_S:
            blip = out.pop()
            out[-1][1].extend(blip[1] + rs)
        else:
            out.append([k, rs])
    return [(k, rs) for k, rs in out if k is not None]


def stats(rs):
    walk = [r for r in rs if r.get("gyro_body")]
    dg = [b - a for r0, r1 in zip(walk, walk[1:]) for a, b in zip(r0["gyro_body"], r1["gyro_body"])
          if r1["t"] - r0["t"] < 0.03]
    jit = None
    if len(dg) > 20:
        mu = sum(dg) / len(dg)
        jit = round((sum((x - mu) ** 2 for x in dg) / len(dg)) ** 0.5, 3)
    dv = sorted(r["battery_dv"] for r in rs if isinstance(r.get("battery_dv"), (int, float)) and 50 <= r["battery_dv"] <= 90)
    loops = sorted(r["loop_ms"] for r in rs if isinstance(r.get("loop_ms"), (int, float)))
    # imu_seq is the head board's frame counter (~190 frames/s at the sender); what the policy needs is a new frame on
    # every 50 Hz tick, so record the share of ticks whose frame number changed (CURRENT-STATE imu_rate_hz: full rate)
    seq = [r["imu_seq"] for r in rs if isinstance(r.get("imu_seq"), int)]
    imu_new = round(sum(1 for a, b in zip(seq, seq[1:]) if b != a) / (len(seq) - 1), 3) if len(seq) > 50 else None
    ts = [r["t"] for r in rs]
    tick_hz = round((len(ts) - 1) / (ts[-1] - ts[0]), 1) if len(ts) > 50 and ts[-1] > ts[0] else None
    return dict(max_tilt_deg=round(max((tilt(r.get("gb")) for r in rs), default=0.0), 1), jitter=jit,
                stale=round(sum(not r.get("fresh", True) for r in rs) / len(rs), 3),
                battery_v=dv[len(dv) // 2] / 10 if dv else None,
                loop_ms_p90=round(loops[int(len(loops) * 0.9)], 1) if loops else None,
                imu_new_share=imu_new, tick_hz=tick_hz, max_action=round(max((max(abs(a) for a in r["action"]) for r in rs if r.get("action")), default=0.0), 2))


def commands(rs):
    out, prev = [], None
    for r in rs:
        c = r.get("cmd")
        key = json.dumps(c, sort_keys=True) if c else None
        if c and key != prev:
            out.append([round(r["t"] - rs[0]["t"], 2), c])
        prev = key
    return out


def fall_limit(kind):
    """Tilt that counts as a fall: the bow of a bend or pick reaches 47 deg by design (2026-11-06 picks), so those
    use 70 deg; everything else 45 deg."""
    return 70.0 if kind in ("bend", "pick") else FALL_DEG


def fall_events(rows):
    """[(onset_t, fall_t, recovered_t)]: fall_t is the first tick over the fall limit of the action in force, onset_t
    the last tick before it under 30 deg (under 50 in a bend or pick), recovered_t the first time the body is back
    under 20 deg for 1 s (None if it never is in the log)."""
    ev, i, n = [], 0, len(rows)
    while i < n:
        r = rows[i]
        k = kind_of(r)
        if tilt(r.get("gb")) > fall_limit(k):
            low = 50.0 if k in ("bend", "pick") else GUARD_TILT_DEG
            j = i
            while j > 0 and tilt(rows[j].get("gb")) >= low:
                j -= 1
            rec, calm_since = None, None
            for q in rows[i:]:
                if tilt(q.get("gb")) < 20.0:
                    calm_since = calm_since or q["t"]
                    if q["t"] - calm_since >= 1.0:
                        rec = q["t"]
                        break
                else:
                    calm_since = None
            ev.append((rows[j]["t"], r["t"], rec))
            if rec is None:
                break
            while i < n and rows[i]["t"] < rec:
                i += 1
        i += 1
    return ev


def outcome(kind, rs, after, falls):
    """(outcome, detail): a fall is charged to the one action in force at its onset; actions that start between a
    fall and the recovery are started_fallen."""
    t0, t1 = rs[0]["t"], rs[-1]["t"]
    for onset, fall_t, rec in falls:
        if onset < t0 and (rec is None or t0 < rec):
            return "started_fallen", None
        if t0 <= onset <= t1:
            return "fell", f"tilt over {fall_limit(kind):.0f} deg {fall_t - t0:.1f} s into the action"
    nxt = after[0] if after else None
    if any(r.get("hw_faults") for r in rs[-10:]):
        return "guard", "servo hardware fault"
    if nxt is not None and kind in ("walk", "turn", "balance", "getup", "kick") and nxt.get("mode") in ("stand", "monitor") \
            or nxt is not None and kind in ("bend", "pick", "sit") and nxt.get("mode") == "monitor":
        last = rs[-10:]
        over = sum(1 for r in last if r.get("action") and max(abs(a) for a in r["action"]) > GUARD_ACTION)
        tilted = sum(1 for r in last if tilt(r.get("gb")) > GUARD_TILT_DEG)
        if over >= 3 or tilted >= 1:
            return "guard", f"{'action over 3 rad' if over >= 3 else 'tilt over 30 deg'} before the switch to {nxt.get('mode')}"
    if kind == "bend":  # a held bend commands a phase short of the end (the 11/01 holds at 0.33): reach that phase
        want = max(min(float((r.get("cmd") or {}).get("phase", 1.0) or 1.0), GP_DONE) for r in rs)
        got = max((r.get("gp_phase") or 0) for r in rs)
        if got < want - 0.02:
            return "incomplete", f"bend reached phase {got:.2f} of {want:.2f}"
    if kind == "pick":
        if not any(r.get("jaw_holding") for r in rs + after[:100]):
            return "incomplete", "jaw not holding at the end of the pick"
    if kind == "getup":
        phases = [r.get("getup") for r in rs + after[:50] if r.get("getup")]
        if "gave_up" in phases:
            return "incomplete", "get-up gave up"
    return "ok", None


def meta_for(log_path, t):
    """The brain-start record in force at time t (walk_wired.write_run_meta), or None for logs before 2026-11-10."""
    mp = log_path.replace(".jsonl.gz", ".meta.jsonl").replace(".jsonl", ".meta.jsonl")
    if not os.path.exists(mp):
        return None
    best = None
    for line in open(mp):
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("t", 0) <= t + 1:
            best = m
    return best


def version_key(meta):
    if not meta:
        return None
    blob = json.dumps([meta.get("code_sha"), meta.get("model_sha"), meta.get("kp_rl"), meta.get("kp_stand")], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:10]


def load_jsonl(p):
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


def cut(paths):
    """Cut logs into episodes; replaces earlier records of the same logs. Returns the number of episodes written."""
    old = [e for e in load_jsonl(EPISODES) if e["log"] not in {os.path.basename(p) for p in paths}]
    new = []
    for p in paths:
        name = os.path.basename(p)
        stem = name.split(".jsonl")[0]
        rows = list(rows_of(p))
        if not rows:
            continue
        segs = segments(rows)
        falls = fall_events(rows)
        idx = {id(r): i for i, r in enumerate(rows)}
        os.makedirs(os.path.join(EPI_DIR, stem), exist_ok=True)
        for k, rs in segs:
            dur = rs[-1]["t"] - rs[0]["t"]
            if k == "balance" and dur < MIN_BALANCE_S:
                continue
            i0, i1 = idx[id(rs[0])], idx[id(rs[-1])]
            after = rows[i1 + 1:i1 + 1 + 200]
            oc, detail = outcome(k, rs, after, falls)
            meta = meta_for(p, rs[0]["t"])
            pol = sorted({r.get("policy") for r in rs if r.get("policy")})
            eid = f"{stem}-{rs[0]['t']:.2f}-{k}"
            pad = [r for r in rows[max(0, i0 - 60):i1 + 61] if rs[0]["t"] - PAD_S <= r["t"] <= rs[-1]["t"] + PAD_S]
            traj = os.path.join(EPI_DIR, stem, f"{eid}.jsonl.gz")
            with gzip.open(traj, "wt") as f:
                for r in pad:
                    f.write(json.dumps(r) + "\n")
            new.append(dict(
                id=eid, log=name, kind=k, t_start=round(rs[0]["t"], 3), t_end=round(rs[-1]["t"], 3),
                when=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rs[0]["t"])),
                day=time.strftime("%Y-%m-%d", time.localtime(rs[0]["t"])), dur_s=round(dur, 2),
                outcome=oc, detail=detail, policies=pol, kp=sorted({r.get("kp") for r in rs if isinstance(r.get("kp"), int)}),
                commands=commands(rs)[:40], n_commands=len(commands(rs)), **stats(rs),
                version=version_key(meta), meta=None if meta is None else dict(
                    code_sha=meta.get("code_sha"), model_sha=meta.get("model_sha"), kp_rl=meta.get("kp_rl"),
                    kp_stand=meta.get("kp_stand"), argv=meta.get("argv")),
                trajectory=os.path.relpath(traj, DATA), replayable=k in REPLAYABLE and oc != "started_fallen"))
        print(f"{name}: {sum(1 for e in new if e['log'] == name)} actions", flush=True)
    allx = sorted(old + new, key=lambda e: e["t_start"])
    tmp = EPISODES + ".tmp"
    with open(tmp, "w") as f:
        for e in allx:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(tmp, EPISODES)
    return len(new)


def copy_from_robot(host):
    """rsync appends new bytes of the brain logs and their meta files (nice 19, idle IO on the A7Z)."""
    os.makedirs(RAW, exist_ok=True)
    reach = subprocess.run(["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", host, "true"],
                           capture_output=True, text=True, timeout=30)
    if reach.returncode != 0:
        return "offline", (reach.stderr.strip().splitlines() or ["unreachable"])[-1]
    p = subprocess.run(["rsync", "-a", "--append-verify", "-z", "--timeout=60", "--rsync-path=nice -n 19 ionice -c3 rsync",
                        f"{host}:duck-logs/duck_wired_log_*.jsonl", RAW + "/"], capture_output=True, text=True, timeout=1800)
    if p.returncode not in (0, 24):  # 24: a file vanished during the copy
        return "error", f"rsync exit {p.returncode}: {p.stderr.strip()[-300:]}"
    return "ok", None


def settled_logs(state):
    """Logs whose size has not changed for SETTLE_S and that were not cut at this size."""
    now, out = time.time(), []
    for p in sorted(glob.glob(os.path.join(RAW, "duck_wired_log_*.jsonl"))):
        if p.endswith(".meta.jsonl"):
            continue
        st = os.stat(p)
        if now - st.st_mtime >= SETTLE_S and state.get(os.path.basename(p)) != st.st_size:
            out.append(p)
    return out


def feed_scorecard():
    """Replay new replayable actions in the sim (scorecard.py auto); returns its summary line or an error."""
    p = subprocess.run([sys.executable, os.path.join(SCORE_DIR, "scorecard.py"), "auto", "--episodes", EPISODES,
                        "--data", DATA, "--jobs", "4"], capture_output=True, text=True, timeout=3600)
    if p.returncode != 0:
        raise RuntimeError(f"scorecard auto exit {p.returncode}: {p.stderr.strip()[-400:]}")
    return (p.stdout.strip().splitlines() or [""])[-1]


def changes():
    """Brain, policy and decision changes by date, for the markers on the page (robotics git history)."""
    paths = ["microduck-sim/guide/firmware/mac/walk_wired.py", "microduck-sim/guide/firmware/mac/walk_brain.py",
             "microduck-sim/guide/firmware/mac/approach.py", "microduck-sim/guide/firmware/mac/seepick.py",
             "microduck-sim/hardware-design-20260912/whole-robot-20260912/runtime-overlay", "DECISIONS.md"]
    repo = os.path.abspath(os.path.join(ROOT, ".."))
    p = subprocess.run(["git", "-C", repo, "log", "--since=2026-10-01", "--date=short", "--format=%ad\t%h\t%s", "--"] + paths,
                       capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip():  # the Mac mini copy has no git: run_ledger_deploy.sh ships the list
        cp = os.path.join(HERE, "run-ledger-changes.json")
        return json.load(open(cp)) if os.path.exists(cp) else []
    out = []
    for line in p.stdout.splitlines():
        d, h, s = line.split("\t", 2)
        out.append(dict(day=d, commit=h, subject=s[:140]))
    return out


def page(health):
    eps = load_jsonl(EPISODES)
    card = {}
    cp = os.path.join(DATA, "scorecard-auto.json")
    if os.path.exists(cp):
        card = json.load(open(cp))
    by = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for e in eps:
        if e["outcome"] != "started_fallen":
            by[e["kind"]][e["day"]][e["outcome"]] += 1
    days = sorted({e["day"] for e in eps})
    ch = changes()
    ch_by_day = collections.defaultdict(list)
    for c in ch:
        ch_by_day[c["day"]].append(c)
    def esc(x):
        return html.escape('' if x is None else str(x))
    parts = []
    for k in ("walk", "turn", "balance", "stand", "bend", "pick", "getup", "sit", "kick"):
        if k not in by:
            continue
        rows = []
        for d in days:
            c = by[k].get(d)
            if not c:
                continue
            n = sum(c.values())
            ok = c.get("ok", 0)
            fails = ", ".join(f"{o} {c[o]}" for o in ("fell", "guard", "incomplete") if c.get(o))
            pct = round(100 * ok / n)
            nch = len(ch_by_day.get(d, []))
            mark = f'<span class="chg">当天改动 {nch} 项</span>' if nch else ""
            rows.append(f'<div class="row"><span class="d">{d}</span><span class="bar"><i style="width:{pct}%"></i></span>'
                        f'<span class="n">{ok}/{n} ok{(" · " + fails) if fails else ""}</span>{mark}</div>')
        parts.append(f'<section><h2>{k}</h2>{"".join(rows)}</section>')
    recent = [e for e in eps if e["outcome"] in ("fell", "guard", "incomplete")][-15:]
    fail_list = "".join(f'<li>{esc(e["when"])} {esc(e["kind"])}: <b>{esc(e["outcome"])}</b> {esc(e.get("detail") or "")} '
                        f'<code>{esc(e["id"])}</code></li>' for e in reversed(recent)) or "<li>none</li>"
    sc = card.get("summary", "no replays yet")
    first = days[0] if days else "9999"
    timeline = "".join(f'<li>{esc(c["day"])} <code>{esc(c["commit"])}</code> {esc(c["subject"])}</li>'
                       for c in ch if c["day"] >= first) or "<li>none</li>"
    h = health
    doc = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MicroDuck 动作记录</title><style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--ok:#2f7d4f;--bad:#b3412e;--line:#e4e1da}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 -apple-system,system-ui,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:16px}} h1{{font-size:22px;margin:4px 0 8px}} h2{{font-size:17px;margin:18px 0 6px}}
.card{{border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin:10px 0;background:#fff}}
.row{{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;padding:4px 0;border-bottom:1px solid var(--line)}}
.d{{width:92px;color:var(--mut)}} .bar{{flex:1 1 120px;height:10px;background:#f1d9d3;border-radius:5px;overflow:hidden}}
.bar i{{display:block;height:100%;background:var(--ok)}} .n{{min-width:120px}}
.chg{{font-size:13px;color:#7a5b12}} .tl li{{font-size:14px}}
code{{font-size:12px;overflow-wrap:anywhere}} .bad{{color:var(--bad)}} li{{margin:4px 0;overflow-wrap:anywhere}}
</style></head><body><main>
<h1>MicroDuck 动作记录</h1>
<div class="card">每次开机后的每个动作都从大脑日志自动切出：结果（ok 成功 / fell 摔倒 / guard 保护停机 / incomplete 未完成）、指令、策略、轨迹。
共 {len(eps)} 个动作，{len(days)} 天。</div>
<div class="card"><b>采集状态</b>：最近一次 {esc(h.get("when", "-"))}，{esc(h.get("status", "-"))}{(" · " + esc(h["error"])) if h.get("error") else ""}；
连续失败 <span class="{"bad" if h.get("consecutive_failures") else ""}">{h.get("consecutive_failures", 0)}</span> 次；
上次成功 {esc(h.get("last_ok", "-"))}；上次新增动作 {h.get("last_new", 0)} 个。</div>
<div class="card"><b>仿真回放记分卡</b>（同指令在仿真里重放，结果是否一致）：{esc(sc)}</div>
<h2>按动作和日期的成功率</h2><p style="color:var(--mut);font-size:14px">黄色行是当天对大脑、策略或决策的改动（git 提交）。</p>
{"".join(parts) or "<p>还没有动作。</p>"}
<h2>改动时间线（大脑、策略、协调脚本、决策）</h2><ul class="tl">{timeline}</ul>
<h2>最近的失败</h2><ul>{fail_list}</ul>
<p style="color:var(--mut);font-size:13px">生成于 {time.strftime("%Y-%m-%d %H:%M")}，来源 guide/firmware/mac/run_ledger.py。</p>
</main></body></html>"""
    os.makedirs(os.path.dirname(PAGE), exist_ok=True)
    tmp = PAGE + ".tmp"
    open(tmp, "w").write(doc)
    os.replace(tmp, PAGE)


def tick(host):
    os.makedirs(DATA, exist_ok=True)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    rec = dict(ts=round(time.time(), 1), when=time.strftime("%Y-%m-%d %H:%M:%S"), host=host)
    try:
        status, err = copy_from_robot(host)
        rec.update(copy=status, copy_error=err)
        logs = settled_logs(state)
        n = cut(logs) if logs else 0
        for p in logs:
            state[os.path.basename(p)] = os.path.getsize(p)
        json.dump(state, open(STATE, "w"))
        rec.update(logs_cut=len(logs), actions=n)
        rec["scorecard"] = feed_scorecard() if n else None
        rec["status"] = "error" if status == "error" else ("robot offline" if status == "offline" else "ok")
        rec["error"] = err if status == "error" else None
    except Exception as e:  # noqa: BLE001
        rec.update(status="error", error=repr(e)[-400:])
    prev = load_jsonl(RUNS)
    fails = 0
    for r in reversed(prev):
        if r.get("status") != "error":
            break
        fails += 1
    rec["consecutive_failures"] = fails + 1 if rec["status"] == "error" else 0
    with open(RUNS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    last_ok = next((r["when"] for r in reversed(prev + [rec]) if r.get("status") != "error"), None)
    try:
        page(dict(when=rec["when"], status=rec["status"], error=rec.get("error"), last_ok=last_ok,
                  consecutive_failures=rec["consecutive_failures"], last_new=rec.get("actions", 0)))
    except Exception as e:  # noqa: BLE001
        rec2 = dict(rec, status="error", error=f"page: {e!r}"[-400:])
        with open(RUNS, "a") as f:
            f.write(json.dumps(rec2, ensure_ascii=False) + "\n")
        print(json.dumps(rec2, ensure_ascii=False))
        return 1
    print(json.dumps(rec, ensure_ascii=False))
    return 1 if rec["status"] == "error" else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tick"); t.add_argument("--host", default=os.environ.get("A7Z_HOST", "a7z"))
    c = sub.add_parser("cut"); c.add_argument("logs", nargs="+")
    sub.add_parser("page")
    sub.add_parser("changes")
    a = ap.parse_args()
    if a.cmd == "changes":  # run_ledger_deploy.sh: the change list for a copy without git
        json.dump(changes(), open(os.path.join(HERE, "run-ledger-changes.json"), "w"), indent=0, ensure_ascii=False)
        return
    if a.cmd == "tick":
        sys.exit(tick(a.host))
    if a.cmd == "cut":
        print(f"{cut(a.logs)} actions")
    runs = load_jsonl(RUNS)
    last = runs[-1] if runs else {}
    page(dict(when=last.get("when"), status=last.get("status"), error=last.get("error"),
              consecutive_failures=last.get("consecutive_failures", 0), last_new=last.get("actions", 0)))


if __name__ == "__main__":
    main()

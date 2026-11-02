"""T2 on the robot with a ball placed by hand: look down, show where the ball is, wait for Enter, run the picture pick.

The robot must stand under the walking policy (walk mode at zero command). The head looks down (--pitch), every frame
goes through orange_target (the same detector as gaze.py, on the A7Z), and after Enter the box of the ball goes to
walk_wired as {"mode": "seepick", "object": {"u", "v", "w", "t", "seen"}}, which selects seepickpix61.onnx for the whole
pick (walk_brain.seepickpix_body). t stays at the capture time of the last real detection and seen is false on a frame
without one, so the policy reads the age as in training (T2-PIXEL.md). walk_wired drives the jaw and hands back to
walk mode at phase 0.9; this script only feeds the box and reads the result.

  ssh -t a7z '~/.venvs/duck-policy/bin/python ~/rt/microduck-sim/guide/firmware/mac/t2pick.py'
  python3 -m pytest -q test_t2pick.py     the feed on a fake robot

Ctrl-C before Enter hands the head back; nothing else is sent. Trace: ~/duck-logs/t2pick_<time>.jsonl.

Every writer of the control file holds the driver lease (microduck-simulator/desktop/duck-command.py): this script refuses
to start while a page or session holds it, and stops writing the moment a page's stop takes it over. It also never
rewrites the pick around the hand-back (seepick.py's 0.85 phase) or over a command the brain itself wrote (a guard trip):
a late write would start a second pick.
"""
import argparse
import contextlib
import fcntl
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gaze import DEFAULT_HEAD, H, MIN_AREA, OPEN_PX, W, track_of  # noqa: E402

LOOK_PITCH = 1.35        # gaze.PITCH_RANGE top: the lowest look the servo reaches (about 1.3)
GATE_PX = 150.0          # a blob further than this from the last box in one frame is something else (the duck's own parts)
CMD_PERIOD_S = 0.1       # the command is rewritten at least this often during the pick
SEEN_S = 0.5             # the ball must have been detected this recently for Enter to start the pick
PICK_TIMEOUT_S = 12.0    # 4.5 s at full rate; read drops stretch the phase clock
T2_WINDOW_R, T2_WINDOW_DEG = (0.057, 0.117), 19.8   # the +-3 cm polar window T2 reached (T2-PIXEL.md)
NO_REWRITE_PHASE = 0.85  # seepick.py: never rewrite the pick command around the hand-back at 0.9
LEASE_ID, LEASE_NAME = "t2pick", "T2 捡球"
LEASE_IDLE_S = 20.0      # duck-command.py IDLE_S
LEASE_RENEW_S = 2.0


class Lease:
    """duck-command.py's driver lease, same file, lock and monotonic clock."""

    def __init__(self, cmd_path, clock=time.monotonic):
        self.path, self.clock, self.renewed = cmd_path + ".driver", clock, -1e9

    @contextlib.contextmanager
    def _lock(self):
        with open(self.path + ".lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def holder(self):
        try:
            with open(self.path) as f:
                d = json.load(f)
        except (OSError, ValueError):
            return None
        return d if 0 <= self.clock() - d["last"] <= LEASE_IDLE_S else None

    def _write(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"id": LEASE_ID, "name": LEASE_NAME, "last": self.clock()}, f)
        os.replace(tmp, self.path)
        self.renewed = self.clock()

    def take(self):
        """None when taken, else the other holder's name."""
        with self._lock():
            d = self.holder()
            if d and d["id"] != LEASE_ID:
                return d["name"]
            self._write()
        return None

    def keep(self):
        """False when someone else took it over (a page's stop always can); renews it otherwise."""
        with self._lock():
            d = self.holder()
            if d and d["id"] != LEASE_ID:
                return False
            if self.clock() - self.renewed >= LEASE_RENEW_S:
                self._write()
        return True

    def release(self):
        with self._lock():
            d = self.holder()
            if d and d["id"] == LEASE_ID:
                os.remove(self.path)


class PixFeed:
    """Frame -> the box the policy reads. The last real detection is kept through blanks and false blobs."""

    def __init__(self, detect):
        self.detect, self.last, self.seen, self.rejected = detect, None, False, 0

    def update(self, frame, t_cap):
        tr = track_of(self.detect(frame))
        if tr is not None and self.last is not None and math.hypot(tr["u"] - self.last["u"], tr["v"] - self.last["v"]) > GATE_PX:
            self.rejected += 1
            tr = None
        self.seen = tr is not None
        if tr is not None:
            self.last = {"u": round(tr["u"], 2), "v": round(tr["v"], 2), "w": round(tr["w"], 2), "t": round(t_cap, 4)}
        return self.object()

    def object(self):
        return None if self.last is None else dict(self.last, seen=self.seen)


def pick_command(obj):
    return {"mode": "seepick", "object": obj}


def run_pick(feed, cam, tail, send, current, keep, now=time.time, sleep=time.sleep, timeout=PICK_TIMEOUT_S):
    """Feed the box until the brain has left seepick after entering it. Returns (rows, why). current() reads the control
    file, keep() is the driver lease."""
    rows, idx, t0, sent_t, entered = [], None, now(), -1.0, False
    send(pick_command(feed.object()))
    while now() - t0 < timeout:
        if not keep():
            return rows, "another driver took over (a stop on the page): stopped writing"
        st = tail.latest()
        if st is not None and st["mode"] == "seepick":
            entered = True
        elif st is not None and entered:
            return rows, f"brain left seepick for {st['mode']}"
        fr = cam.latest()
        new = fr is not None and fr[2] != idx
        if new:
            idx = fr[2]
            obj = feed.update(fr[0], fr[1])
            rows.append(dict(t=round(now(), 3), t_cap=round(fr[1], 3), frame=idx, obj=obj, mode=None if st is None else st["mode"]))
        if entered and (new or now() - sent_t >= CMD_PERIOD_S) and (st.get("sp_phase") or 0.0) < NO_REWRITE_PHASE:
            cmd = current()
            if not cmd or cmd.get("mode") != "seepick":   # the brain or a stop wrote it: the pick is over, never restart it
                return rows, f"the control file now says {cmd}: stopped writing"
            send(pick_command(feed.object()))
            sent_t = now()
        sleep(0.005)
    return rows, f"no hand-back in {timeout:.0f} s" if entered else "the brain never entered seepick (refused: see its .out)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cmd", default="/tmp/duck_cmd.json")
    ap.add_argument("--pitch", type=float, default=LOOK_PITCH)
    ap.add_argument("--yaw", type=float, default=0.0)
    ap.add_argument("--hsv-lo", default="170,50,150", help="gaze.py's home range")
    ap.add_argument("--hsv-hi", default="18,255,255")
    args = ap.parse_args()
    import select

    import orange_target
    from approach import LogTail, ShmCamera, find_log, send_file
    from duck_kin import DuckKin
    lease = Lease(args.cmd)
    other = lease.take()
    if other:
        sys.exit(f"{other} 正在控制机器人（驾驶权锁），等它结束再跑")
    log_path = find_log()
    if not log_path:
        sys.exit("no walk_wired log found: is walk_wired.py running with --log?")
    kin, tail, cam, send = DuckKin(), LogTail(log_path), ShmCamera(), send_file(args.cmd)
    lo, hi = tuple(int(v) for v in args.hsv_lo.split(",")), tuple(int(v) for v in args.hsv_hi.split(","))
    feed = PixFeed(lambda f: orange_target.detect(f, lo, hi, MIN_AREA, open_px=OPEN_PX))
    time.sleep(0.2)
    st = tail.latest()
    if st is None or st["mode"] != "walk":
        sys.exit(f"the brain is in mode {None if st is None else st['mode']}: stand it under the walking policy first")
    head = {"head_pitch": args.pitch, "head_yaw": args.yaw}

    def current():
        try:
            with open(args.cmd) as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    send({"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0, "head": head})
    print("把球放在脚前 6-12 cm、正前方。看到“可以开始”后按 Enter 开始捡；Ctrl-C 退出。", flush=True)
    idx, shown, go, seen_t = None, 0.0, False, -1.0
    try:
        while not go:
            if not lease.keep():
                cam.close()
                sys.exit("别的页面接管了驾驶权，退出，什么都没发")
            fr = cam.latest()
            if fr is not None and fr[2] != idx:
                idx = fr[2]
                # no gate while looking: the hand moves the ball and the box must follow it
                feed.last = None
                obj = feed.update(fr[0], fr[1])
                seen_t = time.time() if obj else seen_t
            if time.time() - shown >= 0.5:
                shown = time.time()
                st = tail.latest()
                obj = feed.object()
                if obj is None or time.time() - seen_t > SEEN_S:
                    print("看不到球（画面下沿大约在脚前 10-12 cm，球可能太近）", flush=True)
                else:
                    g = kin.pixel_to_ground(obj["u"], obj["v"], st["q"], st["gb"], W, H) if st else None
                    if g is None:
                        print(f"球框 u {obj['u']:.0f} v {obj['v']:.0f} 宽 {obj['w']:.0f} px", flush=True)
                    else:
                        r, b = math.hypot(g[0], g[1]), math.degrees(math.atan2(g[1], g[0]))
                        ok = T2_WINDOW_R[0] <= r <= T2_WINDOW_R[1] and abs(b) <= T2_WINDOW_DEG
                        print(f"球框 u {obj['u']:.0f} v {obj['v']:.0f} 宽 {obj['w']:.0f} px，约 {r * 100:.1f} cm，方向 {b:+.0f} 度："
                              + ("可以开始" if ok else "不在范围内，也可以开始，但成功率低"), flush=True)
            if select.select([sys.stdin], [], [], 0.01)[0]:
                sys.stdin.readline()
                if feed.object() is not None and time.time() - seen_t <= SEEN_S:
                    go = True
                else:
                    print("现在没看到球，先摆好再按 Enter", flush=True)
    except KeyboardInterrupt:
        send({"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0,
              "head": {"head_pitch": DEFAULT_HEAD["head_pitch"], "head_yaw": 0.0}})
        cam.close()
        lease.release()
        print("已退出，头回到默认位置", flush=True)
        return
    t_go = time.time()
    rows, why = run_pick(feed, cam, tail, send, current, lease.keep)
    lease.release()
    time.sleep(0.5)
    tail.poll()
    last = tail.rows[-1] if tail.rows else None
    cam.close()
    trace = os.path.expanduser(f"~/duck-logs/t2pick_{time.strftime('%m%d-%H%M%S')}.jsonl")
    with open(trace, "w") as f:
        f.write(json.dumps(dict(t_go=round(t_go, 3), why=why, log=log_path, rejected=feed.rejected,
                                frames=len(rows), frames_seen=sum(bool(r["obj"] and r["obj"]["seen"]) for r in rows))) + "\n")
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"结束：{why}；{len(rows)} 帧，看到球 {sum(bool(r['obj'] and r['obj']['seen']) for r in rows)} 帧。"
          f"模式 {None if last is None else last['mode']}。记录 {trace}", flush=True)


if __name__ == "__main__":
    main()

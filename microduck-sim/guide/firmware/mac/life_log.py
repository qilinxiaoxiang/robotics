"""The duck's everyday listening record: whatever the microphones hear around voices, names and answers, kept so the
name spotter can keep learning from ordinary life without anyone recording sessions for it (Shawn 2026-10-30: a real
pet learns its name in daily life; a solution a real owner would not do must not be asked of him).

namecall.py feeds every 20 ms block (t, (n, 4) float at 48 kHz) and the spotter's newest P(mochi). LifeLog keeps the
last PRE_S of the three microphones (ch0 left ear, ch1 right ear, ch2 back mic) at 16 kHz and opens a segment when
  - the voice band (300-3000 Hz) rises VOICE_DB over its tracked floor (someone speaks, steps, touches),
  - the spotter's P(mochi) reaches SCORE_TRIGGER,
  - namecall notes an event (an answer, a quack), or
  - SAMPLE_EVERY_S passed since the last sample (SAMPLE_S of ordinary background, whatever it holds).
A segment runs until POST_S after its last trigger (an answer's POST_S covers whether he calls again or touches the
head), at most MAX_SEG_S. Files: DIR/YYYYMMDD/HHMMSS_mmm.wav (16 kHz, 3 channels, int16) and one line per segment in
DIR/life_index.jsonl (file, t0, t1, triggers, spotter scores every 100 ms, notes). Writing stops (logged once) when
DIR passes MAX_GB or the disk has under MIN_FREE_GB free; mine_life.py on the Mac mini pulls and labels the segments.
"""
import json
import os
import shutil
import time
import wave

import numpy as np

FS16 = 16000
PRE_S = 4.0
POST_S = 8.0
MAX_SEG_S = 60.0
VOICE_DB = 8.0
SCORE_TRIGGER = 0.2
SAMPLE_EVERY_S = 300.0
SAMPLE_S = 10.0
MAX_GB = 8.0
MIN_FREE_GB = 2.0
MICS = (0, 1, 2)


def _dir_bytes(path):
    n = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                n += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return n


class LifeLog:
    def __init__(self, out_dir, make_decimator, pre_s=PRE_S, post_s=POST_S, max_seg_s=MAX_SEG_S, voice_db=VOICE_DB,
                 score_trigger=SCORE_TRIGGER, sample_every_s=SAMPLE_EVERY_S, sample_s=SAMPLE_S, max_gb=MAX_GB,
                 min_free_gb=MIN_FREE_GB, on_stop=None):
        self.dir = os.path.expanduser(out_dir)
        os.makedirs(self.dir, exist_ok=True)
        self.decs = [make_decimator() for _ in MICS]
        self.pre_s, self.post_s, self.max_seg_s = pre_s, post_s, max_seg_s
        self.voice_db, self.score_trigger = voice_db, score_trigger
        self.sample_every_s, self.sample_s = sample_every_s, sample_s
        self.max_bytes, self.min_free = max_gb * 1e9, min_free_gb * 1e9
        self.on_stop = on_stop
        self.ring = []                    # [(t, int16 (n, 3))], newest last, about pre_s long
        self.ring_n = 0
        self.floor = None
        self.seg = None                   # dict(w=wave, path, t0, until, triggers, scores, notes)
        self.next_sample = None
        self.stopped = None
        self.used = _dir_bytes(self.dir)
        self.segments = 0
        self.n_blocks = 0

    # ---------------------------------------------------------------- input
    def feed(self, t, block, score=None):
        if self.stopped:
            return
        x = np.stack([d(block[:, c]) for d, c in zip(self.decs, MICS)], axis=1)
        pcm = np.clip(x * 32767.0, -32768, 32767).astype("<i2")
        self.n_blocks += 1
        if self.next_sample is None:
            self.next_sample = t + self.sample_every_s
        why = []
        lv = self._voice_db(x.mean(axis=1))
        if self.floor is None:
            self.floor = lv
        if lv > self.floor + self.voice_db:
            why.append("voice")
        self.floor = self.floor + (0.002 if lv > self.floor else 0.05) * (lv - self.floor)   # slow up, fast down
        if score is not None and score >= self.score_trigger:
            why.append("score")
        if t >= self.next_sample:
            self.next_sample = t + self.sample_every_s
            why.append("sample")
        if why:
            self._trigger(t, why, post=self.sample_s if why == ["sample"] else self.post_s)
        if self.seg is not None:
            self.seg["w"].writeframes(pcm.tobytes())
            self.seg["n"] += len(pcm)
            if self.n_blocks % 5 == 0 and score is not None:
                self.seg["scores"].append([round(t - self.seg["t0"], 2), round(float(score), 3)])
            if t >= self.seg["until"] or self.seg["n"] / FS16 >= self.max_seg_s:
                self._close(t)
        else:
            self.ring.append((t, pcm))
            self.ring_n += len(pcm)
            while self.ring and self.ring_n - len(self.ring[0][1]) >= self.pre_s * FS16:
                self.ring_n -= len(self.ring.pop(0)[1])

    def note(self, t, kind, **rec):
        """An event of namecall's (answer, quack, skip): kept in the segment's index and keeps it open POST_S."""
        if self.stopped:
            return
        self._trigger(t, [kind], post=self.post_s)
        self.seg["notes"].append(dict(t=round(t - self.seg["t0"], 3), kind=kind, **rec))

    def close(self):
        if self.seg is not None:
            self._close(time.time())

    # ---------------------------------------------------------------- internals
    @staticmethod
    def _voice_db(y):
        spec = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2
        f = np.fft.rfftfreq(len(y), 1 / FS16)
        return 10 * np.log10(spec[(f >= 300) & (f <= 3000)].sum() + 1e-12)

    def _trigger(self, t, why, post):
        if self.seg is None:
            if not self._room():
                return
            t0 = self.ring[0][0] if self.ring else t
            day = time.strftime("%Y%m%d", time.localtime(t0))
            os.makedirs(os.path.join(self.dir, day), exist_ok=True)
            name = time.strftime("%H%M%S", time.localtime(t0)) + "_%03d.wav" % int((t0 % 1) * 1000)
            path = os.path.join(self.dir, day, name)
            w = wave.open(path, "wb")
            w.setnchannels(len(MICS))
            w.setsampwidth(2)
            w.setframerate(FS16)
            self.seg = dict(w=w, path=path, t0=t0, until=t + post, triggers=[], scores=[], notes=[], n=0)
            for _, pcm in self.ring:
                w.writeframes(pcm.tobytes())
                self.seg["n"] += len(pcm)
            self.ring, self.ring_n = [], 0
        self.seg["until"] = max(self.seg["until"], t + post)
        for w in why:
            if not self.seg["triggers"] or self.seg["triggers"][-1][1] != w or t - self.seg["t0"] - self.seg["triggers"][-1][0] > 1.0:
                self.seg["triggers"].append([round(t - self.seg["t0"], 2), w])

    def _close(self, t):
        s, self.seg = self.seg, None
        s["w"].close()
        size = os.path.getsize(s["path"])
        self.used += size
        self.segments += 1
        rec = dict(file=os.path.relpath(s["path"], self.dir), t0=round(s["t0"], 3), dur_s=round(s["n"] / FS16, 2),
                   mics=list(MICS), triggers=s["triggers"], scores=s["scores"], notes=s["notes"], bytes=size)
        with open(os.path.join(self.dir, "life_index.jsonl"), "a") as f:
            f.write(json.dumps(rec) + "\n")

    def _room(self):
        free = shutil.disk_usage(self.dir).free
        if self.used >= self.max_bytes or free < self.min_free:
            self.stopped = dict(why="life log full" if self.used >= self.max_bytes else "disk nearly full",
                                used_gb=round(self.used / 1e9, 2), free_gb=round(free / 1e9, 2))
            if self.on_stop:
                self.on_stop(self.stopped)
            return False
        return True

    def stats(self):
        return dict(segments=self.segments, used_mb=round(self.used / 1e6, 1), open=self.seg is not None,
                    stopped=self.stopped)

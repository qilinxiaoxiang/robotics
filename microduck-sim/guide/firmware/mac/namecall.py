"""Name call on the MicroDuck: the duck hears a call, turns its head to the sound with a pet/express take, and quacks
when the head arrives. First pet behaviour meant for the robot (register section 12, docs/PET_ROBOT_FEATURES.md).

    ~/.venvs/duck-policy/bin/python namecall.py [--name mochi | --any-voice] [--mute] [--no-head] [--once N]

Chain, all in this process, numpy only (no scipy on the A7Z):
  ears + back mic  ->  OnsetDetector  ->  Localiser (GCC-PHAT, SRP over 1 deg)  ->  HeadPath (pet.express take,
  EMA pre-inverse of walk_brain's HEAD_ALPHA)  ->  /tmp/duck_cmd.json {"mode": "walk", vx 0, "head": {...}} at 50 Hz
  -> stand61 balances while the head turns  ->  QuackBank plays a pitched duck call through duck_sound.Voice on arrival.

After the take the head does not drift home: the attention phase (NameCall._attend_tick) keeps the gaze on the caller
and waits ATTEND_S for whatever comes next (another call re-aims it, a touch is the brain's business). With the
camera (facefind.FaceFinder: a7z_cam's shared frame -> the SCRFD face detector of pet/identity, 4 Hz, 120 ms per frame
on the A7Z) a face in view is centred and followed; with none in view for FACE_WAIT_S the head sweeps SCAN_OFFSETS
once around the heard bearing, pitch at the cap, then waits where the sound came from. A caller behind the head's
reach: with --turn the body turns on the spot and stops on the brain's gyro (GyroTurn), not a clock, only when the
bearing's front/back margin is at least TURN_MARGIN_MIN and no face is in view; the attention phase then continues
with the head on the caller. The turn is off by default: on 2026-10-30 a turn started by a noise "behind" while
Shawn's face was locked in front tripped the duck on the table 2.3 s in (PET_ROBOT_LOG 2026-10-30).

Two trigger modes. --name mochi (the default since 2026-10-30; --any-voice for the listen-only checks and the
tests): a keyword spotter (KeywordGate: sherpa-onnx KeywordSpotter, the public zipformer
gigaspeech-3.3M int8 model in ~/rt/models/kws/, one thread) runs all the time on the two ears downmixed to 16 kHz with
the keywords file namecall-20261029/keywords_mochi.txt; only a spotted "Mochi" is a call. The onset detector keeps
running as a source of word starts: the direction is taken from the 4-channel ring buffer (3 s) at the detector onset
nearest the word's estimated start (KW_BACK_S before the spot), or at that estimate when the detector saw none. While
the duck's own quack plays the spotter is fed silence.

Sound in: the I2S0 card found by name (sndi2s0, its number changes between boots: duck_selfcheck.py), hw:CARD=sndi2s0,
4 channels S32_LE 48 kHz through `arecord -t raw` (CURRENT-STATE a7z_audio_capture): ch0 left ear, ch1 right ear, ch2
back mic, ch3 nothing. INMP441 samples are 24-bit left-justified (>> 8 as the self-check does). Microphone positions
come from the head CAD (guide/print/ears-mouth-20261023/interface.json, the 2026-10-24 three-mic report): ears at
x 60.5, y +-38.5; back mic at x -19.9, y -11 (head frame, mm, x forward, y left). --swap-ears when a tap on the left
ear raises ch1 instead of ch0.

Sound in and out share the I2S0 card, and on this driver the START of a playback stream silences a running capture
for good (2026-10-30 home test: arecord level -50 dBFS, aplay starts, -150 dBFS within 0.5 s until arecord is
reopened). So the program opens a silent playback stream on the ALSA default device (dmix) before the capture and
keeps it open (PlaybackKeepAlive, --no-keepalive to skip): the quacks then mix into the already running stream, the
microphones stay live through them and are back at the room floor half a second after the quack ends, and the capture
starts without its 1.5 s settling ramp.

Detector (--detector bins, the default since the 2 m recordings of 2026-10-29): per 20 ms block, how many 300-4000 Hz
bins of the three-microphone mix stand --snr-db over a tracked noise spectrum; an onset is --min-bins such bins after
a quiet block, confirmed by --confirm-blocks of the next three blocks and by the harmonicity of its first 60-80 ms
(--voicing: footsteps and touches are not periodic), then a refractory period. --detector energy is the earlier
band-energy detector (12 dB over a floor, OnsetDetector). Both are deaf while the own quack plays and for a moment
after (the mics are 10 cm from the speaker). Direction (--localiser call, the default): SRP-PHAT over the whole call
(--call-window 0.8 s after the onset) on the time-frequency bins that stand over the noise spectrum on all three
microphones, in --loc-band (1500-8000 Hz: under 1.5 kHz this head hears through its cavity, NAMECALL.md 10), steered
over azimuth x elevation (--elev, prior 35 deg for a standing owner; several values search); the back mic settles
front/back. --localiser short is the earlier 64 ms GCC-PHAT at the onset. The look-up pitch is fixed (--pitch).

Robot safety: this program never touches the servo bus or the IMU, so it never takes the robot I/O lock
(walk_wired.HW_LOCK); it probes it and refuses to run when nobody holds it (no brain). It refuses to run unless the
brain's newest tick log (~/duck-logs/duck_wired_log_*.jsonl, a line younger than 1.5 s) shows walk or stand mode at zero
velocity; from stand mode it writes the zero-command walk first (stand61) and waits for the log to show walk. While a
take runs it rewrites the control file at 50 Hz only when the file still holds its own last command or a plain
zero-command walk; any other writer (the app, Shawn) wins at once and the take stops where it is. A brain that leaves
walk mode (a guard trip, a stop) or a stale log ends the program. Head targets are the take's own outputs, which
pet/express/cards/duck.json limits inside walk_brain.HEAD_RANGE; the look target itself is capped at +-YAW_CAP rad,
so a call from behind turns the head as far as it goes on that side. Ctrl-C writes one last zero-command walk with the
head at the policy default and exits; the brain keeps balancing.

Log: one JSON line per event in --log (default ~/duck-logs/namecall_<start>.jsonl): detections (energy, floor, azimuth,
per-pair delays, front/back margin), takes (name, parameters, call events), control-file writes per take, refusals,
and a heartbeat every 10 s (floor, blocks, capture gaps, CPU share).

Off the robot: --wav FILE replays a 4-channel recording through the same detector and localiser (--no-head --mute
prints what it hears); namecall-20261029/namecall_sim.py runs the whole chain against the duck sim.
"""
import argparse
import collections
import fcntl
import glob
import json
import math
import os
import queue
import subprocess
import sys
import threading
import time
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))   # .../robotics (or ~/rt on the A7Z)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
from duck_sound import Voice  # noqa: E402
from pet.express import Affect, Expressor, Target, acknowledge, content_idle  # noqa: E402
from pet.express.channels import load_card  # noqa: E402
from pet.express.duck import HEAD_ALPHA, HEAD_JOINTS, HEAD_RANGE, want_head  # noqa: E402
from pet.express.voice import CallPicker, find_calls, read_wav, render_call, write_wav  # noqa: E402

FS = 48000
BLOCK = 960                      # 20 ms, the brain's tick
C_SOUND = 343.0
CARD_NAME = "sndi2s0"            # the I2S0 card, found by name (duck_selfcheck.py)
HW_LOCK = "/tmp/duck-hw.lock"    # walk_wired.HW_LOCK; probed, never taken
CMD_FILE = "/tmp/duck_cmd.json"
BRAIN_LOGS = os.path.expanduser("~/duck-logs/duck_wired_log_*.jsonl")
CARD = os.path.join(ROOT, "pet", "express", "cards", "duck.json")
MODELS = os.path.join(ROOT, "microduck-sim", "hardware-design-20260912", "whole-robot-20260912", "runtime-overlay", "models")
WALK_ZERO = {"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0}
ZERO_KEYS = {"mode", "vx", "vy", "vtheta", "head", "for_s"}
# head frame (x forward, y left, mm): interface.json ears, V1.33 back seat (three-mic report section 4)
MICS_MM = {"left": (60.5, 38.5), "right": (60.5, -38.5), "back": (-19.9, -11.0)}
CHANNELS = {"left": 0, "right": 1, "back": 2}
BAND = (300.0, 4000.0)
YAW_CAP = 1.2                    # rad; the card's head_yaw limit is 1.4 = HEAD_RANGE, this leaves the pre-inverse room
# gaze pitch for the caller, rad up in pet/express units. The duck card maps it 1:1 onto a head_pitch delta (minus,
# since head_pitch + looks down on this robot: approach.py HEAD_PITCH_WALK), so 1.1 = the HEAD_RANGE pitch cap =
# head_pitch -0.75 absolute under stand61, the camera 30 deg above the horizontal (face-view-20261029/README.md): a
# standing adult's face is in frame from 1.0-2.2 m. A caller is a person above the duck; the microphones cannot
# measure elevation (all three lie in one horizontal plane), so the duck always looks up to a face.
LOOK_PITCH = 1.1
KEEPALIVE_CMD = ("aplay", "-q", "-t", "raw", "-f", "S16_LE", "-c", "2", "-r", "48000", "/dev/zero")
# policy default head pose (stand61.onnx metadata default_joint_pos; read from the model when it is there)
DEFAULT_HEAD = {"neck_pitch": 0.349, "head_pitch": 0.349, "head_yaw": 0.0, "head_roll": 0.0}
BRAIN_FRESH_S = 1.5
QUACK_DEAF_S = 0.6               # the detector stays deaf this long after the player ends
QUACK_ALWAYS_OFF_S = 0.35        # a take the library planned silent still answers a call: one quack this long after arrival
# ... unless the caller is really repeating: the library's novelty drops x0.75 per call and recovers with a 40 s time
# constant (pet/express/takes.py Habituation); below this novelty the answer is the head alone (Shawn 2026-10-30:
# skip the call only when he has repeated it over and over). 0.3 = the fifth call inside about 15 s; one call every
# 30 s or more is always answered.
QUACK_NOVELTY_MIN = 0.3
# body turn toward a caller the head cannot reach (|az| > YAW_CAP): the robot-tested turn on the spot, walk61 at
# vtheta +-0.3 (pet/mind/runner.py, survey 2026-10-30: 7-13 deg/s on the floor), after the head take has drifted home
TURN_VTHETA = 0.3
# rad/s assumed for planning the time cap only: the turn itself stops on the body gyro integrated from the brain's tick
# log (2026-10-30 home floor: 0.4 rad/s at vtheta 0.3, a 12 s timed turn went 273 deg; 7-13 deg/s on the 10/30 survey)
TURN_RATE = 0.17
TURN_KEEP = 0.3                  # rad of the caller's bearing left for the head when the body stops turning
TURN_S = (1.5, 12.0)             # turn duration bounds (the cap when the gyro is not readable)
TURN_MARGIN_MIN = 0.3            # no body turn on a bearing whose front/back margin is below this (2026-10-30: three
#                                  noise-level triggers with margin 0.0-0.013 each started a 7-12 s turn)
# attention after the take: the head stays on the caller (not the drift home) and waits for whatever comes next
ATTEND_S = 10.0                  # s since the last call or face sighting; then the head drifts home
FACE_GAIN = 0.6                  # fraction of the measured face offset corrected per new frame
FACE_WAIT_S = 1.0                # s without a face (after the take arrives, or since the last sighting) before the scan
FACE_PITCH = (-0.3, 1.1)         # gaze pitch range while tracking a face (express rad up; 1.1 = the head pitch cap)
SCAN_OFFSETS = (0.0, 0.4, -0.4, 0.8, -0.8, 1.2, -1.2)   # yaw sweep around the heard bearing when no face is in view
SCAN_NEAR = (0.0, 0.3, -0.3)     # sweep around the last seen face when it is lost
SCAN_DWELL_S = 0.7               # s per scan step (the brain's head EMA and the detector's 4 Hz both settle in this)

# name mode (--name): keyword spotter
KWS_FS = 16000
KWS_MODEL_NAME = "sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01"
KWS_MODEL_DIRS = (os.environ.get("NAMECALL_KWS_MODEL", ""), os.path.expanduser(os.path.join("~/rt/models/kws", KWS_MODEL_NAME)))
KEYWORDS = {"mochi": os.path.join(HERE, "namecall-20261029", "keywords_mochi.txt")}
RING_NAME_S = 3.0                # ring buffer in name mode: the spot comes up to about a second after the word starts
KW_BACK_S = 0.75                 # aim point for the onset pick; 1.0 (the median spot delay) chose earlier sounds more often (NAMECALL.md 9.4)
KW_ONSET_WIN = (0.25, 1.6)       # detector onsets between these many seconds before the spot are candidates
ONSET_GAP_S = 0.25               # detector refractory in name mode (its onsets are only candidates)


# ----------------------------------------------------------------------------------------------- sound sources

def i2s_to_float(raw, channels=4):
    """S32_LE INMP441 frames -> float32 (n, channels) in -1..1 (24-bit left-justified, as duck_selfcheck.py reads them)."""
    x = np.frombuffer(raw, "<i4")
    x = x[: len(x) - len(x) % channels].reshape(-1, channels) >> 8
    return x.astype(np.float32) / float(2 ** 23)


def find_card(name=CARD_NAME):
    """ALSA card number of the I2S0 card, or None."""
    p = os.path.realpath(f"/proc/asound/{name}")
    base = os.path.basename(p)
    return int(base[4:]) if base.startswith("card") and base[4:].isdigit() else None


class Capture:
    """arecord -> 20 ms float blocks on a queue, with the wall-clock time of each block's first sample."""

    def __init__(self, device, fs=FS, block=BLOCK, channels=4, cmd=None):
        self.fs, self.block, self.channels = fs, block, channels
        self.cmd = cmd or ["arecord", "-q", "-D", device, "-c", str(channels), "-r", str(fs), "-f", "S32_LE", "-t", "raw", "-"]
        self.q = queue.Queue(maxsize=200)
        self.proc = None
        self.gaps = 0        # blocks dropped because the consumer fell behind
        self.n = 0
        self.err = None

    def start(self):
        self.proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
        threading.Thread(target=self._pump, daemon=True).start()
        return self

    def _pump(self):
        need = self.block * self.channels * 4
        t0, per = None, self.block / self.fs
        while True:
            buf = b""
            while len(buf) < need:
                chunk = self.proc.stdout.read(need - len(buf))
                if not chunk:
                    self.err = (self.proc.stderr.read() or b"").decode(errors="replace").strip() or "arecord ended"
                    self.q.put(None)
                    return
                buf += chunk
            now = time.time()
            if t0 is None or abs(now - (t0 + self.n * per)) > 0.25:
                t0 = now - self.n * per   # resync the sample clock to the wall clock after a stall
            t_block = t0 + self.n * per
            self.n += 1
            try:
                self.q.put_nowait((t_block, i2s_to_float(buf, self.channels)))
            except queue.Full:
                self.gaps += 1

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.kill()


class PlaybackKeepAlive:
    """A silent playback stream on the ALSA default device (dmix), opened before the capture and kept open.

    The sunxi I2S driver behind sndi2s0 silences a running capture when a playback stream starts (module docstring);
    with this stream already running, the quacks mix into it and the microphones never notice them beyond the sound.
    """

    def __init__(self, cmd=KEEPALIVE_CMD, popen=subprocess.Popen):
        self.cmd, self.popen = list(cmd), popen
        self.proc = None
        self.err = None

    def start(self, settle_s=0.3):
        try:
            self.proc = self.popen(self.cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except Exception as e:  # no aplay: the program still runs, deaf after each quack as before
            self.err = repr(e)
            return self
        time.sleep(settle_s)   # the stream is running before arecord opens (no capture settling ramp then)
        if self.proc.poll() is not None:
            self.err = (self.proc.stderr.read() or b"").decode(errors="replace").strip() or f"exit {self.proc.returncode}"
            self.proc = None
        return self

    @property
    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.kill()
            try:
                self.proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass


class WavSource:
    """A recorded multichannel wav as 20 ms blocks (tests, --wav replay); block times start at 0."""

    def __init__(self, path, block=BLOCK, channels=None):
        with wave.open(path) as w:
            self.fs, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
            raw = w.readframes(w.getnframes())
        if sw == 4:
            x = (np.frombuffer(raw, "<i4").reshape(-1, ch) >> 8).astype(np.float32) / 2 ** 23
        elif sw == 2:
            x = np.frombuffer(raw, "<i2").reshape(-1, ch).astype(np.float32) / 2 ** 15
        else:
            raise ValueError(f"{path}: {sw * 8}-bit samples")
        self.x = x if channels is None else x[:, :channels]
        self.block = block

    def blocks(self):
        for i in range(0, len(self.x) - self.block + 1, self.block):
            yield i / self.fs, self.x[i:i + self.block]


# ----------------------------------------------------------------------------------------------- detector

SPAN = (100.0, 8000.0)           # the span the voice-band fraction is judged against (servo whine and hum outside BAND)


def band_energy_db(block, fs, band=BAND, window=None, span=SPAN):
    """(energy in band, energy in span) of a mono block in dB (re 1.0 full scale, per sample)."""
    n = len(block)
    w = np.hanning(n) if window is None else window
    X = np.fft.rfft(block * w)
    p = (X.real ** 2 + X.imag ** 2) / n
    f = np.fft.rfftfreq(n, 1 / fs)
    m = (f >= band[0]) & (f <= band[1])
    ms = (f >= span[0]) & (f <= span[1])
    eb, et = float(p[m].sum()), float(p[ms].sum())
    return 10 * math.log10(max(eb, 1e-14)), 10 * math.log10(max(et, 1e-14))


class OnsetDetector:
    """Voice-band energy onset over a tracked floor, confirmed by the next block, with a refractory period.

    update(t, block) -> None or {"t": onset time (s, the first loud block), "e_db", "floor_db", "rise_db"}.
    The floor follows the room noise with time constant floor_tau_s but only while nothing is loud, so a long call does
    not raise it. A sound counts when it is thresh_db over the floor, at least rise_db over the quietest of the previous
    five blocks (a swell is not a call), mostly in the voice band (band_frac of the 100-8000 Hz span: hum and servo
    whine fall outside), and the next block is still thresh_db - confirm_db over the floor (a click is not a call; a
    clap's tail is). deaf_until(t) silences it (own quack, own servos).
    """

    def __init__(self, fs=FS, block=BLOCK, band=BAND, thresh_db=12.0, rise_db=6.0, refractory_s=2.0,
                 floor_tau_s=3.0, band_frac=0.35, confirm_db=6.0, max_db=None):
        self.fs, self.block, self.band = fs, block, band
        self.thresh, self.rise, self.refractory = thresh_db, rise_db, refractory_s
        self.band_frac, self.confirm_db, self.max_db = band_frac, confirm_db, max_db
        self.alpha = block / fs / floor_tau_s
        self.window = np.hanning(block)
        self.floor = None
        self.hist = collections.deque(maxlen=5)
        self.pending = None
        self.last_onset = -1e9
        self.deaf_until = -1e9
        self.n = 0
        self.floor_settle = int(round(0.5 * fs / block))   # first 0.5 s: the floor is the median of what it hears

    def reset_floor(self):
        self.floor, self.n = None, 0
        self.hist.clear()
        self.pending = None

    def level(self, block):
        mono = block[:, :3].mean(axis=1) if block.ndim == 2 else block
        return band_energy_db(mono, self.fs, self.band, self.window)

    def update(self, t, block):
        e_db, tot_db = self.level(block)
        self.n += 1
        if self.floor is None or self.n <= self.floor_settle:
            self.hist.append(e_db)
            self.floor = float(np.median(self.hist))
            return None
        over = e_db - self.floor
        loud = over >= self.thresh
        if not loud:
            self.floor += self.alpha * (e_db - self.floor) if e_db > self.floor else 3 * self.alpha * (e_db - self.floor)
        out = None
        if t < self.deaf_until or t - self.last_onset < self.refractory:
            self.pending = None
        elif self.pending is not None:
            if over >= self.thresh - self.confirm_db:
                out = dict(self.pending)
                self.last_onset = out["t"]
            self.pending = None
        elif loud and self.hist:
            quiet = min(self.hist)
            voiced = (e_db - tot_db) >= 10 * math.log10(self.band_frac)
            if e_db - quiet >= self.rise and voiced and (self.max_db is None or e_db <= self.max_db):
                self.pending = dict(t=t, e_db=round(e_db, 1), floor_db=round(self.floor, 1), rise_db=round(e_db - quiet, 1),
                                    over_db=round(over, 1))
        self.hist.append(e_db)
        return out


# bins detector defaults: the 2 m trade-off of NAMECALL.md section 10.3 (6 of 8 calls at 2 m, 0.8 false triggers per
# minute on the robot's own noise without a loudspeaker in the room, 3.1 with one)
DET_SNR_DB = 9.0
DET_MIN_BINS = 8
DET_CONFIRM = 3
DET_VOICING = 0.4


class CallDetector:
    """Per-bin SNR detector: how many voice-band bins of a 20 ms block stand snr_db over a tracked noise spectrum.

    update(t, block) -> None or {"t": onset time, "bins", "e_db", "floor_db", "over_db", "rise_db"}. The noise
    spectrum (one value per FFT bin of the three-microphone mix) follows the room with time constant floor_tau_s but
    only while the block is quiet, so a call does not raise it. A block is loud when at least min_bins bins in band
    exceed the noise by snr_db; an onset is a loud block after a quiet one, confirmed when at least confirm_blocks of
    the next three blocks still hold min_bins / 2 such bins (a click or a single footstep does not), then refractory.
    A call 3 dB over the floor in band power still lifts its harmonics 10-20 dB over the noise in their own bins,
    which is why this catches the 2 m calls the band-energy detector (OnsetDetector) misses. deaf_until(t) silences
    it; reset_floor() restarts the noise estimate (after an own playback). last_loud_t tells when the call ended.
    """

    VOICE_BAND = (300.0, 1500.0)     # harmonicity is judged here (the voiced "Mo"; footsteps and touches are not periodic)
    PITCH_HZ = (80.0, 400.0)
    LONG_LOUD_S = 1.5                # loud for longer than this = the room changed, not a call

    def __init__(self, fs=FS, block=BLOCK, band=BAND, snr_db=DET_SNR_DB, min_bins=DET_MIN_BINS, confirm_blocks=DET_CONFIRM,
                 refractory_s=2.5, floor_tau_s=3.0, max_bins=None, voicing=DET_VOICING):
        self.fs, self.block, self.band = fs, block, band
        self.snr, self.min_bins, self.confirm_blocks, self.refractory = 10 ** (snr_db / 10.0), min_bins, confirm_blocks, refractory_s
        self.max_bins, self.voicing = max_bins, voicing
        self.recent = collections.deque(maxlen=6)     # mono blocks for the voicing check (120 ms)
        self.rejected = 0                             # candidates the voicing check turned down
        self.alpha = block / fs / floor_tau_s
        self.window = np.hanning(block).astype(np.float32)
        f = np.fft.rfftfreq(block, 1 / fs)
        self.sel = np.nonzero((f >= band[0]) & (f <= band[1]))[0]
        self.npsd = None
        self.settle = []
        self.settle_n = int(round(0.5 * fs / block))
        self.pending = None
        self.last_onset = -1e9
        self.last_loud_t = -1e9
        self.deaf_until = -1e9
        self.prev_loud = False
        self.loud_since = -1e9
        self.bins = 0

    @property
    def floor(self):
        """Noise level in band, dB (for the heartbeat), or None while settling."""
        if self.npsd is None:
            return None
        return 10 * math.log10(max(float(self.npsd.sum()), 1e-14))

    def reset_floor(self):
        self.npsd, self.settle, self.pending = None, [], None

    def spectrum(self, mono):
        X = np.fft.rfft(mono * self.window)
        return (X.real ** 2 + X.imag ** 2)[self.sel] / len(mono)

    def harmonicity(self, n_blocks=4, win_s=0.06):
        """Largest normalised autocorrelation peak in the pitch range over the last n_blocks (300-1500 Hz band),
        60 ms windows at 20 ms steps: about 0.6-0.9 for a voiced call, under 0.4 for footsteps and touches."""
        if not self.recent:
            return 0.0
        y = np.concatenate(list(self.recent)[-n_blocks:]).astype(np.float64)
        Y = np.fft.rfft(y)
        f = np.fft.rfftfreq(len(y), 1 / self.fs)
        Y[(f < self.VOICE_BAND[0]) | (f > self.VOICE_BAND[1])] = 0
        y = np.fft.irfft(Y, len(y))
        n = int(win_s * self.fs)
        lo, hi = int(self.fs / self.PITCH_HZ[1]), int(self.fs / self.PITCH_HZ[0])
        best = 0.0
        for i in range(0, max(1, len(y) - n + 1), self.block):
            w = y[i:i + n]
            w = w - w.mean()
            e = float(w @ w)
            if e <= 1e-18:
                continue
            nfft = 1 << (2 * len(w) - 1).bit_length()
            W = np.fft.rfft(w, nfft)
            r = np.fft.irfft(W.real ** 2 + W.imag ** 2, nfft)[:hi + 1] / e
            best = max(best, float(r[lo:hi].max()))
        return best

    def update(self, t, block):
        mono = block[:, :3].mean(axis=1) if block.ndim == 2 else block
        self.recent.append(mono)
        p = self.spectrum(mono)
        if self.npsd is None or len(self.settle) < self.settle_n:
            self.settle.append(p)
            self.npsd = np.mean(np.stack(self.settle), axis=0) + 1e-14   # the mean: bin powers are exponential, a median sits 1.6 dB low
            return None
        snr = p / self.npsd
        over = snr > self.snr
        nb = int(over.sum())
        self.bins = nb
        loud = nb >= self.min_bins
        if loud and not self.prev_loud:
            self.loud_since = t
        if not loud or t - self.loud_since > self.LONG_LOUD_S:
            # follow the room while nothing is loud (an asymmetric update would settle under the mean of the
            # exponentially distributed bin powers and fire on the noise itself); a "call" longer than any call is
            # the room getting louder (a fan, a door), so the spectrum follows it too
            self.npsd = self.npsd + self.alpha * (p - self.npsd)
        if loud or nb >= self.min_bins // 2:
            self.last_loud_t = t
        out = None
        e_db = 10 * math.log10(max(float(p.sum()), 1e-14))
        floor_db = 10 * math.log10(max(float(self.npsd.sum()), 1e-14))
        if t < self.deaf_until or t - self.last_onset < self.refractory:
            self.pending = None
        elif self.pending is not None:
            self.pending["seen"] += 1
            if nb >= max(1, self.min_bins // 2):
                self.pending["confirmed"] += 1
            if self.pending["confirmed"] >= self.confirm_blocks:
                h = self.harmonicity(n_blocks=self.pending["seen"] + 1) if self.voicing > 0 else None
                if h is None or h >= self.voicing:
                    out = {k: v for k, v in self.pending.items() if k not in ("seen", "confirmed")}
                    out["voicing"] = None if h is None else round(h, 2)
                    self.last_onset = out["t"]
                else:
                    self.rejected += 1
                self.pending = None
            elif self.pending["seen"] >= 3:
                self.pending = None
        elif loud and not self.prev_loud and (self.max_bins is None or nb <= self.max_bins):
            self.pending = dict(t=t, bins=nb, e_db=round(e_db, 1), floor_db=round(floor_db, 1),
                                over_db=round(e_db - floor_db, 1),
                                rise_db=round(10 * math.log10(max(float(np.median(snr[over])), 1e-9)), 1) if nb else 0.0,
                                seen=0, confirmed=0)
        self.prev_loud = loud
        return out


# ----------------------------------------------------------------------------------------------- direction

def gcc_phat(a, b, fs, band=BAND, nfft=None, max_lag=None):
    """GCC-PHAT of two equal-length signals, band-limited. Returns (lags in samples, correlation), where a positive lag
    means `a` arrives later than `b` (a is a delayed copy of b)."""
    n = len(a)
    nfft = nfft or (1 << (2 * n - 1).bit_length())
    A, B = np.fft.rfft(a, nfft), np.fft.rfft(b, nfft)
    f = np.fft.rfftfreq(nfft, 1 / fs)
    R = A * np.conj(B)
    R /= np.maximum(np.abs(R), 1e-12)
    R[(f < band[0]) | (f > band[1])] = 0
    r = np.fft.irfft(R, nfft)
    max_lag = int(max_lag or nfft // 2)
    lags = np.arange(-max_lag, max_lag + 1)
    return lags, np.concatenate([r[-max_lag:], r[:max_lag + 1]])


def parabolic_peak(y, i):
    """Sub-sample peak position around index i of y (parabola through three points)."""
    if 0 < i < len(y) - 1:
        a, b, c = y[i - 1], y[i], y[i + 1]
        d = a - 2 * b + c
        if d < 0:
            return i + 0.5 * (a - c) / d
    return float(i)


class Localiser:
    """SRP-PHAT over a 1 deg azimuth grid with the three pairs; azimuth 0 ahead, + left (head frame, rad)."""

    PAIRS = (("left", "right"), ("left", "back"), ("right", "back"))

    def __init__(self, fs=FS, mics_mm=MICS_MM, channels=CHANNELS, band=BAND, window=3072, grid_deg=1.0, c=C_SOUND):
        self.fs, self.band, self.window, self.c = fs, band, window, c
        self.pos = {k: np.asarray(v, float) / 1000.0 for k, v in mics_mm.items()}
        self.ch = dict(channels)
        self.az = np.deg2rad(np.arange(0.0, 360.0, grid_deg))
        u = np.stack([np.cos(self.az), np.sin(self.az)], axis=1)         # unit vector toward the source
        # predicted lag (samples) of mic i behind mic j: a mic farther along -u hears it later
        self.pred = {(i, j): -(u @ (self.pos[i] - self.pos[j])) / c * fs for i, j in self.PAIRS}
        self.max_lag = {(i, j): int(math.ceil(np.linalg.norm(self.pos[i] - self.pos[j]) / c * fs)) + 2 for i, j in self.PAIRS}

    def estimate(self, x):
        """x: (n, channels) window around the onset -> dict(az_rad, az_deg, srp, margin_db, pairs)."""
        x = np.asarray(x, np.float32)[: self.window]
        x = x - x.mean(axis=0)
        srp = np.zeros_like(self.az)
        pairs = {}
        nfft = 1 << (2 * len(x) - 1).bit_length()
        for i, j in self.PAIRS:
            lags, r = gcc_phat(x[:, self.ch[i]], x[:, self.ch[j]], self.fs, self.band, nfft, self.max_lag[(i, j)])
            k = int(np.argmax(r))
            pairs[f"{i}-{j}"] = dict(lag=round(float(lags[0] + parabolic_peak(r, k)), 2), peak=round(float(r[k]), 3))
            srp += np.interp(self.pred[(i, j)], lags, r)
        k = int(np.argmax(srp))
        kk = parabolic_peak(np.concatenate([srp[-1:], srp, srp[:1]]), k + 1) - 1   # wrap-aware refinement
        az = float(np.deg2rad(kk * (360.0 / len(self.az))))
        az = (az + math.pi) % (2 * math.pi) - math.pi
        # front/back margin: this peak against the best point in the mirrored half-plane (az -> pi - az)
        mirror = (math.pi - az + math.pi) % (2 * math.pi) - math.pi
        mi = int(round((mirror % (2 * math.pi)) / (2 * math.pi) * len(self.az))) % len(self.az)
        near = (np.abs(((self.az - self.az[mi]) + math.pi) % (2 * math.pi) - math.pi) < math.radians(25))
        margin = float(srp[k] - srp[near].max()) if near.any() else float("nan")
        return dict(az_rad=round(az, 4), az_deg=round(math.degrees(az), 1), srp=round(float(srp[k]), 3),
                    margin=round(margin, 3), pairs=pairs)

    def expected_resolution_deg(self, lag_err_samples=0.25):
        """Azimuth error from a lag error on the ear pair alone (far field): d(az) = c * dtau / (d cos az)."""
        d = float(np.linalg.norm(self.pos["left"] - self.pos["right"]))
        return math.degrees(self.c * lag_err_samples / self.fs / d)


LOC_BAND = (1500.0, 8000.0)       # the call localiser's band: under 1.5 kHz this head hears through its cavity (NAMECALL.md 10)
LOC_ELEV = (35.0,)                # elevation prior: a standing owner 2 m from a robot on the floor
CALL_WINDOW_S = 0.8               # accumulate this long after the onset
LOC_PRE_S = 2.0                   # noise spectrum from this much audio before the onset ...
LOC_GAP_S = 0.3                   # ... leaving this gap before it (the onset detector fires a block or two late)
LOC_LEAD_S = 0.05                 # the call window starts this much before the onset block


class CallLocaliser:
    """SRP-PHAT over the whole call on a time-frequency mask, with an elevation prior and the back microphone.

    estimate(x, i_onset): x (n, channels) holds pre_s + gap_s of audio before the onset sample i_onset and window_s
    after it. STFT (nfft, hop, Hann) of the three microphones; the noise spectrum per microphone and bin is the mean
    power of the frames that end before the gap; a call bin is one whose power on all three microphones is snr_db over
    its noise (weight "hard"), or weighted by how far over (weight "soft", 0 at snr_db, 1 at snr_db + 15). The PHAT
    cross-spectra of the three pairs are summed over the masked bins and frames, then steered to every point of an
    azimuth x elevation grid (the microphones are coplanar, so an elevation e shrinks every lag by cos e); the peak
    gives the azimuth, its elevation, and the margin against the best point in the mirrored half-plane (front/back,
    settled by the back microphone). Band 1500-8000 Hz by default: on this head the cues under 1.5 kHz come through
    the cavity and do not depend on where the caller stands (NAMECALL.md section 10).
    """

    PAIRS = Localiser.PAIRS

    def __init__(self, fs=FS, mics_mm=MICS_MM, channels=CHANNELS, band=LOC_BAND, nfft=1024, hop=256, elev_deg=LOC_ELEV,
                 grid_deg=1.0, snr_db=3.0, weight="soft", pre_s=LOC_PRE_S, gap_s=LOC_GAP_S, window_s=CALL_WINDOW_S,
                 lead_s=LOC_LEAD_S, c=C_SOUND):
        self.fs, self.band, self.nfft, self.hop, self.c = fs, band, nfft, hop, c
        self.pos = {k: np.asarray(v, float) / 1000.0 for k, v in mics_mm.items()}
        self.ch = dict(channels)
        self.snr, self.weight = 10 ** (snr_db / 10.0), weight
        self.snr_db = snr_db
        self.pre_s, self.gap_s, self.window_s, self.lead_s = pre_s, gap_s, window_s, lead_s
        self.before = int(round((pre_s + gap_s + lead_s) * fs))    # samples needed before the onset
        self.after = int(round(window_s * fs))                      # and after it
        self.win = np.hanning(nfft).astype(np.float32)
        f = np.fft.rfftfreq(nfft, 1 / fs)
        self.sel = np.nonzero((f >= band[0]) & (f < band[1]))[0]
        fb = f[self.sel]
        self.az = np.deg2rad(np.arange(0.0, 360.0, grid_deg))
        self.el = np.deg2rad(np.asarray(elev_deg, float))
        AZ, EL = np.meshgrid(self.az, self.el, indexing="ij")
        u = np.stack([np.cos(AZ) * np.cos(EL), np.sin(AZ) * np.cos(EL)], axis=-1).reshape(-1, 2)
        # steering: predicted lag (s) of mic i behind mic j for each direction, as a phase per bin
        self.steer = {}
        for i, j in self.PAIRS:
            tau = -(u @ (self.pos[i] - self.pos[j])) / c
            self.steer[(i, j)] = np.exp(2j * math.pi * np.outer(tau, fb)).astype(np.complex64)
        self.lags = np.arange(-16.0, 16.01, 0.25)
        self.lag_mat = np.exp(2j * math.pi * np.outer(self.lags / fs, fb)).astype(np.complex64)

    def stft(self, x):
        n = (len(x) - self.nfft) // self.hop + 1
        if n < 1:
            return np.zeros((0, x.shape[1], len(self.sel)), np.complex64)
        idx = np.arange(self.nfft)[None, :] + self.hop * np.arange(n)[:, None]
        fr = x[idx] * self.win[None, :, None]                         # (frames, nfft, ch)
        return np.fft.rfft(fr, axis=1)[:, self.sel, :].transpose(0, 2, 1)   # (frames, ch, bins)

    def estimate(self, x, i_onset):
        x = np.asarray(x, np.float32)
        x = x - x.mean(axis=0)
        F = self.stft(x)
        n = len(F)
        starts = self.hop * np.arange(n)
        ends = starts + self.nfft
        noise = F[ends <= i_onset - int(self.gap_s * self.fs)]
        i0 = i_onset - int(self.lead_s * self.fs)
        call = F[(starts >= i0) & (ends <= i_onset + self.after)]
        if len(noise) < 4 or len(call) < 2:
            return None
        npsd = (np.abs(noise[:, :3]) ** 2).mean(axis=0) + 1e-14           # (3, bins)
        snr = (np.abs(call[:, :3]) ** 2) / npsd[None]
        chans = [self.ch[k] for k in ("left", "right", "back")]
        smin = snr[:, chans].min(axis=1)                                # (frames, bins)
        if self.weight == "soft":
            w = np.clip(10 * np.log10(smin + 1e-12) - self.snr_db, 0.0, 15.0) / 15.0
        else:
            w = (smin > self.snr).astype(np.float32)
        n_bins = int((w > 0).sum())
        total = float(w.sum())
        if n_bins == 0:
            return None
        srp = np.zeros(self.steer[self.PAIRS[0]].shape[0])
        pairs = {}
        for i, j in self.PAIRS:
            g = call[:, self.ch[i]] * np.conj(call[:, self.ch[j]])
            g = g / (np.abs(g) + 1e-30)
            acc = (g * w).sum(axis=0).astype(np.complex64) / total
            srp += (self.steer[(i, j)] @ acc).real
            r = (self.lag_mat @ acc).real
            k = int(np.argmax(r))
            pairs[f"{i}-{j}"] = dict(lag=round(float(self.lags[k]), 2), peak=round(float(r[k]), 3))
        srp = srp.reshape(len(self.az), len(self.el))
        ka, ke = np.unravel_index(int(np.argmax(srp)), srp.shape)
        col = srp[:, ke]
        kk = parabolic_peak(np.concatenate([col[-1:], col, col[:1]]), ka + 1) - 1
        az = float(kk * (2 * math.pi / len(self.az)))
        az = (az + math.pi) % (2 * math.pi) - math.pi
        mirror = (math.pi - az + math.pi) % (2 * math.pi) - math.pi
        mi = int(round((mirror % (2 * math.pi)) / (2 * math.pi) * len(self.az))) % len(self.az)
        near = np.abs(((self.az - self.az[mi]) + math.pi) % (2 * math.pi) - math.pi) < math.radians(25)
        margin = float(col[ka] - col[near].max()) if near.any() else float("nan")
        return dict(az_rad=round(az, 4), az_deg=round(math.degrees(az), 1), el_deg=round(float(np.degrees(self.el[ke])), 1),
                    srp=round(float(col[ka]), 3), margin=round(margin, 3), pairs=pairs, bins=n_bins,
                    frames=int(len(call)), window_s=round(len(call) * self.hop / self.fs, 2))


def synth_call(fs=FS, dur=0.45, f0=210.0, seed=0, kind="voice"):
    """A voice-like call (harmonics under formant bumps with a vibrato, 0.45 s) or a clap (short noise burst)."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(dur * fs)) / fs
    if kind == "clap":
        env = np.exp(-t / 0.03)
        return rng.standard_normal(len(t)).astype(np.float32) * env
    f = f0 * (1 + 0.02 * np.sin(2 * math.pi * 5.5 * t)) * (1 + 0.08 * (t / dur))
    ph = 2 * math.pi * np.cumsum(f) / fs
    y = np.zeros_like(t)
    for h in range(1, 18):
        fh = h * f0
        formant = math.exp(-((fh - 600) / 250) ** 2) + 0.6 * math.exp(-((fh - 1700) / 350) ** 2) + 0.3 * math.exp(-((fh - 2800) / 400) ** 2)
        y += (formant + 0.02) / h ** 0.5 * np.sin(h * ph + rng.uniform(0, 2 * math.pi))
    y += 0.03 * rng.standard_normal(len(t))
    env = np.minimum(1.0, t / 0.03) * np.minimum(1.0, (dur - t) / 0.08)
    y = y * env
    return (y / np.abs(y).max()).astype(np.float32)


def render_scene(signal, az_rad, fs=FS, mics_mm=MICS_MM, channels=CHANNELS, n_channels=4, pre_s=0.6, post_s=0.6,
                 snr_db=20.0, seed=0, c=C_SOUND, floor=None, el_rad=0.0):
    """Far-field 4-channel rendering of `signal` from azimuth az (head frame, + left) and elevation el (coplanar
    microphones: every lag shrinks by cos el) with white noise at snr_db (and an optional extra floor signal (n, ch));
    fractional delays by FFT phase shift. Returns (x (n, 4), onset_s)."""
    rng = np.random.default_rng(seed)
    u = np.array([math.cos(az_rad), math.sin(az_rad)]) * math.cos(el_rad)
    n = int(pre_s * fs) + len(signal) + int(post_s * fs)
    x = np.zeros((n, n_channels), np.float32)
    s = np.zeros(n, np.float32)
    s[int(pre_s * fs):int(pre_s * fs) + len(signal)] = signal
    S = np.fft.rfft(s)
    f = np.fft.rfftfreq(n, 1 / fs)
    for name, ch in channels.items():
        p = np.asarray(mics_mm[name], float) / 1000.0
        delay = -(u @ p) / c           # seconds: a mic farther along -u hears it later
        x[:, ch] = np.fft.irfft(S * np.exp(-2j * math.pi * f * delay), n).astype(np.float32)
    rms = float(np.sqrt(np.mean(signal ** 2)))
    noise = rng.standard_normal(x.shape).astype(np.float32) * rms * 10 ** (-snr_db / 20)
    for ch in range(n_channels):
        if ch not in channels.values():
            noise[:, ch] = 0
    x = x + noise
    if floor is not None:
        x[: len(floor)] += floor[:n]
    return x, pre_s


# ----------------------------------------------------------------------------------------------- keyword spotter

def lowpass_fir(n_taps=97, cutoff_hz=7000.0, fs=FS):
    """Windowed-sinc low-pass (Blackman), unit DC gain."""
    n = np.arange(n_taps) - (n_taps - 1) / 2.0
    h = np.sinc(2.0 * cutoff_hz / fs * n) * np.blackman(n_taps)
    return (h / h.sum()).astype(np.float32)


class Decimate3:
    """48 kHz -> 16 kHz in 20 ms blocks: FIR low-pass with its history carried across blocks, every third sample
    (block lengths are multiples of 3, so the phase never slips). Delay (taps - 1) / 2 = 1 ms."""

    def __init__(self, h=None):
        self.h = lowpass_fir() if h is None else np.asarray(h, np.float32)
        self.tail = np.zeros(len(self.h) - 1, np.float32)

    def __call__(self, x):
        z = np.concatenate([self.tail, np.asarray(x, np.float32)])
        self.tail = z[len(z) - (len(self.h) - 1):]
        return np.convolve(z, self.h, mode="valid")[::3]


def model_file(model_dir, stem):
    """encoder/decoder/joiner file of a sherpa KWS model folder: int8 when there is one, the 16-frame chunk first."""
    for pat in (f"{stem}-*.int8.onnx", f"{stem}-*.onnx"):
        found = sorted(glob.glob(os.path.join(model_dir, pat)), key=lambda p: ("chunk-16" not in p, p))
        if found:
            return found[0]
    return None


def find_kws_model(dirs=KWS_MODEL_DIRS):
    for d in dirs:
        if d and os.path.isfile(os.path.join(d, "tokens.txt")):
            return d
    return None


class KeywordGate:
    """Keyword spotter on the two ears downmixed to 16 kHz (sherpa-onnx KeywordSpotter, one thread).

    feed(t, block, silent) -> None or dict(t_hit: end of the block that completed the keyword, keyword, span_s: first
    to last token time, tokens). silent=True feeds zeros instead of the block (the duck's own quack) while the
    decimator keeps its history. Per-keyword boost (:x) and threshold (#x) live in the keywords file; score and
    threshold here apply to lines without them."""

    def __init__(self, model_dir, keywords_file, score=1.0, threshold=0.25, threads=1, trailing_blanks=1, gain_db=0.0,
                 ears=(0, 1), max_active_paths=4):
        try:
            import sherpa_onnx
        except ImportError:
            raise SystemExit("namecall: --name needs sherpa-onnx in this Python (pip install sherpa-onnx==2.0.0)")
        if not model_dir or not os.path.isdir(model_dir):
            raise SystemExit(f"namecall: keyword model folder not found ({model_dir}); see NAMECALL.md section 9")

        def one(stem):
            found = model_file(model_dir, stem)
            if not found:
                raise SystemExit(f"namecall: no {stem}-*.onnx in {model_dir}")
            return found

        self.kws = sherpa_onnx.KeywordSpotter(
            tokens=os.path.join(model_dir, "tokens.txt"), encoder=one("encoder"), decoder=one("decoder"),
            joiner=one("joiner"), keywords_file=keywords_file, num_threads=threads, keywords_score=score,
            keywords_threshold=threshold, num_trailing_blanks=trailing_blanks, max_active_paths=max_active_paths)
        self.stream = self.kws.create_stream()
        self.dec = Decimate3()
        self.ears = list(ears)
        self.gain = 10 ** (gain_db / 20.0)
        self.model_dir, self.keywords_file = model_dir, keywords_file
        self.hits = 0

    def reset(self):
        """A fresh stream (after a pause): nothing heard before it can complete a keyword."""
        self.stream = self.kws.create_stream()
        self.dec = Decimate3()

    def feed(self, t, block, silent=False):
        x = block[:, self.ears].mean(axis=1) if block.ndim == 2 else block
        y = self.dec(x) * self.gain
        if silent:
            y = np.zeros_like(y)
        self.stream.accept_waveform(KWS_FS, y)
        hit = None
        while self.kws.is_ready(self.stream):
            self.kws.decode_stream(self.stream)
            r = self.kws.keyword_spotter.get_result(self.stream)
            word = r.keyword.strip()
            if word:
                ts = list(r.timestamps)
                if hit is None:
                    hit = dict(t_hit=round(t + len(x) / FS, 3), keyword=word, tokens=list(r.tokens),
                               span_s=round(ts[-1] - ts[0], 2) if len(ts) > 1 else None)
                    self.hits += 1
                self.kws.reset_stream(self.stream)
        return hit


# ----------------------------------------------------------------------------------------------- head path

def policy_default_head(models=MODELS):
    """Head joints of the policy default pose from stand61.onnx's metadata, else DEFAULT_HEAD."""
    try:
        import onnxruntime as ort
        s = ort.InferenceSession(os.path.join(models, "stand61.onnx"), providers=["CPUExecutionProvider"])
        m = s.get_modelmeta().custom_metadata_map
        names, vals = m["joint_names"].split(","), [float(v) for v in m["default_joint_pos"].split(",")]
        d = dict(zip(names, vals))
        return {n: d[n] for n in HEAD_JOINTS}
    except Exception:
        return dict(DEFAULT_HEAD)


class HeadPath:
    """One pet/express take at a time, ticked at 50 Hz, with walk_brain's head EMA pre-inverted.

    start(now, az_rad, pitch) submits an acknowledge toward the caller (az in the resting head frame); tick(now) returns
    (head dict for want["head"] in absolute model rad, call events due now, active). After the take a content_idle
    drifts the head home, then the path goes quiet (tick returns head None) and the last command holds.
    """

    def __init__(self, card=CARD, default=None, seed=None, preinverse=True, yaw_cap=YAW_CAP, warmth=0.8, energy=0.7,
                 affect=(0.6, 0.6), idle=False):
        self.ex = Expressor(load_card(card), seed=int(time.time() * 1000) % 2 ** 31 if seed is None else seed)
        self.default = default or dict(DEFAULT_HEAD)
        self.preinverse, self.yaw_cap, self.idle = preinverse, yaw_cap, idle
        self.warmth, self.energy, self.affect = warmth, energy, Affect(*affect)
        self.lim = np.asarray(HEAD_RANGE, float)
        self.c = np.zeros(4)            # walk_brain's head_cmd as this path believes it (deltas)
        self.active_until = None
        self.settle_at = None
        self.last = None
        self.home_at = None
        self.holding = False            # attention: after the take the gaze stays where it is (aim() moves it)

    def start(self, now, az_rad, pitch=LOOK_PITCH, hold=False):
        """Returns the Performance (take name in .take, params, events). hold: after the take keep the gaze on the
        caller (the attention phase) instead of drifting home."""
        behind = abs(az_rad) > self.yaw_cap
        yaw = float(np.clip(az_rad, -self.yaw_cap, self.yaw_cap))
        perf = self.ex.submit(acknowledge(Target(yaw, pitch, "caller"), warmth=self.warmth, energy=self.energy,
                                          affect=self.affect), now)
        self.settle_at = now + perf.duration
        self.active_until = self.settle_at + 2.5
        self.home_at = None
        self.holding = bool(hold)
        self.last = dict(take=perf.take, yaw=yaw, pitch=pitch, behind=behind, t=now,
                         arrival=None if perf.arrival is None else now + perf.arrival, events=list(perf.events))
        return perf

    @property
    def active(self):
        """Still writing head commands (take, attention hold, or the drift home)."""
        return self.active_until is not None or self.holding

    @property
    def busy(self):
        """The take itself is running (the drift home afterwards may be interrupted by a new call)."""
        return self.settle_at is not None

    def gaze(self, now):
        """(yaw, pitch up) the gaze is at now, express rad."""
        cur = self.ex.current(now)
        return float(cur["ATTEND.yaw"]), float(cur["ATTEND.pitch"])

    def aim(self, yaw, pitch):
        """Attention: move the held gaze to (yaw, pitch up), express rad; the brain's head EMA eases the head there.
        Ignored while a take runs (the take owns the gaze until it ends)."""
        if self.ex.perf is not None:
            return False
        self.ex.state["ATTEND.yaw"] = float(np.clip(yaw, -self.yaw_cap, self.yaw_cap))
        self.ex.state["ATTEND.pitch"] = float(np.clip(pitch, *FACE_PITCH))
        return True

    def set_pose(self, yaw, pitch):
        """Attention hand-over from the body turn: the gaze is already at (yaw, pitch up) and so is the brain's EMA."""
        self.holding, self.settle_at, self.active_until = True, None, None
        if self.ex.perf is not None:
            self.ex.state = self.ex.current(self.ex._last_now or 0.0)
            self.ex.perf = None
        self.ex.state["ATTEND.yaw"], self.ex.state["ATTEND.pitch"] = float(yaw), float(pitch)
        self.ex._prev_out = None                       # the card's rate limit starts from here, not the take's end
        self.c[:] = [0.25 * pitch, -pitch, yaw, 0.0]   # the duck card's ATTEND map (neck, head pitch, yaw, roll)

    def release(self, now):
        """Attention over: drift home over 2.5 s, then quiet."""
        if not self.holding:
            return
        self.holding = False
        self.ex.submit(content_idle(affect=Affect(self.affect.valence, max(0.2, self.affect.arousal - 0.2))), now)
        self.active_until = now + 2.5

    def tick(self, now):
        if self.active_until is None and not self.idle and not self.holding:
            return None, [], False
        if self.settle_at is not None and now >= self.settle_at:
            self.settle_at = None
            if self.holding:
                self.active_until = None     # the gaze stays on the caller; release() starts the drift home
            else:
                self.ex.submit(content_idle(affect=Affect(self.affect.valence, max(0.2, self.affect.arousal - 0.2))), now)
        frame = self.ex.step(now)
        y = np.array([frame["outputs"][j] for j in HEAD_JOINTS])
        if self.preinverse and not (self.holding and self.ex.perf is None):
            # the EMA pre-inverse serves the take's snaps; the attention hold sends its slow gaze as it is (the
            # pre-inverse would multiply the idle breathing and each face correction by 1 / HEAD_ALPHA)
            r = np.clip(self.c + (y - self.c) / HEAD_ALPHA, -self.lim, self.lim)
        else:
            r = np.clip(y, -self.lim, self.lim)
        self.c = self.c + HEAD_ALPHA * (r - self.c)
        active = True
        if self.active_until is not None and now >= self.active_until:
            self.active_until = None
            active = self.idle
            if not self.idle:
                r = np.zeros(4)      # one last command at the policy default; the brain's EMA eases into it
                self.c[:] = 0
        return want_head(r, self.default), frame["events"], active


# ----------------------------------------------------------------------------------------------- quacks

class QuackBank:
    """Duck calls at a few pitches and lengths, rendered once from the existing recordings (pet.express.voice), played
    with duck_sound.Voice (aplay on the ALSA default device, the -3 dB softvol ceiling of D-012). play(event) picks the
    variant nearest the take's pitch and stretch. playing() tells the detector when to listen again."""

    PITCHES = (0.85, 1.0, 1.15, 1.3)
    STRETCHES = (0.85, 1.0, 1.25)

    def __init__(self, out_dir, sounds_dir=None, muted=False, rng=None, max_sources=4):
        self.muted = muted
        self.rng = rng or np.random.default_rng()
        self.files = {}
        self.voice = None
        self.last_end = None
        self.sources = find_calls() if sounds_dir is None else sorted(glob.glob(os.path.join(sounds_dir, "*.wav")))
        self.sources = self.sources[:max_sources]
        if not self.sources:
            return
        os.makedirs(out_dir, exist_ok=True)
        for si, src in enumerate(self.sources):
            x, rate = read_wav(src)
            for p in self.PITCHES:
                for s in self.STRETCHES:
                    path = os.path.join(out_dir, f"call{si}_p{p:.2f}_s{s:.2f}.wav")
                    if not os.path.exists(path):
                        write_wav(path, render_call(x, p, s, 0.0) * 0.9, rate)
                    self.files[(si, p, s)] = path
        self.picker = CallPicker(list(range(len(self.sources))), self.rng)
        self.voice = Voice(out_dir)   # its own random quack() is not used; play() queues the chosen file

    @property
    def available(self):
        return bool(self.files)

    def play(self, event):
        """Queue the nearest variant for a pet/express call event; returns the file (None when muted/unavailable)."""
        if self.muted or not self.files:
            return None
        si = self.picker.pick()
        p = min(self.PITCHES, key=lambda v: abs(v - event.get("pitch", 1.0)))
        s = min(self.STRETCHES, key=lambda v: abs(v - event.get("stretch", 1.0)))
        f = self.files[(si, p, s)]
        self.voice.q.put(f)
        return f

    def playing(self):
        """True while a player process runs (or is about to)."""
        v = self.voice
        if v is None:
            return False
        if not v.q.empty():
            return True
        return v.proc is not None and v.proc.poll() is None


# ----------------------------------------------------------------------------------------------- brain gate

def tail_json(path, max_bytes=16384):
    """Last complete JSON line of a jsonl file, or None."""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            lines = f.read().split(b"\n")
        for line in reversed(lines):
            line = line.strip()
            if line:
                try:
                    return json.loads(line)
                except ValueError:
                    continue
    except OSError:
        return None
    return None


def newest(pattern):
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None


def procs_named(names=("walk_wired.py", "duck_selfcheck.py")):
    """Python processes running one of these scripts (the duck_sense.py scan), by script name; [] where /proc is absent."""
    found = []
    if not os.path.isdir("/proc"):
        return found
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                argv = f.read().split(b"\0")
        except OSError:
            continue
        if argv and b"python" in os.path.basename(argv[0]):
            for a in argv[1:3]:
                b = os.path.basename(a).decode(errors="replace")
                if b in names:
                    found.append(b)
    return found


def lock_free(path=HW_LOCK):
    """True when nobody holds the robot I/O lock (no brain, no reader): the lock is probed and released at once."""
    try:
        f = open(path, "a")
    except OSError:
        return True
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        return False
    fcntl.flock(f, fcntl.LOCK_UN)
    f.close()
    return True


def zero_walk(cmd):
    return isinstance(cmd, dict) and cmd.get("mode") == "walk" and \
        all(abs(float(cmd.get(k, 0) or 0)) < 1e-6 for k in ("vx", "vy", "vtheta"))


def read_cmd_file(path=CMD_FILE):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return None


class BrainGate:
    """What the brain is doing, from its newest tick log and the control file; refuses anything but walk/stand at rest."""

    def __init__(self, log_pattern=BRAIN_LOGS, cmd_file=CMD_FILE, fresh_s=BRAIN_FRESH_S, now=time.time):
        self.pattern, self.cmd_file, self.fresh_s, self.now = log_pattern, cmd_file, fresh_s, now
        self.log = None

    def state(self):
        """dict(ok, why, mode, cmd, fresh_s, log)."""
        self.log = newest(self.pattern) if (self.log is None or not os.path.exists(self.log)) else self.log
        n = newest(self.pattern)
        if n and n != self.log:
            self.log = n
        if not self.log:
            return dict(ok=False, why="no brain tick log (~/duck-logs/duck_wired_log_*.jsonl): is walk_wired.py running?",
                        mode=None, cmd=None, fresh_s=None, log=None)
        row = tail_json(self.log)
        if not row or "mode" not in row:
            return dict(ok=False, why=f"no readable tick in {self.log}", mode=None, cmd=None, fresh_s=None, log=self.log)
        age = self.now() - float(row.get("t", 0))
        mode, cmd = row.get("mode"), row.get("cmd") or {}
        st = dict(ok=False, why=None, mode=mode, cmd=cmd, fresh_s=round(age, 2), log=self.log, torque=row.get("torque"))
        if age > self.fresh_s:
            st["why"] = f"brain log stale ({age:.1f} s): the brain stopped or hangs"
        elif mode not in ("walk", "stand"):
            st["why"] = f"brain in {mode} mode (needs walk at zero command, or stand)"
        elif mode == "walk" and not zero_walk(cmd):
            st["why"] = f"brain walking with command {cmd}: waits for a zero command"
        else:
            st["ok"] = True
        return st


class GyroTurn:
    """Body rotation from the brain's tick log: integrates gyro_body z (rad/s, + left) over the rows that appear while
    a turn runs; update() returns the angle turned since start(), or None before the first two rows."""

    def __init__(self, log_path=None):
        self.path = log_path
        self.last_t = None
        self.theta = 0.0
        self.n = 0

    @property
    def ok(self):
        return self.n >= 2

    def start(self, log_path=None):
        if log_path:
            self.path = log_path
        self.last_t, self.theta, self.n = None, 0.0, 0
        row = tail_json(self.path) if self.path else None
        if row and "t" in row:
            self.last_t, self.n = float(row["t"]), 1

    def update(self):
        row = tail_json(self.path) if self.path else None
        if not row or "t" not in row or not row.get("gyro_body"):
            return self.theta if self.ok else None
        t = float(row["t"])
        if self.last_t is None:
            self.last_t, self.n = t, 1
            return None
        if t > self.last_t:
            dt = min(t - self.last_t, 0.2)          # a stalled log must not integrate a long gap at the last rate
            self.theta += float(row["gyro_body"][2]) * dt
            self.last_t = t
            self.n += 1
        return self.theta if self.ok else None


class CmdWriter:
    """Writes the zero-command walk with a head pose to the control file, only while nobody else has written it."""

    def __init__(self, path=CMD_FILE, dry=False):
        self.path, self.dry = path, dry
        self.mine = None
        self.writes = 0
        self.taken = None

    def claimable(self):
        cur = read_cmd_file(self.path)
        if cur is None:
            return True
        if self.mine is not None and cur == self.mine:
            return True
        return zero_walk(cur) and set(cur) <= ZERO_KEYS

    def write(self, head=None, vtheta=0.0, for_s=None):
        want = dict(WALK_ZERO)
        if vtheta:
            want["vtheta"] = round(float(vtheta), 3)
        if for_s is not None:
            want["for_s"] = round(float(for_s), 2)
        if head is not None:
            want["head"] = {k: round(float(v), 4) for k, v in head.items()}
        if not self.claimable():
            self.taken = read_cmd_file(self.path)
            return False
        if not self.dry:
            tmp = self.path + ".namecall.tmp"
            with open(tmp, "w") as f:
                json.dump(want, f)
            os.replace(tmp, self.path)
        self.mine = want
        self.writes += 1
        return True


# ----------------------------------------------------------------------------------------------- the program

class Log:
    def __init__(self, path, echo=True):
        self.path, self.echo = path, echo
        self.f = None
        if path:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            self.f = open(path, "a")

    def write(self, kind, **rec):
        rec = dict(ts=round(time.time(), 3), kind=kind, **rec)   # ts wall clock; a call's own "t" is its onset time
        if self.f:
            self.f.write(json.dumps(rec) + "\n")
            self.f.flush()
        if self.echo:
            short = {k: v for k, v in rec.items() if k not in ("ts", "kind", "pairs", "params", "events")}
            print(f"{time.strftime('%H:%M:%S')} {kind}: {json.dumps(short)}", flush=True)


class NameCall:
    """Glue: blocks in, detector, localiser, head path, quack, control file. run_blocks drives it for tests and
    --wav; run_live for the robot."""

    def __init__(self, args, log, now=time.time, kws=None):
        self.a, self.log, self.now = args, log, now
        name = None if getattr(args, "any_voice", False) else getattr(args, "name", None)
        refractory = getattr(args, "onset_gap", ONSET_GAP_S) if name else args.refractory
        if getattr(args, "detector", "bins") == "bins":
            self.det = CallDetector(snr_db=getattr(args, "snr_db", DET_SNR_DB), min_bins=getattr(args, "min_bins", DET_MIN_BINS),
                                    confirm_blocks=getattr(args, "confirm_blocks", DET_CONFIRM), refractory_s=refractory,
                                    floor_tau_s=args.floor_tau, voicing=getattr(args, "voicing", DET_VOICING))
        else:
            self.det = OnsetDetector(thresh_db=args.threshold_db, rise_db=args.rise_db, refractory_s=refractory,
                                     floor_tau_s=args.floor_tau)
        ch = dict(CHANNELS)
        if args.swap_ears:
            ch["left"], ch["right"] = ch["right"], ch["left"]
        if getattr(args, "localiser", "call") == "call":
            band = tuple(float(v) for v in str(getattr(args, "loc_band", "%g,%g" % LOC_BAND)).split(","))
            elev = tuple(float(v) for v in str(getattr(args, "elev", ",".join("%g" % e for e in LOC_ELEV))).split(","))
            self.loc = CallLocaliser(channels=ch, band=band, elev_deg=elev, window_s=getattr(args, "call_window", CALL_WINDOW_S),
                                     snr_db=getattr(args, "loc_snr_db", 3.0), weight=getattr(args, "loc_weight", "soft"))
            self.before, self.after = self.loc.before, self.loc.after
        else:
            self.loc = Localiser(channels=ch)
            self.before, self.after = BLOCK // 2, self.loc.window - BLOCK // 2
        # name mode: a spotter (or the one a test passes in); the detector's onsets are only candidate word starts
        self.kws = kws
        if self.kws is None and name and getattr(args, "spotter", "own") == "own":
            # the duck's own spotter, trained on Shawn's calls (ownkws.py; the public model never heard him, 2026-10-30)
            import ownkws
            self.kws = ownkws.OwnSpotter(getattr(args, "own_model", None) or ownkws.MODEL_DEFAULT, ears=(ch["left"], ch["right"]),
                                         threshold=getattr(args, "own_threshold", None))
        if self.kws is None and name:
            self.kws = KeywordGate(args.kws_model or find_kws_model(), args.kws_keywords or KEYWORDS[name],
                                   score=args.kws_score, threshold=args.kws_threshold, threads=args.kws_threads,
                                   gain_db=args.kws_gain_db, ears=(ch["left"], ch["right"]))
        ring_s = max(RING_NAME_S if self.kws is not None else 0.0, (self.before + self.after) / FS + 0.1)
        self.ring = collections.deque(maxlen=int(math.ceil(ring_s * FS / BLOCK)) + 1)
        self.onsets = collections.deque(maxlen=64)   # name mode: recent detector onsets
        self.last_kw_t = -1e9                        # name mode: spot time of the last accepted call
        self.kw_hits = 0
        self.kws_paused = False                      # name mode: the spotter rests while a take runs
        self.block_ms = []                         # offline drivers: processing time per block
        self.pending = None                          # onset waiting for its window to fill
        self.head = None if args.no_head else HeadPath(default=policy_default_head() if not args.default_head_file else
                                                       json.load(open(args.default_head_file)), seed=args.seed,
                                                       preinverse=not args.smooth, idle=args.idle)
        self.bank = QuackBank(args.bank_dir, args.sounds, muted=args.mute) if not args.no_sound else None
        self.writer = CmdWriter(args.cmd, dry=args.dry) if not args.no_head else None
        self.gate = BrainGate(args.brain_logs, args.cmd) if not args.no_gate else None
        self.responses = 0
        self.head_yaw_now = 0.0          # the head's commanded yaw in the resting frame: mics turn with the head
        self.quack_due = []              # (t_abs, event): quacks of the program's own (takes the library planned silent)
        self.turn = None                 # planned body turn toward a caller behind: dict(sign, dur_s, az_rad)
        self.turn_until = None           # the body turn runs until this time
        self.turn_t0 = self.turn_plan = self.turn_home_t = self.turn_home_from = None
        self.gyro = GyroTurn(self.gate.log if self.gate is not None else None) if self.gate is not None else None
        self.finder = None               # facefind.FaceFinder (run_live starts it) or a test double with latest(now)
        self.attend_s = float(getattr(args, "attend", ATTEND_S))
        self.attend_until = None         # attention phase runs until this time (extended by calls and face sightings)
        self.attend_base = None          # (yaw, pitch) the scan is built around
        self.face_t = None               # last face sighting time
        self.face_used_t = -1e9          # frame time of the last sighting acted on
        self.face_seen = False           # a face was seen in this attention phase
        self.scan = None                 # [(until, yaw)] remaining scan steps, [] when the scan is spent
        self.no_face_since = None
        self.deaf_from_quack = False
        self.calls = []                  # per response records (tests / sim)
        self.rows = None                 # offline drivers collect (t, head, events) here
        self.heartbeat_at = now() + 10
        self.cpu0, self.wall0 = time.process_time(), time.perf_counter()

    # --- sound side
    def hear(self, t, block):
        """One 20 ms block. Returns a detection dict when a call was localised."""
        self.ring.append((t, block))
        if self.bank is not None and self.bank.playing():
            self.det.deaf_until = max(self.det.deaf_until, t + QUACK_DEAF_S)
            self.deaf_from_quack = True
        elif self.deaf_from_quack and t >= self.det.deaf_until:
            self.deaf_from_quack = False
            self.det.reset_floor()       # a playback stream may have reconfigured the shared I2S0 (duck_selfcheck.py)
        if self.head is not None and self.head.busy:
            self.det.deaf_until = max(self.det.deaf_until, t + 0.1)   # own servos; the refractory covers the rest
        ev = self.det.update(t, block)
        if self.kws is not None:
            cand = self._hear_name(t, block, ev)
            if cand is not None:
                self.pending = cand
        elif ev is not None:
            self.pending = ev
        if self.pending is not None:
            ready, x, i_on = self._window(self.pending["t"])
            if ready:
                est = self._estimate(x, i_on) if x is not None else None
                det = dict(self.pending, decided_t=round(t + BLOCK / FS, 3), **(est or {}))
                self.pending = None
                if est is not None:
                    return det
                self.log.write("skip", why="call heard but the ring no longer holds its start or it had no voice bins",
                               t=det["t"])
        return None

    def _estimate(self, x, i_on):
        if isinstance(self.loc, CallLocaliser):
            return self.loc.estimate(x, i_on)
        return self.loc.estimate(x[max(0, i_on - BLOCK // 2):])

    def _window(self, t_onset):
        """(ready, x, i_onset): the localiser's audio around the onset out of the ring: self.before samples before the
        onset block's centre and self.after after it. ready is False while that audio has not been heard yet; x is
        None when the ring no longer holds its start."""
        t_on = t_onset + 0.5 * BLOCK / FS
        t0 = t_on - self.before / FS
        need_end = t_on + self.after / FS
        have = [b for b in self.ring if b[0] + BLOCK / FS > t0 - 1e-9]
        if not have or have[-1][0] + BLOCK / FS < need_end - 1e-9:
            return False, None, None
        x = np.concatenate([b[1] for b in have])
        off = int(round((t0 - have[0][0]) * FS))
        if off < 0:
            x = x[: self.before + self.after + off]           # the ring starts late: fewer samples before the onset
            return True, (x if len(x) >= self.after + BLOCK else None), self.before + off
        x = x[off: off + self.before + self.after]
        return True, (x if len(x) >= self.before + self.after - 1 else None), self.before

    def pick_onset(self, t_hit):
        """The detector onset nearest the word's estimated start (t_hit - KW_BACK_S), among those KW_ONSET_WIN before
        the spot; None when the detector heard none there."""
        lo, hi = t_hit - KW_ONSET_WIN[1], t_hit - KW_ONSET_WIN[0]
        cands = [o for o in self.onsets if lo <= o["t"] <= hi]
        if not cands:
            return None
        est = t_hit - KW_BACK_S
        return min(cands, key=lambda o: abs(o["t"] - est))

    def _hear_name(self, t, block, ev):
        if ev is not None:
            self.onsets.append(ev)
        if self.head is not None and self.head.busy:
            # a take is running: a name now would be skipped anyway, and the spotter's decode bursts (up to 30 ms on
            # the A7Z's A76, 60 ms on an A55) would delay the 50 Hz head writes; it starts afresh after the take
            self.kws_paused = True
            return None
        if self.kws_paused:
            self.kws.reset()
            self.kws_paused = False
        hit = self.kws.feed(t, block, silent=self.deaf_from_quack)
        if hit is None:
            return None
        self.kw_hits += 1
        if hit["t_hit"] - self.last_kw_t < self.a.refractory:
            self.log.write("skip", why="name heard again within the refractory period", keyword=hit["keyword"],
                           t_hit=hit["t_hit"])
            return None
        onset = self.pick_onset(hit["t_hit"])
        t_on = onset["t"] if onset is not None else round(hit["t_hit"] - KW_BACK_S, 3)
        self.last_kw_t = hit["t_hit"]
        base = dict(onset) if onset is not None else dict(t=t_on)
        # the direction is decided by hear() once the ring holds the localiser's window around t_on
        return dict(base, onset_from="detector" if onset is not None else "keyword", keyword=hit["keyword"],
                    t_hit=hit["t_hit"], span_s=hit["span_s"])

    def respond(self, det, now):
        """Turn a detection into a take (azimuth in the head frame -> resting frame)."""
        az = det["az_rad"] + self.head_yaw_now
        az = (az + math.pi) % (2 * math.pi) - math.pi
        rec = dict(det, az_rest_rad=round(az, 4), head_yaw_now=round(self.head_yaw_now, 3))
        if self.head is not None:
            perf = self.head.start(now, az, self.a.pitch, hold=True)
            self.attend_until = now + self.attend_s
            self.attend_base = (self.head.last["yaw"], self.a.pitch)
            self.scan, self.no_face_since, self.face_seen = None, None, False
            rec.update(take=perf.take, behind=self.head.last["behind"], arrival_s=perf.arrival,
                       params={k: (round(v, 4) if isinstance(v, float) else v) for k, v in perf.params.items()},
                       events=perf.events, target_yaw=self.head.last["yaw"])
            novelty = float(perf.params.get("novelty", 1.0))
            if not any(e.get("kind") == "call" for e in perf.events):
                # the library drops the call at random on habituated or glancing takes; a name call is answered
                # unless the caller is really repeating (QUACK_NOVELTY_MIN)
                if novelty >= QUACK_NOVELTY_MIN:
                    t_q = now + (perf.arrival if perf.arrival is not None else 0.8) + QUACK_ALWAYS_OFF_S
                    self.quack_due.append((t_q, dict(kind="call", pitch=1.0, stretch=1.0, gain_db=0.0, own=True)))
                    rec["quack_own_at"] = round(t_q, 3)
                else:
                    rec["quack_skipped"] = dict(novelty=round(novelty, 3), why="caller repeating; head only")
            self.turn = self.plan_turn(az) if (self.head.last["behind"] and not getattr(self.a, "no_turn", True)) else None
            margin = det.get("margin")
            if self.turn is not None and margin is not None and not (margin >= TURN_MARGIN_MIN):
                rec["turn_skipped"] = dict(margin=margin, why=f"front/back margin under {TURN_MARGIN_MIN}: the bearing is a guess")
                self.turn = None
            if self.turn is not None and self.finder is not None and self.finder.latest(now) is not None:
                # 2026-10-30 table test: a face was locked in front and a noise "behind" started a turn; the turn tripped
                rec["turn_skipped"] = dict(why="a face is in view; the body stays")
                self.turn = None
            if self.turn is not None:
                rec["turn"] = dict(self.turn)
        self.responses += 1
        self.calls.append(rec)
        self.log.write("call", **rec)
        return rec

    @staticmethod
    def plan_turn(az_rest_rad, rate=TURN_RATE, keep=TURN_KEEP, bounds=TURN_S):
        """Body turn so the caller comes inside the head's reach: sign and seconds at TURN_VTHETA, or None."""
        rest = abs(az_rest_rad) - keep
        if rest <= 0:
            return None
        dur = float(np.clip(rest / rate, *bounds))
        return dict(sign=1.0 if az_rest_rad > 0 else -1.0, dur_s=round(dur, 2), az_rad=round(float(az_rest_rad), 4))

    def _quack(self, e):
        f = self.bank.play(e) if self.bank is not None else None
        self.log.write("quack", file=None if f is None else os.path.basename(f), pitch=e.get("pitch"),
                       stretch=e.get("stretch"), muted=self.a.mute or self.bank is None, own=bool(e.get("own")))

    # --- motion side
    def motion_tick(self, now):
        """50 Hz: write the head command, play due calls, run the body turn. Returns False when the control file was taken.

        A caller the head cannot reach: the take snaps the head toward the caller as usual; when it arrives the body
        starts turning on the spot (walk61 at TURN_VTHETA) and from then on this program holds the head on the caller
        in the turning body frame (yaw = bearing - estimated body rotation, pitch up to the face), so the head unwinds
        toward centre as the body comes round, the way a person turns; the turn ends when the bearing left is within
        TURN_KEEP, the head eases home over a second, and the control file goes back to the zero-command walk.
        """
        if self.head is None:
            return True
        head, events, active = self.head.tick(now)
        for e in events:
            if e.get("kind") == "call":
                self._quack(e)
        while self.quack_due and self.quack_due[0][0] <= now:
            self._quack(self.quack_due.pop(0)[1])
        if self.rows is not None and head is not None:
            self.rows.append((now, head, events))
        if self.turn_until is None and self.turn is not None and self.head.last is not None \
                and self.head.last["arrival"] is not None and now >= self.head.last["arrival"]:
            self._start_turn(now)
            head = None
        if self.turn_until is not None:
            return self._turn_tick(now)
        if self.attend_until is not None and not self.head.busy:
            self._attend_tick(now)
        if head is not None:
            self.head_yaw_now = float(head["head_yaw"] - self.head.default["head_yaw"])
            if self.writer is not None and not self.writer.write(head):
                self.log.write("yield", why="control file written by another program; take stopped", found=self.writer.taken)
                self.head.active_until, self.head.settle_at, self.head.holding = None, None, False
                self.turn, self.attend_until = None, None
                return False
        return True

    # --- attention: hold the gaze on the caller, find the face, wait
    def _attend_tick(self, now):
        """After the take (and after a body turn): the gaze stays on the caller; a face in the camera is centred and
        followed; with no face in view after FACE_WAIT_S the head sweeps SCAN_OFFSETS around the heard bearing, once;
        ATTEND_S after the last call or sighting the head drifts home (HeadPath.release)."""
        if now >= self.attend_until:
            self.attend_until = None
            self.head.release(now)
            self.log.write("attend_done", face_seen=self.face_seen)
            return
        face = self.finder.latest(now) if self.finder is not None else None
        if face is not None and face["t"] > self.face_used_t:
            self.face_used_t, self.face_t = face["t"], now
            yaw, pitch = self.head.gaze(now)
            yaw = yaw - FACE_GAIN * face["yaw_err"]       # face right of centre -> yaw down (head_yaw + is left)
            pitch = pitch + FACE_GAIN * face["pitch_err"]  # face above centre -> look up
            if self.head.aim(yaw, pitch):
                self.attend_until = now + self.attend_s
                self.scan, self.no_face_since = None, None
                self.attend_base = (self.head.gaze(now)[0], self.head.gaze(now)[1])
                if not self.face_seen:
                    self.face_seen = True
                    self.log.write("face", yaw_err_deg=round(math.degrees(face["yaw_err"]), 1),
                                   pitch_err_deg=round(math.degrees(face["pitch_err"]), 1), size_deg=round(math.degrees(face["size"]), 1),
                                   score=face.get("score"), gaze_yaw_deg=round(math.degrees(yaw), 1), gaze_pitch_deg=round(math.degrees(pitch), 1))
            return
        if self.no_face_since is None:
            self.no_face_since = now
        if self.finder is None or self.scan == [] or now - self.no_face_since < FACE_WAIT_S:
            return                       # no camera: nothing to scan with, the gaze waits on the heard bearing
        if self.scan is None:
            if self.face_seen:
                base, offs = self.head.gaze(now), SCAN_NEAR
            else:
                base, offs = self.attend_base or self.head.gaze(now), SCAN_OFFSETS
            self.scan = [(now + (i + 1) * SCAN_DWELL_S, base[0] + off) for i, off in enumerate(offs)]
            self.scan.append((now + (len(offs) + 1) * SCAN_DWELL_S, base[0]))   # back to where the sound came from
            self.scan_pitch = max(base[1], LOOK_PITCH) if not self.face_seen else base[1]
            self.log.write("scan", around_deg=round(math.degrees(base[0]), 1), steps=len(offs), near=self.face_seen)
        until, yaw = self.scan[0]
        if self.head.aim(yaw, self.scan_pitch) and yaw != getattr(self, "scan_sent", None):
            self.scan_sent = yaw
            self.det.deaf_until = max(self.det.deaf_until, now + 0.1)   # own servos as the head steps, not the whole sweep
        if now >= until:
            self.scan.pop(0)
            if not self.scan:
                self.face_seen = False       # a lost face is searched once; then wait where the sound came from

    def _start_turn(self, now):
        plan, self.turn = self.turn, None
        # the take's own call, not yet due, still happens (the express path stops writing from here)
        t0 = self.head.last["t"]
        for e in self.head.last["events"]:
            if e.get("kind") == "call" and t0 + e["t"] >= now:
                self.quack_due.append((t0 + e["t"], dict(e)))
        self.head.active_until, self.head.settle_at, self.head.holding = None, None, False
        self.turn_until = now + plan["dur_s"]
        self.turn_t0, self.turn_plan, self.turn_home_t = now, plan, None
        if self.gyro is not None:
            self.gyro.start(self.gate.log if self.gate is not None else None)
        self.log.write("turn", vtheta=plan["sign"] * TURN_VTHETA, dur_s=plan["dur_s"], az_deg=round(math.degrees(plan["az_rad"]), 1),
                       until=round(self.turn_until, 3), gyro=self.gyro is not None)

    def _turned(self, now):
        """Body rotation since the turn began, rad (+ left): the brain's gyro integral, else the planning rate."""
        if self.gyro is not None:
            th = self.gyro.update()
            if th is not None:
                return th
        return self.turn_plan["sign"] * TURN_RATE * (now - self.turn_t0)

    def _turn_head(self, now, theta=None):
        """Head on the caller in the turning body frame: yaw unwinds with the body rotation, pitch up."""
        plan = self.turn_plan
        theta = self._turned(now) if theta is None else theta
        yaw = float(np.clip(plan["az_rad"] - theta, -self.head.yaw_cap, self.head.yaw_cap))
        pitch = -float(np.clip(self.a.pitch, 0.0, HEAD_RANGE[1]))   # head_pitch delta, minus = up
        return yaw, pitch

    def _turn_tick(self, now):
        """The body turns at TURN_VTHETA until the caller's bearing is within TURN_KEEP of straight ahead by the gyro
        (or the time cap), then the attention phase takes over with the head on the caller."""
        plan = self.turn_plan
        self.det.deaf_until = max(self.det.deaf_until, now + 0.1)   # own servos while turning
        theta = self._turned(now)
        yaw, pitch = self._turn_head(now, theta)
        self.head_yaw_now = yaw
        head = want_head(np.array([0.0, pitch, yaw, 0.0]), self.head.default)
        done = now >= self.turn_until or plan["sign"] * (plan["az_rad"] - theta) <= TURN_KEEP
        if not done:
            left = max(0.0, self.turn_until - now)
            ok = self.writer is None or self.writer.write(head, vtheta=plan["sign"] * TURN_VTHETA, for_s=left + 1.0)
        else:
            ok = self.writer is None or self.writer.write(head)   # body stops; the gaze stays on the caller
        if not ok:
            self.log.write("yield", why="control file written by another program; body turn stopped", found=self.writer.taken)
            self.turn_until = self.attend_until = None
            return False
        if done:
            self.turn_until = None
            self.log.write("turn_done", az_deg=round(math.degrees(plan["az_rad"]), 1), turned_deg=round(math.degrees(theta), 1),
                           by="gyro" if (self.gyro is not None and self.gyro.ok) else "time", s=round(now - self.turn_t0, 2))
            self.det.deaf_until = max(self.det.deaf_until, now + 0.5)
            self.head.set_pose(yaw, -pitch)
            self.attend_until = now + self.attend_s
            self.attend_base = (yaw, -pitch)
            self.scan, self.no_face_since, self.face_seen = None, None, False
        return True

    def mode_info(self):
        info = dict(detector=type(self.det).__name__, localiser=type(self.loc).__name__)
        if isinstance(self.loc, CallLocaliser):
            info.update(loc_band=list(self.loc.band), elev_deg=[round(float(np.degrees(e)), 1) for e in self.loc.el],
                        call_window_s=self.loc.window_s, loc_weight=self.loc.weight, loc_snr_db=self.loc.snr_db)
        if isinstance(self.det, CallDetector):
            info.update(snr_db=round(10 * math.log10(self.det.snr), 1), min_bins=self.det.min_bins,
                        confirm_blocks=self.det.confirm_blocks, voicing=self.det.voicing)
        if self.kws is None:
            return dict(trigger="any-voice", **info)
        return dict(trigger="name", name=getattr(self.a, "name", None),
                    keywords=getattr(self.kws, "keywords_file", None), kws_model=getattr(self.kws, "model_dir", None),
                    kws_threshold=getattr(self.kws, "threshold", None), **info)

    def gate_ok(self):
        if self.gate is None:
            return True, None
        st = self.gate.state()
        return st["ok"], st

    # --- drivers
    def run_blocks(self, blocks, head_rows=None):
        """Offline: iterate (t, block) pairs; motion ticks follow the block clock (the same motion_tick as the robot,
        writing the control file unless --dry). Returns detections."""
        dets = []
        self.rows = head_rows
        clock = time.perf_counter
        for t, b in blocks:
            c0 = clock()
            det = self.hear(t, b)
            if det is not None:
                dets.append(self.respond(det, t + BLOCK / FS))
                if self.a.once and self.responses >= self.a.once:
                    break
            self.motion_tick(t)
            self.block_ms.append((clock() - c0) * 1000.0)
        return dets

    def run_live(self, cap):
        a, log = self.a, self.log
        ok, st = self.gate_ok()
        if not ok:
            sys.exit(f"namecall: refused, {st['why'] if st else 'gate'}")
        if st and st["mode"] == "stand":
            if self.writer is None or not self.writer.write(None):
                sys.exit("namecall: refused, the brain stands but the control file belongs to another program")
            log.write("start", note="brain in stand mode: wrote the zero-command walk (stand61), waiting for walk mode")
            t_end = self.now() + 6.0
            while self.now() < t_end:
                time.sleep(0.2)
                ok, st = self.gate_ok()
                if ok and st["mode"] == "walk":
                    break
            else:
                sys.exit(f"namecall: refused, the brain did not enter walk mode ({st['why'] if st else '?'})")
            time.sleep(1.5)   # stand61 settles before the first take
        log.write("start", brain=st, lock_free=lock_free(), procs=procs_named(), mute=a.mute, no_head=a.no_head,
                  threshold_db=a.threshold_db, refractory_s=a.refractory, bank=0 if self.bank is None else len(self.bank.files),
                  default_head=None if self.head is None else self.head.default, **self.mode_info())
        period = BLOCK / FS
        next_tick = time.perf_counter()
        next_gate = self.now() + 0.5
        try:
            while True:
                try:
                    item = cap.q.get(timeout=1.0)
                except queue.Empty:
                    log.write("capture", why="no audio block for 1 s", err=cap.err)
                    if cap.proc is not None and cap.proc.poll() is not None:
                        sys.exit(f"namecall: capture ended: {cap.err}")
                    continue
                if item is None:
                    sys.exit(f"namecall: capture ended: {cap.err}")
                t, block = item
                det = self.hear(t, block)
                now = self.now()
                if det is not None:
                    if self.head is not None and self.head.busy:
                        log.write("skip", why="a take is running", az_deg=det["az_deg"])
                    else:
                        ok, st = self.gate_ok()
                        if not ok:
                            log.write("skip", why=st["why"], az_deg=det["az_deg"])
                        else:
                            self.respond(det, now)
                if not self.motion_tick(now):
                    pass
                if now >= next_gate:
                    next_gate = now + 0.5
                    ok, st = self.gate_ok()
                    if not ok and (self.head is None or not self.head.active or st["mode"] not in ("walk",)):
                        if st and st["mode"] not in ("walk", "stand"):
                            log.write("stop", why=st["why"])
                            sys.exit(f"namecall: stopped, {st['why']}")
                        if st and st["why"] and "stale" in st["why"]:
                            log.write("stop", why=st["why"])
                            sys.exit(f"namecall: stopped, {st['why']}")
                if now >= self.heartbeat_at:
                    self.heartbeat_at = now + 10
                    cpu = (time.process_time() - self.cpu0) / max(1e-6, time.perf_counter() - self.wall0)
                    self.cpu0, self.wall0 = time.process_time(), time.perf_counter()
                    floor = self.det.floor
                    log.write("heartbeat", floor_db=None if floor is None else round(floor, 1),
                              blocks=cap.n, gaps=cap.gaps, cpu_share=round(cpu, 3), responses=self.responses,
                              kw_hits=self.kw_hits,
                              writes=None if self.writer is None else self.writer.writes, brain=st and st.get("mode"),
                              face=None if self.finder is None else self.finder.stats())
                if a.once and self.responses >= a.once and (self.head is None or not self.head.active) \
                        and self.turn is None and self.turn_until is None and self.attend_until is None and not self.quack_due:
                    # the drift home has finished too: the last command is the policy default
                    log.write("done", responses=self.responses)
                    break
        except KeyboardInterrupt:
            log.write("stop", why="Ctrl-C")
        finally:
            cap.stop()
            if self.writer is not None and self.head is not None:
                self.writer.write(want_head(np.zeros(4), self.head.default))   # head home; the brain keeps balancing


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--device", default=None, help="ALSA capture device (default: hw:CARD=sndi2s0,DEV=0 found by name)")
    ap.add_argument("--wav", default=None, help="replay a 4-channel wav instead of the microphones")
    ap.add_argument("--cmd", default=CMD_FILE)
    ap.add_argument("--brain-logs", default=BRAIN_LOGS)
    ap.add_argument("--log", default=None, help="default ~/duck-logs/namecall_<start>.jsonl")
    ap.add_argument("--sounds", default=None, help="recordings for the quacks (default: walk_wired's sounds folder)")
    ap.add_argument("--bank-dir", default="/tmp/namecall_calls")
    ap.add_argument("--detector", choices=("bins", "energy"), default="bins",
                    help="bins: per-bin SNR over a tracked noise spectrum (catches 2 m calls); energy: band energy over a floor")
    ap.add_argument("--snr-db", type=float, default=DET_SNR_DB, help="bins detector: a bin counts this far over its noise")
    ap.add_argument("--min-bins", type=int, default=DET_MIN_BINS, help="bins detector: voice bins in a 20 ms block for an onset")
    ap.add_argument("--confirm-blocks", type=int, default=DET_CONFIRM, help="bins detector: of the next 3 blocks, this many must hold half the bins")
    ap.add_argument("--voicing", type=float, default=DET_VOICING,
                    help="bins detector: least harmonicity (0-1) of the onset's first 60-80 ms in 300-1500 Hz; 0 = off")
    ap.add_argument("--threshold-db", type=float, default=12.0, help="energy detector: onset over the room floor")
    ap.add_argument("--rise-db", type=float, default=6.0, help="energy detector: onset over the quietest of the last 100 ms")
    ap.add_argument("--localiser", choices=("call", "short"), default="call",
                    help="call: masked SRP-PHAT over the whole call with an elevation prior; short: 64 ms GCC at the onset")
    ap.add_argument("--loc-band", default="%g,%g" % LOC_BAND, help="Hz, call localiser band (low,high)")
    ap.add_argument("--elev", default=",".join("%g" % e for e in LOC_ELEV),
                    help="deg, caller elevation prior; several values (comma) search over them")
    ap.add_argument("--call-window", type=float, default=CALL_WINDOW_S, help="s after the onset the call localiser accumulates")
    ap.add_argument("--loc-snr-db", type=float, default=3.0, help="call localiser: a time-frequency bin counts this far over its noise on all mics")
    ap.add_argument("--loc-weight", choices=("soft", "hard"), default="soft", help="call localiser: weight bins by SNR or mask them")
    ap.add_argument("--refractory", type=float, default=2.5, help="s between accepted calls")
    ap.add_argument("--floor-tau", type=float, default=3.0, help="s, room floor tracking")
    ap.add_argument("--pitch", type=float, default=LOOK_PITCH,
                    help="gaze rad up for the caller; 1.1 = the head pitch cap, camera 30 deg up, a standing face at 1-2 m")
    ap.add_argument("--turn", action="store_true",
                    help="turn the body on the spot (vtheta 0.3) toward a caller the head cannot reach; off by default since the "
                         "2026-10-30 table test, where the turn tripped the duck 2.3 s in")
    ap.add_argument("--no-turn", action="store_true", help="accepted for old start lines; the body turn is off unless --turn")
    ap.add_argument("--no-keepalive", action="store_true",
                    help="do not hold a silent playback stream open (then every quack silences the capture)")
    ap.add_argument("--no-face", action="store_true",
                    help="no camera: the attention phase holds the heard bearing without looking for the face")
    ap.add_argument("--attend", type=float, default=ATTEND_S, help="s the gaze waits on the caller after the last call or face")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--once", type=int, default=0, help="stop after N responses (0 = run on)")
    ap.add_argument("--mute", action="store_true", help="no quack (first robot test)")
    ap.add_argument("--no-sound", action="store_true", help="do not even render the call bank")
    ap.add_argument("--no-head", action="store_true", help="detect and localise only, no control-file writes")
    ap.add_argument("--smooth", action="store_true", help="send the take's targets as they are (no EMA pre-inverse)")
    ap.add_argument("--idle", action="store_true", help="stream the Perlin idle between calls (50 Hz writes all the time)")
    ap.add_argument("--swap-ears", action="store_true", help="ch0 is the right ear")
    ap.add_argument("--no-gate", action="store_true", help="skip the brain checks (off-robot only)")
    ap.add_argument("--dry", action="store_true", help="do not write the control file (prints the writes count)")
    ap.add_argument("--default-head-file", default=None, help="json {joint: rad} instead of the stand61 metadata")
    ap.add_argument("--quiet", action="store_true")
    trig = ap.add_mutually_exclusive_group()
    trig.add_argument("--any-voice", action="store_true", help="every voice-band onset is a call (tests, listen-only checks)")
    trig.add_argument("--name", choices=sorted(KEYWORDS), default=None,
                      help="respond only to this name (keyword spotter, --spotter); mochi is the "
                           "default on the robot since 2026-10-30 (Shawn: answer only to Mochi); --wav replays stay any-voice")
    ap.add_argument("--spotter", choices=("own", "sherpa"), default="own",
                    help="name spotter: own = ownkws.py, trained on Shawn's calls (default); sherpa = the public keyword model")
    ap.add_argument("--own-model", default=None, help="ownkws model .npz (default namecall-20261029/models/mochi_own.npz)")
    ap.add_argument("--own-threshold", type=float, default=None, help="P(mochi) to fire (default: the threshold stored in the model)")
    ap.add_argument("--kws-model", default=None, help=f"model folder (default ~/rt/models/kws/{KWS_MODEL_NAME})")
    ap.add_argument("--kws-keywords", default=None, help="keywords file (default namecall-20261029/keywords_<name>.txt)")
    ap.add_argument("--kws-score", type=float, default=1.0, help="boost for keyword lines without their own :x")
    ap.add_argument("--kws-threshold", type=float, default=0.25, help="threshold for lines without their own #x")
    ap.add_argument("--kws-threads", type=int, default=1)
    ap.add_argument("--kws-gain-db", type=float, default=0.0, help="gain before the spotter")
    ap.add_argument("--onset-gap", type=float, default=ONSET_GAP_S, help="s, detector refractory in name mode")
    a = ap.parse_args(argv)
    if a.any_voice:
        a.name = None
    elif a.name is None and not a.wav:
        a.name = "mochi"
    a.no_turn = not a.turn      # the body turn is opt-in (--turn); --no-turn is kept for old start lines
    return a


def replay(nc, src, log):
    """--wav: run the recording through the chain as fast as it goes; returns (detections, cost stats)."""
    if src.fs != FS:
        raise SystemExit(f"namecall: the wav is {src.fs} Hz, needs {FS}")
    c0, w0 = time.process_time(), time.perf_counter()
    dets = nc.run_blocks(src.blocks())
    cpu, wall = time.process_time() - c0, time.perf_counter() - w0
    audio_s = len(src.x) / float(src.fs)
    ms = np.asarray(nc.block_ms) if nc.block_ms else np.zeros(1)
    stats = dict(audio_s=round(audio_s, 2), cpu_s=round(cpu, 3), wall_s=round(wall, 3),
                 cpu_share=round(cpu / max(audio_s, 1e-9), 4), block_ms_p50=round(float(np.percentile(ms, 50)), 2),
                 block_ms_p99=round(float(np.percentile(ms, 99)), 2), block_ms_max=round(float(ms.max()), 2),
                 kw_hits=nc.kw_hits, responses=nc.responses, **nc.mode_info())
    log.write("replay", **stats)
    return dets, stats


def main(argv=None):
    a = parse_args(argv)
    log_path = a.log or os.path.expanduser(time.strftime("~/duck-logs/namecall_%Y%m%d-%H%M%S.jsonl"))
    log = Log(log_path, echo=not a.quiet)
    if a.wav:
        a.no_gate = True
        nc = NameCall(a, log)
        dets, stats = replay(nc, WavSource(a.wav), log)
        print(f"{len(dets)} call(s) in {a.wav}: " + ", ".join(
            f"{d['t']:.2f} s az {d['az_deg']:+.0f} deg" + (f" ({d['keyword']} at {d['t_hit']:.2f} s)" if "keyword" in d else "")
            for d in dets))
        print("cost: " + json.dumps(stats))
        return 0
    if not a.no_gate and lock_free():
        sys.exit("namecall: refused, nobody holds the robot I/O lock (no walk_wired.py brain running)")
    if "duck_selfcheck.py" in procs_named():
        sys.exit("namecall: refused, duck_selfcheck.py is using the sound card; try again when it is done")
    dev = a.device
    if dev is None:
        n = find_card()
        if n is None:
            sys.exit(f"namecall: no {CARD_NAME} sound card (I2S0 overlay not loaded?)")
        dev = f"hw:CARD={CARD_NAME},DEV=0"
    nc = NameCall(a, log)
    if nc.bank is not None and not nc.bank.available and not a.mute:
        log.write("warn", why="no duck recordings found; quacks are silent")
    keep = None
    if not a.no_keepalive:
        keep = PlaybackKeepAlive().start()
        log.write("keepalive", alive=keep.alive, err=keep.err, cmd=" ".join(keep.cmd))
        if not keep.alive:
            log.write("warn", why="no silent playback stream: the microphones go dead after each quack until the capture is reopened")
    if nc.head is not None and not a.no_face:
        try:
            from facefind import FaceFinder
            nc.finder = FaceFinder().start()
            log.write("face_finder", rate_hz=nc.finder.rate_hz, det_size=nc.finder.det_size)
        except Exception as e:     # no camera daemon, no models: the attention phase holds the heard bearing instead
            nc.finder = None
            log.write("warn", why=f"face finder not started: {e!r}; attention holds the heard bearing")
    cap = Capture(dev).start()
    try:
        nc.run_live(cap)
    finally:
        if keep is not None:
            keep.stop()
        if nc.finder is not None:
            nc.finder.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Expressive intents and affect: what the mind may ask for. Never joint motions.

Affect is valence (-1 unhappy .. +1 happy) and arousal (0 asleep .. 1 excited). Motion quality uses the four Laban
Effort factors, each in 0..1:
  time   0 sustained .. 1 sudden
  weight 0 light     .. 1 strong
  space  0 indirect  .. 1 direct
  flow   0 free      .. 1 bound
"Cute" is light, sudden but small, indirect (head tilt), free (bouncy springs).

Targets are gaze directions in the body's resting frame: yaw + left, pitch + up, radians.
"""
from dataclasses import dataclass, field

KINDS = ("acknowledge", "attend", "greet", "startle", "content_idle")


def _clip(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


@dataclass(frozen=True)
class Affect:
    valence: float = 0.3
    arousal: float = 0.5

    def __post_init__(self):
        object.__setattr__(self, "valence", _clip(float(self.valence), -1.0, 1.0))
        object.__setattr__(self, "arousal", _clip(float(self.arousal)))


@dataclass(frozen=True)
class Effort:
    time: float
    weight: float
    space: float
    flow: float


@dataclass(frozen=True)
class Target:
    yaw: float = 0.0
    pitch: float = 0.0
    label: str = "owner"


@dataclass(frozen=True)
class Intent:
    kind: str
    target: Target = field(default_factory=Target)
    warmth: float = 0.5   # how much the pet likes the target (0 neutral .. 1 beloved)
    energy: float = 0.5   # how much effort the response gets (0 minimal .. 1 full)
    affect: Affect = field(default_factory=Affect)
    seconds: float = 0.0  # content_idle: how long; 0 = until the next intent

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown intent {self.kind!r}; one of {KINDS}")
        object.__setattr__(self, "warmth", _clip(float(self.warmth)))
        object.__setattr__(self, "energy", _clip(float(self.energy)))


def acknowledge(target, warmth=0.6, energy=0.6, affect=None):
    """Answer a call: look at the caller, a small cute reaction, usually a vocal."""
    return Intent("acknowledge", _target(target), warmth, energy, affect or Affect())


def attend(target, affect=None):
    """Look at something (sound, motion, a face) without a social reply."""
    return Intent("attend", _target(target), 0.3, 0.4, affect or Affect())


def greet(target, warmth=0.9, energy=0.8, affect=None):
    """The owner came back: acknowledge plus bobbing and a longer vocal."""
    return Intent("greet", _target(target), warmth, energy, affect or Affect(0.8, 0.8))


def startle(target, affect=None):
    """A sudden stimulus: recoil, snap toward it, settle."""
    return Intent("startle", _target(target), 0.0, 1.0, affect or Affect(-0.3, 0.9))


def content_idle(seconds=0.0, affect=None):
    """Living stillness: drifting gaze, breathing posture."""
    return Intent("content_idle", Target(0.0, 0.0, "none"), 0.5, 0.2, affect or Affect(0.5, 0.25), seconds)


def _target(t):
    if isinstance(t, Target):
        return t
    if isinstance(t, (tuple, list)):
        return Target(float(t[0]), float(t[1]) if len(t) > 1 else 0.0)
    if isinstance(t, dict):
        return Target(float(t.get("yaw", 0.0)), float(t.get("pitch", 0.0)), str(t.get("label", "owner")))
    raise TypeError(f"target must be Target, (yaw, pitch) or dict, not {type(t).__name__}")


def effort_for(intent):
    """Laban Effort of a response, from the intent and its affect."""
    a, v = intent.affect.arousal, intent.affect.valence
    if intent.kind == "startle":
        return Effort(time=1.0, weight=0.8, space=1.0, flow=0.9)
    time = _clip(0.15 + 0.6 * a + 0.25 * intent.energy)
    weight = _clip(0.15 + 0.35 * (1 - intent.warmth) + 0.2 * max(0.0, -v))
    space = _clip(0.85 - 0.6 * intent.warmth + 0.15 * intent.energy)
    flow = _clip(0.45 - 0.35 * v + 0.2 * (1 - a))
    return Effort(time, weight, space, flow)

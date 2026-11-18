"""Does the runtime evaluator carry a recurrent policy's state? One episode of flight_eval.episode with the stateful
wrapper counted: policy calls, calls that started from a zero state, ticks with more than one call of the same file.

  $PY train/ts_statecheck.py <models dir> <manifest> <case> [extra probe flags ...]
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flight_eval as fe  # noqa: E402
import numpy as np  # noqa: E402

log = []
orig = fe._StatefulSession.run


def run(self, out, feed):
    b, tick = self.brain, self.brain._hist_tick
    st = b._hist_state.get(self.group)
    gap = tick - b._hist_last.get(self.group, -10 ** 9)
    zero = st is None or (gap > fe.RECURRENT_MAX_GAP if self.state_name == "state_in" else gap != 1)
    res = orig(self, out, feed)
    log.append((tick, self.group, bool(zero), float(np.abs(b._hist_state[self.group]).max())))
    return res


fe._StatefulSession.run = run
models, manifest, case = sys.argv[1:4]
r = fe.episode((models, manifest, case, 0, 0.0, 8.0, False, sys.argv[4:]))
per_tick = collections.Counter(t for t, _, _, _ in log)
zeros = [t for t, _, z, _ in log if z]
print(json.dumps(dict(fell_at=r["fell_at"], speed=r["speed"], calls=len(log), ticks_with_calls=len(per_tick),
                      first_tick=min(per_tick) if per_tick else None, last_tick=max(per_tick) if per_tick else None,
                      ticks_with_2_calls=sum(1 for v in per_tick.values() if v > 1), zero_state_calls=len(zeros),
                      zero_state_ticks_first20=zeros[:20], groups=len({g for _, g, _, _ in log}),
                      state_abs_max_last=log[-1][3] if log else None)))

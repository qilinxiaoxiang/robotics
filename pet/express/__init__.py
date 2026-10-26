"""Expressive motion layer: the mind's expressive intents become timed, varied, body-specific channel motion.

The mind calls `Expressor.submit(intent, now)` with an intent from `pet.express.intents`; the body loop calls
`Expressor.step(now)` at 50 Hz and sends the returned outputs to its joints and devices. See README.md.
"""
from .intents import Affect, Effort, Intent, Target, acknowledge, attend, content_idle, greet, startle  # noqa: F401
from .express import Expressor  # noqa: F401

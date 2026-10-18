# Rear electronics pack: leg-reach evidence

Frame: robot frame in mm, x forward, y left, z up. Scripts and scratch copies: `reach_pitch.py` (sweep), `reach_shift.py`
(how far the limiting part must move), `reach_summary.py` (figure and headline). Run with the bounded CAD runner; the sweep
takes about 20 minutes per leg.

## Bend-forward (nose-down hip pitch) reach, 2026-10-12

`reach-pitch.json`, `reach-pitch.png`. Compares the Layout L pack (plate trimmed to the original power-support silhouette)
with the original battery plus power support. Grid per leg: knee 0/22.5/45/67.5/90°, four ankle settings (zero, level,
range ends), hip yaw 0/±10°, hip roll 0/±10°; hip pitch in 2° steps to ±90°; contact = gap under 1 mm (exact manifold3d
gap at every first contact, 0.4 mm distance field elsewhere).

Headline, worst case over ankle/yaw/roll (|hip pitch| at first contact, deg): straight leg pack 52 / 82 (left / right)
against baseline 24 / 24; half crouch 24 / 26 against 10 / 10; full crouch 52 / 88 against 32 / 32. The nominal posture
(ankle level, yaw 0, roll 0) never touches either solid within ±90°. Nose-up: no contact anywhere.

The pack is more limiting than the baseline in 28 of 360 combinations, all on the left leg at hip yaw −10°: roll +10°
(pack 52° against 68–74°) and roll 0° with knee 0/25 % (pack 70/74° against no contact). Every one is the left shin's
lower part at (−37…−38.6, 24.9…26.0, 10.2…11.6) hitting the outboard-bottom edge of the junction box J (box x −38…−28,
y 13…25, z 11…27). Required move to keep 1 mm at every pitch the baseline allows: J's outer face at y ≤ 18.5 (6.5 mm
inboard); or 15 mm up; moving it back does not fit. After that move the next limiter over those angles is the plate
(1.6–6.9 mm) or the DFR1202 (4.4–5.6 mm). The OpenRB bay's lower-front corner is not a limiter: its contacts at 24–26°
(knee 50 %, ankle at a range end, roll ±10°) sit where the original battery underside already touched at 10°.

Decision carried into the pack geometry: J moves inboard to y ≤ 18.5; the bay corner keeps its plain face.

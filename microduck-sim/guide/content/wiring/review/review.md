# OpenRB wiring drawing review (rear converter box layout)

**2026-10-14 layout F (mirrored, final 16:47 meshes): drawing redrawn (XL4015 unturned, IN right, OUT left, + the lower screw; 5991 turned 270 degrees, USB-C left, terminal right). Independent re-review verdict: FAIL on one point. The #1 OUT+ label sat above the OUT- label although + is the lower screw, so a reader matching labels top to bottom would swap polarity. Fixed: every terminal marker now names its screw height in both pages (for example `13 #1 OUT+ (lower)`, `14 #1 OUT- (upper)`, `9 5991 + (lower)`; Chinese `（下）`/`（上）`), and openrb-wiring-large.png was re-captured at 16:55 after the guide rebuild. Still open from that review: in the 390 px inline view the titles crowd and 4 of 18 pin labels are dropped (pre-existing, the large view shows all 18); label 17 overlaps the middle board's edge in the large view. The rounds below are for the earlier layout.**

Reviewer: independent draw-diagrams reviewer agent, criteria `~/.claude/skills/draw-diagrams/references/aesthetic-principles.md`.
Artifacts: `openrb-wiring-large.png` (guide large view of step bench-test, 1400 px at scale 2) and the Chinese step-12 drawing in `bringup/BRINGUP.html` at 1280 px.

**Verdict: round 3 FAIL; blockers that could mislead a reader fixed after it, cosmetic findings left open (time box, 2026-10-14).**

Content check (round 3): connections correct in both languages. Box seen from behind, #1 (7 V) left, #2 (5 V) right, OUT at the top; 5991 below; Pi turned 180 degrees with pin 2 rightmost, then 6, 8, 10. All 18 end markers drawn on desktop (probe counts pills: 18 at 1280 px).

Rounds:
- 1 and 2 (old layout, boards upside down): FAIL on leaders through pills and pills on foreign wires.
- 3 (box layout): FAIL. Blockers: XL4015 titles placed in the centre lane could be read as the other board's title; short "Pi" title among the J4 pills; pills 9, 10 and 5 on board photos; in Chinese, the Rx leader passes through the Tx pill, the J4 + pill touches the black wire, and the #2 IN pills sit swapped relative to their screws.
- Fixed after round 3: each converter title names its side ("#1 left: 6.80 V", "#2 right: 5.00 V"; Chinese "#1（左）6.80 V", "#2（右）5.00 V"), and the Chinese IN markers name the wire colour ("#2 IN+（红）") so a swapped pill position cannot be read as the wrong screw. wiring-kit label placement now pads label boxes by the wire stroke, keeps titles off wires and other modules where it can, measures pills with 8 % spare, and never drops a pill because its leader would cross another label.

Open (cosmetic, not re-reviewed):
- The "#2 right" title sits in the centre lane next to #1's photo edge rather than on #2.
- Pills 9 and 10 (5991 terminal) and 5 (Pi pin 8) partly cover board photos.
- Chinese: the Rx leader passes the Tx pill's right end; "端子 +" pill is 1 px from the black J4 − wire; the #2 IN pills are swapped (their text now names the colour).
- Several leaders cross wires that are not their own.
- On a 390 px phone the inline overview is crowded and shows 12 of 18 markers, as before; the full-screen view and wire-by-wire mode carry the rest.
- The wire passage is described in the caption; wiring-kit has no waypoint to draw wires through it.

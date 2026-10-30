# gaze.py on the robot, 2026-10-30 05:39 (home, closed-loop stand under the walking policy)

First live run of PLAN-continuous-vision.md item N2: the head follows the orange ball every camera frame; nothing
projected to the floor decides the motion.

- `gaze_1030-053922.jsonl`: `--observe 8`, no head motion. Ball found in every frame at (231, 132), 6-7 px wide,
  single-frame projection 0.88 m ahead, 0.115 m left, head 0.362 / neck 0.161.
- `gaze_1030-053947.jsonl`: `--max-s 20`, head following. 201 frames, the ball in all of them. The yaw loop centred
  the ball (u 230 -> 322, aim 320) in 0.58 s and held it there for 19 s. The head yaw servo settled at 0.126 rad while
  the command integrated to 0.202: the loop closed on the picture error and did not need to know that gain (the
  point of image-space control, Chaumette and Hutchinson 2006). The pitch loop wanted to look up (ball at row 104,
  aim 223) and sat at its lower bound 0.35, the policy's default; the policy itself holds the head at 0.466 at that
  command, so a far ball stays high in the picture. The aim row matters near, where the pitch range is downward.
- Chain evidence: the single-frame projection of the same still ball read 0.879 m at head 0.362 and 0.861 m at head
  0.466, 1.8 cm apart from a 0.1 rad head move. The landmark filter attributed it to a camera pitch bias of
  -2.1 deg with range 0.98 m (sd 3.3 cm); with head motion only, range and bias are weakly separable
  (test_gaze.py::test_filter_standing_still_reports_the_range_as_uncertain), so this is a lead for N1, not a number.

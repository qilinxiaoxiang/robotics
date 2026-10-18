# SPDX-License-Identifier: MIT
"""Launch already-installed 61D community main with a latched bench supervisor.

Does not install/modify community files or change operating mode, offsets, gains,
ONNX, geometry or firmware. Only this explicit entry uses the additional guard.
"""
import argparse
import hashlib
from pathlib import Path
import signal
import sys
import time
from runtime_guard import GuardController, SafetyStop

def run_main(module, controller_factory, imu_to_body, *, max_session_s=120):
    previous = module.RobotController
    created = []
    def factory(*args, **kwargs):
        raw = controller_factory(*args, **kwargs)
        guard = GuardController(raw, imu_to_body, max_session_s=max_session_s)
        created.append(guard)
        # IMU worker can need a little time at cold start; torque is already off.
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if raw.get_imu_status().get('valid') is True:
                break
            time.sleep(.01)
        guard.check()
        return guard
    module.RobotController = factory
    try:
        return module.main()
    finally:
        for guard in created:
            guard.stop('launcher exit: normal, exception or SIGTERM')
            try:
                guard.raw.shutdown()
            except Exception:
                pass
            if guard.last_torque_off_error:
                print('TORQUE-OFF REQUEST FAILED; SWITCH EN OFF: ' + guard.last_torque_off_error, file=sys.stderr)
        module.RobotController = previous

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--community', type=Path, required=True, help='Directory containing community src/')
    ap.add_argument('--max-session-seconds', type=float, default=120)
    args = ap.parse_args()
    if not 1 <= args.max_session_seconds <= 600:
        ap.error('supervised session must be 1..600 seconds; this is not cell-voltage protection')
    source = args.community.resolve() / 'src'
    if not (source / 'main.py').is_file():
        ap.error('community/src/main.py not found')
    # Refuse the old 51/53D entry or an unreviewed replacement before opening hardware.
    expected_walk = "ec7b2de0bdf9230022484f507344054a7bc9c77e5224c284b64b2dea7f209964"
    if hashlib.sha256((source / "moves/walk.py").read_bytes()).hexdigest() != expected_walk:
        ap.error("Install the frozen official-61D overlay first; unreviewed walk source rejected")
    sys.path.insert(0, str(source))
    import constants
    if constants.KP_RL != 200 or constants.BAM_VIN != 5:
        ap.error("Expected the KP200 / 5V constants overlay before opening hardware")
    import main as community_main
    from robot_controller import RobotController
    from imu_reader import imu_quat_to_body
    previous_term = signal.getsignal(signal.SIGTERM)
    def terminate(signum, frame):
        raise SafetyStop('SIGTERM requested')
    signal.signal(signal.SIGTERM, terminate)
    try:
        run_main(community_main, RobotController, imu_quat_to_body, max_session_s=args.max_session_seconds)
    finally:
        signal.signal(signal.SIGTERM, previous_term)

if __name__ == '__main__':
    main()

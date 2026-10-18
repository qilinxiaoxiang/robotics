"""Bound CAD memory/time: four measured light jobs or one exclusive larger job.

This launcher is required for further head-layout calculations after the
2026-10-08 memory-pressure incident. It never signals processes it did not start.
It also gates on the whole machine (2026-10-12 freeze: a CAD audit ran beside an
8-worker training job on the 16 GB laptop): a job starts only when the kernel's
available-memory estimate covers its budget plus a reserve, and it is stopped if
the kernel reports critical memory pressure. A busy machine returns 75 like a
busy lock, so callers retry instead of swapping the machine to a halt.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def process_tree(root):
    output = subprocess.check_output(
        ['ps', '-axo', 'pid=,ppid=,rss='], text=True)
    rows = [tuple(map(int, line.split())) for line in output.splitlines()]
    owned = {root}
    while True:
        updated = owned | {pid for pid, parent, _ in rows if parent in owned}
        if updated == owned:
            break
        owned = updated
    return sum(rss for pid, _, rss in rows if pid in owned), sorted(owned)


RESERVE_MIB = float(os.environ.get('MICRODUCK_CAD_RESERVE_MIB', 2048))
# 2026-10-13 incident: a 156k-pose jaw sweep started mid-release held this lock for about four hours and a second
# agent then queued 1.5 hours of jaw rechecks behind it. The print gate itself takes about three minutes. Any job
# over this budget needs Shawn's explicit go, carried in MICRODUCK_CAD_LONG_JOB_OK (his words or the message id);
# without it the wall-time budget is clamped and the clamp is recorded. Every start and end is appended to
# .cad-queue.log next to the lock so `--status` answers who holds the lock and for how long.
CAP_SECONDS = 600
LEDGER = Path(__file__).with_name('.cad-queue.log')


def ledger_write(event):
    event['ts'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    with open(LEDGER, 'a') as f:
        f.write(json.dumps(event) + '\n')


def ledger_status():
    """Current lock holder and the last few jobs, from the ledger plus live pids."""
    rows = []
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    ended = {r['pid'] for r in rows if r.get('event') == 'end'}
    live = []
    for r in rows:
        if r.get('event') == 'start' and r['pid'] not in ended:
            try:
                os.kill(r['pid'], 0)
                live.append(r)
            except OSError:
                continue
    return live, rows[-12:]


def print_status():
    live, tail = ledger_status()
    if live:
        for r in live:
            print(f"holding: pid {r['pid']} since {r['ts']} budget {r['maxSeconds']} s "
                  f"long-job-ok={r.get('longJobOk') or '-'} :: {' '.join(r['command'])[:200]}")
    else:
        print('lock free')
    for r in tail:
        print(json.dumps(r)[:240])


def sysctl_int(name):
    return int(subprocess.check_output(['sysctl', '-n', name], text=True).strip())


def machine_memory():
    """Kernel estimate of available memory (MiB) and VM pressure (1 normal, 2 warn, 4 critical)."""
    total = sysctl_int('hw.memsize') / 2**20
    return total * sysctl_int('kern.memorystatus_level') / 100, sysctl_int('kern.memorystatus_vm_pressure_level')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-mib', type=float, default=512)
    parser.add_argument('--seconds', type=float, default=120)
    parser.add_argument('--wait-lock-seconds', type=float, default=0,
                        help='Queue using only the lightweight launcher, at most60seconds; CAD libraries start only after the lock is acquired')
    parser.add_argument('--parallel-light', action='store_true',
                        help='Permit at most four isolated light workers; each must fit within512MiB. Larger/unknown jobs stay exclusive.')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--status', action='store_true', help='Print who holds the lock and the recent ledger, then exit')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.status:
        print_status()
        return 0
    if args.report is None:
        parser.error('--report is required')
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or args.max_mib <= 0 or args.seconds <= 0:
        parser.error('Provide a command and positive resource budgets')
    long_job_ok = os.environ.get('MICRODUCK_CAD_LONG_JOB_OK', '').strip()
    clamped_from = None
    if args.seconds > CAP_SECONDS and not long_job_ok:
        clamped_from = args.seconds
        args.seconds = CAP_SECONDS
        print(f'Wall-time budget clamped from {clamped_from:.0f} to {CAP_SECONDS} s: jobs over {CAP_SECONDS} s need '
              f"Shawn's explicit go in MICRODUCK_CAD_LONG_JOB_OK (robotics/AGENTS.md, release time-box).", file=sys.stderr)
    if not 0 <= args.wait_lock_seconds <= 60:
        parser.error('Lock wait must be between0and60seconds')
    if args.parallel_light and args.max_mib > 512:
        parser.error('Parallel light workers have a512MiB maximum each')
    lock = open(Path(__file__).with_name('.cad-compute.lock'), 'a+')
    slot_locks = [open(Path(__file__).with_name(f'.cad-light-slot-{i}.lock'),'a+') for i in range(4)] if args.parallel_light else []
    acquired_slot = None
    queued = time.monotonic()
    while True:
        try:
            fcntl.flock(lock, (fcntl.LOCK_SH if args.parallel_light else fcntl.LOCK_EX) | fcntl.LOCK_NB)
            if args.parallel_light:
                for i,slot in enumerate(slot_locks):
                    try:
                        fcntl.flock(slot,fcntl.LOCK_EX | fcntl.LOCK_NB)
                        acquired_slot=i
                        break
                    except BlockingIOError:
                        continue
                if acquired_slot is None:
                    fcntl.flock(lock,fcntl.LOCK_UN)
                    raise BlockingIOError('All four light-worker slots are occupied')
            break
        except BlockingIOError:
            if time.monotonic()-queued >= args.wait_lock_seconds:
                print('Another bounded CAD check is running; no additional job started.', file=sys.stderr)
                live, _ = ledger_status()
                for r in live:
                    print(f"lock holder: pid {r['pid']} since {r['ts']} budget {r['maxSeconds']} s :: "
                          f"{' '.join(r['command'])[:160]}", file=sys.stderr)
                return 75
            time.sleep(.1)
    # Machine-wide admission: wait inside the same queue budget for memory, then give up with 75.
    while True:
        available, pressure = machine_memory()
        if available >= args.max_mib + RESERVE_MIB and pressure < 4:
            break
        if time.monotonic()-queued >= args.wait_lock_seconds:
            print(f'Machine memory busy: {available:.0f} MiB available, pressure level {pressure}; '
                  f'need {args.max_mib + RESERVE_MIB:.0f} MiB. No job started.', file=sys.stderr)
            return 75
        time.sleep(1)
    waited = time.monotonic()-queued
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               MKL_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1',
               NUMEXPR_NUM_THREADS='1', MICRODUCK_BOUNDED_CAD='1')
    # The BLAS limits do not promise to limit Manifold/TBB worker threads.
    process = subprocess.Popen(['/usr/bin/nice', '-n', '10', *command],
                               env=env, start_new_session=True)
    started = time.monotonic()
    ledger_write({'event': 'start', 'pid': process.pid, 'command': command, 'cwd': os.getcwd(),
                  'maxSeconds': args.seconds, 'clampedFromSeconds': clamped_from, 'maxMiB': args.max_mib,
                  'longJobOk': long_job_ok or None, 'report': str(args.report),
                  'mode': 'four-light-slots' if args.parallel_light else 'exclusive'})
    peak = 0
    reason = None
    last_pressure_check = 0.0
    interrupted = False

    def stop(signum, frame):
        nonlocal interrupted
        interrupted = True

    old_handlers = {s: signal.signal(s, stop) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        while process.poll() is None:
            rss, _ = process_tree(process.pid)
            peak = max(peak, rss)
            elapsed = time.monotonic() - started
            if interrupted:
                reason = 'interrupted'
            elif rss > args.max_mib * 1024:
                reason = 'process-tree-rss-limit'
            elif elapsed > args.seconds:
                reason = 'wall-time-limit'
            elif elapsed - last_pressure_check >= 1:
                last_pressure_check = elapsed
                if machine_memory()[1] >= 4:
                    reason = 'machine-memory-critical'
            if reason:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                break
            time.sleep(.25)
    finally:
        for s, handler in old_handlers.items():
            signal.signal(s, handler)
    result = {
        'command': command, 'pid': process.pid,
        'exitCode': process.returncode, 'stoppedByGuard': reason,
        'elapsedSeconds': round(time.monotonic() - started, 3),
        'peakSampledTreeRssMiB': round(peak / 1024, 3),
        'maxMiB': args.max_mib, 'maxSeconds': args.seconds,
        'lockWaitSeconds': round(waited, 3),
        'clampedFromSeconds': clamped_from, 'longJobOk': long_job_ok or None,
        'machineAvailableMiBAtStart': round(available), 'machinePressureAtStart': pressure, 'reserveMiB': RESERVE_MIB,
        'concurrencyMode': 'four-light-slots' if args.parallel_light else 'exclusive',
        'lightSlot': acquired_slot,
        'samplingIntervalSeconds': .25,
        'measurementScope': 'RSS samples; excludes compressed/swapped footprint; not a hard allocation cap',
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    ledger_write({'event': 'end', 'pid': process.pid, 'exitCode': process.returncode, 'stoppedByGuard': reason,
                  'elapsedSeconds': result['elapsedSeconds'], 'peakMiB': result['peakSampledTreeRssMiB']})
    print(json.dumps(result), flush=True)
    return 124 if reason else process.returncode


if __name__ == '__main__':
    sys.exit(main())

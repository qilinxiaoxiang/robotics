"""Verify prior training identity and reject bring-up as a visual-pickup handoff."""
import argparse
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parent.parent


def review(root=ROOT):
    context = json.loads((root / 'PROJECT-CONTEXT.json').read_text())
    training = context['training']
    results = json.loads((root / training['results']).read_text())
    summary = json.loads((root / training['summary']).read_text())
    errors = []
    for field, expected in [('checkpoint', 'checkpointSha256'), ('exported_actor', 'actorSha256')]:
        path = root / training[field]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != results[expected]:
            errors.append('Training artifact mismatch: ' + field)
    if not results['accepted'] or not results['learning']['accepted'] or summary['trainingDecisions'] <= 0:
        errors.append('Prior training evidence does not validate')
    contract = json.loads((root / context['current_build']['contract']).read_text())
    missing = sorted(set(context['required_capabilities']) - set(contract.get('implemented_capabilities', [])))
    pack = (root / context['current_build']['contract']).parent.parent
    policy = json.loads((pack / 'procurement/sourcing-policy.json').read_text())
    camera_holds = [key for key in ('camera', 'camera_ffc')
                    if policy['items'][key]['decision'] == 'review_hold']
    physical_path = contract.get('visual_pickup_physical_acceptance')
    physical = json.loads((root / physical_path).read_text()) if physical_path else {}
    trace_path = root / physical['trial_log'] if physical.get('trial_log') else None
    trace_verified = (trace_path is not None and trace_path.is_file()
                      and hashlib.sha256(trace_path.read_bytes()).hexdigest() == physical.get('trial_log_sha256'))
    physical_verified = (physical.get('kind') == 'hardware_visual_pickup'
                         and physical.get('build_revision') == contract['revision']
                         and physical.get('observation_source') == 'camera'
                         and physical.get('policy_checkpoint_sha256') == results['checkpointSha256']
                         and physical.get('accepted') is True
                         and physical.get('trials', 0) > 0 and trace_verified)
    return {
        'context_path': str((root / 'PROJECT-CONTEXT.json').resolve()),
        'training_evidence_verified': not errors,
        'training_errors': errors,
        'training_decisions': summary['trainingDecisions'],
        'recorded_initial_successes': results['initialSuccesses'],
        'recorded_trained_successes': results['trainedSuccesses'],
        'recorded_scripted_successes': results['scriptedSuccesses'],
        'recorded_trials': results['trials'],
        'training_reexecuted': False,
        'missing_capabilities': missing,
        'required_camera_items_on_hold': camera_holds,
        'project_handoff_ready': not errors and not missing and not camera_holds and physical_verified,
        'physical_acceptance_verified': physical_verified,
        'physical_tests': physical.get('trials', 0) if physical_verified else 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', choices=['project', 'bringup'], default='project')
    args = parser.parse_args()
    result = review()
    (P / 'project-context-review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if not result['training_evidence_verified'] or (args.scope == 'project' and not result['project_handoff_ready']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()

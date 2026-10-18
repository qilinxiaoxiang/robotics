"""Regression for losing the trained visual-pickup goal during procurement."""
import json
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest
from check_project_context import ROOT, review


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.context = json.loads((ROOT / 'PROJECT-CONTEXT.json').read_text())
        self.contract = self.context['current_build']['contract']
        paths = ['PROJECT-CONTEXT.json', self.contract,
                 'build-pack-20260913/procurement/sourcing-policy.json']
        paths += [self.context['training'][key] for key in ('results', 'summary', 'checkpoint', 'exported_actor')]
        for path in paths:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        # Reconstruct the actual failed bring-up configuration explicitly;
        # a future completed live project must not make this regression fail.
        path = self.root / self.contract
        contract = json.loads(path.read_text())
        contract['implemented_capabilities'] = ['teleoperated_walk', 'scripted_jaw_pickup']
        contract.pop('visual_pickup_physical_acceptance', None)
        path.write_text(json.dumps(contract))
        path = self.root / 'build-pack-20260913/procurement/sourcing-policy.json'
        policy = json.loads(path.read_text())
        for key in ('camera', 'camera_ffc'):
            policy['items'][key]['decision'] = 'review_hold'
        path.write_text(json.dumps(policy))

    def test_actual_manual_bringup_does_not_complete_goal(self):
        result = review(self.root)
        self.assertTrue(result['training_evidence_verified'])
        self.assertFalse(result['project_handoff_ready'])
        for capability in ('camera_observation', 'visual_alignment', 'learned_jaw_control'):
            self.assertIn(capability, result['missing_capabilities'])

    def prepare_capabilities(self, acceptance_path):
        path = self.root / self.contract
        contract = json.loads(path.read_text())
        contract['implemented_capabilities'] = self.context['required_capabilities']
        contract['visual_pickup_physical_acceptance'] = acceptance_path
        path.write_text(json.dumps(contract))
        path = self.root / 'build-pack-20260913/procurement/sourcing-policy.json'
        policy = json.loads(path.read_text())
        for key in ('camera', 'camera_ffc'):
            policy['items'][key]['decision'] = 'included'
        path.write_text(json.dumps(policy))
        return contract

    def test_simulation_cannot_be_reused_as_hardware_acceptance(self):
        self.prepare_capabilities(self.context['training']['results'])
        result = review(self.root)
        self.assertFalse(result['physical_acceptance_verified'])
        self.assertEqual(result['physical_tests'], 0)
        self.assertFalse(result['project_handoff_ready'])

    def test_completed_fixture_can_pass_and_stale_trace_is_rejected(self):
        # Synthetic unit-test fixture only, never written to the live project.
        contract = self.prepare_capabilities('physical-test-fixture.json')
        trace = self.root / 'test-trials.jsonl'
        trace.write_text('{"synthetic_unit_test": true}\n')
        results = json.loads((self.root / self.context['training']['results']).read_text())
        record = {'kind': 'hardware_visual_pickup', 'build_revision': contract['revision'],
                  'observation_source': 'camera', 'policy_checkpoint_sha256': results['checkpointSha256'],
                  'accepted': True, 'trials': 1, 'trial_log': trace.name,
                  'trial_log_sha256': hashlib.sha256(trace.read_bytes()).hexdigest()}
        (self.root / 'physical-test-fixture.json').write_text(json.dumps(record))
        self.assertTrue(review(self.root)['project_handoff_ready'])
        trace.write_text('changed')
        self.assertFalse(review(self.root)['project_handoff_ready'])

    def test_checkpoint_cannot_be_replaced_without_revalidation(self):
        (self.root / self.context['training']['checkpoint']).write_bytes(b'wrong model')
        self.assertFalse(review(self.root)['training_evidence_verified'])

    def test_capability_claims_cannot_release_camera_hold_or_certify_hardware(self):
        path = self.root / self.contract
        contract = json.loads(path.read_text())
        contract['implemented_capabilities'] = self.context['required_capabilities']
        path.write_text(json.dumps(contract))
        result = review(self.root)
        self.assertFalse(result['missing_capabilities'])
        self.assertTrue(result['required_camera_items_on_hold'])
        self.assertFalse(result['physical_acceptance_verified'])
        self.assertFalse(result['project_handoff_ready'])


if __name__ == '__main__':
    unittest.main()

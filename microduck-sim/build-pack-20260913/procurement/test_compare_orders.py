"""Reject reuse of a whole-order quote after either merchant changes."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

P = Path(__file__).resolve().parent


class OrderComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('compare_orders.py', 'split-cart-live-comparison.json',
                     'cart-status-root.json', 'cart-status-procurement.json'):
            shutil.copyfile(P / name, self.root / name)

    def change_store(self, merchant, **changes):
        for name in ('cart-status-root.json', 'cart-status-procurement.json'):
            path = self.root / name
            data = json.loads(path.read_text())
            for store in data['stores']:
                if store['store'] == merchant:
                    store.update(changes)
            path.write_text(json.dumps(data))

    def run_comparison(self):
        return subprocess.run([sys.executable, str(self.root / 'compare_orders.py')],
                              capture_output=True, text=True)

    def test_robotis_shipping_change_requires_new_comparison(self):
        self.change_store('ROBOTIS', shipping_usd=20.00,
                          displayed_checkout_total_usd=457.65)
        self.assertNotEqual(self.run_comparison().returncode, 0)

    def test_digikey_displayed_total_cannot_be_stale(self):
        self.change_store('DigiKey', displayed_checkout_total_usd=55.26)
        self.assertNotEqual(self.run_comparison().returncode, 0)

    def test_source_line_totals_must_reconcile(self):
        path = self.root / 'split-cart-live-comparison.json'
        data = json.loads(path.read_text())
        # Preserve like-for-like lines while making both subtotals inconsistent.
        for key in ('split_digikey', 'restored_digikey'):
            data[key]['lines'][0]['line_total_usd'] = 3.48
        path.write_text(json.dumps(data))
        self.assertNotEqual(self.run_comparison().returncode, 0)

    def test_valid_order_exposes_existing_evidence_artifacts(self):
        result = self.run_comparison()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['saving_from_consolidation_alone_usd'], 6.05)
        for path in data['artifact_paths'].values():
            self.assertTrue(Path(path).is_absolute())
            self.assertTrue(Path(path).is_file())


if __name__ == '__main__':
    unittest.main()

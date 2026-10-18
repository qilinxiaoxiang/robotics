"""Regression checks through the actual handoff verifier, without changing artifacts."""
from pathlib import Path
import importlib.util
import json
import unittest
from unittest.mock import patch

P=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('handoff',P/'verify_assembly_handoff.py')
handoff=importlib.util.module_from_spec(spec);spec.loader.exec_module(handoff)

class SourceBindings(unittest.TestCase):
    def test_native_handoff(self):
        self.assertEqual(handoff.inspect_assembly(), [])

    def test_changed_nested_closure_report(self):
        original=handoff.sha
        target=P/'fastener-audit/electronics-head-closure-verification.json'
        with patch.object(handoff,'sha',side_effect=lambda p:'0'*64 if Path(p)==target else original(p)):
            self.assertIn('Head closure report changed after electronics audit',handoff.inspect_assembly())

    def test_changed_nested_closure_source(self):
        original=handoff.sha
        target=P/'fastener-audit/electronics_head_closure_check.py'
        with patch.object(handoff,'sha',side_effect=lambda p:'0'*64 if Path(p)==target else original(p)):
            self.assertIn('Head closure evidence source changed: '+str(target),handoff.inspect_assembly())

    def test_missing_required_binding(self):
        original=Path.read_text
        target=P/'fastener-audit/joint-fasteners.json'
        def read(path,*args,**kwargs):
            text=original(path,*args,**kwargs)
            if path==target:
                value=json.loads(text)
                value['source_hashes']={k:v for k,v in value['source_hashes'].items() if Path(k).name!='jaw-head-seats.json'}
                return json.dumps(value)
            return text
        with patch.object(Path,'read_text',read):
            self.assertIn('Incomplete fastener source binding: fastener-audit/joint-fasteners.json',handoff.inspect_assembly())

if __name__=='__main__': unittest.main()

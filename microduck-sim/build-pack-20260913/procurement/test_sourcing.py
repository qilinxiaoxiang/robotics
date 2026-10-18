"""Regression: available stock and old cart contents cannot authorize held purchases."""
import copy
import json
import subprocess
import sys
import tempfile
import shutil
import unittest
import hashlib
from pathlib import Path
from sourcing import P, load_policy, apply_policy, validate_selection, cart_conflicts, validate_cart_freshness

class SourcingRegression(unittest.TestCase):
    def setUp(self):
        self.items=json.loads((P/'catalog-en.json').read_text())
        self.policy=load_policy(self.items)

    def test_original_purchase_error_is_rejected(self):
        with self.assertRaisesRegex(AssertionError,'non-purchasable'):
            validate_selection(self.items,self.policy)

    def test_cart_stock_cannot_release_hold(self):
        items=copy.deepcopy(self.items)
        for item in items:
            item['purchase']['stock_status']='cart_verified'
        fixed=apply_policy(items,self.policy)
        validate_selection(fixed,self.policy)
        held={i['id']:i for i in fixed if i['sourcing']['decision']!='buy'}
        self.assertEqual(held['pi']['purchase']['packages'],0)
        self.assertEqual(held['filament']['purchase']['packages'],0)
        for key in ['sd','usb_otg','bench_pi_psu']:
            self.assertEqual(held[key]['category'],'borrow_first')

    def test_unmapped_lines_and_held_lines_block_handoff(self):
        cases=[{'item_id':'pi','quantity':1},{'item_id':'filament','quantity':1},{'item':'Unmapped Pi bundle','quantity':1}]
        for line in cases:
            self.assertTrue(cart_conflicts([{'store':'test','lines':[line]}],self.policy))

    def test_stale_bom_cannot_bypass_cart_generator(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst=Path(tmp)
            for name in ['build_cart_plan.py','redesign_procurement.py','fastener_cart.py','sourcing.py','sourcing-policy.json','cart-status-omx-20260918.json','order-2034348-confirmation.json']:
                (dst/name).write_bytes((P/name).read_bytes())
            shutil.copytree(P/'fasteners-amazon-20260929', dst/'fasteners-amazon-20260929')
            bom=json.loads((P/'bom.json').read_text())
            bom['items']=self.items
            (dst/'bom.json').write_text(json.dumps(bom))
            subprocess.run([sys.executable,str(dst/'build_cart_plan.py')],check=True,capture_output=True)
            plan=json.loads((dst/'cart-plan.json').read_text())
            rows={r['item_id']:r for r in plan['all_item_classifications']}
            for key,row in self.policy['items'].items():
                if row['decision']!='buy':self.assertNotEqual(rows[key]['action'],'add_now')

    def test_bundled_components_cannot_be_purchased_separately(self):
        fixed={x['id']:x for x in apply_policy(self.items,self.policy)}
        for key in ['servo','controller']:
            self.assertEqual(fixed[key]['sourcing']['decision'],'included')
            self.assertEqual(fixed[key]['purchase']['packages'],0)
            self.assertTrue(cart_conflicts([{'store':'ROBOTIS','lines':[{'item_id':key}]}],self.policy))

    def test_replacement_bundle_mapping_rejects_quantity_model_and_hold_changes(self):
        from sourcing import validate_bundle
        validate_bundle(self.policy, self.items)
        cases = [lambda b: b.update(quantity=1),
                 lambda b: b['components'][0].update(model='XL330-M077-T'),
                 lambda b: b['components'][0].update(engineering_quantity=16),
                 lambda b: b['components'][0].update(supplied_quantity=15),
                 lambda b: b['components'][1].update(item_id='pi'),
                 lambda b: b.update(received=True),
                 lambda b: b['stock'].update(independently_verified=True)]
        for mutate in cases:
            bad = copy.deepcopy(self.policy)
            mutate(bad['replacement_bundle'])
            with self.assertRaises(AssertionError):
                validate_bundle(bad, self.items)

    def test_bundle_cart_mapping_is_exact_and_does_not_hide_held_lines(self):
        ordered_line = {'bundle_id':self.policy['replacement_bundle']['id'],'model':'ROBOTIS OMX-AI','url':self.policy['replacement_bundle']['url'],'quantity':3}
        self.assertTrue(cart_conflicts([{'store':'ROBOTIS US','lines':[ordered_line]}],self.policy))
        policy = copy.deepcopy(self.policy)
        policy['replacement_bundle']['url'] = 'https://example.test/omx-ai'
        policy['replacement_bundle']['order_placed'] = False
        line = {'bundle_id':'omx_ai_order_2034348','model':'ROBOTIS OMX-AI',
                'url':'https://example.test/omx-ai','quantity':3}
        self.assertFalse(cart_conflicts([{'store':'ROBOTIS US','lines':[line]}],policy))
        for change in [{'quantity':2},{'url':'https://example.test/pi'},{'model':'Other kit'},{'item_id':'pi'}]:
            self.assertTrue(cart_conflicts([{'store':'ROBOTIS US','lines':[dict(line,**change)]}],policy))
        self.assertTrue(cart_conflicts([{'store':'ROBOTIS US','lines':[line,{'item_id':'pi','quantity':1}]}],policy))

    def test_omx_order_rejects_wrong_quantity_hidden_item_and_received_claim(self):
        from unittest.mock import patch
        import redesign_procurement as r
        evidence = json.loads((P/'order-2034348-confirmation.json').read_text())
        cases = [lambda e: e['lines'][0].update(quantity=2),
                 lambda e: e['lines'].append({'item_id':'pi','quantity':1}),
                 lambda e: e.update(displayed_total_usd=700),
                 lambda e: e.update(received=True)]
        for mutate in cases:
            bad = copy.deepcopy(evidence); mutate(bad)
            with tempfile.TemporaryDirectory() as tmp, patch.object(r,'P',Path(tmp)):
                (Path(tmp)/'order-2034348-confirmation.json').write_text(json.dumps(bad))
                with self.assertRaises(AssertionError):
                    r.bundle_order(self.policy)

    def test_required_camera_audio_and_held_otg_are_distinct(self):
        fixed={x['id']:x for x in apply_policy(self.items,self.policy)}
        for key in ['camera','camera_ffc','amp','speaker','audio_fuse','audio_gain_resistor']:
            self.assertGreater(fixed[key]['purchase']['packages'],0)
        self.assertEqual(fixed['usb_otg']['installed_quantity'],1)
        self.assertEqual(fixed['usb_otg']['purchase']['packages'],0)
        self.assertIn('SC0727',fixed['usb_otg']['model'])
        self.assertEqual(fixed['audio_power_connector']['purchase']['packages'],0)

    def test_unjustified_spares_fail_at_generation_entry(self):
        from redesign_procurement import validate_minimum_quantities
        fixed=apply_policy(self.items,self.policy)
        validate_minimum_quantities(fixed)
        for key in ['main_fuse','branch_fuse','input_fuse','audio_fuse','audio_gain_resistor']:
            bad=copy.deepcopy(fixed)
            item=next(x for x in bad if x['id']==key)
            item['purchase']['packages']+=1
            with self.subTest(item_id=key), self.assertRaisesRegex(AssertionError,'unjustified extra purchase'):
                validate_minimum_quantities(bad)

    def test_original_extra_purchase_snapshot_is_rejected(self):
        from redesign_procurement import validate_minimum_quantities
        before=P/'archive/before-cost-correction'
        old_items=json.loads((before/'catalog-en.json').read_text())
        old_policy=json.loads((before/'sourcing-policy.json').read_text())
        with self.assertRaisesRegex(AssertionError,'unjustified extra purchase'):
            validate_minimum_quantities(apply_policy(old_items,old_policy))

    def test_new_design_never_promotes_old_carts(self):
        from redesign_procurement import verify
        verify()
        plan=json.loads((P/'cart-plan.json').read_text())
        for snapshot in plan['actual_cart_readbacks']:
            self.assertEqual(snapshot['file'], 'cart-status-r3.json')
            self.assertEqual(snapshot['revision'], 'microduck-charger-camera-r3')
        self.assertTrue(all(not x['applies_to_revision'] for x in plan['historical_cart_snapshots']))
        self.assertFalse(plan['checkout_ready'])
        self.assertTrue(plan['purchasing_handoff_ready'])
        self.assertEqual(plan['replacement_bundle_order']['displayed_total_usd'],1086.27)
        self.assertEqual(plan['replacement_bundle']['quantity'],3)
        self.assertEqual(plan['add_now_quoted_subtotal_usd'],114.61)
        self.assertEqual(len(plan['stores']),1)

    def test_current_cart_mismatch_is_rejected(self):
        from redesign_procurement import validate_actual_cart
        evidence=json.loads((P/'cart-status-r3.json').read_text())
        fixed=apply_policy(self.items,self.policy)
        validate_actual_cart(evidence,fixed,self.policy)
        cases=[lambda e:e.update(revision='old'),
               lambda e:e['lines'].pop(),
               lambda e:e['lines'][0].update(quantity=999),
               lambda e:e['lines'][0].update(item_id='pi'),
               lambda e:e['lines'][0].update(digikey_part_number='wrong-SKU'),
               lambda e:e.update(total_estimate_usd=0),
               lambda e:e.update(browser_readback_sha256='stale')]
        for mutate in cases:
            altered=copy.deepcopy(evidence);mutate(altered)
            with self.assertRaises(AssertionError):
                validate_actual_cart(altered,fixed,self.policy)

    def test_missing_cart_evidence_does_not_certify_current_cart(self):
        from unittest.mock import patch
        import redesign_procurement as r
        with tempfile.TemporaryDirectory() as tmp, patch.object(r,'P',Path(tmp)):
            self.assertIsNone(r.current_cart(apply_policy(self.items,self.policy),self.policy))

    def test_kit_receipt_needs_photo_evidence_and_claims_no_tracking(self):
        import redesign_procurement as r
        self.assertTrue(r.bundle_receipt(self.policy)['received'])
        cases=[lambda x:x.update(photo=''),lambda x:x.update(photo_sha256='0'),
               lambda x:x.update(evidence_type='user_statement_only'),lambda x:x.update(tracking_required=True),
               lambda x:x.update(unit_count_verified=True),lambda x:x.update(bundle_id='other'),lambda x:x.update(order_id='1')]
        for mutate in cases:
            bad=copy.deepcopy(self.policy);mutate(bad['replacement_bundle_receipt'])
            with self.assertRaises(AssertionError):
                r.bundle_receipt(bad)

    def test_wall_end_kit_parts_are_owned_not_bought(self):
        fixed={x['id']:x for x in apply_policy(self.items,self.policy)}
        for key in self.policy['active_power_phase_20261013']['owned_item_ids']:
            self.assertEqual(fixed[key]['sourcing']['decision'],'owned')
            self.assertEqual(fixed[key]['purchase']['packages'],0)
            self.assertTrue(cart_conflicts([{'store':'ROBOTIS US','lines':[{'item_id':key}]}],self.policy))

    def test_unknown_catalog_item_fails_closed(self):
        self.items.append({'id':'unapproved_addition'})
        with self.assertRaisesRegex(AssertionError,'explicit sourcing'):
            load_policy(self.items)

    def test_paid_item_cannot_hide_as_gift(self):
        line={'item':'Pi kit','quantity':1,'line_total_usd':89.95,'classification':'free_gift'}
        self.assertTrue(cart_conflicts([{'store':'CanaKit','lines':[line]}],self.policy))
        line['classification']='preexisting_item_outside_current_BOM'
        self.assertTrue(cart_conflicts([{'store':'Pololu','lines':[line]}],self.policy))

    def test_engineering_constraints_survive_sourcing_change(self):
        fixed={x['id']:x for x in apply_policy(self.items,self.policy)}
        original={x['id']:x for x in self.items}
        for key in ['foam','pi_mount_screws']:
            self.assertIn(original[key]['notes_zh'],fixed[key]['notes_zh'])

    def test_new_cart_observation_invalidates_old_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);f=base/'cart.json'
            f.write_text(json.dumps({'updated_at':'test','stores':[]}))
            snapshots=[{'file':'cart.json','sha256':hashlib.sha256(f.read_bytes()).hexdigest()}]
            validate_cart_freshness(snapshots,[],base)
            f.write_text(json.dumps({'updated_at':'new','stores':[{'store':'CanaKit','lines':[{'item_id':'pi'}]}]}))
            with self.assertRaisesRegex(AssertionError,'Cart evidence changed'):
                validate_cart_freshness(snapshots,[],base)

class FastenerCartRegression(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        shutil.copytree(P/'fasteners-amazon-20260929', self.base/'fasteners-amazon-20260929')
        self.policy = json.loads((P/'sourcing-policy.json').read_text())
        self.items = json.loads((P/'catalog-en.json').read_text())
        self.manifest_path = self.base / self.policy['fastener_cart_authorization']['offers_file']
        self.manifest = json.loads(self.manifest_path.read_text())
        self.manifest.update(selected_offers=[], verified_stock_credits=[], native_cart_evidence=None)
        (self.base/'fixture-evidence.txt').write_text('Synthetic test evidence; never a supplier quote.')
        self.evidence = {'file':'fixture-evidence.txt','sha256':hashlib.sha256((self.base/'fixture-evidence.txt').read_bytes()).hexdigest()}

    def run_plan(self):
        from fastener_cart import build_fastener_cart
        self.manifest_path.write_text(json.dumps(self.manifest))
        return build_fastener_cart(self.base, self.policy, self.items)

    def select_fixture(self):
        self.manifest['selected_offers'] = [{'offer_id':'synthetic-fixture','store':'test','url':'https://example.test/fixture','product_variant':'Synthetic M2x6 fixture','package_quantity':1,'package_price_usd':3.99,'subtotal_usd':3.99,'price_verified':True,'compatibility_verified':True,'price_evidence':self.evidence,'coverage':[{'item_id':'m2_6','units_per_package':50,'allocated_units':4,'compatibility_verified':True,'verified_specification':'Synthetic test specification','compatibility_evidence':self.evidence}]}]

    def test_pending_manifest_does_not_release_fallbacks_or_claim_cart(self):
        self.manifest.update(selected_offers=[],verified_stock_credits=[],native_cart_evidence=None)
        p = self.run_plan()
        self.assertEqual(p['selected_offer_count'],0)
        self.assertFalse(p['native_cart_verified'])
        self.assertFalse(p['checkout_authorized'])
        self.assertFalse(p['catalog_fallback_offers_released'])
        self.assertEqual(self.policy['items']['pi']['decision'],'borrow_first')

    def test_minimum_assortment_package_allowed_but_extra_package_rejected(self):
        self.select_fixture();self.run_plan()
        self.manifest['selected_offers'][0].update(package_quantity=2,subtotal_usd=7.98)
        with self.assertRaisesRegex(AssertionError,'Extra packages'):self.run_plan()

    def test_unrelated_item_and_unverified_stock_are_rejected(self):
        self.select_fixture()
        self.manifest['selected_offers'][0]['coverage'][0]['item_id']='pi'
        with self.assertRaisesRegex(AssertionError,'Unapproved'):self.run_plan()
        self.select_fixture()
        self.manifest['verified_stock_credits']=[{'item_id':'m2_6','quantity':1,'physically_verified':False,'evidence':self.evidence}]
        with self.assertRaisesRegex(AssertionError,'Unverified kit'):self.run_plan()

    def test_unrelated_hold_and_price_ceiling_are_enforced(self):
        self.policy['items']['pi']['decision']='buy'
        with self.assertRaisesRegex(AssertionError,'Unrelated sourcing'):self.run_plan()
        self.policy = json.loads((P/'sourcing-policy.json').read_text())
        self.select_fixture();self.manifest['selected_offers'][0].update(package_price_usd=31,subtotal_usd=31)
        with self.assertRaisesRegex(AssertionError,'ceiling'):self.run_plan()

    def test_missing_compatibility_evidence_and_duplicate_allocation_rejected(self):
        self.select_fixture();self.manifest['selected_offers'][0]['coverage'][0]['compatibility_evidence']={'file':'missing','sha256':'none'}
        with self.assertRaisesRegex(AssertionError,'Missing or changed'):self.run_plan()
        self.select_fixture();other=copy.deepcopy(self.manifest['selected_offers'][0]);other['offer_id']='another';self.manifest['selected_offers'].append(other)
        with self.assertRaisesRegex(AssertionError,'Duplicate allocation'):self.run_plan()

    def test_native_cart_requires_exact_offer_price_and_no_unmapped_lines(self):
        self.select_fixture()
        offer=self.manifest['selected_offers'][0]
        line={k:offer[k] for k in ['offer_id','store','url','product_variant','package_quantity','package_price_usd','subtotal_usd']}
        observed={'browser_readback':self.evidence,'verified_after_reload':True,'checkout_submitted':False,'lines':[line],'unmapped_lines':[],'merchandise_subtotal_usd':3.99}
        def write_observation():
            path=self.base/'cart-fixture.json';path.write_text(json.dumps(observed))
            self.manifest['native_cart_evidence']={'file':'cart-fixture.json','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        write_observation();self.assertTrue(self.run_plan()['native_cart_verified'])
        observed['lines'][0]['package_quantity']=2;write_observation()
        with self.assertRaisesRegex(AssertionError,'Native fastener cart mismatch'):self.run_plan()
        observed['lines'][0]['package_quantity']=1;observed['unmapped_lines']=[{'title':'unmapped'}];write_observation()
        with self.assertRaisesRegex(AssertionError,'Unmapped'):self.run_plan()

if __name__=='__main__':unittest.main()



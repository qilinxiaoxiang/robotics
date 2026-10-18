"""Replay actual omissions and prevent cart-driven changes to engineering quantities."""
import copy,json,unittest,subprocess,sys,tempfile
from pathlib import Path
from check_system import errors,cart_errors,P
class WholeSystemRegression(unittest.TestCase):
 def setUp(self):
  self.c=json.loads((P/'catalog-en.json').read_text());self.p=json.loads((P/'sourcing-policy.json').read_text());self.k=json.loads((P.parent/'phase1/system-contract.json').read_text());self.by={x['id']:x for x in self.c}
  self.carts=sum([json.loads((P/n).read_text())['stores'] for n in ['cart-status-root.json','cart-status-procurement.json']],[])
 def test_current_system(self):self.assertFalse(errors(self.c,self.p,self.k));self.assertFalse(cart_errors(self.c,self.p,self.carts))
 def test_actual_previous_fuse_omission(self):
  old=json.loads((P.parent/'phase1/audit-20260913/before/procurement/catalog-en.json').read_text())
  self.assertIn('quantity coverage: branch_fuse',errors(old,self.p))
 def test_missing_jaw(self):
  self.by['servo']['installed_quantity']=14;self.assertTrue(errors(self.c,self.p,self.k))
 def test_no_free_servo_from_removed_starter_kit(self):
  self.by['controller']['purchase']['packages']=0;self.assertIn('quantity coverage: servo',errors(self.c,self.p,self.k))
 def test_second_power_source(self):
  self.k['power_sources'].append(copy.deepcopy(self.k['power_sources'][0]));self.assertTrue(errors(self.c,self.p,self.k))
 def test_third_store(self):
  self.by['imu']['purchase']['store']='Adafruit';self.assertIn('avoidable store fragmentation',errors(self.c,self.p,self.k))
 def test_missing_interface(self):
  for key in ['pi_power_plug','imu_cable','main_wire','sd']:
   self.assertTrue(errors([x for x in self.c if x['id']!=key],self.p,self.k))
 def test_cart_missing_duplicate_or_wrong_store(self):
  dk=next(s for s in self.carts if s['store']=='DigiKey');line=dk['lines'].pop();self.assertTrue(cart_errors(self.c,self.p,self.carts));dk['lines'].extend([line,line]);self.assertTrue(cart_errors(self.c,self.p,self.carts))
 def test_actual_old_quantity_cannot_be_rewritten_from_cart(self):
  # Exercise the actual generator with a stale cart: selected demand must remain unchanged.
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);q=base/'procurement';q.mkdir()
   for n in ['build_bom.py','sourcing.py','sourcing-policy.json','catalog-en.json']:(q/n).write_bytes((P/n).read_bytes())
   text=(q/'build_bom.py').read_text();text=text[:text.index('items=apply_policy')]+"\nprint(json.dumps(by_id['branch_fuse']['purchase']))\n"
   (q/'build_bom.py').write_text(text)
   f=self.by['branch_fuse']['purchase'];(q/'cart-status-root.json').write_text(json.dumps({'stores':[{'store':'DigiKey','status':'cart_verified','lines':[{'bom_item_id':'branch_fuse','quantity':1,'product_url':f['url'],'line_total_usd':.99}]}]}))
   r=subprocess.run([sys.executable,str(q/'build_bom.py')],capture_output=True,text=True,check=True)
   self.assertEqual(json.loads(r.stdout)['packages'],10)
if __name__=='__main__':unittest.main()

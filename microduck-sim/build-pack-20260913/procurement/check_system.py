"""Check whole-robot requirements independently of prices and cart contents."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent

def errors(catalog, policy, contract=None):
    issues=[];by={x['id']:x for x in catalog}
    buy=[x for x in catalog if policy['items'][x['id']]['decision']=='buy']
    for x in buy:
        need=(x.get('installed_quantity') or 0)+(x.get('bench_quantity',0) if x.get('installed_quantity')==0 else 0)
        spare=x.get('spare_quantity',0)
        supplied=x['purchase']['packages']*x['purchase']['package_content_quantity']
        if x['id']=='servo':
            kit=by.get('controller')
            if kit and policy['items']['controller']['decision']=='buy' and 'Starter Kit' in kit['model']:
                supplied+=kit['purchase']['packages']
        if supplied < need+spare:issues.append('quantity coverage: '+x['id'])
    if by.get('servo',{}).get('installed_quantity')!=15:issues.append('jaw missing from fifteen-servo requirement')
    if not contract:return issues+['no whole-system contract']
    if len(contract['power_sources'])!=1 or sum(x['quantity'] for x in contract['power_sources'])!=1:issues.append('robot requires more than one power source')
    if len({x['purchase']['store'] for x in buy})>contract['max_buying_stores']:issues.append('avoidable store fragmentation')
    for key in contract['required_items']:
        if key not in by:issues.append('required interface/component absent: '+key)
        elif policy['items'][key]['decision'] not in ['buy','borrow_first','club_supply','included','reuse_or_borrow','reuse_or_optional_buy']:
            issues.append('required component has no active supply route: '+key)
    for key in contract['superseded_power_items']:
        if policy['items'][key]['decision']=='buy':issues.append('superseded power purchase: '+key)
    return issues

def cart_errors(catalog,policy,carts):
    issues=[];alias={'ROBOTIS':'ROBOTIS US'}
    for x in catalog:
        if policy['items'][x['id']]['decision']!='buy':continue
        found=[(s,l) for s in carts for l in s['lines'] if l.get('bom_item_id',l.get('item_id'))==x['id']]
        if len(found)!=1:issues.append('cart line missing or duplicated: '+x['id']);continue
        s,l=found[0];p=x['purchase']
        if alias.get(s['store'],s['store'])!=p['store'] or l['product_url']!=p['url'] or l['quantity']!=p['packages']:
            issues.append('cart differs from selected supplier/quantity: '+x['id'])
    return issues

def check():
    catalog=json.loads((P/'catalog-en.json').read_text());policy=json.loads((P/'sourcing-policy.json').read_text())
    path=P.parent/'phase1/system-contract.json'
    contract=json.loads(path.read_text()) if path.exists() else None
    return errors(catalog,policy,contract)

if __name__=='__main__':
    found=check();print(json.dumps({'passed':not found,'errors':found},indent=2));raise SystemExit(bool(found))

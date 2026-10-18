"""Apply sourcing decisions independently of engineering quantities and shop availability."""
import copy
import json
import hashlib
from pathlib import Path

P = Path(__file__).resolve().parent
POLICY = P / 'sourcing-policy.json'
NONBUY = {'club_supply', 'borrow_first', 'included', 'optional', 'review_hold', 'already_ordered', 'owned'}

def load_policy(items):
    policy = json.loads(POLICY.read_text())
    assert set(policy['items']) == {x['id'] for x in items}, 'Every item needs an explicit sourcing decision'
    for key, row in policy['items'].items():
        assert row['decision'] in NONBUY | {'buy'}, (key, 'invalid decision')
        assert row.get('evidence'), (key, 'missing decision evidence')
        if row.get('purchase_requires_stock_check') and row['decision']=='buy':
            assert row.get('missing_stock_evidence') and row.get('decision_change_evidence'), (key, 'stock check and changed decision required before purchase')
    validate_bundle(policy, items)
    return policy

def validate_bundle(policy, items):
    bundle = policy.get('replacement_bundle')
    if not bundle:
        return
    by = {x['id']: x for x in items}
    assert bundle['quantity'] == 3 and bundle['authorization_evidence'], 'Unapproved bundle quantity'
    assert round(bundle['quantity'] * bundle['unit_price_usd'], 2) == bundle['merchandise_subtotal_usd'], 'Bundle price arithmetic mismatch'
    assert bundle['status'] == 'merchant_confirmed_preparing_shipment'
    assert bundle['order_placed'] and bundle['paid'] and not bundle['received']
    assert bundle['payment_evidence'] == 'user_reported_and_merchant_confirmed'
    assert bundle['microduck_kit_quantity'] == 2 and bundle['intact_experiment_kit_quantity'] == 1
    assert bundle['microduck_kit_quantity'] + bundle['intact_experiment_kit_quantity'] == bundle['quantity']
    assert bundle['prior_order']['status'] == 'fully_refunded_at_merchant'
    assert not bundle['stock']['independently_verified'], 'Phone report is not independent stock verification'
    expected = {'servo': ('XL330-M288-T', 8, 15), 'controller': ('OpenRB-150', 2, 1)}
    assert len(bundle['components']) == len(expected)
    assert {c['item_id'] for c in bundle['components']} == set(expected), 'Unapproved bundle component mapping'
    for component in bundle['components']:
        key = component['item_id']
        model, per_kit, required = expected[key]
        decision = policy['items'][key]
        assert decision['decision'] == 'included' and decision['bundle_id'] == bundle['id'], 'Bundle cannot release another sourcing hold'
        assert component['model'] == model and component['per_kit'] == per_kit
        assert component['engineering_quantity'] == by[key]['installed_quantity'] == required
        assert component['supplied_quantity'] == bundle['microduck_kit_quantity'] * per_kit
        assert component['bundle_surplus'] == component['supplied_quantity'] - required


def apply_policy(items, policy):
    result = copy.deepcopy(items)
    for item in result:
        decision = policy['items'][item['id']]
        item['sourcing'] = copy.deepcopy(decision)
        if decision['decision'] == 'buy':
            continue
        item.setdefault('reference_purchase', copy.deepcopy(item['purchase']))
        item['purchase'].update(packages=0, subtotal_usd=0, stock_status=decision['decision'])
        item['category'] = decision['decision']
        item.setdefault('engineering_notes', item['notes_zh'])
        item['notes_zh'] = (decision.get('note','')+' '+item['engineering_notes']).strip()
    return result

def validate_selection(items, policy, rows=None):
    for item in items:
        state = policy['items'][item['id']]['decision']
        if state != 'buy':
            assert item['purchase']['packages'] == 0, (item['id'], 'non-purchasable sourcing decision has purchase quantity')
            assert item['purchase']['subtotal_usd'] in (None, 0), (item['id'], 'non-purchasable item charged')
    for row in rows or []:
        if policy['items'][row['item_id']]['decision'] != 'buy':
            assert row['action'] != 'add_now', (row['item_id'], 'sourcing hold bypassed')

def cart_conflicts(carts, policy):
    problems = []
    for cart in carts:
        for line in cart.get('lines', []):
            if line.get('bundle_id'):
                bundle = policy.get('replacement_bundle', {})
                if (bundle.get('order_placed') or line.get('item_id') or line.get('bom_item_id')
                    or line['bundle_id'] != bundle.get('id') or cart['store'] != bundle.get('store')
                    or line.get('quantity') != bundle.get('quantity')
                    or not bundle.get('url') or line.get('url') != bundle['url']
                    or line.get('model') != bundle.get('model')):
                    problems.append({'store': cart['store'], 'reason': 'unapproved bundle cart line', 'line': line})
                continue
            item_id = line.get('bom_item_id', line.get('item_id'))
            if not item_id:
                if line.get('classification') == 'free_gift' and line.get('line_total_usd') == 0:
                    continue
                if (line.get('classification') == 'preexisting_item_outside_current_BOM'
                    and cart['store']=='Pololu' and line.get('item','').startswith('2815 ')
                    and line.get('quantity')==1 and line.get('line_total_usd')==8.49):
                    continue
                problems.append({'store': cart['store'], 'reason': 'unmapped cart line', 'line': line})
            elif item_id not in policy['items'] or policy['items'][item_id]['decision'] != 'buy':
                problems.append({'store': cart['store'], 'item_id': item_id, 'reason': 'remove non-purchasable item'})
    return problems

def validate_cart_freshness(snapshots, actual, base=P):
    expected=[]
    for snapshot in snapshots:
        raw=(base/snapshot['file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==snapshot['sha256'], 'Cart evidence changed; regenerate before handoff'
        data=json.loads(raw)
        expected.extend(dict(s,source_file=snapshot['file'],source_updated_at=data.get('updated_at')) for s in data['stores'])
    assert expected==actual, 'Cart plan does not match current source observations'

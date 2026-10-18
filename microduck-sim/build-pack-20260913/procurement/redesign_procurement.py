"""Current design procurement, with historical carts kept outside current evidence.

The original generators and historical proof assertions remain in their entry
files. Current browser evidence is accepted only when every observed line matches
the selected revision; cart preparation remains separate from payment and testing.
"""
import copy
import datetime
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

from sourcing import P, apply_policy, load_policy, validate_selection, cart_conflicts
from fastener_cart import build_fastener_cart, summary_lines

REVISION = 'microduck-charger-camera-r3'
BUY_IDS = {'camera', 'camera_ffc', 'imu', 'imu_cable', 'amp', 'speaker',
           'main_fuse', 'branch_fuse', 'usb_c_data', 'audio_fuse',
           'audio_gain_resistor', 'pd_receiver',
           'shared_regulator', 'input_fuse', 'power_disconnect'}
ADA_IDS = {'pd_receiver': '5991', 'imu': '4754', 'imu_cable': '4397',
           'amp': '3006', 'usb_c_data': '4472'}


def active(base=P):
    path = base / 'sourcing-policy.json'
    return path.exists() and json.loads(path.read_text()).get('active_revision') == REVISION


def write(name, data):
    (P / name).write_text(json.dumps(data, indent=2) + '\n')


def total(rows, field='subtotal_usd'):
    return float(sum((Decimal(str(r[field])) for r in rows), Decimal('0')))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_minimum_quantities(items):
    """Current unit-pack basket: only installed/external working parts are bought.

    Extra stock needs a new, evidenced cost decision; convenience alone is not
    permission to charge the user. This check also runs on stale BOM input.
    """
    for item in items:
        if item['sourcing']['decision'] != 'buy':
            continue
        assert item.get('required_current_design', True), (item['id'], 'optional item charged')
        required = item['installed_quantity'] + item.get('bench_quantity', 0)
        purchased = item['purchase']['packages'] * item['purchase']['package_content_quantity']
        assert purchased == required, (item['id'], 'unjustified extra purchase', purchased, required)
        assert item.get('spare_quantity', 0) == 0, (item['id'], 'unjustified spare allocation')


def historical_evidence():
    result = []
    for name in ['cart-status-root.json', 'cart-status-procurement.json']:
        path = P / name
        if path.exists():
            result.append({'file': name, 'sha256': digest(path),
                           'status': 'stale_for_redesign_reference_only',
                           'applies_to_revision': False})
    return result


def parse_browser_cart(text, items):
    """Parse the saved, rendered DigiKey cart; account details are excluded."""
    by_url = {x['purchase']['url']: x for x in items if x['sourcing']['decision'] == 'buy'}
    lines = []
    for match in re.finditer(r'^    - row "\d+ (.*?)":\n(.*?)(?=^    - |\Z)', text, re.M | re.S):
        title, body = match.groups()
        part = re.match(r'(\S+) \1 (.*?) (\d+) Immediate ([\d.]+) \$([\d.]+)$', title)
        assert part, ('Unrecognized or unavailable cart line', title)
        sku, description, qty, unit, subtotal = part.groups()
        url = 'https://www.digikey.com' + re.search(r'/url: (\S+)', body).group(1)
        assert url in by_url, ('Unmapped or held cart product', sku, url)
        item = by_url[url]
        lines.append({'item_id': item['id'], 'digikey_part_number': sku,
                      'description': description, 'url': url, 'quantity': int(qty),
                      'availability': 'Immediate', 'unit_price_usd': float(unit),
                      'subtotal_usd': float(subtotal)})
    assert len(lines) == len(BUY_IDS) and len({x['item_id'] for x in lines}) == len(BUY_IDS), 'Missing or duplicate cart lines'
    summary = text.split('- generic: Cart Summary')[1]
    amounts = [float(x) for x in re.findall(r'\$([\d.]+)', summary)]
    assert len(amounts) == 4, 'Cart fee fields changed'
    return {'lines': lines, 'subtotal_usd': amounts[0], 'shipping_estimate_usd': amounts[1],
            'tariff_estimate_usd': amounts[2], 'total_estimate_usd': amounts[3]}


def validate_actual_cart(evidence, items, policy, base=P):
    assert evidence['revision'] == REVISION, 'Stale cart revision'
    assert evidence['store'] == 'DigiKey' and evidence['verified_after_reload'] is True
    proof = base / evidence['browser_readback_file']
    assert digest(proof) == evidence['browser_readback_sha256'], 'Browser evidence changed'
    parsed = parse_browser_cart(proof.read_text(), items)
    for key, value in parsed.items():
        assert evidence[key] == value, ('Cart record disagrees with browser evidence', key)
    assert not cart_conflicts([evidence], policy), 'Held or unmapped cart line'
    selected = {x['id']: x['purchase'] for x in items if x['sourcing']['decision'] == 'buy'}
    assert {x['item_id'] for x in evidence['lines']} == set(selected)
    for line in evidence['lines']:
        expected = selected[line['item_id']]
        assert line['quantity'] == expected['packages'], ('Cart quantity mismatch', line['item_id'])
        assert line['unit_price_usd'] == expected['unit_price_usd']
        assert line['subtotal_usd'] == expected['subtotal_usd']
        assert line['url'] == expected['url']
        assert line['digikey_part_number'] == expected['digikey_part_number'], ('Cart SKU mismatch', line['item_id'])
    assert total(evidence['lines']) == evidence['subtotal_usd']
    assert round(evidence['subtotal_usd'] + evidence['shipping_estimate_usd'] + evidence['tariff_estimate_usd'], 2) == evidence['total_estimate_usd']
    assert evidence['sales_tax_usd'] is None and evidence['order_placed'] is False
    return evidence


def current_cart(items, policy):
    path = P / 'cart-status-r3.json'
    if not path.exists():
        return None
    return validate_actual_cart(json.loads(path.read_text()), items, policy)


def cart_snapshot(cart):
    return [{'file': 'cart-status-r3.json', 'sha256': digest(P / 'cart-status-r3.json'),
             'revision': REVISION, 'verified_at': cart['verified_at']}] if cart else []


def cart_status_text(cart):
    if not cart:
        return 'Planned basket; a current browser readback is still required.'
    return (f"All 15 DigiKey lines were verified after browser reload. Merchandise ${cart['subtotal_usd']:.2f}; "
            f"estimated shipping ${cart['shipping_estimate_usd']:.2f}; estimated tariff ${cart['tariff_estimate_usd']:.2f}; "
            f"displayed estimate ${cart['total_estimate_usd']:.2f}. Sales tax is not shown in the cart. No order was placed. "
            '[Actual cart evidence](cart-status-r3.json).')


def bundle_order(policy):
    bundle = policy['replacement_bundle']
    path = P / bundle['order_evidence_file']
    evidence = json.loads(path.read_text())
    assert evidence['evidence_type'] == 'main_task_merchant_confirmation_readback'
    assert evidence['store'] == bundle['store'] and len(evidence['lines']) == 2
    line, protection = evidence['lines']
    for field in ['sku', 'url', 'model', 'quantity', 'unit_price_usd']:
        assert line[field] == bundle[field], ('Order line mismatch', field)
    assert line['bundle_id'] == bundle['id']
    assert line['subtotal_usd'] == evidence['kit_merchandise_usd'] == bundle['merchandise_subtotal_usd']
    assert protection['classification'] == 'shipping_protection'
    assert round(protection['quantity'] * protection['unit_price_usd'], 2) == protection['subtotal_usd'] == evidence['protection_usd']
    assert round(evidence['kit_merchandise_usd'] + evidence['protection_usd'], 2) == evidence['subtotal_usd']
    assert round(evidence['subtotal_usd'] + evidence['shipping_usd'] + evidence['sales_tax_usd'], 2) == evidence['displayed_total_usd'] == bundle['landed_total_usd']
    assert evidence['arrival_estimate'] == bundle['arrival_window'] and evidence['arrival_evidence']
    assert evidence['order_placed'] and evidence['paid'] and not evidence['received']
    assert evidence['payment_evidence'] == bundle['payment_evidence']
    assert evidence['allocation'] == {'microduck_kits':2, 'intact_leader_follower_kits':1}
    assert not evidence['tracking_number']
    historical = bundle['historical_checkout']
    assert digest(P / historical['file']) == historical['sha256'], 'Historical two-kit checkout changed'
    return dict(evidence, file=path.name, sha256=digest(path))


def bundle_receipt(policy):
    """Kit receipt is its own evidence record; the merchant confirmation stays the order-time record."""
    receipt = policy.get('replacement_bundle_receipt')
    if not receipt:
        return None
    assert receipt['bundle_id'] == policy['replacement_bundle']['id'], 'Receipt names another bundle'
    assert receipt['order_id'] == json.loads((P / policy['replacement_bundle']['order_evidence_file']).read_text())['order_id']
    assert receipt['received'] is True and receipt['evidence_type'] == 'user_photo_assembled_servos'
    assert receipt['photo'] and len(receipt['photo_sha256']) == 64 and receipt['evidence_date'] and receipt['observed'], 'Receipt needs photo evidence'
    assert receipt['tracking_required'] is False and receipt['unit_count_verified'] is False, 'Photo receipt does not certify tracking or unit counts'
    return receipt


def bundle_status_text(policy):
    b = policy['replacement_bundle']
    observed = bundle_order(policy)
    receipt = bundle_receipt(policy)
    status = (f"Payment is user-reported and merchant-confirmed. Received: the user photo of {receipt['evidence_date']} shows {receipt['observed']}. "
              'No tracking record is needed; unit counts were not taken from the photo. '
              if receipt else
              f"Payment is user-reported and merchant-confirmed; shipment is being prepared, with no tracking or receipt verified. Estimated arrival {observed['arrival_estimate']} is not a dispatch confirmation. ")
    return ('## OMX-AI order\n\n'
            f"Order {observed['order_id']}: 3 × [ROBOTIS OMX-AI]({b['url']}), SKU {b['sku']}, ${b['unit_price_usd']:.2f} each / ${b['merchandise_subtotal_usd']:.2f} kit merchandise. "
            'Two kits supply 16 XL330-M288-T and 4 OpenRB-150 for MicroDuck; allocate 15 servos and one controller. The third kit stays intact for leader/follower experiments. '
            'One SMPS 12V 5A + SMPS2DXL + 3-wire cable set from a duck-allocated kit is the robot wall supply. '
            f"Shipping protection ${observed['protection_usd']:.2f}; {observed['shipping_method']} ${observed['shipping_usd']:.2f}; tax ${observed['sales_tax_usd']:.2f}; total ${observed['displayed_total_usd']:.2f}. "
            + status + f"[Merchant confirmation]({observed['file']}). "
            'The earlier two-kit unpaid checkout remains a historical snapshot. '
            'The phone-reported stock count of ten is not independent inventory verification. Other sourcing holds remain unchanged.')


def checklist_notes(item):
    """Current notes first; the sourcing note frozen with the decision follows, labelled as such."""
    note = item['sourcing'].get('note', '')
    if 'engineering_notes' in item and note:
        return item['engineering_notes'] + ' Sourcing note recorded with the decision: ' + note
    return item['notes_zh']


def build_bom():
    raw = json.loads((P / 'catalog-en.json').read_text())
    policy = load_policy(raw)
    items = apply_policy(raw, policy)
    validate_selection(items, policy)
    validate_minimum_quantities(items)
    buy = [x for x in items if x['sourcing']['decision'] == 'buy']
    cart = current_cart(items, policy)
    prices = [x['purchase'] for x in buy]
    assert {x['id'] for x in buy} == BUY_IDS
    assert all(x['purchase']['store'] == 'DigiKey' for x in buy)
    scope = ('15 required XL330 servos and one OpenRB-150 allocated from two of the three received OMX-AI kits; existing first-generation Zero W with soldered 40-pin header, or Pi 3 Model B V1.2 (identities confirmed; populated-board fit, runtime and loaded power unverified); '
             'required Camera Module 3 Wide with correct FFC; body BNO085 and inexpensive '
             'audio (MAX98357A with the 100k GAIN-to-Vin resistor and the 1W speaker, V1.9 head); '
             'owned ROBOTIS SMPS 12V 5A + SMPS2DXL wall end from a duck-allocated OMX-AI kit, its 3-wire cable '
             'spliced to the 2m 18AWG tether and XT30, onboard common 5V regulator, servo power through the '
             'OpenRB-150, and short parallel GPIO Pi power. The received fuses are not used and the received '
             'Adafruit 5991 is a day-1 5V bench part only. '
             'Camera-guided learned pickup remains the goal; this procurement check '
             'does not demonstrate physical operation or trained visual autonomy.')
    result = {'schema_version': 3, 'revision': REVISION, 'language': 'en',
              'problem_ids': ['P5', 'P6'], 'verified_date_local': '2026-09-13',
              'currency': 'USD', 'destination_region': 'Pittsburgh, PA, USA',
              'destination_zip': None, 'design_scope': scope,
              'no_new_order_placed_by_agent': True,
              'bundle_merchandise_subtotal_usd': policy['replacement_bundle']['merchandise_subtotal_usd'],
              'combined_ordered_and_planned_merchandise_usd': round(total(prices) + policy['replacement_bundle']['merchandise_subtotal_usd'], 2),
              'prior_servo_order_status': 'fully_refunded_at_merchant',
              'replacement_bundle': copy.deepcopy(policy['replacement_bundle']),
              'replacement_bundle_order': bundle_order(policy),
              'replacement_bundle_receipt': bundle_receipt(policy),
              'items': items, 'quoted_buy_subtotal_usd': total(prices),
              'all_priced_required_subtotal_usd': total(prices),
              'store_totals_usd': {'DigiKey': total(prices)},
              'selected_route': 'one_remaining_DigiKey_basket_Pi_and_club_holds_preserved',
              'shipping_and_tax_status': 'Current redesigned order shipping, tax and tariff unknown; prior cart fees are stale.',
              'shipping_usd': None, 'tax_usd': None, 'tariff_usd': None,
              'landed_total_usd': None, 'physical_test_count': 0,
              'sourcing_policy': policy,
              'actual_cart_snapshots': [], 'historical_cart_snapshots': historical_evidence(),
              'current_cart_state_known': False,
              'quote_boundary': 'Remaining selected merchandise only; not a delivered robot or checkout total.',
              'open_checks': [
                  'Read back the revised actual basket and verify exact quantities, no held/unmapped lines, shipping, tax and tariff before purchasing handoff.',
                  'Confirm borrowed Pi with pre-soldered header, microSD and SC0727-equivalent OTG adapter; these are required resources with zero purchase quantity.',
                  'Confirm all club wire/headers/insulation/fasteners and test-instrument stock; the 12V wall end uses owned OMX-AI kit parts.',
                  'Use current redesign mechanical print instructions; historical slice evidence does not validate the new converter/audio/cable layout.',
                  'Execute electrical and mechanical commissioning and the camera-guided learned-pickup acceptance; planning checks are not hardware evidence.']}
    if cart:
        result.update(actual_cart_snapshots=cart_snapshot(cart), current_cart_state_known=True,
                      shipping_and_tax_status=cart_status_text(cart),
                      shipping_usd=cart['shipping_estimate_usd'], tariff_usd=cart['tariff_estimate_usd'],
                      cart_total_estimate_usd=cart['total_estimate_usd'])
        result['open_checks'][0] = 'Cart contents verified; read final sales tax and payable total at checkout before payment.'
    result['fastener_cart'] = build_fastener_cart(P, policy, items)
    write('bom.json', result)
    write('quotes.json', {'schema_version': 3, 'revision': REVISION,
                         'source': 'Product-page/catalog quotes; ' + ('matched to current browser cart' if cart else 'no current cart readback'),
                         'quotes': [dict(item_id=x['id'], model=x['model'], **x['purchase']) for x in buy]})
    lines = ['# Remaining procurement and required resources', '',
             f'Revision: {REVISION}. Remaining selected merchandise: **${total(prices):.2f}**, '
             f'{len(buy)} lines at DigiKey. '
             'The original servo/controller order was refunded. Three OMX-AI kits were subsequently ordered: two provide 16 XL330-M288-T and 4 OpenRB-150 for the unchanged 15/1 requirement; the third remains intact. See the order mapping below.', '',
             cart_status_text(cart), '', bundle_status_text(policy), '']
    for x in items:
        amount = x['purchase']['subtotal_usd']
        lines.extend([f"## {x['name_zh']} — {x['sourcing']['decision']}", '',
                      f"{x['model']}. Installed: {x['installed_quantity']} {x['unit']}; external/bench: {x.get('bench_quantity', 0)}; "
                      f"remaining purchase packages: {x['purchase']['packages']}; merchandise: ${amount or 0:.2f}.", '',
                      (x.get('current_role') or ('Required in current design.' if x.get('required_current_design', True) else x['scope_note'])), '',
                      checklist_notes(x), ''])
        if x['purchase'].get('url'):
            lines.extend([f"[Selected or reference supplier]({x['purchase']['url']})", ''])
    lines.extend(summary_lines(result['fastener_cart']))
    (P / 'CHECKLIST.md').write_text('\n'.join(lines))


def comparison(rows):
    """Compare the complete remaining set, retaining identical quantities/parts."""
    selected = [r for r in rows if r['action'] == 'add_now']
    split = []
    for row in selected:
        r = copy.deepcopy(row)
        if r['item_id'] in ADA_IDS:
            r['store'] = 'Adafruit'
            r['url'] = 'https://www.adafruit.com/product/' + ADA_IDS[r['item_id']]
            r['evidence'] = 'Fresh direct Adafruit product-page check 2026-09-13; same price and quantity as DigiKey.'
        split.append(r)
    ada = total([x for x in split if x['store'] == 'Adafruit'], 'quoted_subtotal_usd')
    dk = total([x for x in split if x['store'] == 'DigiKey'], 'quoted_subtotal_usd')
    return {'scope': 'all fifteen remaining purchasable lines, identical models and quantities',
            'checked_date': '2026-09-13', 'consolidated': {'store_count': 1, 'lines': selected,
              'merchandise_usd': total(selected, 'quoted_subtotal_usd'), 'shipping_usd': None,
              'tax_usd': None, 'tariff_usd': None, 'landed_total_usd': None},
            'split': {'store_count': 2, 'lines': split, 'merchandise_usd': round(ada + dk, 2),
              'store_merchandise_usd': {'Adafruit': ada, 'DigiKey': dk},
              'shipping_usd': None, 'tax_usd': None, 'tariff_usd': None, 'landed_total_usd': None},
            'merchandise_penalty_for_consolidation_usd': 0,
            'adafruit_free_shipping_threshold_usd': 199,
            'adafruit_threshold_gap_usd': round(199 - ada, 2),
            'shipping_sources': ['https://www.adafruit.com/free',
              'https://www.adafruit.com/shipping',
              'https://www.digikey.com/en/help-support/delivery-information'],
            'shipping_evidence': 'Adafruit free continental-US ground threshold is $199. DigiKey US shipping starts at $4.99; that is a published starting rate, not the current order quote. No checkout totals were obtained.',
            'verdict': 'Choose the one-store DigiKey basket: it covers the entire remaining purchase set with no verified merchandise-price penalty and one fewer order. This is not a claim of the lowest final landed cost; taxes, tariff and both route shipping fees require current checkout readback.',
            'landed_break_even': 'Split wins on landed cost only if its reduction in tariff/tax/DigiKey shipping exceeds the extra Adafruit shipping. Merchandise savings are zero.'}


def build_cart_plan():
    b = json.loads((P / 'bom.json').read_text())
    policy = load_policy(b['items'])
    items = apply_policy(b['items'], policy)
    validate_minimum_quantities(items)
    rows = []
    for x in items:
        q = x['purchase']; decision = x['sourcing']['decision']
        rows.append({'item_id': x['id'], 'model': x['model'], 'store': q['store'],
                     'url': q['url'], 'action': 'add_now' if decision == 'buy' else 'do_not_add_' + decision,
                     'sourcing_decision': decision, 'installed_quantity': x['installed_quantity'],
                     'required_current_design': x.get('required_current_design', True),
                     'bench_quantity': x.get('bench_quantity', 0),
                     'quantity': q['packages'], 'quoted_subtotal_usd': q['subtotal_usd'] or 0,
                     'notes': x['notes_zh']})
    validate_selection(items, policy, rows)
    selected = [r for r in rows if r['action'] == 'add_now']
    comp = comparison(rows)
    cart = current_cart(items, policy)
    if cart:
        comp['consolidated'].update(shipping_usd=cart['shipping_estimate_usd'],
                                    tariff_usd=cart['tariff_estimate_usd'],
                                    cart_total_estimate_usd=cart['total_estimate_usd'],
                                    evidence='cart-status-r3.json')
        comp['shipping_evidence'] = (f"DigiKey current browser cart: shipping ${cart['shipping_estimate_usd']:.2f}, tariff ${cart['tariff_estimate_usd']:.2f}, estimate ${cart['total_estimate_usd']:.2f}, sales tax not shown. "
                                    'Adafruit free continental-US ground threshold is $199; split-order shipping and final taxes have not been quoted.')
    plan = {'schema_version': 3, 'revision': REVISION, 'language': 'en',
            'status': 'planned_basket_not_actual_cart', 'all_item_classifications': rows,
            'stores': [{'store': 'DigiKey', 'lines': selected,
                        'quoted_subtotal_usd': total(selected, 'quoted_subtotal_usd'),
                        'cart_verified': False, 'shipping_usd': None, 'tax_usd': None,
                        'tariff_usd': None, 'landed_total_usd': None}],
            'add_now_quoted_subtotal_usd': total(selected, 'quoted_subtotal_usd'),
            'unresolved_item_ids': [x['id'] for x in items if x.get('required_current_design', True) and x['sourcing']['decision'] in ['borrow_first', 'club_supply']],
            'actual_cart_readbacks': [], 'historical_cart_snapshots': b.get('historical_cart_snapshots', []),
            'current_cart_state_known': False, 'purchasing_handoff_ready': False,
            'checkout_ready': False, 'orders_placed_by_this_work': False,
            'prior_servo_order_status': 'fully_refunded_at_merchant',
              'replacement_bundle': copy.deepcopy(policy['replacement_bundle']),
              'replacement_bundle_order': bundle_order(policy),
              'replacement_bundle_receipt': bundle_receipt(policy),
            'whole_order_comparison': comp,
            'checkout_blocks': ['The historical basket is stale for this revision; no current full-basket readback.',
                                'Current shipping, tax and tariff are unknown; do not reuse old checkout totals.',
                                'Borrow/club requirements remain non-purchasable; no stock check has released them.']}
    if cart:
        plan.update(status='digikey_cart_unpaid_omx_order_confirmed', actual_cart_readbacks=cart_snapshot(cart),
                    current_cart_state_known=True, purchasing_handoff_ready=True,
                    cart_total_estimate_usd=cart['total_estimate_usd'],
                    checkout_blocks=['Final sales tax and payable total require checkout readback; no payment is authorized.'])
        plan['stores'][0].update(cart_verified=True, actual_lines=cart['lines'],
                                shipping_usd=cart['shipping_estimate_usd'], tariff_usd=cart['tariff_estimate_usd'],
                                cart_total_estimate_usd=cart['total_estimate_usd'])
    plan['bundle_merchandise_subtotal_usd'] = policy['replacement_bundle']['merchandise_subtotal_usd']
    plan['combined_ordered_and_planned_merchandise_usd'] = round(plan['add_now_quoted_subtotal_usd'] + plan['bundle_merchandise_subtotal_usd'], 2)
    plan['purchasing_handoff_ready'] = bool(bundle_order(policy)) and bool(cart)
    plan['replacement_bundle_cart_verified'] = False
    plan['replacement_bundle_order_confirmed'] = True
    plan['checkout_blocks'].append('OMX-AI kits are ordered and received; do not check out duplicate kits.' if bundle_receipt(policy)
                                   else 'OMX-AI is already ordered by the user; do not check out duplicate kits. Shipment tracking and receipt remain pending.')
    plan['fastener_cart'] = build_fastener_cart(P, policy, items)
    write('cart-plan.json', plan)
    write('whole-order-comparison.json', comp)
    text = ['# One remaining electronic order', '',
            f"Selected **{len(selected)} DigiKey lines, ${plan['add_now_quoted_subtotal_usd']:.2f} merchandise**. " +
            cart_status_text(cart), '', bundle_status_text(policy), '']
    for r in selected:
        text.append(f"- {r['quantity']} × [{r['model']}]({r['url']}): ${r['quoted_subtotal_usd']:.2f}.")
    text.extend(['', 'Servos/controller are allocated to the two of three merchant-confirmed OMX-AI kits and excluded from separate component purchases. Pi, microSD, the required SC0727 OTG adapter '
                 'and all club resources remain on their sourcing holds. The adapter has a $1.54 reference fallback; '
                 'it is not charged in the $114.61 plan.', '', '## Complete-order comparison', '',
                 f"All DigiKey: ${comp['consolidated']['merchandise_usd']:.2f}, one order. "
                 f"Identical complete basket split across DigiKey and Adafruit: ${comp['split']['merchandise_usd']:.2f}, "
                 f"two orders (DigiKey ${comp['split']['store_merchandise_usd']['DigiKey']:.2f}; Adafruit ${comp['split']['store_merchandise_usd']['Adafruit']:.2f}). "
                 'No parts-price saving comes from splitting.', '',
                 f"The five direct-Adafruit lines are 5991, 4754, 4397, 3006 and 4472. Their "
                 f"${comp['split']['store_merchandise_usd']['Adafruit']:.2f} order is ${comp['adafruit_threshold_gap_usd']:.2f} below "
                 '[Adafruit\'s $199 free-ground-shipping threshold](https://www.adafruit.com/free). '
                 '[DigiKey US delivery](https://www.digikey.com/en/help-support/delivery-information) starts at $4.99; ' +
                 ('the current DigiKey cart confirms that $4.99 estimate; split shipping is unquoted.' if cart else 'neither current shipping charge is confirmed.'), '', comp['verdict'], '',
                 comp['landed_break_even'], '',
                 'See [machine-readable whole-order comparison](whole-order-comparison.json) for every line in both routes.'])
    text.extend(summary_lines(plan['fastener_cart']))
    (P / 'CARTS.md').write_text('\n'.join(text) + '\n')


def verify():
    raw = json.loads((P / 'catalog-en.json').read_text())
    policy = load_policy(raw)
    b = json.loads((P / 'bom.json').read_text())
    c = json.loads((P / 'cart-plan.json').read_text())
    q = json.loads((P / 'quotes.json').read_text())
    evidence = json.loads((P / 'price-evidence-20260913.json').read_text())
    by = {x['id']: x for x in b['items']}
    old_policy = json.loads((P / 'historical-before-mdy14ed/sourcing-policy.json').read_text())
    for key, prior in old_policy['items'].items():
        if prior['decision'] in ['borrow_first', 'club_supply']:
            assert policy['items'][key]['decision'] == prior['decision'], (key, 'user sourcing hold changed')
    fasteners = build_fastener_cart(P, policy, raw)
    assert b.get('fastener_cart') == c.get('fastener_cart') == fasteners, 'Stale fastener authorization or selection; regenerate'
    assert b['revision'] == c['revision'] == q['revision'] == REVISION
    assert set(by) == {x['id'] for x in raw}
    validate_selection(b['items'], policy, c['all_item_classifications'])
    validate_minimum_quantities(b['items'])
    selected = [x for x in c['all_item_classifications'] if x['action'] == 'add_now']
    assert {x['item_id'] for x in selected} == BUY_IDS
    assert len(selected) == len(BUY_IDS) and all(x['store'] == 'DigiKey' for x in selected)
    quotes_by_id = {x['item_id']: x for x in evidence['digikey']}
    assert set(quotes_by_id) == BUY_IDS
    for row in selected:
        proof = quotes_by_id[row['item_id']]
        assert row['quantity'] == proof['quantity'] <= proof['stock_quantity']
        assert row['url'] == proof['url']
        assert row['quoted_subtotal_usd'] == proof['subtotal_usd']
    assert {x['item_id'] for x in evidence['adafruit']} == set(ADA_IDS)
    assert all(x['in_stock'] and x['unit_price_usd'] == quotes_by_id[x['item_id']]['unit_price_usd'] for x in evidence['adafruit'])
    assert total(selected, 'quoted_subtotal_usd') == total(q['quotes']) == b['quoted_buy_subtotal_usd'] == 114.61
    receipt = json.loads((P / 'order-receipt-items.json').read_text())
    assert receipt['receipt_verified'] and receipt['confirmation_text'] == 'Your order is confirmed'
    assert {(x['item_id'], x['quantity']) for x in receipt['engineering_lines']} == {('servo', 14), ('controller', 1)}
    for key in ['servo', 'controller']:
        assert by[key]['sourcing'] == policy['items'][key], 'Stale sourcing state; regenerate BOM'
        assert by[key]['sourcing']['decision'] == 'included'
        assert by[key]['purchase']['packages'] == 0 and by[key]['order_status']['receipt_verified']
        assert by[key]['order_status']['status'] == 'merchant_confirmed_preparing_shipment'
    assert b['replacement_bundle'] == c['replacement_bundle'] == policy['replacement_bundle']
    assert b['prior_servo_order_status'] == c['prior_servo_order_status'] == 'fully_refunded_at_merchant'
    assert by['servo']['installed_quantity'] == 15 and by['controller']['installed_quantity'] == 1
    for key in ['pi', 'sd', 'usb_otg', 'bench_pi_psu']:
        assert by[key]['sourcing']['decision'] == 'borrow_first' and by[key]['purchase']['packages'] == 0
    assert by['usb_otg']['installed_quantity'] == 1 and 'SC0727' in by['usb_otg']['model']
    assert by['pi_power_plug']['purchase']['packages'] == 0
    assert by['shared_regulator']['installed_quantity'] == 1 and by['pd_receiver']['bench_quantity'] == 1
    assert by['input_fuse']['purchase']['packages'] == 1 and by['branch_fuse']['installed_quantity'] == 9
    assert by['camera']['purchase']['packages'] == by['camera_ffc']['purchase']['packages'] == 1
    assert all(by[k]['purchase']['packages'] > 0 for k in ['amp', 'speaker', 'audio_fuse', 'audio_gain_resistor'])
    cart = current_cart(b['items'], policy)
    assert b['actual_cart_snapshots'] == c['actual_cart_readbacks'] == cart_snapshot(cart)
    assert c['current_cart_state_known'] == bool(cart)
    assert c['purchasing_handoff_ready'] == (bool(bundle_order(policy)) and bool(cart))
    assert b['replacement_bundle_order'] == c['replacement_bundle_order'] == bundle_order(policy)
    assert b['replacement_bundle_receipt'] == c['replacement_bundle_receipt'] == bundle_receipt(policy)
    assert b['current_cart_state_known'] == bool(cart)
    assert c['stores'][0]['cart_verified'] == bool(cart)
    if cart:
        assert c['stores'][0]['actual_lines'] == cart['lines']
        assert c['cart_total_estimate_usd'] == b['cart_total_estimate_usd'] == cart['total_estimate_usd']
    assert not c['checkout_ready']
    assert not c['orders_placed_by_this_work'] and b['physical_test_count'] == 0
    for x in b['historical_cart_snapshots']:
        assert x['sha256'] == digest(P / x['file']) and not x['applies_to_revision']
    comp = c['whole_order_comparison']
    norm = lambda rs: sorted((r['item_id'], r['quantity'], r['model']) for r in rs)
    assert norm(comp['consolidated']['lines']) == norm(comp['split']['lines'])
    assert comp['consolidated']['merchandise_usd'] == comp['split']['merchandise_usd'] == 114.61
    assert comp['split']['store_merchandise_usd'] == {'Adafruit': 49.30, 'DigiKey': 65.31}
    assert comp['adafruit_threshold_gap_usd'] == 149.70
    assert comp['consolidated']['landed_total_usd'] is None and comp['split']['landed_total_usd'] is None
    for name in ['CHECKLIST.md', 'CARTS.md', 'README.md']:
        text = (P / name).read_text()
        assert not any(line.lstrip().startswith('|') for line in text.splitlines()), (name, 'table')
    assert cart_conflicts([{'store': 'DigiKey', 'lines': [{'item_id': 'servo'}]}], policy)
    assert cart_conflicts([{'store': 'DigiKey', 'lines': [{'item': 'unknown'}]}], policy)
    report = {'checked_at': datetime.datetime.now().astimezone().isoformat(),
              'revision': REVISION, 'status': 'PASS_OMX_ORDER_RECEIVED_USER_PHOTO' if bundle_receipt(policy) else 'PASS_OMX_ORDER_CONFIRMED_NOT_RECEIVED',
              'purchasing_handoff_ready': c['purchasing_handoff_ready'], 'replacement_bundle': policy['replacement_bundle'],
              'replacement_bundle_order': bundle_order(policy), 'replacement_bundle_receipt': bundle_receipt(policy), 'actual_cart_line_count': len(cart['lines']) if cart else 0,
              'cart_total_estimate_usd': cart['total_estimate_usd'] if cart else None, 'planned_line_count': len(BUY_IDS),
              'planned_merchandise_usd': b['quoted_buy_subtotal_usd'], 'new_orders_placed_by_agent': False, 'user_placed_omx_order_confirmed': True,
              'physical_test_count': 0,
              'verified': ['Explicit sourcing for every engineering item',
                           'Refunded historical order retained; confirmed three-kit OMX-AI order allocates two kits to unchanged 15/1 engineering demand',
                           'Camera/audio present and user Pi/club holds preserved',
                           'Identical entire basket compared across one versus two stores',
                           'Current cart accepted only by all-line browser evidence; historical hashes retained separately',
                           'Unmapped and held cart lines still block checkout']}
    report['fastener_cart'] = fasteners
    write('english-verification.json', report)
    print(json.dumps(report, indent=2))

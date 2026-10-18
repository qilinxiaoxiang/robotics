"""Narrow cart-only fastener authorization; catalog fallback offers stay held."""
import hashlib
import json
import math
from pathlib import Path


def proof(base, record):
    path = (base / record['file']).resolve()
    assert path.is_relative_to(base.resolve()), 'Evidence must remain in procurement'
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256'], 'Missing or changed fastener evidence'
    return path


def build_fastener_cart(base, policy, items):
    config = policy.get('fastener_cart_authorization')
    if not config:
        return None
    authorization_path = proof(base, {'file': config['authorization_file'], 'sha256': config['authorization_sha256']})
    authorization = json.loads(authorization_path.read_text())
    assert not authorization['checkout_authorized'] and not config['checkout_authorized'], 'Fastener cart scope does not authorize checkout'
    assert authorization['verbatim_user_request'] and authorization['root_session_id']
    scope = set(authorization['scope_item_ids'])
    assert scope == set(config['scope_item_ids']), 'Fastener authorization scope mismatch'
    by = {i['id']: i for i in items}
    assert scope <= set(by)
    for key, before in authorization['unrelated_policy_items_before'].items():
        assert policy['items'][key] == before, (key, 'Unrelated sourcing hold changed')
    for key in scope:
        assert by[key].get('required_current_design', True) and by[key]['installed_quantity'] + by[key].get('bench_quantity', 0) > 0, (key, 'Inactive or zero-demand fastener')
    manifest_path = base / config['offers_file']
    manifest = json.loads(manifest_path.read_text())
    assert manifest['authorization_id'] == authorization['authorization_id']
    required = {key: by[key]['installed_quantity'] + by[key].get('bench_quantity', 0) for key in scope}
    credited = {key: 0 for key in scope}
    allocated = dict(credited)
    for credit in manifest.get('verified_stock_credits', []):
        key = credit['item_id']
        assert key in scope and isinstance(credit['quantity'], int) and credit['quantity'] > 0
        proof(base, credit['evidence'])
        assert credit['physically_verified'] is True, 'Unverified kit contents cannot reduce fastener demand'
        credited[key] += credit['quantity']
        assert credited[key] <= required[key]
    offers = manifest['selected_offers']
    ids = set(); merchandise = 0
    for offer in offers:
        assert offer['offer_id'] not in ids, 'Duplicate offer'
        ids.add(offer['offer_id'])
        assert offer['store'] and offer['url'].startswith('https://') and offer['product_variant']
        assert offer['compatibility_verified'] is True and offer['price_verified'] is True
        proof(base, offer['price_evidence'])
        count = offer['package_quantity']
        assert isinstance(count, int) and count > 0
        assert offer['package_price_usd'] > 0 and round(count * offer['package_price_usd'], 2) == offer['subtotal_usd']
        assert offer['coverage'], 'No mapped fastener coverage'
        seen = set(); minimum_packages = 0
        for coverage in offer['coverage']:
            key = coverage['item_id']; units = coverage['units_per_package']; used = coverage['allocated_units']
            assert key in scope and key not in seen, 'Unapproved or duplicate fastener mapping'
            seen.add(key)
            assert isinstance(units, int) and isinstance(used, int) and units > 0 and used > 0 and used <= count * units
            assert coverage['compatibility_verified'] is True and coverage['verified_specification']
            proof(base, coverage['compatibility_evidence'])
            allocated[key] += used
            assert allocated[key] + credited[key] <= required[key], (key, 'Duplicate allocation or unsupported stock credit')
            minimum_packages = max(minimum_packages, math.ceil(used / units))
        assert count == minimum_packages, 'Extra packages not needed for allocated working parts'
        merchandise += offer['subtotal_usd']
    merchandise = round(merchandise, 2)
    assert merchandise <= authorization['working_merchandise_ceiling_usd'], 'Working inexpensive-cart ceiling exceeded'
    native = manifest.get('native_cart_evidence')
    verified = False
    if native:
        observed = json.loads(proof(base, native).read_text())
        proof(base, observed['browser_readback'])
        assert observed['verified_after_reload'] is True and observed['checkout_submitted'] is False
        assert {x['offer_id'] for x in observed['lines']} == ids and len(observed['lines']) == len(offers), 'Native fastener lines differ from selected offers'
        by_offer = {x['offer_id']: x for x in offers}
        for line in observed['lines']:
            offer = by_offer[line['offer_id']]
            for key in ['store', 'url', 'product_variant', 'package_quantity', 'package_price_usd', 'subtotal_usd']:
                assert line[key] == offer[key], ('Native fastener cart mismatch', key)
        assert observed.get('unmapped_lines', []) == [], 'Unmapped current cart lines block handoff'
        assert observed['merchandise_subtotal_usd'] == merchandise
        verified = bool(offers)
    return {'authorization_id': authorization['authorization_id'], 'authorization_file': config['authorization_file'],
            'authorization_sha256': config['authorization_sha256'], 'offers_file': config['offers_file'],
            'offers_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'status': ('partial_cart_verified' if any(credited[k] + allocated[k] < required[k] for k in scope) else 'native_cart_verified_no_checkout') if verified else ('selected_offers_await_native_cart' if offers else 'authorized_research_pending_selection'),
            'selected_offers': offers, 'selected_offer_count': len(offers), 'selected_merchandise_usd': merchandise,
            'required_units': required, 'verified_stock_credits': credited, 'allocated_units': allocated,
            'remaining_uncovered_units': {k: required[k] - credited[k] - allocated[k] for k in sorted(scope) if required[k] > credited[k] + allocated[k]},
            'working_merchandise_ceiling_usd': authorization['working_merchandise_ceiling_usd'],
            'budget_is_user_selected': False, 'native_cart_verified': verified, 'checkout_authorized': False,
            'all_required_fasteners_covered': all(credited[k] + allocated[k] == required[k] for k in scope),
            'catalog_fallback_offers_released': False, 'unrelated_sourcing_holds_preserved': True}


def summary_lines(plan):
    if not plan:
        return []
    lines = ['## Separate fastener cart authorization', '',
             'The September 29 user request authorizes researching inexpensive compatible fasteners on Amazon and adding verified offers to cart. Checkout is not authorized. Other sourcing holds remain unchanged.', '',
             f"Status: {plan['status']}. Selected packages: {plan['selected_offer_count']} offers, ${plan['selected_merchandise_usd']:.2f} merchandise. The $30 working ceiling is an agent assumption, not a user-selected budget.", '',
             '[Exact authorization and evidence requirements](fasteners-amazon-20260929/README.md). Catalog fallback offers remain held; only the separate exact offer manifest can authorize fastener cart lines.', '']
    for offer in plan['selected_offers']:
        lines.append(f"- {offer['package_quantity']} package(s) of [{offer['product_variant']}]({offer['url']}): ${offer['subtotal_usd']:.2f}; " + ', '.join(f"{c['allocated_units']} working units for {c['item_id']}" for c in offer['coverage']) + '.')
    lines.extend(['', f"Uncovered fastener requirements: {len(plan['remaining_uncovered_units'])} specifications. Native cart verified: {plan['native_cart_verified']}. No checkout or physical stock is implied.", ''])
    return lines

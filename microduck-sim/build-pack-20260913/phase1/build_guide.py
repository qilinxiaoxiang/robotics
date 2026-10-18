"""Build the single English Phase1 handbook from the reviewed component recipes."""
from pathlib import Path
import json, re, os, subprocess, hashlib
P=Path(__file__).resolve().parent
bom=json.loads((P.parent/'procurement/bom.json').read_text())
rows=[x for x in bom['items'] if x['sourcing']['decision']=='buy']
context=json.loads((P.parent.parent/'PROJECT-CONTEXT.json').read_text())
training=json.loads((P.parent.parent/context['training']['results']).read_text())
header=f"""# MicroDuck component bring-up — one source, two suppliers

Revision: **phase1-single-source-r2** · 13 September 2026 · Problems P5/P6

**Project goal:** {context['goal']}

**Existing training:** recorded held-out results are {training['initialSuccesses']}/{training['trials']} before training, {training['trainedSuccesses']}/{training['trials']} after training, and {training['scriptedSuccesses']}/{training['trials']} for the scripted controller. The learned jaw uses simulation observations. See the [training evidence](../../microduck-simulator/rl/RESULTS.md) and [canonical project context](../../PROJECT-CONTEXT.json).

**Incomplete project handoff:** the current software package supports component bring-up. Camera capture, visual alignment and transfer of the trained jaw to real observations remain missing. The camera is required for the pickup goal. The listed order excludes camera/audio additions while their integration review is open; it is not the complete visual-pickup purchase list. The [project check](project-context-review.json) rejects that complete-project claim.

Assemble the 15-servo chassis, including ID15 jaw, using the existing Xiaomi power bank as its single source. A USB-C receiver requests 12V and one regulator supplies 5V to both motors and Pi. These source parts stay beside the test lane, with one bundled tether into the duck. Keep the borrow-first Pi 3 or first-generation Pi Zero options and RoboClub printing/fasteners/consumables route. Exact board variant is unconfirmed; the existing CAD is only a Zero-form-factor reference, not Pi 3 mounting or power approval.

## Work in this order

1. Record delivery of the servo order already placed. Review the remaining DigiKey selection and required camera integration. Settle the borrowed Pi/header/microSD and club fastener, wire and test-tool resources before scheduling assembly.
2. Print the [85-instance, six-plate Phase 1 queue](PRINT-LIST.md). Check the jaw sliding fit and idler screw fit before repeating assembly. Do not print the legacy 89-instance queue.
3. Prepare the frozen software and calibrate the torso IMU before connecting motors. Prepare and test the single-source power assembly with external loads.
4. Connect one motor at a time, assign IDs1-15 and pass the Wizard small-motion checks. Assemble and test the jaw, then torso, legs and head.
5. Complete supported standing, walking/stopping and pickup component tests, then five consecutive bring-up trials. This intermediate check is operator-controlled walking 0.3m to a prepositioned soft foam object, stopping, lifting at least 10mm, holding three seconds and releasing. Passing it does not complete the visual-pickup goal.

Fill the [physical acceptance record](ACCEPTANCE-RECORD.md). Actual hardware tests remain zero. The supplied checks cannot establish actual borrowed stock or physical performance before assembly.

## Procurement record

"""
total=sum(x['purchase']['subtotal_usd'] for x in rows)
carts=sum([json.loads((P.parent/'procurement'/name).read_text())['stores'] for name in ['cart-status-root.json','cart-status-procurement.json']],[])
active=[x for x in carts if x['store'] in ['ROBOTIS','DigiKey']]
fees=sum((x.get('shipping_usd') or 0)+(x.get('duties_usd') or 0) for x in active)
header+=f"**Recorded merchandise: ${total:.2f}.** The recorded shipping/tariff estimates add ${fees:.2f}, for **${total+fees:.2f} before any additional final-checkout tax**. The user reports the servo order has been placed; the ROBOTIS figures below are historical and are not a repeat-purchase instruction. DigiKey's eight recorded lines exclude the required camera addition.\n\n"
for x in active:
 header+=f"- {x['store']}: shipping ${x.get('shipping_usd',0):.2f}; tariff estimate ${(x.get('duties_usd') or 0):.2f}; displayed total ${x['displayed_checkout_total_usd']:.2f}.\n"
header+='\n'
for store,url in [('ROBOTIS US','https://robotis.us/cart'),('DigiKey','https://www.digikey.com/ordering/shoppingcart')]:
 chosen=[x for x in rows if x['purchase']['store']==store]
 status='Ordered, per user report' if store=='ROBOTIS US' else 'Incomplete for visual pickup'
 link_label='Historical supplier cart' if store=='ROBOTIS US' else 'Open existing cart'
 header+=f"### {store} — ${sum(x['purchase']['subtotal_usd'] for x in chosen):.2f} — {status}\n\n[{link_label}]({url})\n\n"
 for x in chosen:
  p=x['purchase'];header+=f"- **{p['packages']} × {x['name_zh']}:** {x['model']}. ${p['subtotal_usd']:.2f}. [Product]({p['url']})\n"
 header+='\n'
header+="""Fourteen standalone motors plus the motor in the Starter Kit give **15**. Ten 3A fuses supply nine installed and one spare; two 10A fuses supply one installed and one spare. Two MicroB plugs make the compact Pi power and data connections. Adafruit's four duplicate lines have been removed and its cart is empty. Other historical carts are not buying destinations; the unrelated preexisting Pololu $8.49 item is excluded.

The [actual same-parts whole-order comparison](../procurement/ORDER-COMPARISON.md) independently checks supplier consolidation: two stores total $535.70; the temporarily reconstructed three-store orders quote $541.75, both before sales tax. Consolidation alone saves $6.05. Afterwards the two-store basket was restored and Adafruit returned to zero items.

## Existing resources needed for assembly

- Borrow a Pi 3 or first-generation Pi Zero. Confirm its exact variant, fitted 40-pin header, bootable microSD, card reader and Imager access. Existing Zero-form-factor geometry and connector/power calculations do not qualify Pi 3 mounting or power; either choice still needs camera, USB, network and runtime checks.
- Use the existing Xiaomi PB1033MI 33W bank and its intact attached cable. The receiver and regulator stay on an insulated ventilated fixture beside the lane; no new onboard mass is introduced in Phase 1.
- Use club PLA/printer, **1m per color 16AWG wire**, **2m per color 20AWG wire**, solder, heat-shrink, ties, glue and fasteners. Check the exact **M2.6 × 6 TAP** idler screws; ordinary similarly sized machine screws are not interchangeable. The assembly section lists the retained lengths and printed bearings.
- Use club soldering tools, meter, adjustable electronic load and transient/current measurement equipment, caliper, screwdrivers, marker, scale and fall-catching support. Arrange a ventilated insulating fixture for the source modules. Copper prototyping board/thermal assembly may be needed if the converter fails its initial thermal test; do not buy a second source as an unreviewed workaround.

These are requirements, not verified claims of club stock. Purchasing holds remain in force. [Detailed sourcing policy](../procurement/sourcing-policy.json).

## Connector basics and OpenRB preparation

A **terminal** is a wire connection point; the receiver's screw terminal clamps stripped wire. Its screw does not enter the USB plug. A **regulator** changes the received 12V to steady 5V. A **branch** splits that same 5V source to different loads. A **fuse** opens after sufficient overcurrent and time; it does not regulate voltage. **AWG** describes wire size: 16AWG is thicker than 20AWG. **Strain relief** transfers a cable pull to the supporting frame instead of the solder joint.

New OpenRB boards ship with the **usb_to_dynamixel** bridge. First test it; if other firmware is installed, follow the [official board-manager and firmware recovery instructions](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/). Keep motors disconnected while uploading. The detailed power section establishes the USB jumper and data-only motor connection before the software's one-motor ID steps.

"""
# Rebase component-document links into this one delivery directory.
def fragment(path):
 txt=path.read_text();txt=re.sub(r'^# ', '## ', txt,flags=re.M);txt=re.sub(r'^## (?!Phase 1)', '### ', txt,flags=re.M)
 def rebase(m):
  label,url=m.groups()
  if url.startswith(('https:','http:','#','mailto:')):return m.group(0)
  file,sep,anchor=url.partition('#');target=Path(file);target=target if target.is_absolute() else path.parent/target
  return '['+label+']('+os.path.relpath(target,P)+(sep+anchor if sep else '')+')'
 return re.sub(r'\[([^\]]*)\]\(([^)]+)\)',rebase,txt)
assembly=fragment(P/'assembly-audit.md')
power=fragment(P/'power-research.md')
runtime=fragment(P/'runtime/README.md')
power_use=power
sim=json.loads((P/'simulation/candidate-regression.json').read_text());off=json.loads((P/'runtime/offline-results.json').read_text())
footer=f"""## Verification and remaining physical acceptance

The current print route contains 85 instances on six plates. Walking/stopping simulation passes {sim['gait_and_stop_passed']}/{sim['count']} cases; frozen-runtime offline checks pass {off['offline_tests']}/{off['offline_tests']}. These are software evidence, not actual walking or power measurements. The new power screen separately checks motor and Pi endpoints; the current catalog, carts and guide are generated and checked together. [Verification record](verification.json).

Complete the physical power, joint calibration, supported walking and pickup gates above, followed by five consecutive bring-up trials. If measurements contradict the selected source or harness, record the failing condition and revise that decision before purchasing replacements. Camera integration and the learned-policy transfer remain required work toward the project goal; the component tests do not defer or remove them.

[Print files](PRINT-LIST.md) · [Editable handbook](START-HERE.md) · [Power sources and calculations](power-research.md) · [Repair audit](audit-20260913/REPAIR-AUDIT.md)
"""
text=header+assembly+'\n## Build and test the power harness\n\n'+power_use+'\n'+runtime+'\n'+footer
(P/'START-HERE.md').write_text(text)
css='''<style>body{font-family:system-ui,-apple-system,sans-serif;color:#21313b;background:#f7f9fa;max-width:1080px;margin:auto;padding:40px 30px;line-height:1.65;font-size:17px}h1{font-size:40px;line-height:1.2}h2{margin-top:60px;border-top:1px solid #ccd8dd;padding-top:24px;line-height:1.25}h3{margin-top:35px}a{color:#1761a2}img{max-width:100%;height:auto;background:white;border:1px solid #dde6e9;border-radius:12px}figure{margin:28px 0}figcaption{font-size:14px;color:#687b87}pre{padding:18px;background:#eaf0f3;overflow:auto;border-radius:10px;font-size:14px;line-height:1.55}code{font-size:.9em}li{margin:9px 0}#TOC{padding:20px;background:white;border-radius:14px}#TOC ul{list-style:none;padding-left:20px}blockquote{margin:20px 0;padding:10px 22px;border-left:4px solid #dd9940}body>p:first-of-type{color:#657984}</style>'''
(P/'guide-style.html').write_text(css)
subprocess.run(['pandoc',str(P/'START-HERE.md'),'--standalone','--toc','--toc-depth=2','--metadata','title=MicroDuck Phase 1 build handbook','--include-in-header',str(P/'guide-style.html'),'-o',str(P/'START-HERE.html')],check=True)
print(json.dumps({'guide':str(P/'START-HERE.html'),'word_count':len(text.split()),'buy_lines':len(rows)}))

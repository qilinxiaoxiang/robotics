"""Build the single English Phase1 handbook from the reviewed component recipes."""
from pathlib import Path
import json, re, os, subprocess, hashlib
P=Path(__file__).resolve().parent
bom=json.loads((P.parent/'procurement/bom.json').read_text())
rows=[x for x in bom['items'] if x['sourcing']['decision']=='buy']
header='''# MicroDuck Phase 1 — Build, commission, walk and pick up

Revision: 13 September 2026 · English build handbook · Problems P5/P6

**Build the complete 15-servo duck, including its moving jaw.** Use an external 5V motor supply, the existing power bank for control electronics, a borrowed Raspberry Pi Zero 2 W, and Mac keyboard control. Keep the camera, sound system and onboard battery for Phase 2.

The Phase 1 task is specific: on a level test surface, the operator walks the duck toward a prepositioned soft foam object, stops, lowers its head, closes its beak, lifts the object, holds it for three seconds and releases it. Five consecutive unassisted robot/object trials complete acceptance. The operator still controls the sequence. Camera-based object finding, arbitrary objects, autonomous navigation and carrying while walking are later work.

This is the current build route. Earlier battery/regulator purchasing lists and assembly steps are Phase 2 references. The existing camera, battery and sound mounting interfaces remain in the retained structure.

![Whole Phase 1 system and acceptance path](figures/phase1-panorama.png)

## Work in this order

1. Check out the three **Order today** carts below, and resolve the **existing-resource list** before scheduling assembly.
2. Print the six plates using the club's actual printer and plate settings; inspect the jaw's sliding fit before duplicating assembly operations.
3. Prepare the Pi and frozen software bundle in the software section. The dependency/model check does not need connected motors.
4. Prepare the unpowered fused harness and complete the source/load checks in **Build and test the power harness**. Keep unused motor outputs insulated.
5. Connect and label one motor at a time. Complete the Wizard small-motion check for IDs1–15, then assemble and test the jaw module.
6. Assemble torso, legs and head. Install the Pi, BNO085 and harness, then commission each powered branch with the body supported. Perform the sensor-only torso calibration before full-body motor enable.
7. Capture actual body/jaw poses. Pass supported pickup, standing and walking/stopping before the five complete walk-up-and-pickup trials.

Each numbered assembly stage below has its own pass criterion. The software section contains the exact commands; the power section contains the detailed wire recipe. Fill the [physical acceptance record](ACCEPTANCE-RECORD.md) as the work is performed.

## Order today

Three current carts contain the ten purchasing lines below. Merchandise is **$514.92**. This is not a delivered total: DigiKey currently estimates another **$8.30 tariff and $4.99 shipping**, while ROBOTIS/Adafruit shipping and all final sales taxes still depend on checkout. No payment or order has been made.

'''
for store,title,url in [('ROBOTIS US','ROBOTIS','https://robotis.us/cart'),('Adafruit','Adafruit','https://www.adafruit.com/shopping_cart'),('DigiKey','DigiKey','https://www.digikey.com/ordering/shoppingcart')]:
 chosen=[x for x in rows if x['purchase']['store']==store]
 header+=f'### {title} — ${sum(x["purchase"]["subtotal_usd"] for x in chosen):.2f}\n\n[Open the prepared cart]({url})\n\n'
 for x in chosen:
  p=x['purchase'];header+=f'- **{p["packages"]} × {x["name_zh"]}:** {x["model"]}. ${p["subtotal_usd"]:.2f}. [Exact product]({p["url"]})\n'
 header+='\n'
header+='''The Starter Kit includes one XL330: fourteen standalone motors plus that one gives **15**, not 14. The 10A fuse order provides one installed and one spare; the ten 3A fuses provide eight installed and two spare. The two Micro-B plugs make the compact Pi power and data connections.

These three carts were read back after removing deferred parts. Ten other project carts are empty; Pololu retains one unrelated preexisting $8.49 item, excluded from this build and not a Phase 1 order. No additional items are needed to reach free shipping. The previous camera/audio/onboard-power carts should not be checked out.

**Arrival:** all four DigiKey lines show immediate availability, but DigiKey warns that processing may take an extra business day. Neither stock nor a ground-shipping menu provides a destination delivery date. Record the actual delivery dates when checking out; none is asserted here.

## Obtain from existing resources before assembly

These are required resources with purchasing holds, not claims that stock has already been found:

- Borrow a **Raspberry Pi Zero 2 W with its 40-pin header fitted**, a microSD card (16GB or larger), card reader and access to Raspberry Pi Imager. Another Pi model needs a mounting, connector and timing check before replacing this baseline.
- Use the existing **Xiaomi 5V / 3A USB-C power bank** for Pi, IMU and OpenRB logic. Borrow a suitable USB-C-to-Micro-B cable to prepare the compact power lead. Leave the power bank and its attached cable unmodified. If its automatic shutoff interrupts the 30-minute logic test, use a borrowed Pi supply and repeat.
- Borrow an intact **grounded US wall-to-IEC-C13 power cord** for the Mean Well adapter. This is the common three-contact computer-style wall cord. It is not included with this adapter; no exposed mains wiring is required.
- Use RoboClub's printer, PLA, wire, heat-shrink, solder, ties, glue and fasteners. The exact **M2.6 × 6 TAP screws for passive idler stations** must be checked in club stock; they do not come in the standalone motor packages. The assembly section identifies the other lengths. Do not substitute an ordinary machine screw because its diameter looks similar.
- Use club screwdrivers, caliper, soldering tools, multimeter and suitable power-load/current/voltage measurement equipment. A multimeter checks voltage and connections; a scope/current instrument catches short events a slow display can miss. Arrange a fall-catching support and a scale for the foam sample.

The Pi and exact idler screws are the two stock checks to settle before scheduling full assembly. Their purchasing holds remain in force. A complete shopping cart cannot itself supply borrowed items.

## Learn the connections before touching a wire

You already know plugging a USB cable into a computer. A **connector** is that physical joining part: a **plug** enters a **socket**, and small metal **contacts** touch inside it. A bare wire has conductive metal inside insulating plastic.

A **terminal** is a place where a wire joins a device. A **terminal block** holds several such places in an insulating body. A **screw terminal** uses a screw to tighten a metal clamp around the prepared wire end. Loosen, insert exposed metal into the wire hole, tighten, then gently tug. The screw belongs to the connector on the board; it never screws into a USB-C plug.

A **USB power breakout** presents power from a USB socket at wire terminals. In the example below, the USB-C cable plugs normally into the small board; two separate wires leave its other side for OpenRB. This explains the earlier power-bank suggestion. The complete Phase 1 motor route uses the Mean Well supply and prewired socket instead, so the example breakout is **not** another item to order.

![USB-C socket, wire terminals and the screw clamp](figures/usb-c-to-terminals.png)

The adapter's round **DC barrel plug** enters the matching **barrel jack/socket**. The specified supply is **center positive**: the center contact is +5V, and the outer contact is the return. **Polarity** means which connection is positive and which is return; reversing them is not a valid alternative. A meter verifies the actual connection.

A **fuse** is a sacrificial link that opens after excessive current for a sufficient time. It protects the wiring against faults; it does not make the voltage correct or clamp current to its printed number. A **wire harness** is the prepared collection of wires and connectors. In this design, a shared positive/return point splits into eight fused branches, then each motor receives its own power tail. The command wire remains shared.

**Soldering** joins metal with molten solder. **Heat-shrink tubing** is insulating plastic slipped over that joint and shrunk with heat. **Strain relief** means securing the cable to the frame so a pull reaches the frame, rather than the electrical joint. **AWG**, American Wire Gauge, specifies wire size: the lower number here means thicker copper, so 16AWG is thicker than 20AWG.

**IMU**, inertial measurement unit, is the BNO085 body-orientation sensor. It helps the controller know whether the torso is leaning. Its **I2C** sensor connection uses two signal wires plus power and return. Pi performs the balance calculation; OpenRB provides the compatible motor communication connection. The **power-source jumper** is a removable cap placed over the specified pair of pins to select a board's power path.

The learning graph now contains the terminal/connector prerequisites and records the reported gaps as unknown, not understood. [Open screw-terminal learning path](http://127.0.0.1:5063/?target=screw-terminal&dimension=intuition).

## OpenRB firmware and first communication

New OpenRB boards ship with the **usb_to_dynamixel** bridge already installed. Start by testing that bridge, instead of reflashing a working new board. It supports motor communication up to 1Mbps. [ROBOTIS firmware reference](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/#dynamixel-wizard-20)

If the board has other firmware, recover the bridge in Arduino IDE: add the official board-manager URL below in Preferences; install **Arduino SAMD Boards** and **OpenRB** in Boards Manager; select OpenRB-150 and its detected USB port; open the board package's **usb_to_dynamixel** example and Upload. Disconnect motor power while uploading. Reconnect only after the bridge enumerates successfully. The connector is USB-C; the firmware supplies the USB-to-motor communication behavior.

```text
https://raw.githubusercontent.com/ROBOTIS-GIT/OpenRB-150/master/package_openrb_index.json
```

[Official board installation steps](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/#install-board-manager). First prepare and verify the external power harness as described below; then assign IDs with exactly one motor connected at a time using the software section. Read that software setup before mounting the motors, since configuration precedes closing each joint.

'''
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
# Supplier-comparison audit stays an appendix rather than interrupting the wiring recipe.
power_start=power.index('### Assemble the motor harness')
power_end=power.index('### Why FanGe')
power_use=power[power_start:power_end]
footer='''## Why the 6.4V video can run

The XL330 operating range is 3.7–6.0V, but its factory **Max Voltage Limit** value is 7.0V. A motor can therefore move at 6.4V without reaching that default shutdown threshold. FanGe's tutorial also removes the input-voltage shutdown trigger to avoid battery-dip interruptions. Neither changes the manufacturer's permitted operating range. The visible pack label is nominal battery voltage, not a regulated-output measurement. Our Phase 1 uses regulated 5V and retains voltage, temperature and overload protections. [ROBOTIS control table](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/), [FanGe tutorial](https://github.com/AI-FanGe/Microduck-build-tutorial).

## Verification record and next physical test

The current digital checks advance the build toward a physical MVP. They do not label absent hardware as already tested.

'''
sim=json.loads((P/'simulation/candidate-regression.json').read_text());off=json.loads((P/'runtime/offline-results.json').read_text())
footer+=f'- **Printing:** 85 instances sliced successfully across six plates, predicted 372.97g PLA and 16h44m13s. Actual printing and fit remain arrival/club work.\n- **Walking and stopping:** {sim["gait_and_stop_passed"]}/{sim["count"]} simulated cases pass, including4.0V and mass changes, with sensor prediction disabled. Original20/27 baseline failures are preserved; changed controller gain and stop behavior address them. [Scope and results](simulation/README.md).\n- **Hardware software path:** {off["offline_tests"]}/{off["offline_tests"]} offline cases pass with actual frozen controller classes and both real ONNX models. Serial transport and sensor readings are substituted; actual motor/grasp tests remain0. [Test record](runtime/offline-results.json).\n- **Power:** the selected supply and stated harness assumptions calculate a4.011V worst endpoint at the5A screen. This is a narrow calculated margin, not a measured guarantee. Simulation motor-current proxies do not prove source current. The actual load/transient and task gates above are mandatory. [Calculation and exact assumptions](power-research.md).\n- **Procurement:** ten buy lines across three carts total$514.92; zero held items in mapped carts after reconciliation. Club supply and Pi borrowing remain separate. [Purchasing consistency record](../procurement/english-verification.json).\n\n'
footer+='''Start with the unpowered harness/one-motor tests, then jaw, standing, walking/stopping and the combined task. If a stage fails, record the failure and correct that stage before continuing. Do not mark a later acceptance box from an earlier simulated or unloaded test.

## Phase 2

Add monocular camera/video and object perception, sound, and untethered battery operation after Phase 1 measurements establish actual power demand and balance. Reuse the existing jaw, OpenRB, servos, IMU, frame mounting interfaces and fused motor distribution. Reweigh and repeat walking/pickup tests whenever a module is installed. Only then select the final battery/converter capacity from measured loads.

[Exact print files](PRINT-LIST.md) · [Editable handbook](START-HERE.md) · [Frozen runtime bundle](runtime/bundle/) · [Source and calculation appendix](power-research.md)
'''
text=header+assembly+'\n## Build and test the power harness\n\n'+power_use+'\n'+runtime+'\n'+footer
(P/'START-HERE.md').write_text(text)
css='''<style>body{font-family:system-ui,-apple-system,sans-serif;color:#21313b;background:#f7f9fa;max-width:1080px;margin:auto;padding:40px 30px;line-height:1.65;font-size:17px}h1{font-size:40px;line-height:1.2}h2{margin-top:60px;border-top:1px solid #ccd8dd;padding-top:24px;line-height:1.25}h3{margin-top:35px}a{color:#1761a2}img{max-width:100%;height:auto;background:white;border:1px solid #dde6e9;border-radius:12px}figure{margin:28px 0}figcaption{font-size:14px;color:#687b87}pre{padding:18px;background:#eaf0f3;overflow:auto;border-radius:10px;font-size:14px;line-height:1.55}code{font-size:.9em}li{margin:9px 0}#TOC{padding:20px;background:white;border-radius:14px}#TOC ul{list-style:none;padding-left:20px}blockquote{margin:20px 0;padding:10px 22px;border-left:4px solid #dd9940}body>p:first-of-type{color:#657984}</style>'''
(P/'guide-style.html').write_text(css)
subprocess.run(['pandoc',str(P/'START-HERE.md'),'--standalone','--toc','--toc-depth=2','--metadata','title=MicroDuck Phase 1 build handbook','--include-in-header',str(P/'guide-style.html'),'-o',str(P/'START-HERE.html')],check=True)
print(json.dumps({'guide':str(P/'START-HERE.html'),'word_count':len(text.split()),'buy_lines':len(rows)}))

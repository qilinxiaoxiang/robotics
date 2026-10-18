# Smaller battery option — research, not a purchase release

Verified 2026-10-08. Problem P0/P5. Retain the procurement review holds; no purchase or cart change is authorized by this research request.

The compact candidate is [Tattu 650 mAh 2S 7.4 V 75C, XT30](https://www.tattuworld.com/products/tattu-classic-650mah-2s1p-7-4v-75c-fpv-lipo-battery.html), model TAA6502S75XT3 / TA-75C-650-2S1P-XT30. Manufacturer nominal size is 57 × 31 × 12 mm, 43 g; allow the stated +5/+2/+2 mm size tolerance, plus 45 mm leads and connectors. The high discharge rating is a manufacturer claim; robot load performance remains unmeasured.

At the existing 45 W output budget, nominal 7.4 V and an assumed 85% converter efficiency require about 7.2 A from the pack. Its rating offers nominal current headroom. Energy is only 4.81 Wh: idealized runtime is about 5.5 minutes at 45 W or 12 minutes at 20 W, before reserve, voltage sag, temperature and usable-capacity losses. This trades Xiaomi's much larger energy reserve for a lighter, smaller pack.

The maximum-tolerance pack fits the old 22 × 34 × 63 mm battery allowance alone. DFR1202 now occupies part of that volume. The current geometric review finds that a battery behind the converter would need about 6.1 mm of additional rear depth for 2 mm separation. This is a plausible small extension, not proven complete coexistence or a released print design. Leads, insertion, retention and motion remain to be modeled for this alternative.

## Availability and total cost

- [GetFPV exact product](https://www.getfpv.com/tattu-650mah-2s1p-75c-7-4v-lipo-battery-pack-with-xt30-plug.html): live Chrome product page showed **$14.99, In Stock**. [Shipping terms](https://www.getfpv.com/terms) say in-stock weekday orders before 2:30 pm Eastern typically ship the same day, but batteries require ground shipment. Its [shipping page](https://www.getfpv.com/shipping.html) gives economy 3–10 business days, usually 3–5. These are general estimates, not an address-specific delivery promise; expedited 2–3 day claims do not apply reliably to batteries.
- [Manufacturer US store](https://genstattu.com/tattu-650mah-2s1p-75c-7-4v-lipo-battery-pack-with-xt30-plug.html): earlier lookup showed $8.19. California dispatch plus ground transit to Pennsylvania makes this a lower-price option rather than a verified urgent-delivery choice.
- [B&H exact model](https://www.bhphotovideo.com/c/product/1878031-REG/tattu_taa6502s75xt3_650mah_2s_75c_7_4v.html): $8.19, special order, currently lists 8–10 months. Reject for this urgent task.

The battery price is not a complete power-system price. A 2S balance charger and individual-cell low-voltage monitoring are required. Club equipment should be checked before buying another charger. The [ISDT 608PD manufacturer manual](https://www.isdt.co/down/pdf/608PD.pdf) describes a compatible charger class with USB-C input and adjustable current; a current in-stock charger offer and delivered kit price have not been verified. The GetFPV page links a $5.49 low-voltage buzzer, which signals low voltage but does not cut power automatically.

## Integration consequences

Feed the raw 2S pack into the existing DFR1202 input through correctly rated protection and wiring. It bypasses the USB-C negotiation board. Never connect raw 7.4–8.4 V to the Pi or existing 5 V motor rail. Recheck the original 20 V input fuse and current path: a fuse suitable for the 20 V source may be too small for approximately 7.2 A at 7.4 V. Use the balance connector for per-cell monitoring; 5 V output monitoring alone does not protect against cell over-discharge.

Decision: this is a credible smaller electrical/mechanical option, with a known in-stock seller. A complete inexpensive next-day battery system is **not established**. Do not silently replace the approved existing-power-bank trial, release held purchase rows, or promise arrival from a general shipping banner. Address-specific checkout and charger availability are the remaining procurement checks if the user selects it.

AI assistance was used to draft.

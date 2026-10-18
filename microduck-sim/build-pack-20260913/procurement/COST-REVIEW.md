# MicroDuck procurement cost correction

The revised DigiKey cart is **$129.88 including estimated shipping and tariff**, down from $138.17. Sales tax is not displayed. All 15 product lines were verified after reloading the cart; no order was placed. This is a correction to excess quantities and an optional connector within the current integrated design.

## Objective and failure

Required functionality, electrical limits and mechanical fit are constraints. Within those constraints, minimize remaining delivered spending, purchase sites and assembly work, using existing and borrowed resources first. The prior basket treated spare stock and service convenience as automatic purchases without demonstrating a worthwhile benefit. A cheaper unit price was also allowed to obscure a higher order total.

## Exact changes

- Main 10 A fuse: two to one, saving $1.24 in merchandise.
- Branch 3 A fuses: ten to nine, saving $0.23. The site's quantity selector quoted nine at $9.22 and ten at $9.45. Nine covers eight motor groups and the Pi branch.
- Audio 0.5 A fuse: three to one, saving $2.74.
- Input 5 A fuse: two to one, saving $1.24.
- 100 kilohm gain resistor: three to one, saving $0.20.
- Adafruit 1131 audio service connector: one to zero, saving $1.95. Use the existing club-sourced 24 AWG audio supply pair directly, with insulated joints, strain relief and a service loop. Keep the 0.5 A fuse. Removing the head will require disconnecting those direct supply joints.

These changes remove five spare fuses and two spare resistors. The twelve installed fuses remain: one input, one motor main, nine 3 A branches and one audio branch. The XT30 whole-robot power disconnect remains necessary for the external tether and later battery conversion.

## Whole-order readback

- Merchandise: $122.21 to $114.61, saving $7.60.
- Estimated shipping: $4.99 to $4.99.
- Estimated tariff: $10.97 to $10.28, saving $0.69.
- Displayed order estimate: $138.17 to $129.88, saving **$8.29**.

Sources: [saved current cart](cart-status-r3.json), [rendered browser readback](cart-r3-browser-readback.txt), [archived original cart](archive/before-cost-correction/cart-status-r3.json), and [item-by-item decisions](cost-review.json). These are basket estimates rather than a paid invoice.

## Prevention

The current procurement generator checks that each purchased unit is needed for installation or the external working assembly and that optional items are not charged. The archived original basket fails this check with two main fuses bought for one working position. Regression checks also add an extra unit to each of the five affected products and require rejection. Any future extra stock needs a separate evidenced cost decision instead of being silently included.

The [current design and procurement verification](../redesign-20260913/current-build-verification.json) passed after the cart correction, including the quantity regressions and the saved-cart consistency check. This verifies the procurement correction; physical hardware commissioning remains a separate acceptance step.

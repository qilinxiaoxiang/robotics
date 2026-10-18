# Procurement and system-design repair audit

Verified 2026-09-13. Problems P5/P6. Revision phase1-single-source-r2. The current deliverable is the [single build handbook](../START-HERE.html). All before-repair source files are preserved in [before](before/).

## What failed

The previous work repeatedly optimized the component named in the latest message without preserving a whole-robot acceptance contract. A high, unmeasured current allocation became expensive regulator capacity; the later attempt to reuse the existing bank powered only logic and introduced a separate motor adapter. Neither step demonstrated that two independent sources were required. The original FanGe build already uses a single battery with distribution/regulation branches. Its battery voltage must still be checked against the selected XL330's limits; copying the topology does not authorize an out-of-range voltage.

Shopping was treated as unrelated product lookups. The same manufacturer Adafruit items are stocked by DigiKey, which was already needed for fuses. Their consolidation removes a third order. Product-page prices were also weaker evidence than actual carts: the current sensor cart price is $29.50, despite an older $24.95 page quote.

Engineering demand, purchasing quantities and rendered prose diverged. The archived catalog requires nine installed 3A fuses and two spares, but its cart had ten. The old generator then copied cart quantity into the selected bill of materials. The old checks verified catalog/quote/cart agreement, so internally consistent wrong numbers could pass. The handbook said eight installed/two spares. The root entrypoint also retained an older full-battery route and obsolete print queue while Phase 1 described a different build.

This is an observed workflow/checking failure. Long context may have contributed, but the records cannot establish a model-internal cause, a special intelligence decline or a token-count threshold. More generic instructions to be careful would not fix the missing checks.

## What changed

- A small whole-system contract now fixes the 15-servo task, single existing source, two buying destinations, required interfaces and superseded power purchases. Any contradictory change fails the pack check.
- Engineering quantity cannot be overwritten by cart observations. Prices can refresh only for the exact selected supplier, URL and quantity. Each required buy line must appear exactly once in the right cart.
- The original fuse mismatch is replayed as a negative test. Additional negative tests remove the jaw, Starter Kit, interface wire/accessory, duplicate a cart line, add a second source, add a third store, and inject a stale cart quantity. They must be rejected.
- The current handbook, order lines and price are generated from the selected records. It checks revision, exact product links, old instructions, 85 current print instances, frozen-runtime archive integrity and both voltage endpoints.
- Existing-resource requirements remain explicit. Borrowing and club supply are not proof of inventory and cannot silently authorize purchases.

## Selected repair and price evidence

Use one existing PB1033MI bank, its attached cable, Adafruit5991 set to12V and DFR1202 shared5V. Source hardware remains offboard in the already selected Phase 1 tether arrangement. Separate Pi and motor wire pairs share that one source. The motor distribution bypasses OpenRB's3A path. The whole5V commissioning screen is5A, including logic; module16A marketing is not system capacity. Bench thermal, transient and actual task tests are still required.

ROBOTIS retains fourteen standalone motors plus one Starter Kit: **$437.65**, with visible UPS Ground **$16.74**, displayed total **$454.39**. DigiKey now contains eight exact lines: **$70.08**, estimated shipping **$4.99**, estimated tariff **$6.24**, displayed estimate **$81.31**. Adafruit's four duplicate lines were removed and its cart visibly reads empty. No order/payment occurred.

Merchandise totals **$507.73**, versus the prior three-cart **$514.92**. Current displayed merchandise/ship/tariff combined is **$535.70**, before additional final tax. The old Adafruit checkout offered USPS **$6.05** or selected UPS **$9.07**; consolidation removes that order's shipping. ROBOTIS remains unchanged. Against the old cheapest displayed Adafruit shipping, the new route saves **$15.30** before differences in final tax; against its selected UPS shipping it saves **$18.32**. These are comparisons of observed baskets, not a global cheapest-market claim.

The bank-only power additions cost **$22.85** before tariff. Most of the bill is the retained smart-servo/controller platform: **$437.65**, about86% of merchandise. A substantially cheaper robot would require changing the actuator/controller platform and validating different control and mechanics; that is a different design, not a minor equivalent substitution in the source build.

## What evidence would change this decision

A failed negotiated12V test, Pi input outside4.75–5.25V, servo task voltage outside4.0–5.5V, source current beyond2.5A, combined5V output beyond5A, unstable converter temperature, resets, or failed five walk-stop-pickup trials requires revising the measured cause. None is excused by the existing33/33 simulated gait cases or50/50 offline runtime tests. Physical hardware tests remain zero; there is no claim that an unbuilt robot has passed.

Primary sources: [FanGe build](https://github.com/AI-FanGe/Microduck-build-tutorial), [Xiaomi bank profiles](https://www.mi.com/ph/product/xiaomi-33w-power-bank-10000-integrated-cable/specs/), [Adafruit receiver](https://learn.adafruit.com/adafruit-usb-type-c-power-delivery-switchable-breakout/pinouts), [DFRobot converter](https://www.dfrobot.com/product-2907.html), [XL330](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/), [OpenRB](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/). Each was checked on2026-09-13. Current price/availability evidence comes from visible authenticated carts, with per-store timestamps in the procurement records.

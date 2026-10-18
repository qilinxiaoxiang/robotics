# Head USB connector access

Problem P5/P6: repacking the OpenRB PCB is insufficient if its USB-C plug cannot enter the restored curved cap.

The existing electrical contract keeps the Pi Zero SC0727 Micro-B OTG adapter (80 mm) and Adafruit 4472 USB-A-to-USB-C cable (152 mm). These are separate cables with a mated USB-A junction. A local Pi USB opening does not establish space for that junction or the OpenRB plug. Keep this topology unchanged; do not silently replace it with a UART connection.

`check_usb.py` transforms the original head design's 7 × 12 × 15 mm OpenRB USB-C receiving envelope into the current board pose. This is a declared legacy receiving envelope, not a measurement of the owned 4472 moulding. In the native curved shell it intersects the rear cap by 233.158 mm³. The failed static and 121-pose insertion checks are retained in `usb-before-service-opening.json`.

The required repair is a local rear service opening aligned with the actual connector axis. The plug must be able to enter with the cap closed, or the declared closure operation must carry a preconnected plug and its cable without pinching them. The original curved outline remains the shell reference; a service opening is reported as an explicit local exterior change.

Rerun the check on the final cap export and record its hash. Connector fit and the complete 80 + 152 mm cable route are separate acceptance items. Do not infer that two verified connector pockets prove space for the USB-A junction, excess cable, strain relief or joint movement. Physical moulding dimensions and cable bend behavior remain receiving checks.

AI assistance was used to draft.

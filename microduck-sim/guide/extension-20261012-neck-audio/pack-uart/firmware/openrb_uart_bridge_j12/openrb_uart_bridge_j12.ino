// MicroDuck OpenRB-150 UART bridge, J12 variant (owner decision 2026-10-13: no cover window, wires soldered to J12).
// Pi Zero UART (GPIO14/15, 1 Mbps) <-> OpenRB Serial2 (J12 pad 3 SERIAL_RX, pad 4 SERIAL_TX) <-> DYNAMIXEL TTL bus (Serial1).
// Same bridge as guide/firmware/openrb_uart_bridge/openrb_uart_bridge.ino; only the host port changes.
// Serial2 is the board's 4-pin UART: variant.h PIN_SERIAL2_TX 28, PIN_SERIAL2_RX 29; schematic J12 pin 3 SERIAL_RX, pin 4 SERIAL_TX.
// J12 pad 3 (RX) <- Pi pin 8 (TXD); J12 pad 4 (TX) -> Pi pin 10 (RXD). Pads 1 (GND) and 2 (+3V3) stay empty.
// Flash once over USB from a laptop (Arduino IDE, board "OpenRB-150"). USB stays usable for re-flashing.

#include <Dynamixel2Arduino.h>

#define DXL_BUS Serial1   // OpenRB DYNAMIXEL ports (auto TX enable on the board)
#define HOST    Serial2   // J12: pad 3 = RX (from Pi pin 8 TXD), pad 4 = TX (to Pi pin 10 RXD)

const uint32_t BAUD = 1000000;  // XL330 bus and Pi UART both run at 1 Mbps
const int BUF_LEN = 1024;

uint8_t buf[BUF_LEN];
Dynamixel2Arduino dxl(DXL_BUS);
unsigned long ledOffAt = 0;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  HOST.begin(BAUD);
  dxl.begin(BAUD);
}

void loop() {
  int n = HOST.available();
  if (n > 0) {
    if (n > BUF_LEN) n = BUF_LEN;
    for (int i = 0; i < n; i++) buf[i] = HOST.read();
    DXL_BUS.write(buf, n);
    blink();
  }
  n = DXL_BUS.available();
  if (n > 0) {
    if (n > BUF_LEN) n = BUF_LEN;
    for (int i = 0; i < n; i++) buf[i] = DXL_BUS.read();
    HOST.write(buf, n);
    blink();
  }
  if (ledOffAt && millis() > ledOffAt) {
    digitalWrite(LED_BUILTIN, LOW);
    ledOffAt = 0;
  }
}

void blink() {
  digitalWrite(LED_BUILTIN, HIGH);
  ledOffAt = millis() + 20;
}

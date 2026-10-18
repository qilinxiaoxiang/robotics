// MicroDuck OpenRB-150 UART bridge, STUDY VARIANT for the pack-UART option A (compiles on OpenRB-150:samd 0.2.1; not bench-tested).
// Same bridge as guide/firmware/openrb_uart_bridge/openrb_uart_bridge.ino, but the Pi link uses the left header row:
//   J6 socket 3 = A1 = PB02 = SERCOM5 PAD0 -> TX (to Pi pin 10, RXD)
//   J6 socket 4 = A2 = PB03 = SERCOM5 PAD1 -> RX (from Pi pin 8, TXD)
// (OpenRB variant.cpp: PB02 "5/00", PB03 "5/01" in the SERCOM-ALT column; schematic J6 pins 3/4.)
// Serial3 already owns SERCOM5 and its interrupt handler, so the sketch starts Serial3 normally and then moves its pads:
// TXPO = 0 (TX on PAD0), RXPO = 1 (RX on PAD1). D13/D14 are released to plain inputs.

#include <Dynamixel2Arduino.h>
#include "wiring_private.h"   // pinPeripheral()

#define DXL_BUS Serial1   // OpenRB DYNAMIXEL ports (auto TX enable on the board)
#define HOST    Serial3   // SERCOM5, moved to A1 (TX) / A2 (RX) by hostBegin()

const uint32_t BAUD = 1000000;  // XL330 bus and Pi UART both run at 1 Mbps
const int BUF_LEN = 1024;

uint8_t buf[BUF_LEN];
Dynamixel2Arduino dxl(DXL_BUS);
unsigned long ledOffAt = 0;

void hostBegin(uint32_t baud) {
  HOST.begin(baud);                               // configures SERCOM5 for D13 (PAD3 RX) / D14 (PAD2 TX)
  SERCOM5->USART.CTRLA.bit.ENABLE = 0;            // TXPO/RXPO are enable-protected
  while (SERCOM5->USART.SYNCBUSY.bit.ENABLE) {}
  SERCOM5->USART.CTRLA.bit.TXPO = 0;              // TX on PAD0 = PB02 = A1
  SERCOM5->USART.CTRLA.bit.RXPO = 1;              // RX on PAD1 = PB03 = A2
  SERCOM5->USART.CTRLA.bit.ENABLE = 1;
  while (SERCOM5->USART.SYNCBUSY.bit.ENABLE) {}
  pinPeripheral(A1, PIO_SERCOM_ALT);
  pinPeripheral(A2, PIO_SERCOM_ALT);
  pinMode(13, INPUT);                             // D13 / D14 no longer used
  pinMode(14, INPUT);
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  hostBegin(BAUD);
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

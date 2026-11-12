/*
 * The MIT License (MIT)
 *
 * Copyright (c) 2020 Ha Thach (tinyusb.org)
 * Copyright (c) 2020 Jerzy Kasenberg
 * Copyright (c) 2026 MicroDuck project contributors (MicroDuck head USB board: audio + CDC composite)
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 *
 * Adapted from TinyUSB examples/device/uac2_headset/src/usb_descriptors.c.
 */

#include <string.h>

#include "pico/unique_id.h"
#include "tusb.h"
#include "usb_descriptors.h"

// 0x1209 is the pid.codes open-hardware vendor ID; 0x0001 is its test product ID, for private use only.
// A board that leaves the bench for other people needs its own product ID (README, open items).
#define USB_VID 0x1209
#define USB_PID 0x0001

//--------------------------------------------------------------------+
// Device Descriptor
//--------------------------------------------------------------------+
tusb_desc_device_t const desc_device =
{
    .bLength            = sizeof(tusb_desc_device_t),
    .bDescriptorType    = TUSB_DESC_DEVICE,
    .bcdUSB             = 0x0200,

    // Interface Association Descriptors are used, so the device class is Miscellaneous / Common / IAD
    .bDeviceClass       = TUSB_CLASS_MISC,
    .bDeviceSubClass    = MISC_SUBCLASS_COMMON,
    .bDeviceProtocol    = MISC_PROTOCOL_IAD,
    .bMaxPacketSize0    = CFG_TUD_ENDPOINT0_SIZE,

    .idVendor           = USB_VID,
    .idProduct          = USB_PID,
    .bcdDevice          = 0x0100,

    .iManufacturer      = STRID_MANUFACTURER,
    .iProduct           = STRID_PRODUCT,
    .iSerialNumber      = STRID_SERIAL,

    .bNumConfigurations = 0x01
};

uint8_t const * tud_descriptor_device_cb(void)
{
  return (uint8_t const *)&desc_device;
}

//--------------------------------------------------------------------+
// Configuration Descriptor
//--------------------------------------------------------------------+
#define CONFIG_TOTAL_LEN    (TUD_CONFIG_DESC_LEN + HEAD_AUDIO_DESC_LEN + TUD_CDC_DESC_LEN)

// The RP2040 allows the same endpoint number in both directions.
#define EPNUM_AUDIO_OUT   0x01
#define EPNUM_AUDIO_IN    0x81
#define EPNUM_CDC_NOTIF   0x82
#define EPNUM_CDC_OUT     0x03
#define EPNUM_CDC_IN      0x83

uint8_t const desc_configuration[] =
{
    // Config number, interface count, string index, total length, attribute, power in mA.
    // 100 mA: a device behind a bus-powered hub is refused by Linux if it asks for more (README, power).
    TUD_CONFIG_DESCRIPTOR(1, ITF_NUM_TOTAL, 0, CONFIG_TOTAL_LEN, 0x00, 100),

    // EP Out & EP In address
    HEAD_AUDIO_DESCRIPTOR(EPNUM_AUDIO_OUT, EPNUM_AUDIO_IN),

    // Interface number, string index, EP notification address and size, EP data address (out, in) and size
    TUD_CDC_DESCRIPTOR(ITF_NUM_CDC, STRID_CDC, EPNUM_CDC_NOTIF, 8, EPNUM_CDC_OUT, EPNUM_CDC_IN, 64)
};

TU_VERIFY_STATIC(sizeof(desc_configuration) == CONFIG_TOTAL_LEN, "configuration descriptor length");

uint8_t const * tud_descriptor_configuration_cb(uint8_t index)
{
  (void)index; // one configuration
  return desc_configuration;
}

// Sample rates the clock source reports. Kept as a named table so tools/check_descriptors.py can read it from the ELF.
uint32_t const usb_audio_sample_rates[] = { HEAD_AUDIO_SAMPLE_RATE };
uint32_t const usb_audio_sample_rate_count = TU_ARRAY_SIZE(usb_audio_sample_rates);

//--------------------------------------------------------------------+
// String Descriptors
//--------------------------------------------------------------------+

static char const *const string_desc_arr[] =
{
  [STRID_LANGID]       = (const char[]) { 0x09, 0x04 },  // English (0x0409)
  [STRID_MANUFACTURER] = "MicroDuck",
  [STRID_PRODUCT]      = "MicroDuck Head",
  [STRID_SERIAL]       = NULL,                           // flash unique ID
  [STRID_SPEAKER]      = "MicroDuck Head Speaker",
  [STRID_MICROPHONES]  = "MicroDuck Head Microphones",
  [STRID_CDC]          = "MicroDuck Head Touch",
};

static uint16_t _desc_str[32 + 1];

uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
  (void) langid;
  size_t chr_count;
  char serial[2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1];
  const char *str;

  if ( index == STRID_LANGID ) {
    memcpy(&_desc_str[1], string_desc_arr[0], 2);
    chr_count = 1;
  } else {
    if ( index == STRID_SERIAL ) {
      pico_get_unique_board_id_string(serial, sizeof(serial));
      str = serial;
    } else {
      if ( !(index < sizeof(string_desc_arr) / sizeof(string_desc_arr[0])) ) return NULL;
      str = string_desc_arr[index];
    }

    // Cap at max char
    chr_count = strlen(str);
    size_t const max_count = sizeof(_desc_str) / sizeof(_desc_str[0]) - 1; // -1 for string type
    if ( chr_count > max_count ) chr_count = max_count;

    // Convert ASCII string into UTF-16
    for ( size_t i = 0; i < chr_count; i++ ) {
      _desc_str[1 + i] = str[i];
    }
  }

  // first byte is length (including header), second byte is string type
  _desc_str[0] = (uint16_t) ((TUSB_DESC_STRING << 8) | (2 * chr_count + 2));

  return _desc_str;
}

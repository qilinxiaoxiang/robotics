/*
 * The MIT License (MIT)
 *
 * Copyright (c) 2020 Ha Thach (tinyusb.org)
 * Copyright (c) 2020 Jerzy Kasenberg
 * Copyright (c) 2026 MicroDuck project contributors (MicroDuck head USB board: 4-channel capture, CDC port, no volume unit)
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
 * Adapted from TinyUSB examples/device/uac2_headset/src/tusb_config.h.
 */

#ifndef _TUSB_CONFIG_H_
#define _TUSB_CONFIG_H_

#ifdef __cplusplus
extern "C" {
#endif

#include "usb_descriptors.h"

//--------------------------------------------------------------------
// COMMON CONFIGURATION
//--------------------------------------------------------------------

// CFG_TUSB_MCU and CFG_TUSB_OS are set by the Pico SDK's TinyUSB integration.

#define BOARD_TUD_RHPORT          0
#define CFG_TUSB_RHPORT0_MODE     (OPT_MODE_DEVICE | OPT_MODE_FULL_SPEED)

#ifndef CFG_TUSB_DEBUG
#define CFG_TUSB_DEBUG            0
#endif

#define CFG_TUD_ENABLED           1

#ifndef CFG_TUSB_MEM_SECTION
#define CFG_TUSB_MEM_SECTION
#endif

#ifndef CFG_TUSB_MEM_ALIGN
#define CFG_TUSB_MEM_ALIGN        __attribute__ ((aligned(4)))
#endif

//--------------------------------------------------------------------
// DEVICE CONFIGURATION
//--------------------------------------------------------------------

#ifndef CFG_TUD_ENDPOINT0_SIZE
#define CFG_TUD_ENDPOINT0_SIZE    64
#endif

//------------- CLASS -------------//
#define CFG_TUD_CDC               1
#define CFG_TUD_MSC               0
#define CFG_TUD_HID               0
#define CFG_TUD_MIDI              0
#define CFG_TUD_AUDIO             1
#define CFG_TUD_VENDOR            0

//--------------------------------------------------------------------
// CDC CLASS DRIVER CONFIGURATION (touch lines, 50 lines of 51 bytes per second)
//--------------------------------------------------------------------
#define CFG_TUD_CDC_RX_BUFSIZE    64
#define CFG_TUD_CDC_TX_BUFSIZE    512
#define CFG_TUD_CDC_EP_BUFSIZE    64

//--------------------------------------------------------------------
// AUDIO CLASS DRIVER CONFIGURATION
//--------------------------------------------------------------------

#define CFG_TUD_AUDIO_FUNC_1_DESC_LEN                                HEAD_AUDIO_DESC_LEN

// One format per direction: 48 kHz, 16 bit in 16-bit slots
#define CFG_TUD_AUDIO_FUNC_1_N_FORMATS                               1
#define CFG_TUD_AUDIO_FUNC_1_MAX_SAMPLE_RATE                         HEAD_AUDIO_SAMPLE_RATE
#define CFG_TUD_AUDIO_FUNC_1_N_CHANNELS_TX                           HEAD_AUDIO_CAPTURE_CHANNELS
#define CFG_TUD_AUDIO_FUNC_1_N_CHANNELS_RX                           HEAD_AUDIO_PLAYBACK_CHANNELS
#define CFG_TUD_AUDIO_FUNC_1_FORMAT_1_N_BYTES_PER_SAMPLE_TX          HEAD_AUDIO_BYTES_PER_SAMPLE
#define CFG_TUD_AUDIO_FUNC_1_FORMAT_1_RESOLUTION_TX                  HEAD_AUDIO_BITS
#define CFG_TUD_AUDIO_FUNC_1_FORMAT_1_N_BYTES_PER_SAMPLE_RX          HEAD_AUDIO_BYTES_PER_SAMPLE
#define CFG_TUD_AUDIO_FUNC_1_FORMAT_1_RESOLUTION_RX                  HEAD_AUDIO_BITS

// Capture endpoint. No TinyUSB flow control: the firmware decides how many frames go into each packet, which is
// what an asynchronous IN endpoint means (the device's own clock sets the rate).
#define CFG_TUD_AUDIO_ENABLE_EP_IN                1
#define CFG_TUD_AUDIO_EP_IN_FLOW_CONTROL          0
#define CFG_TUD_AUDIO_FUNC_1_EP_IN_SZ_MAX         HEAD_AUDIO_EP_IN_SIZE
#define CFG_TUD_AUDIO_FUNC_1_EP_IN_SW_BUF_SZ      (HEAD_AUDIO_EP_IN_SIZE * 2)

// Playback endpoint
#define CFG_TUD_AUDIO_ENABLE_EP_OUT               1
#define CFG_TUD_AUDIO_FUNC_1_EP_OUT_SZ_MAX        HEAD_AUDIO_EP_OUT_SIZE
#define CFG_TUD_AUDIO_FUNC_1_EP_OUT_SW_BUF_SZ     (HEAD_AUDIO_EP_OUT_SIZE * 4)

#define CFG_TUD_AUDIO_ENABLE_FEEDBACK_EP          0
#define CFG_TUD_AUDIO_ENABLE_INTERRUPT_EP         0

// Two audio streaming interfaces: speaker and microphones
#define CFG_TUD_AUDIO_FUNC_1_N_AS_INT             2

// Size of control request buffer
#define CFG_TUD_AUDIO_FUNC_1_CTRL_BUF_SZ          64

#ifdef __cplusplus
}
#endif

#endif /* _TUSB_CONFIG_H_ */

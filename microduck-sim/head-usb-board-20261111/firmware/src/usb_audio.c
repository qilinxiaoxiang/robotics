/*
 * The MIT License (MIT)
 *
 * Copyright (c) 2020 Jerzy Kasenberg
 * Copyright (c) 2026 MicroDuck project contributors (MicroDuck head USB board: fixed 48 kHz clock, no feature unit, I2S rings)
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
 * The control-request handlers are adapted from TinyUSB examples/device/uac2_headset/src/main.c.
 */

#include "audio.h"
#include "tusb.h"
#include "usb_descriptors.h"

extern uint32_t const usb_audio_sample_rates[];
extern uint32_t const usb_audio_sample_rate_count;

// Frames of one USB packet, both directions (one extra frame of room, as the endpoint sizes allow)
#define PACKET_FRAMES (HEAD_AUDIO_FRAMES_PER_MS + 1)

static int16_t mic_packet[PACKET_FRAMES * HEAD_AUDIO_CAPTURE_CHANNELS];
static int16_t spk_packet[PACKET_FRAMES * HEAD_AUDIO_PLAYBACK_CHANNELS];

//--------------------------------------------------------------------+
// Clock source requests (the only entity with controls)
//--------------------------------------------------------------------+

static bool clock_get_request(uint8_t rhport, audio_control_request_t const *request)
{
  if (request->bControlSelector == AUDIO_CS_CTRL_SAM_FREQ)
  {
    if (request->bRequest == AUDIO_CS_REQ_CUR)
    {
      audio_control_cur_4_t curf = { (int32_t) tu_htole32(usb_audio_sample_rates[0]) };
      return tud_audio_buffer_and_schedule_control_xfer(rhport, (tusb_control_request_t const *)request, &curf, sizeof(curf));
    }
    else if (request->bRequest == AUDIO_CS_REQ_RANGE)
    {
      audio_control_range_4_n_t(1) rangef =
      {
        .wNumSubRanges = tu_htole16(1)
      };
      rangef.subrange[0].bMin = (int32_t) usb_audio_sample_rates[0];
      rangef.subrange[0].bMax = (int32_t) usb_audio_sample_rates[0];
      rangef.subrange[0].bRes = 0;
      return tud_audio_buffer_and_schedule_control_xfer(rhport, (tusb_control_request_t const *)request, &rangef, sizeof(rangef));
    }
  }
  else if (request->bControlSelector == AUDIO_CS_CTRL_CLK_VALID &&
           request->bRequest == AUDIO_CS_REQ_CUR)
  {
    audio_control_cur_1_t cur_valid = { .bCur = 1 };
    return tud_audio_buffer_and_schedule_control_xfer(rhport, (tusb_control_request_t const *)request, &cur_valid, sizeof(cur_valid));
  }
  return false;
}

// The descriptor says the frequency is read-only. A host that writes it anyway is accepted only for 48000.
static bool clock_set_request(uint8_t rhport, audio_control_request_t const *request, uint8_t const *buf)
{
  (void)rhport;

  TU_VERIFY(request->bRequest == AUDIO_CS_REQ_CUR);
  TU_VERIFY(request->bControlSelector == AUDIO_CS_CTRL_SAM_FREQ);
  TU_VERIFY(request->wLength == sizeof(audio_control_cur_4_t));

  return (uint32_t) ((audio_control_cur_4_t const *)buf)->bCur == usb_audio_sample_rates[0];
}

//--------------------------------------------------------------------+
// Application Callback API Implementations
//--------------------------------------------------------------------+

bool tud_audio_get_req_entity_cb(uint8_t rhport, tusb_control_request_t const *p_request)
{
  audio_control_request_t const *request = (audio_control_request_t const *)p_request;

  if (request->bEntityID == UAC2_ENTITY_CLOCK)
    return clock_get_request(rhport, request);
  return false;
}

bool tud_audio_set_req_entity_cb(uint8_t rhport, tusb_control_request_t const *p_request, uint8_t *buf)
{
  audio_control_request_t const *request = (audio_control_request_t const *)p_request;

  if (request->bEntityID == UAC2_ENTITY_CLOCK)
    return clock_set_request(rhport, request, buf);
  return false;
}

bool tud_audio_set_itf_close_EP_cb(uint8_t rhport, tusb_control_request_t const * p_request)
{
  (void)rhport;
  (void)p_request;
  return true;
}

bool tud_audio_set_itf_cb(uint8_t rhport, tusb_control_request_t const * p_request)
{
  (void)rhport;
  uint8_t const itf = tu_u16_low(tu_le16toh(p_request->wIndex));
  uint8_t const alt = tu_u16_low(tu_le16toh(p_request->wValue));

  if (ITF_NUM_AUDIO_STREAMING_MIC == itf && alt != 0)
    audio_mic_restart();

  return true;
}

// A playback packet arrived and TinyUSB has put it in its FIFO (post-read: on the RP2040 the packet is copied from
// a linear buffer after the pre-read callback): move it into the amplifier ring.
bool tud_audio_rx_done_post_read_cb(uint8_t rhport, uint16_t n_bytes_received, uint8_t func_id, uint8_t ep_out, uint8_t cur_alt_setting)
{
  (void)rhport;
  (void)n_bytes_received;
  (void)func_id;
  (void)ep_out;
  (void)cur_alt_setting;

  const uint16_t frame_bytes = HEAD_AUDIO_PLAYBACK_CHANNELS * HEAD_AUDIO_BYTES_PER_SAMPLE;
  while (tud_audio_available() >= frame_bytes)
  {
    uint16_t want = tud_audio_available();
    if (want > sizeof(spk_packet)) want = sizeof(spk_packet);
    want = (uint16_t)(want - want % frame_bytes);
    uint16_t got = tud_audio_read(spk_packet, want);
    if (got < frame_bytes) break;
    audio_spk_write(spk_packet, got / frame_bytes);
  }
  return true;
}

// The previous capture packet has gone: load every frame the microphones produced since then (47 to 49 a millisecond).
bool tud_audio_tx_done_pre_load_cb(uint8_t rhport, uint8_t itf, uint8_t ep_in, uint8_t cur_alt_setting)
{
  (void)rhport;
  (void)itf;
  (void)ep_in;
  (void)cur_alt_setting;

  uint32_t frames = audio_mic_read(mic_packet, PACKET_FRAMES);
  tud_audio_write((uint8_t *)mic_packet, (uint16_t)(frames * HEAD_AUDIO_CAPTURE_CHANNELS * HEAD_AUDIO_BYTES_PER_SAMPLE));
  return true;
}

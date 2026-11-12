// I2S side of the head USB board. Original work for this project (BSD-3-Clause, see ../README.md, Licences).
//
// Both directions run without interrupts. Each PIO state machine is served by a pair of DMA channels that chain to
// each other and wrap inside a 16 KiB ring, so the microphones are always being recorded into mic_ring and the
// amplifier is always being played from spk_ring. The USB side (main loop, core 0) only reads and writes those rings
// and looks at the DMA address to know where the hardware is.
//
// Rates: the I2S clocks come from this board's crystal; the USB host has its own clock. Capture is an asynchronous
// endpoint: each millisecond the host gets however many frames the microphones produced (47 to 49). Playback has no
// feedback endpoint: the distance between the USB write position and the DMA read position is held near
// SPK_TARGET_FRAMES by dropping or repeating a single frame when it drifts (README, known limits).

#include "audio.h"

#include <string.h>

#include "hardware/clocks.h"
#include "hardware/dma.h"
#include "hardware/gpio.h"
#include "hardware/pio.h"
#include "pico/stdlib.h"

#include "i2s_mic.pio.h"
#include "i2s_spk.pio.h"

#define RING_BITS 14                                  // DMA address wrap: 2^14 bytes
#define RING_BYTES (1u << RING_BITS)
#define RING_WORDS (RING_BYTES / 4)
// Transfers per DMA run: a whole number of rings, so a channel always stops and restarts at ring offset 0 and the
// two channels of a pair hand over without a gap or an address jump.
#define RING_DMA_COUNT (RING_WORDS * 1024u)

#define MIC_RING_FRAMES (RING_WORDS / MIC_WORDS_PER_FRAME)   // 1024 frames, 21 ms
#define SPK_RING_FRAMES (RING_WORDS / SPK_WORDS_PER_FRAME)   // 2048 frames, 43 ms

#define MIC_MAX_LAG_FRAMES 96                         // reader further behind than 2 ms: jump to the newest audio
#define MIC_RESYNC_FRAMES 48

#define SPK_TARGET_FRAMES 384                         // 8 ms queued ahead of the amplifier
#define SPK_SLIP_FRAMES 144                           // drift allowed either side before a frame is dropped or repeated
#define SPK_LOW_FRAMES 96                             // less than 2 ms queued: pad with silence
#define SPK_MAX_FRAMES 1536                           // more than this "queued" means the DMA has passed the writer
#define SPK_GAP_US 20000                              // no USB audio for this long: the next packet starts a new run

static uint32_t mic_ring[RING_WORDS] __attribute__((aligned(RING_BYTES)));
static uint32_t spk_ring[RING_WORDS] __attribute__((aligned(RING_BYTES)));

static uint mic_dma_a, mic_dma_b, spk_dma_a, spk_dma_b;
static uint32_t mic_rd;                               // next frame the USB side reads
static uint32_t spk_wr;                               // next frame the USB side writes
static bool spk_padded;                               // silence was inserted since the last USB packet
static absolute_time_t spk_last_rx;
static unsigned mic_gain_shift;

volatile audio_stats_t audio_stats;

// Word offset in the ring where the DMA pair is working now. The idle channel of a pair always rests at offset 0,
// which is also where the busy one will hand over, so reading either during the hand-over gives the right place.
static uint32_t ring_word_pos(uint chan_a, uint chan_b, const uint32_t *ring, bool to_pio) {
    for (;;) {
        bool a_busy = dma_channel_is_busy(chan_a);
        uint chan = a_busy ? chan_a : chan_b;
        uint32_t addr = to_pio ? dma_hw->ch[chan].read_addr : dma_hw->ch[chan].write_addr;
        if (dma_channel_is_busy(chan_a) == a_busy) {
            return ((addr - (uint32_t)(uintptr_t)ring) / 4u) & (RING_WORDS - 1u);
        }
    }
}

static void ring_dma_pair(uint chan_a, uint chan_b, bool to_pio, uintptr_t fifo_addr, uint32_t *ring, uint dreq) {
    volatile void *fifo = (volatile void *)fifo_addr;
    const uint chans[2] = {chan_a, chan_b};
    for (int i = 0; i < 2; i++) {
        dma_channel_config c = dma_channel_get_default_config(chans[i]);
        channel_config_set_transfer_data_size(&c, DMA_SIZE_32);
        channel_config_set_read_increment(&c, to_pio);
        channel_config_set_write_increment(&c, !to_pio);
        channel_config_set_ring(&c, !to_pio, RING_BITS);   // wrap the ring side: write when capturing, read when playing
        channel_config_set_dreq(&c, dreq);
        channel_config_set_chain_to(&c, chans[1 - i]);
        if (to_pio) {
            dma_channel_configure(chans[i], &c, fifo, ring, RING_DMA_COUNT, false);
        } else {
            dma_channel_configure(chans[i], &c, ring, fifo, RING_DMA_COUNT, false);
        }
    }
    dma_channel_start(chan_a);
}

static inline uint32_t mic_hw_frame(void) {
    return ring_word_pos(mic_dma_a, mic_dma_b, mic_ring, false) / MIC_WORDS_PER_FRAME;
}

static inline uint32_t spk_hw_frame(void) {
    return ring_word_pos(spk_dma_a, spk_dma_b, spk_ring, true) / SPK_WORDS_PER_FRAME;
}

void audio_init(void) {
    PIO pio = pio0;
    const uint mic_sm = 0, spk_sm = 1;

    // ---- microphones: SCK and WS out, two data lines in ----
    uint mic_offset = pio_add_program(pio, &i2s_mic_program);
    pio_sm_config mc = i2s_mic_program_get_default_config(mic_offset);
    sm_config_set_sideset_pins(&mc, HEAD_MIC_SCK_PIN);           // SCK, then WS
    sm_config_set_in_pins(&mc, HEAD_MIC_SD_EARS_PIN);            // ears, then back
    sm_config_set_in_shift(&mc, false, true, 32);                // shift left (MSB first), autopush at 32 bits
    sm_config_set_fifo_join(&mc, PIO_FIFO_JOIN_RX);
    sm_config_set_clkdiv_int_frac(&mc, AUDIO_PIO_CLKDIV, 0);
    pio_gpio_init(pio, HEAD_MIC_SCK_PIN);
    pio_gpio_init(pio, HEAD_MIC_WS_PIN);
    gpio_init(HEAD_MIC_SD_EARS_PIN);
    gpio_init(HEAD_MIC_SD_BACK_PIN);
    gpio_pull_down(HEAD_MIC_SD_EARS_PIN);                        // the board has 100 k pull-downs (R8, R9) as well:
    gpio_pull_down(HEAD_MIC_SD_BACK_PIN);                        // the lines float while every microphone is tri-stated
    pio_sm_set_consecutive_pindirs(pio, mic_sm, HEAD_MIC_SCK_PIN, 2, true);
    pio_sm_set_consecutive_pindirs(pio, mic_sm, HEAD_MIC_SD_EARS_PIN, 2, false);
    pio_sm_init(pio, mic_sm, mic_offset + i2s_mic_offset_entry, &mc);

    // ---- amplifier: BCLK and LRC out, DIN out ----
    uint spk_offset = pio_add_program(pio, &i2s_spk_program);
    pio_sm_config sc = i2s_spk_program_get_default_config(spk_offset);
    sm_config_set_sideset_pins(&sc, HEAD_SPK_BCLK_PIN);          // BCLK, then LRC
    sm_config_set_out_pins(&sc, HEAD_SPK_DIN_PIN, 1);
    sm_config_set_out_shift(&sc, false, true, 32);               // shift left (MSB first), autopull at 32 bits
    sm_config_set_fifo_join(&sc, PIO_FIFO_JOIN_TX);
    sm_config_set_clkdiv_int_frac(&sc, AUDIO_PIO_CLKDIV, 0);
    pio_gpio_init(pio, HEAD_SPK_BCLK_PIN);
    pio_gpio_init(pio, HEAD_SPK_LRC_PIN);
    pio_gpio_init(pio, HEAD_SPK_DIN_PIN);
    pio_sm_set_consecutive_pindirs(pio, spk_sm, HEAD_SPK_BCLK_PIN, 3, true);
    pio_sm_init(pio, spk_sm, spk_offset + i2s_spk_offset_entry, &sc);

    // ---- DMA rings ----
    memset(mic_ring, 0, sizeof(mic_ring));
    memset(spk_ring, 0, sizeof(spk_ring));
    mic_dma_a = dma_claim_unused_channel(true);
    mic_dma_b = dma_claim_unused_channel(true);
    spk_dma_a = dma_claim_unused_channel(true);
    spk_dma_b = dma_claim_unused_channel(true);
    ring_dma_pair(mic_dma_a, mic_dma_b, false, (uintptr_t)&pio->rxf[mic_sm], mic_ring, pio_get_dreq(pio, mic_sm, false));
    ring_dma_pair(spk_dma_a, spk_dma_b, true, (uintptr_t)&pio->txf[spk_sm], spk_ring, pio_get_dreq(pio, spk_sm, true));

    mic_rd = 0;
    spk_wr = SPK_TARGET_FRAMES;
    spk_last_rx = get_absolute_time();

    pio_enable_sm_mask_in_sync(pio, (1u << mic_sm) | (1u << spk_sm));
}

// ---------------------------------------------------------------- capture

void audio_mic_restart(void) {
    mic_rd = mic_hw_frame();
}

uint32_t audio_mic_read(int16_t *out, uint32_t max_frames) {
    uint32_t hw = mic_hw_frame();
    uint32_t avail = (hw - mic_rd) & (MIC_RING_FRAMES - 1u);
    if (avail > MIC_MAX_LAG_FRAMES) {
        mic_rd = (hw - MIC_RESYNC_FRAMES) & (MIC_RING_FRAMES - 1u);
        avail = MIC_RESYNC_FRAMES;
        audio_stats.mic_resyncs++;
    }
    uint32_t n = avail < max_frames ? avail : max_frames;
    for (uint32_t i = 0; i < n; i++) {
        audio_mic_frame_to_usb(&mic_ring[mic_rd * MIC_WORDS_PER_FRAME], out, mic_gain_shift);
        out += MIC_USB_CHANNELS;
        mic_rd = (mic_rd + 1u) & (MIC_RING_FRAMES - 1u);
    }
    audio_stats.mic_frames += n;
    return n;
}

// Core 1, once per touch poll: level meter over everything recorded since the previous call (at most one ring).
// It reads the ring while the DMA writes it; a frame caught half-written only disturbs the meter, never the stream.
void audio_scan_peaks(void) {
    static uint32_t scanned;
    uint32_t hw = mic_hw_frame();
    uint32_t n = (hw - scanned) & (MIC_RING_FRAMES - 1u);
    uint16_t peak[3] = {0, 0, 0};
    int16_t frame[MIC_USB_CHANNELS];
    for (uint32_t i = 0; i < n; i++) {
        audio_mic_frame_to_usb(&mic_ring[scanned * MIC_WORDS_PER_FRAME], frame, mic_gain_shift);
        for (int ch = 0; ch < 3; ch++) {
            int32_t v = frame[ch];
            uint16_t mag = (uint16_t)(v < 0 ? (v == -32768 ? 32767 : -v) : v);
            if (mag > peak[ch]) peak[ch] = mag;
        }
        scanned = (scanned + 1u) & (MIC_RING_FRAMES - 1u);
    }
    for (int ch = 0; ch < 3; ch++) {
        if (peak[ch] > audio_stats.mic_peak[ch]) audio_stats.mic_peak[ch] = peak[ch];
    }
}

void audio_take_peaks(uint16_t peaks[3]) {
    for (int ch = 0; ch < 3; ch++) {
        peaks[ch] = audio_stats.mic_peak[ch];
        audio_stats.mic_peak[ch] = 0;
    }
}

void audio_set_mic_gain_shift(unsigned shift) {
    mic_gain_shift = shift > 8u ? 8u : shift;
}

unsigned audio_get_mic_gain_shift(void) {
    return mic_gain_shift;
}

// ---------------------------------------------------------------- playback

static inline void spk_put(uint32_t frame, uint32_t left_word, uint32_t right_word) {
    spk_ring[frame * SPK_WORDS_PER_FRAME] = left_word;
    spk_ring[frame * SPK_WORDS_PER_FRAME + 1u] = right_word;
}

// Make everything between the writer and hw + SPK_TARGET_FRAMES silence and move the writer there.
// If the DMA has already passed the writer, the silence starts at the DMA position instead.
static void spk_pad_silence(uint32_t hw, uint32_t queued) {
    uint32_t from = queued > SPK_MAX_FRAMES ? hw : spk_wr;
    uint32_t to = (hw + SPK_TARGET_FRAMES) & (SPK_RING_FRAMES - 1u);
    for (uint32_t f = from; f != to; f = (f + 1u) & (SPK_RING_FRAMES - 1u)) spk_put(f, 0, 0);
    spk_wr = to;
}

void audio_task(void) {
    uint32_t hw = spk_hw_frame();
    uint32_t queued = (spk_wr - hw) & (SPK_RING_FRAMES - 1u);
    if (queued < SPK_LOW_FRAMES || queued > SPK_MAX_FRAMES) {
        spk_pad_silence(hw, queued);
        spk_padded = true;
    }
}

void audio_spk_write(const int16_t *in, uint32_t frames) {
    if (frames == 0) return;
    absolute_time_t now = get_absolute_time();
    uint32_t hw = spk_hw_frame();
    uint32_t queued = (spk_wr - hw) & (SPK_RING_FRAMES - 1u);
    bool new_run = absolute_time_diff_us(spk_last_rx, now) > SPK_GAP_US;

    // Silence was inserted, or the DMA passed the writer, and the stream then went on: the amplifier ran dry mid-stream.
    if (!new_run && (spk_padded || queued > SPK_MAX_FRAMES)) audio_stats.spk_underruns++;
    if (new_run || queued > SPK_MAX_FRAMES) {
        spk_pad_silence(hw, queued);                       // a run starts a full target ahead of the amplifier
        queued = SPK_TARGET_FRAMES;
    }
    spk_padded = false;
    spk_last_rx = now;

    uint32_t skip = 0, repeat = 0;
    if (queued > SPK_TARGET_FRAMES + SPK_SLIP_FRAMES) {
        skip = 1;                                          // host is fast: lose one frame of this packet
        audio_stats.spk_dropped++;
    } else if (queued < SPK_TARGET_FRAMES - SPK_SLIP_FRAMES) {
        repeat = 1;                                        // host is slow: play one frame twice
        audio_stats.spk_repeated++;
    }

    uint32_t w[SPK_WORDS_PER_FRAME] = {0, 0};
    for (uint32_t i = skip; i < frames; i++) {
        audio_usb_frame_to_spk(&in[i * SPK_USB_CHANNELS], w);
        spk_put(spk_wr, w[0], w[1]);
        spk_wr = (spk_wr + 1u) & (SPK_RING_FRAMES - 1u);
    }
    if (repeat && frames > skip) {
        spk_put(spk_wr, w[0], w[1]);
        spk_wr = (spk_wr + 1u) & (SPK_RING_FRAMES - 1u);
    }
    audio_stats.spk_frames += frames;
}

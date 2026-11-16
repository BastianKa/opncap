// SPDX-License-Identifier: GPL-2.0-or-later
// opncap v0.3 keyboard-level code: events to the host over raw HID (protocol v1) and
// the Hall joystick. Not built or tested on real hardware yet.
#include QMK_KEYBOARD_H
#include <math.h>
#include <string.h>
#include "analog.h"
#include "raw_hid.h"
#include "timer.h"
#include "opncap_protocol.h"

#define FW_MAJOR 0
#define FW_MINOR 1
#define FW_PATCH 0

#define JOY_X_PIN A1
#define JOY_Y_PIN A2
#define JOY_SAMPLE_MS 10
#define JOY_CAL_SAMPLES 32
#define JOY_DEADZONE 25 // percent of full deflection
#define JOY_SLOTS 7
#define JOY_SLOT_NONE 0xFF

static uint8_t tx_seq;

static void send_frame(uint8_t msg, uint8_t seq, const uint8_t *payload, uint8_t len) {
    opncap_frame_t f;
    memset(&f, 0, sizeof f);
    f.version = OPNCAP_PROTOCOL_VERSION;
    f.msg     = msg;
    f.seq     = seq;
    f.len     = len;
    memcpy(f.payload, payload, len);
    uint8_t out[OPNCAP_FRAME_SIZE];
    if (opncap_frame_encode(&f, out) == 0) {
        raw_hid_send(out, OPNCAP_FRAME_SIZE);
    }
}

static void send_event(uint8_t msg, const uint8_t *payload, uint8_t len) {
    send_frame(msg, tx_seq++, payload, len);
}

static void send_ack(uint8_t seq, uint8_t msg, uint8_t status) {
    const uint8_t p[2] = {msg, status};
    send_frame(OPNCAP_MSG_ACK, seq, p, 2);
}

// --- keys, encoder, layers ---------------------------------------------------

bool process_record_kb(uint16_t keycode, keyrecord_t *record) {
    if (!process_record_user(keycode, record)) {
        return false;
    }
    const uint8_t p[2] = {(uint8_t)(record->event.key.row * MATRIX_COLS + record->event.key.col), record->event.pressed ? 1 : 0};
    send_event(OPNCAP_MSG_KEY_EVENT, p, 2);
    return true;
}

bool encoder_update_kb(uint8_t index, bool clockwise) {
    if (!encoder_update_user(index, clockwise)) {
        return false;
    }
    const uint8_t p[1] = {(uint8_t)(int8_t)(clockwise ? 1 : -1)};
    send_event(OPNCAP_MSG_ENCODER_EVENT, p, 1);
    // Standalone default: volume. Host adapters can take over later.
    tap_code_delay(clockwise ? KC_VOLU : KC_VOLD, 10);
    return true;
}

layer_state_t layer_state_set_kb(layer_state_t state) {
    state = layer_state_set_user(state);
    const uint8_t p[1] = {get_highest_layer(state)};
    send_event(OPNCAP_MSG_LAYER_EVENT, p, 1);
    return state;
}

// --- Hall joystick -------------------------------------------------------------
// Center is measured at start (mean of JOY_CAL_SAMPLES samples), min/max are tracked
// while running. Values are scaled to -100..100 around the center.

static int16_t  cal_x, cal_y;
static int16_t  min_x = 0, max_x = 1023, min_y = 0, max_y = 1023;
static uint16_t cal_sum_x, cal_sum_y;
static uint8_t  cal_count;
static bool     calibrated;
static uint32_t last_sample;
static uint8_t  last_dir  = 0xFF;
static uint8_t  last_slot = JOY_SLOT_NONE;

static int8_t scale_axis(int16_t v, int16_t center, int16_t lo, int16_t hi) {
    int32_t d    = v - center;
    int32_t span = d >= 0 ? hi - center : center - lo;
    if (span < 50) {
        span = 50; // avoid division by a tiny range before min/max are known
    }
    int32_t s = d * 100 / span;
    if (s > 100) s = 100;
    if (s < -100) s = -100;
    return (int8_t)s;
}

// Orientation (which axis is up) depends on how the module is mounted. [prüfen] on hardware.
static uint8_t direction_of(int8_t x, int8_t y) {
    int ax = x < 0 ? -x : x;
    int ay = y < 0 ? -y : y;
    if (ax * ax + ay * ay < JOY_DEADZONE * JOY_DEADZONE) {
        return OPNCAP_DIRECTION_CENTER;
    }
    if (ay * 1000 < ax * 414) { // within 22.5 degrees of the horizontal axis
        return x > 0 ? OPNCAP_DIRECTION_RIGHT : OPNCAP_DIRECTION_LEFT;
    }
    if (ax * 1000 < ay * 414) {
        return y > 0 ? OPNCAP_DIRECTION_UP : OPNCAP_DIRECTION_DOWN;
    }
    if (y > 0) {
        return x > 0 ? OPNCAP_DIRECTION_UP_RIGHT : OPNCAP_DIRECTION_UP_LEFT;
    }
    return x > 0 ? OPNCAP_DIRECTION_DOWN_RIGHT : OPNCAP_DIRECTION_DOWN_LEFT;
}

// Slot 0 is centered on "up", slots run clockwise.
static uint8_t slot_of(int8_t x, int8_t y) {
    float deg = atan2f((float)x, (float)y) * (180.0f / 3.14159265f);
    if (deg < 0) {
        deg += 360.0f;
    }
    return (uint8_t)((int)((deg + 180.0f / JOY_SLOTS) / (360.0f / JOY_SLOTS)) % JOY_SLOTS);
}

static void joystick_task(void) {
    if (timer_elapsed32(last_sample) < JOY_SAMPLE_MS) {
        return;
    }
    last_sample = timer_read32();
    int16_t rx = analogReadPin(JOY_X_PIN);
    int16_t ry = analogReadPin(JOY_Y_PIN);

    if (!calibrated) {
        cal_sum_x += rx;
        cal_sum_y += ry;
        if (++cal_count >= JOY_CAL_SAMPLES) {
            cal_x      = cal_sum_x / JOY_CAL_SAMPLES;
            cal_y      = cal_sum_y / JOY_CAL_SAMPLES;
            calibrated = true;
        }
        return;
    }
    if (rx < min_x) min_x = rx;
    if (rx > max_x) max_x = rx;
    if (ry < min_y) min_y = ry;
    if (ry > max_y) max_y = ry;

    int8_t  x    = scale_axis(rx, cal_x, min_x, max_x);
    int8_t  y    = scale_axis(ry, cal_y, min_y, max_y);
    uint8_t dir  = direction_of(x, y);
    uint8_t slot = dir == OPNCAP_DIRECTION_CENTER ? JOY_SLOT_NONE : slot_of(x, y);
    if (dir != last_dir || slot != last_slot) {
        last_dir  = dir;
        last_slot = slot;
        const uint8_t p[2] = {dir, slot};
        send_event(OPNCAP_MSG_JOYSTICK_EVENT, p, 2);
    }
}

void housekeeping_task_kb(void) {
    joystick_task();
    housekeeping_task_user();
}

// --- agent status LEDs -----------------------------------------------------------
// Agent keys K1..K6 show the state of one agent session each, the status LED shows the
// most urgent one. LED indices follow the data order in hardware/pinout.md.

#define AGENT_SLOTS 6
#define STATUS_LED 12
static const uint8_t slot_led[AGENT_SLOTS] = {0, 1, 2, 3, 7, 6}; // K1, K2, K3, K4, K5, K6

static uint8_t agent_state[AGENT_SLOTS]; // OPNCAP_STATE_* values, all off at start
static uint8_t overall_state;

static void state_color(uint8_t state, uint8_t *r, uint8_t *g, uint8_t *b) {
    switch (state) {
        case OPNCAP_STATE_IDLE:     *r = 255; *g = 255; *b = 255; break; // white
        case OPNCAP_STATE_THINKING: *r = 0;   *g = 0;   *b = 255; break; // blue
        case OPNCAP_STATE_DONE:     *r = 0;   *g = 255; *b = 0;   break; // green
        case OPNCAP_STATE_INPUT:    *r = 255; *g = 100; *b = 0;   break; // orange
        case OPNCAP_STATE_ERROR:    *r = 255; *g = 0;   *b = 0;   break; // red
        default:                    *r = 0;   *g = 0;   *b = 0;   break; // off
    }
}

static void set_state_led(uint8_t led, uint8_t state, uint8_t led_min, uint8_t led_max) {
    if (led < led_min || led >= led_max) {
        return;
    }
    uint8_t r, g, b;
    state_color(state, &r, &g, &b);
    // Scale by the configured brightness so the USB current limit holds.
    uint8_t v = rgb_matrix_get_val();
    rgb_matrix_set_color(led, (uint16_t)r * v / 255, (uint16_t)g * v / 255, (uint16_t)b * v / 255);
}

bool rgb_matrix_indicators_advanced_kb(uint8_t led_min, uint8_t led_max) {
    if (!rgb_matrix_indicators_advanced_user(led_min, led_max)) {
        return false;
    }
    for (uint8_t i = 0; i < AGENT_SLOTS; i++) {
        set_state_led(slot_led[i], agent_state[i], led_min, led_max);
    }
    set_state_led(STATUS_LED, overall_state, led_min, led_max);
    return true;
}

// --- raw HID from the host -----------------------------------------------------

void raw_hid_receive(uint8_t *data, uint8_t length) {
    opncap_frame_t f;
    if (length != OPNCAP_FRAME_SIZE || opncap_frame_decode(data, &f) != OPNCAP_OK) {
        return; // malformed frames are dropped without a reply
    }
    switch (f.msg) {
        case OPNCAP_MSG_GET_VERSION: {
            const uint8_t p[4] = {OPNCAP_PROTOCOL_VERSION, FW_MAJOR, FW_MINOR, FW_PATCH};
            send_frame(OPNCAP_MSG_VERSION_INFO, f.seq, p, 4);
            break;
        }
        case OPNCAP_MSG_SET_STATE:
            if (f.len != OPNCAP_MSG_SET_STATE_SIZE || f.payload[OPNCAP_MSG_SET_STATE_STATE_OFFSET] > OPNCAP_STATE_ERROR) {
                send_ack(f.seq, f.msg, OPNCAP_ACK_STATUS_BAD_PAYLOAD);
                break;
            }
            overall_state = f.payload[OPNCAP_MSG_SET_STATE_STATE_OFFSET];
            send_ack(f.seq, f.msg, OPNCAP_ACK_STATUS_OK);
            break;
        case OPNCAP_MSG_SET_AGENT_STATE: {
            uint8_t slot  = f.payload[OPNCAP_MSG_SET_AGENT_STATE_SLOT_OFFSET];
            uint8_t state = f.payload[OPNCAP_MSG_SET_AGENT_STATE_STATE_OFFSET];
            if (f.len != OPNCAP_MSG_SET_AGENT_STATE_SIZE || slot >= AGENT_SLOTS || state > OPNCAP_STATE_ERROR) {
                send_ack(f.seq, f.msg, OPNCAP_ACK_STATUS_BAD_PAYLOAD);
                break;
            }
            agent_state[slot] = state;
            send_ack(f.seq, f.msg, OPNCAP_ACK_STATUS_OK);
            break;
        }
        default:
            // set_led, set_display and set_config arrive with the display and configuration features.
            send_ack(f.seq, f.msg, OPNCAP_ACK_STATUS_UNKNOWN_MESSAGE);
            break;
    }
}

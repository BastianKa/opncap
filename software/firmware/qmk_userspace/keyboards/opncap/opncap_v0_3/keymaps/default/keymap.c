// SPDX-License-Identifier: GPL-2.0-or-later
#include QMK_KEYBOARD_H

// LAYOUT order: encoder push, joystick push, K1..K12, K13, K14.
// K11 cycles through the six layers (TO). Layers 1 to 5 are transparent otherwise.
const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [0] = LAYOUT(KC_MUTE, KC_ENT,
                 KC_F13, KC_F14, KC_F15, KC_F16,
                 KC_F17, KC_F18, KC_F19, KC_F20,
                 KC_F21, KC_F22, TO(1),  KC_F24,
                 KC_SPC, KC_SPC),
    [1] = LAYOUT(KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, TO(2),   KC_TRNS,
                 KC_TRNS, KC_TRNS),
    [2] = LAYOUT(KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, TO(3),   KC_TRNS,
                 KC_TRNS, KC_TRNS),
    [3] = LAYOUT(KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, TO(4),   KC_TRNS,
                 KC_TRNS, KC_TRNS),
    [4] = LAYOUT(KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, TO(5),   KC_TRNS,
                 KC_TRNS, KC_TRNS),
    [5] = LAYOUT(KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS,
                 KC_TRNS, KC_TRNS, TO(0),   KC_TRNS,
                 KC_TRNS, KC_TRNS),
};

/* SPDX-License-Identifier: Apache-2.0 */
/* Generated from software/protocol/protocol.yaml by software/protocol/gen.py. Do not edit. */
#ifndef OPNCAP_PROTOCOL_H
#define OPNCAP_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define OPNCAP_PROTOCOL_VERSION 1
#define OPNCAP_FRAME_SIZE 32
#define OPNCAP_MAX_PAYLOAD 24
#define OPNCAP_MAGIC0 0x4F
#define OPNCAP_MAGIC1 0x43

#define OPNCAP_STATE_OFF 0
#define OPNCAP_STATE_IDLE 1
#define OPNCAP_STATE_THINKING 2
#define OPNCAP_STATE_DONE 3
#define OPNCAP_STATE_INPUT 4
#define OPNCAP_STATE_ERROR 5

#define OPNCAP_DIRECTION_CENTER 0
#define OPNCAP_DIRECTION_UP 1
#define OPNCAP_DIRECTION_UP_RIGHT 2
#define OPNCAP_DIRECTION_RIGHT 3
#define OPNCAP_DIRECTION_DOWN_RIGHT 4
#define OPNCAP_DIRECTION_DOWN 5
#define OPNCAP_DIRECTION_DOWN_LEFT 6
#define OPNCAP_DIRECTION_LEFT 7
#define OPNCAP_DIRECTION_UP_LEFT 8

#define OPNCAP_ACK_STATUS_OK 0
#define OPNCAP_ACK_STATUS_UNKNOWN_MESSAGE 1
#define OPNCAP_ACK_STATUS_BAD_PAYLOAD 2
#define OPNCAP_ACK_STATUS_BUSY 3

#define OPNCAP_MSG_GET_VERSION 0x01
#define OPNCAP_MSG_GET_VERSION_SIZE 0
#define OPNCAP_MSG_SET_LED 0x02
#define OPNCAP_MSG_SET_LED_SIZE 4
#define OPNCAP_MSG_SET_LED_INDEX_OFFSET 0
#define OPNCAP_MSG_SET_LED_R_OFFSET 1
#define OPNCAP_MSG_SET_LED_G_OFFSET 2
#define OPNCAP_MSG_SET_LED_B_OFFSET 3
#define OPNCAP_MSG_SET_STATE 0x03
#define OPNCAP_MSG_SET_STATE_SIZE 1
#define OPNCAP_MSG_SET_STATE_STATE_OFFSET 0
#define OPNCAP_MSG_SET_AGENT_STATE 0x04
#define OPNCAP_MSG_SET_AGENT_STATE_SIZE 2
#define OPNCAP_MSG_SET_AGENT_STATE_SLOT_OFFSET 0
#define OPNCAP_MSG_SET_AGENT_STATE_STATE_OFFSET 1
#define OPNCAP_MSG_SET_DISPLAY 0x05
#define OPNCAP_MSG_SET_DISPLAY_SIZE 2
#define OPNCAP_MSG_SET_DISPLAY_VIEW_OFFSET 0
#define OPNCAP_MSG_SET_DISPLAY_ARG_OFFSET 1
#define OPNCAP_MSG_SET_CONFIG 0x06
#define OPNCAP_MSG_SET_CONFIG_SIZE 3
#define OPNCAP_MSG_SET_CONFIG_KEY_OFFSET 0
#define OPNCAP_MSG_SET_CONFIG_VALUE_OFFSET 1
#define OPNCAP_MSG_ACK 0x70
#define OPNCAP_MSG_ACK_SIZE 2
#define OPNCAP_MSG_ACK_MSG_OFFSET 0
#define OPNCAP_MSG_ACK_STATUS_OFFSET 1
#define OPNCAP_MSG_VERSION_INFO 0x71
#define OPNCAP_MSG_VERSION_INFO_SIZE 4
#define OPNCAP_MSG_VERSION_INFO_PROTOCOL_OFFSET 0
#define OPNCAP_MSG_VERSION_INFO_MAJOR_OFFSET 1
#define OPNCAP_MSG_VERSION_INFO_MINOR_OFFSET 2
#define OPNCAP_MSG_VERSION_INFO_PATCH_OFFSET 3
#define OPNCAP_MSG_KEY_EVENT 0x80
#define OPNCAP_MSG_KEY_EVENT_SIZE 2
#define OPNCAP_MSG_KEY_EVENT_KEY_OFFSET 0
#define OPNCAP_MSG_KEY_EVENT_PRESSED_OFFSET 1
#define OPNCAP_MSG_ENCODER_EVENT 0x81
#define OPNCAP_MSG_ENCODER_EVENT_SIZE 1
#define OPNCAP_MSG_ENCODER_EVENT_DELTA_OFFSET 0
#define OPNCAP_MSG_JOYSTICK_EVENT 0x82
#define OPNCAP_MSG_JOYSTICK_EVENT_SIZE 2
#define OPNCAP_MSG_JOYSTICK_EVENT_DIRECTION_OFFSET 0
#define OPNCAP_MSG_JOYSTICK_EVENT_SLOT_OFFSET 1
#define OPNCAP_MSG_LAYER_EVENT 0x83
#define OPNCAP_MSG_LAYER_EVENT_SIZE 1
#define OPNCAP_MSG_LAYER_EVENT_LAYER_OFFSET 0

enum {
    OPNCAP_OK = 0,
    OPNCAP_ERR_MAGIC = -1,
    OPNCAP_ERR_VERSION = -2,
    OPNCAP_ERR_LENGTH = -3,
    OPNCAP_ERR_PADDING = -4,
    OPNCAP_ERR_CRC = -5,
};

typedef struct {
    uint8_t version;
    uint8_t msg;
    uint8_t seq;
    uint8_t len;
    uint8_t payload[OPNCAP_MAX_PAYLOAD];
} opncap_frame_t;

/* CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no reflection, no xorout. Check value of "123456789" is 0x29B1. */
static inline uint16_t opncap_crc16(const uint8_t *data, size_t len) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int b = 0; b < 8; b++) crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
    }
    return crc;
}

/* Returns 0 on success, -1 if the payload is too long. */
static inline int opncap_frame_encode(const opncap_frame_t *f, uint8_t out[OPNCAP_FRAME_SIZE]) {
    if (f->len > OPNCAP_MAX_PAYLOAD) return -1;
    memset(out, 0, OPNCAP_FRAME_SIZE);
    out[0] = OPNCAP_MAGIC0; out[1] = OPNCAP_MAGIC1; out[2] = f->version; out[3] = f->msg;
    out[4] = f->seq; out[5] = f->len;
    memcpy(&out[6], f->payload, f->len);
    uint16_t crc = opncap_crc16(out, OPNCAP_FRAME_SIZE - 2);
    out[OPNCAP_FRAME_SIZE - 2] = (uint8_t)(crc & 0xFF); out[OPNCAP_FRAME_SIZE - 1] = (uint8_t)(crc >> 8);
    return 0;
}

/* Returns OPNCAP_OK or a negative OPNCAP_ERR_* code. */
static inline int opncap_frame_decode(const uint8_t in[OPNCAP_FRAME_SIZE], opncap_frame_t *f) {
    if (in[0] != OPNCAP_MAGIC0 || in[1] != OPNCAP_MAGIC1) return OPNCAP_ERR_MAGIC;
    uint16_t crc = (uint16_t)(in[OPNCAP_FRAME_SIZE - 2] | (in[OPNCAP_FRAME_SIZE - 1] << 8));
    if (crc != opncap_crc16(in, OPNCAP_FRAME_SIZE - 2)) return OPNCAP_ERR_CRC;
    if (in[2] != OPNCAP_PROTOCOL_VERSION) return OPNCAP_ERR_VERSION;
    if (in[5] > OPNCAP_MAX_PAYLOAD) return OPNCAP_ERR_LENGTH;
    for (size_t i = 6 + in[5]; i < OPNCAP_FRAME_SIZE - 2; i++) if (in[i] != 0) return OPNCAP_ERR_PADDING;
    f->version = in[2]; f->msg = in[3]; f->seq = in[4]; f->len = in[5];
    memset(f->payload, 0, OPNCAP_MAX_PAYLOAD);
    memcpy(f->payload, &in[6], f->len);
    return OPNCAP_OK;
}

#endif /* OPNCAP_PROTOCOL_H */

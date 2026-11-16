// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// Encoder pulses per detent. EC11 types differ (2 or 4). [prüfen] on the real part.
#define ENCODER_RESOLUTION 4

// WS2812 chain on B4 = TIM3_CH1 (AF2), DMA1 stream 2 channel 5 = TIM3_UP. [prüfen] against the
// STM32F411 reference manual DMA request table and on hardware.
#define WS2812_PWM_DRIVER PWMD3
#define WS2812_PWM_CHANNEL 1
#define WS2812_PWM_PAL_MODE 2
#define WS2812_PWM_DMA_STREAM STM32_DMA1_STREAM2
#define WS2812_PWM_DMA_CHANNEL 5

// 23 LEDs at full white would draw about 1.4 A; stay well below the 500 mA USB limit.
#define RGB_MATRIX_MAXIMUM_BRIGHTNESS 80
#define RGB_MATRIX_DEFAULT_MODE RGB_MATRIX_SOLID_COLOR
#define ENABLE_RGB_MATRIX_SOLID_COLOR
#define RGB_MATRIX_DEFAULT_HUE 0
#define RGB_MATRIX_DEFAULT_SAT 0
#define RGB_MATRIX_DEFAULT_VAL 40

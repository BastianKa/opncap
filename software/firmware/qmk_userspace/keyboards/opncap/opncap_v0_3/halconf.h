// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// ADC for the Hall joystick (A1 = ADC1_IN1, A2 = ADC1_IN2)
#define HAL_USE_ADC TRUE
// PWM + DMA for the WS2812 chain (TIM3)
#define HAL_USE_PWM TRUE

#include_next <halconf.h>

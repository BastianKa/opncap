<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Generated from hardware/pinout.yaml by hardware/scripts/gen_pinout.py. Do not edit. -->
# opncap pinout

MCU: WeAct BlackPill F411 (STM32F411CEU6). Mounting: bottom side of the PCB, upside-down on 2x20 pin headers, USB-C to the back.

Status: generated, not tested on hardware.

| Signal | STM32 pin | Function | Note |
|---|---|---|---|
| COL0 | A6 | matrix column 0 | K1 K5 K9 + encoder push |
| COL1 | A5 | matrix column 1 | K2 K6 K10 K13 |
| COL2 | B3 | matrix column 2 | K3 K7 K11 K14 (JTDO pin, free when only SWD is used) |
| COL3 | B4 | matrix column 3 | K4 K8 K12 + joystick push (NJTRST pin, free with SWD) |
| ROW0 | A4 | matrix row 0 | K1..K4 |
| ROW1 | A3 | matrix row 1 | K5..K8 |
| ROW2 | B5 | matrix row 2 | K9..K12 |
| ROW3 | B8 | matrix row 3 | encoder push, K13, K14, joystick push |
| ENC_A | B0 | encoder phase A | internal pull-up, common pin to GND |
| ENC_B | B1 | encoder phase B | internal pull-up |
| JOY_X | A1 | joystick X | ADC1_IN1 |
| JOY_Y | A2 | joystick Y | ADC1_IN2 |
| I2C_SCL | B6 | OLED SCL | I2C1, pull-ups are on the OLED module |
| I2C_SDA | B7 | OLED SDA | I2C1 |
| RGB_3V3 | A7 | LED data (3.3 V) | SPI1_MOSI / TIM3_CH2, goes through 74AHCT125 to 5 V |

## Power

| Net | Source and use |
|---|---|
| +5V | USB VBUS from the BlackPill 5V pins; LEDs and level shifter |
| +3V3 | BlackPill regulator; OLED and joystick |
| GND | common ground, poured on both layers |

## Reserved pins

| STM32 pin | Reason |
|---|---|
| A0 | user key on the BlackPill |
| A9 | USART1_TX, kept free for the phase 2 BLE bridge |
| A10 | USART1_RX, kept free for the phase 2 BLE bridge |
| A11 | USB D- |
| A12 | USB D+ |
| B2 | BOOT1 |
| C13 | on-board LED |

## Matrix (COL2ROW)

| | COL0 | COL1 | COL2 | COL3 |
|---|---|---|---|---|
| ROW0 | K1 | K2 | K3 | K4 |
| ROW1 | K5 | K6 | K7 | K8 |
| ROW2 | K9 | K10 | K11 | K12 |
| ROW3 | ENC_PUSH | K13 | K14 | JOY_PUSH |

## LED chain

Per key, in data order: K1, K2, K3, K4, K8, K7, K6, K5, K9, K10, K11, K12, K14, K13.

Then underglow: UG1, UG2, UG3, UG4, UG5, UG6, UG7, UG8.

## Layout

```
( ENC )    [  OLED  ]    ( JOY )

       [K1]  [K2]  [K3]  [K4]
       [K5]  [K6]  [K7]  [K8]
       [K9]  [K10] [K11] [K12]

              [K13] [K14]
```

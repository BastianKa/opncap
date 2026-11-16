<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Generated from hardware/pinout.yaml by hardware/scripts/gen_pinout.py. Do not edit. -->
# opncap pinout

MCU: WeAct BlackPill F411 (STM32F411CEU6). Mounting: under the main PCB on low-profile socket strips, component side facing the main PCB, USB-C to the back.

Status: generated, not tested on hardware.

| Signal | STM32 pin | Function | Note |
|---|---|---|---|
| COL0 | B0 | matrix column 0 | K1 K5 K9 + encoder push |
| COL1 | B1 | matrix column 1 | K2 K6 K10 K13 |
| COL2 | A6 | matrix column 2 | K3 K7 K11 K14 |
| COL3 | A5 | matrix column 3 | K4 K8 K12 + joystick push |
| ROW0 | A4 | matrix row 0 | K1..K4 |
| ROW1 | A3 | matrix row 1 | K5..K8 |
| ROW2 | A7 | matrix row 2 | K9..K12 |
| ROW3 | B8 | matrix row 3 | encoder push, K13, K14, joystick push |
| ENC_A | B6 | encoder phase A | TIM4_CH1, internal pull-up, common pin to GND |
| ENC_B | B7 | encoder phase B | TIM4_CH2, internal pull-up |
| JOY_X | A1 | joystick X | ADC1_IN1 |
| JOY_Y | A2 | joystick Y | ADC1_IN2 |
| DISP_SCK | B13 | display SPI clock | SPI2_SCK, module pin SCL |
| DISP_MOSI | B15 | display SPI data | SPI2_MOSI, module pin SDA |
| DISP_DC | B14 | display data/command | GPIO |
| DISP_CS | B12 | display chip select | GPIO, active low |
| DISP_RST | A8 | display reset | GPIO, active low |
| DISP_BL | B9 | display backlight | TIM4_CH4 for PWM dimming, high = on |
| RGB_3V3 | B4 | LED data (3.3 V) | TIM3_CH1, goes through 74AHCT125 to 5 V (NJTRST pin, free with SWD) |
| MIC_CLK | B3 | microphone clock | I2S3_CK, 1 to 3.3 MHz (JTDO pin, free with SWD) |
| MIC_DATA | B5 | microphone data | I2S3_SD, PDM bit stream |

## Power

| Net | Source and use |
|---|---|
| +5V | USB VBUS from the BlackPill 5V pins; LEDs and level shifter |
| +3V3 | BlackPill regulator; display (about 30 to 50 mA with backlight) and joystick |
| GND | common ground, poured on both layers |

## Reserved pins

| STM32 pin | Reason |
|---|---|
| A0 | user key on the BlackPill |
| A9 | USART1_TX, kept free for the phase 2 BLE bridge |
| A10 | USART1_RX, kept free for the phase 2 BLE bridge |
| A11 | USB D- |
| A12 | USB D+ |
| A15 | free (I2S3_WS, not needed for PDM) |
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

Per key, in data order: K1, K2, K3, K4, K8, K7, K6, K5, K9, K10, K11, K12, STATUS, K14, K13.

Then underglow: UG1, UG2, UG3, UG4, UG5, UG6, UG7, UG8.

## Layout

```
( ENC )     ( DISPLAY )     ( JOY )

       [K1]  [K2]  [K3]  [K4]
       [K5]  [K6]  [K7]  [K8]
       [K9]  [K10] [K11] [K12]

        (mic) [K13] [K14] (status)
```

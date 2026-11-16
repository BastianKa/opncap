<!-- SPDX-License-Identifier: Apache-2.0 -->
# opncap — Bill of Materials (Phase 1 prototype, wired)

Status: **draft, nothing ordered or tested.** Part numbers are suggestions and must be checked against the manufacturer datasheet before ordering. No prices are listed on purpose; they were not verified.

## Prototype (Phase 1)

| # | Qty | Part | Value / spec | Purpose | Notes |
|---|-----|------|--------------|---------|-------|
| 1 | 1 | WeAct BlackPill F411 (STM32F411CE) | 3.3 V logic, USB-C | Main MCU | Prototype board; QMK support to be confirmed in the current repo. |
| 2 | 14 | MX-style switch | Any 3-pin or 5-pin MX switch | Keys K1–K14 | Choose by feel; no firmware impact. |
| 3 | 14 | Hotswap socket | Kailh MX hotswap | Switch mounting | Only needed on a PCB; skip for hand-wired tests. |
| 4 | 16 | Diode | 1N4148 (THT) or 1N4148W (SOD-123) | Matrix, one per key plus encoder push plus joystick push | Orientation `COL2ROW`. |
| 5 | 14 | RGB LED | SK6812 MINI-E or WS2812B-compatible, 5 V | Per-key LED | One per key. Verify footprint against the chosen switch socket. |
| 6 | 8 | RGB LED | Same family as #5 | Underglow | Count is an assumption; adjust to the enclosure. |
| 7 | 1 | Rotary encoder with push | EC11-type, 20 detents, with switch | Encoder | Push is wired into the matrix. |
| 8 | 1 | Hall-effect joystick with push | 3.3 V analog, 2 axes + switch | Joystick | Candidate: FJH10K-S3D class. **Datasheet, voltage and pinout unconfirmed**; ask the seller before ordering. |
| 9 | 1 | OLED module | 0.91" 128x32, SSD1306, I²C, 3.3 V | Display | I²C address usually 0x3C; check the module. |
| 10 | 1 | Level shifter | 74AHCT125 (or 74HCT245) | 3.3 V to 5 V LED data | SK6812 at 5 V expects about 3.5 V for a high level; a shifter makes the data line reliable. |
| 11 | 1 | Resistor | 330 Ω | LED data line series resistor | |
| 12 | 24 | Capacitor | 100 nF ceramic | One per LED | Decoupling. |
| 13 | 1 | Capacitor | 220–470 µF electrolytic | LED supply bulk | Near the first LED. |
| 14 | 1 | USB-C cable | Data cable, not charge-only | Power and data | |
| 15 | 1 | Perfboard or placeholder PCB | — | Prototype carrier | The final KiCad PCB is a later step. |
| 16 | 1 | Pin headers, wire | — | Connections | |

## Power note

22 LEDs at full white draw about 60 mA each, roughly 1.3 A in the worst case, which is above the 500 mA a standard USB port guarantees. The firmware must cap RGB brightness (this is what the `full` / `reduced` / `minimal` profiles are for). Check the cap on a bench supply or USB meter during hardware tests.

## Not part of Phase 1 (placeholders, unverified)

| Item | Phase | Notes |
|------|-------|-------|
| nRF52840 module (e.g. Raytac MDBT50Q) | 2 | BLE bridge. |
| LiPo battery, charger/protection IC, power path | 2 | Selection depends on the final STM32 variant and the LED power budget. |
| Low-power STM32 (L4 family) | Final PCB | QMK/ChibiOS support for the exact variant to be confirmed. |
| Enclosure, plate, keycaps | Design | Original design, no copying of existing products. |

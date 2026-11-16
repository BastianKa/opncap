<!-- SPDX-License-Identifier: Apache-2.0 -->
# opncap hardware design notes

Status: everything here is generated and checked in software only. Nothing is ordered or tested on real hardware.

## Design language

1. **Slab wedge.** One 6° wedge with a single continuous corner radius; the PCB, plate and top surface are parallel, only the underside is tilted.
2. **Console band above the keys.** Knob, display and joystick sit on one line in a calm band, the keys sit in one recessed well below it.
3. **Bone, graphite and one signal colour.** A light case, dark keycaps, and orange only on the two things you reach for without looking: the knob and the K13/K14 pair.

## Decisions where the task or the spec was open

| Topic | Decision | Reason |
|---|---|---|
| KiCad version | Files are written by KiCad 7.0.11 (`pcbnew` Python API). | The task asks for KiCad 8+. Only 7.0.11 could be installed here (Ubuntu archive; the KiCad 8/9/10 package archive is blocked by the network policy). KiCad 8 and later open version 7 files and convert them on save. |
| DRC | `pcbnew.WriteDRCReport` from KiCad 7.0.11. | `kicad-cli pcb drc` only exists from KiCad 8. It is the same DRC engine as the GUI. Re-run DRC once in your own KiCad version. |
| Board size | 102 x 137 mm, console zone 50 mm deep. | The BlackPill is 52.8 mm long and its USB-C port must face the back, so it has to sit lengthwise at the top edge. Its pin rows cannot run under the key field: they would hit the hotswap pads and the switch peg holes. |
| BlackPill mounting | Bottom side, upside-down on 2x20 pin headers, centred, USB-C at the top edge. | Keeps the top side free for the OLED. The wedge gives the room: the cavity is deepest at the back. |
| K13/K14 | On the 19.05 mm grid in x (under columns 2 and 3), 0.25u extra gap below row 3. | The sketch shows a blank line between the grid and the pair. |
| Matrix row 3 | encoder push, K13, K14, joystick push (columns 0 to 3). | Follows the physical left-to-right order. |
| MCU pins | See `pinout.yaml`. A9/A10 (USART1) are left free for the phase 2 BLE bridge. | |
| LED data pin | A7 (SPI1_MOSI / TIM3_CH2), through one gate of the 74AHCT125 and 330 Ω. | Works with both QMK WS2812 drivers. Unused gates are disabled, inputs tied to GND. |
| LED chain order | K1 K2 K3 K4, K8 K7 K6 K5, K9 K10 K11 K12, K14 K13, then underglow UG1 to UG8 clockwise from bottom left. | Snake, shortest hops. |
| Underglow | 8 LEDs on the top side, shining down through the board. | Reverse-mount LEDs shine through their cut-out. The bottom case must be printed in a translucent material for the glow to be visible. |
| 100 nF count | 24: one per LED (22), one at the level shifter, one at the joystick supply. | Matches the 24 in `bom.md`. |
| Bulk capacitor | 330 µF, radial 6.3 mm, on the bottom side near K1. Up to 11 mm tall fits. | Inside the 220 to 470 µF range of the BOM. |
| OLED | 4-pin socket at the east end of the module, order GND, VCC, SCL, SDA. Module underside 7.5 mm above the PCB. | Common pin order of 0.91" modules; some modules swap VCC and GND. |
| Joystick | Parametric placeholder: 18 x 18 mm body, 1x6 header (VCC, GND, VRX, VRY, SW_A, SW_B), two locating holes. | The FJH10K-S3D datasheet is unconfirmed. |
| Copper | 0.25 mm signal tracks, 0.5 mm for +5 V, vias 0.6/0.3 mm, GND poured on both layers with solid pad connections. | Within JLCPCB standard capabilities. Solid connections avoid starved thermal spokes; ground pins need a little more heat when soldering. |
| Design rules | Clearance 0.15 mm, edge clearance 0.3 mm, hole clearance 0.25 mm. The router keeps 0.2 mm. | |
| Routing | A small grid router in `scripts/router.py` (0.3175 mm grid, two layers). Every net is routed as tracks; the pours are extra. | Deterministic and reproducible. Not as tidy as hand routing. |
| Case fixing | Six M2 screws from below through standoff, PCB, 3.5 mm spacer and plate into heat-set inserts in the top case. Lengths about 14, 18 and 26 mm (printed by the case script). | One screw stack aligns all four layers on the same holes. |
| Plate | 1.5 mm, 1.2 mm smaller than the PCB all round. | Leaves room for the alignment lip of the top case. |
| Key well | The top case has one T-shaped opening around the caps; the 14.0 mm switch cut-outs are in the plate. | A per-key bezel would collide with the 15.6 mm switch flange. |

## Assumptions to verify before ordering

- **SK6812 MINI-E footprint.** The pin functions (1 VDD, 2 DOUT, 3 GND, 4 DIN) match the OPSCO datasheet. Which corner each pin sits on, the pad size (1.3 x 0.85 mm at ±2.75/±0.75 mm) and the 3.4 x 2.8 mm window were not checked against the datasheet drawing.
- **BlackPill header order and outline** (52.81 x 20.78 mm, first pin 2.275 mm from the USB edge, connector overhang 1.0 mm) must be checked against your board revision.
- **EC11 mounting lugs** are round 2.3 mm plated holes; many parts want slots.
- **Kailh socket** footprint uses the commonly published pad positions; check against the socket drawing.
- **Pick-and-place rotations** in `positions.csv` are KiCad's values for script-made footprints. They are not matched to JLCPCB's rotation conventions.
- **LED current.** 22 LEDs can draw about 1.3 A at full white, more than the 0.5 mm supply track and a USB port should carry. The firmware brightness cap is required.

## Known gaps

- The schematic is a netlist-style sheet (parts with net labels, no drawn wires). It matches the board net for net, but ERC was not run.
- There is no footprint library on disk; footprints live in the board file. The DRC library-parity checks are switched off for that reason.
- No opening in the case for the BOOT0 and NRST buttons of the BlackPill. For the first flash the bottom has to be open.
- The enclosure was not reviewed for 3D-printing (supports, insert bosses, tolerances) or moulding.
- All 3D part models are simple placeholders with nominal dimensions. Screws and inserts are not modelled.
- The copper pours leave an unfilled area between the BlackPill pin rows where signal tracks fence it in.

<!-- SPDX-License-Identifier: Apache-2.0 -->
# opncap hardware design notes

Status: everything here is generated and checked in software only. Nothing is ordered or tested on real hardware.

## Design language

1. **Flat slab.** One 17 mm slab with a single continuous corner radius and no typing angle; PCB, plate, top and underside are parallel.
2. **Console band above the keys.** Knob, round display and joystick sit on one line in a calm band, the low-profile keys sit in one shallow well below it.
3. **Bone, graphite and one signal colour.** A light case, dark keycaps, and orange only on the two things you reach for without looking: the knob and the K13/K14 pair.

## Revision 0.2: flat build

Changed against 0.1 on request: Kailh Choc V1 hotswap instead of MX, a round 1.28" GC9A01 display instead of the 0.91" OLED, no typing angle, case as low as the chosen parts allow. `spec.md` and `features.md` still describe MX switches and an I²C OLED; they were not edited.

### Height budget (case underside to top surface: 16.9 mm)

| Layer | mm | Set by |
|---|---|---|
| Floor | 1.6 | print strength |
| Cavity under the PCB | 6.9 | socketed BlackPill: 3.94 board gap + 1.6 module + 0.8 pin tails + 0.6 air |
| Main PCB | 1.6 | |
| PCB top to case top | 6.8 | display module: 2.5 header + 1.6 carrier + 1.8 panel + 0.2 air + 0.7 rim |

Keycap tops are 19.7 mm above the underside, rubber feet add 1.2 mm. The keys themselves need only 5.0 mm above the PCB (Choc housing) and 1.8 mm below it (socket). The height is set by the BlackPill socket below and the display module above. The knob and the joystick stand well above the case, as chosen.

What would make it flatter, in order of effect: the STM32 directly on the board (cavity 6.9 to about 2.5 mm), a bare GC9A01 panel on an FPC connector (about 3 mm less above the PCB), the BlackPill soldered flat (1.4 mm).

## Decisions where the task or the spec was open

| Topic | Decision | Reason |
|---|---|---|
| KiCad version | Files are written by KiCad 7.0.11 (`pcbnew` Python API). | The task asks for KiCad 8+. Only 7.0.11 could be installed here (Ubuntu archive; the KiCad 8/9/10 package archive is blocked by the network policy). KiCad 8 and later open version 7 files and convert them on save. |
| DRC | `pcbnew.WriteDRCReport` from KiCad 7.0.11. | `kicad-cli pcb drc` only exists from KiCad 8. It is the same DRC engine as the GUI. Re-run DRC once in your own KiCad version. |
| Board size | 102 x 137 mm, console zone 50 mm deep. Unchanged from 0.1. | The BlackPill is 52.8 mm long and its USB-C port must face the back, so it has to sit lengthwise at the top edge. Its pin rows cannot run under the key field: they would hit the hotswap pads and the switch peg holes. |
| Key pitch | 19.05 mm, although Choc V1 allows 18 x 17 mm. | Keeps the outline, the mounting holes and the routing grid (pitch / 60). Choc caps up to 17.5 x 16.5 mm leave a 1.5 to 2.5 mm gap between keys. A tighter pitch would be a new layout. |
| BlackPill mounting | Under the board on low-profile socket strips (Mill-Max 315 socket and 335 header class, 3.94 mm board to board), **component side facing the main board**, centred, USB-C at the top edge. | Socketed as chosen. Turned this way the 3.26 mm USB-C receptacle sits in the gap between the boards instead of below the module, which saves about 3 mm of case height. The pin headers have to be soldered to the component side of the BlackPill. BOOT0 and NRST are then covered: flash once before plugging the module in, afterwards use the QMK bootloader keycode. |
| BlackPill socket length | 19 of 20 positions per row. Pads 20 (second 3V3) and 21 (VBAT) are not connected. | A 20-way strip would touch the hotswap sockets of K2 and K3. Cut the strips and headers to 19 positions. |
| Display | LCDwiki MSP1281 class module (carrier 38.03 x 45.80 mm, 1x8 header: GND, VCC, SCL, SDA, RES, DC, CS, BLK), lying rotated by 90° with the header as a north-south column on the west side, pin 1 north. Soldered on a pin header, carrier underside 2.5 mm above the board. | With the header across the board its pins would fall between the BlackPill socket rows. The picture is rotated in firmware. |
| Display bus | SPI2 (B13 SCK, B15 MOSI), B14 DC, B12 CS, A8 RST, B9 backlight (TIM4_CH4). | All on the BlackPill row next to the display header. The former I²C pins B6/B7 now carry the encoder (TIM4_CH1/CH2). |
| K13/K14 | On the 19.05 mm grid in x (under columns 2 and 3), 0.25u extra gap below row 3. | The sketch shows a blank line between the grid and the pair. |
| Matrix row 3 | encoder push, K13, K14, joystick push (columns 0 to 3). | Follows the physical left-to-right order. |
| MCU pins | See `pinout.yaml`. A9/A10 (USART1) are left free for the phase 2 BLE bridge. | |
| LED data pin | B5 (SPI1_MOSI / TIM3_CH2), through one gate of the 74AHCT125 and 330 Ω. ROW2 moved to A7. | Works with both QMK WS2812 drivers. Unused gates are disabled, inputs tied to GND. |
| LED chain order | K1 K2 K3 K4, K8 K7 K6 K5, K9 K10 K11 K12, K14 K13, then underglow UG1 to UG8 clockwise from bottom left. | Snake, shortest hops. |
| Underglow | 8 LEDs on the top side, shining down through the board. | Reverse-mount LEDs shine through their cut-out. The bottom case must be printed in a translucent material for the glow to be visible. |
| 100 nF count | 24: one per LED (22), one at the level shifter, one at the joystick supply. | Matches the 24 in `bom.md`. |
| Bulk capacitor | 220 µF polymer tantalum, EIA 7343, 3.1 mm tall, on the bottom side near K1. | A radial electrolytic no longer fits under the board. Inside the 220 to 470 µF range of the BOM. |
| Joystick | Parametric placeholder: 18 x 18 x 9 mm body, 1x6 header (VCC, GND, VRX, VRY, SW_A, SW_B), two locating holes. The body is taller than the case, so the top case has a 31 mm collar around it. | The FJH10K-S3D datasheet is unconfirmed. |
| Encoder and joystick position | 35.5 mm left and right of the centre line (was 32). | Room for the 45.8 mm display carrier between them. |
| Copper | 0.25 mm signal tracks, 0.5 mm for +5 V, vias 0.6/0.3 mm, GND poured on both layers with solid pad connections. | Within JLCPCB standard capabilities. Solid connections avoid starved thermal spokes; ground pins need a little more heat when soldering. |
| Design rules | Clearance 0.15 mm, edge clearance 0.3 mm, hole clearance 0.25 mm. The router keeps 0.2 mm. | |
| Routing | A small grid router in `scripts/router.py` (0.3175 mm grid, two layers). Every net is routed as tracks; the pours are extra. | Deterministic and reproducible. Not as tidy as hand routing. |
| Case fixing | Six M2 x 14 screws from below through standoff, PCB, 1.0 mm spacer (washer) and plate into 3 mm heat-set inserts in the top case. | One screw stack aligns all four layers on the same holes. The top case is only 4.6 mm high, hence the short inserts. |
| Plate | 1.2 mm (Choc), top 2.2 mm above the PCB, 13.8 mm cut-outs, 1.2 mm smaller than the PCB all round. | Leaves room for the alignment lip of the top case. The plate is cut away under the display carrier. |
| Key well | The top case has one T-shaped opening around the caps. | A per-key bezel would collide with the 15 mm switch housing. |
| Display window | 33 mm round window with a 0.7 mm rim over the edge of the panel, panel pocket from below. | The display sits just under the surface. |

## Assumptions to verify before ordering

- **Display module geometry.** Only the carrier size (38.03 x 45.80 mm), the 32.4 mm active diameter and the pin order are published values. The header position (2.2 mm from the short edge), the pin 1 end, the position of the panel on the carrier (centre 19 mm from the far edge), the panel diameter (35.6 mm) and thickness (1.8 mm) and the height of parts on the carrier underside are assumptions. Measure your module before ordering the board; other GC9A01 modules (for example the round Waveshare board) do not fit.
- **Display support.** The carrier is held only by its pin header and the rim of the top case. A foam pad under its free end may be needed.
- **Choc footprint** follows the kiswitch library footprint (socket pads 2.55 x 2.5 mm at -3.5/-6.0 and 8.5/-3.8 mm, holes 3.05, 3.45 and 1.9 mm). Check it against the Kailh drawings for PG1350 and CPG135001S30.
- **Choc heights** (plate top 2.2 mm, housing top 5.0 mm, 3 mm travel) are the commonly published values. The keycap is a generic 17.5 x 16.5 x 3.8 mm placeholder.
- **Low-profile socket strips.** 3.94 mm board to board is the Mill-Max figure for the 315 socket with the 335 header. The USB-C receptacle then has about 0.7 mm of air to the main board. Other sockets change the case height (`BP_STANDOFF` in `layout.py`).
- **GC9A01 in QMK.** The pin choice assumes the Quantum Painter GC9A01 driver on SPI2; this was not built.
- **SK6812 MINI-E footprint.** The pin functions (1 VDD, 2 DOUT, 3 GND, 4 DIN) match the OPSCO datasheet. Which corner each pin sits on, the pad size (1.3 x 0.85 mm at ±2.75/±0.75 mm) and the 3.4 x 2.8 mm window were not checked against the datasheet drawing.
- **BlackPill header order and outline** (52.81 x 20.78 mm, first pin 2.275 mm from the USB edge, connector overhang 1.0 mm) must be checked against your board revision.
- **EC11 mounting lugs** are round 2.3 mm plated holes; many parts want slots.
- **Pick-and-place rotations** in `positions.csv` are KiCad's values for script-made footprints. They are not matched to JLCPCB's rotation conventions.
- **LED current.** 22 LEDs can draw about 1.3 A at full white, more than the 0.5 mm supply track and a USB port should carry. The firmware brightness cap is required. The display backlight adds about 30 to 50 mA on the 3.3 V regulator of the BlackPill.

## Known gaps

- The schematic is a netlist-style sheet (parts with net labels, no drawn wires). It matches the board net for net, but ERC was not run.
- There is no footprint library on disk; footprints live in the board file. The DRC library-parity checks are switched off for that reason.
- BOOT0 and NRST of the BlackPill face the main board and cannot be reached once the module is plugged in.
- The enclosure was not reviewed for 3D-printing (supports, 0.7 mm display rim, insert bosses, tolerances) or moulding.
- All 3D part models are simple placeholders with nominal dimensions. Screws and inserts are not modelled.
- The copper pours leave an unfilled area between the BlackPill pin rows where signal tracks fence it in.

# SPDX-License-Identifier: Apache-2.0
"""Single source of truth for the opncap mechanical layout.

Both the PCB generator (gen_pcb.py) and the enclosure (enclosure/opncap_case.py)
import this module, so the board and the case cannot drift apart.

Board frame: millimetres, origin at the top-left corner of the PCB outline,
x to the right, y towards the front (KiCad convention, top view).
"""
import math

# ---------------------------------------------------------------- grid
P = 19.05                 # key pitch (1u). Choc V1 switches on the MX pitch, see DESIGN_NOTES.md
G = P / 60                # routing / placement grid = 0.3175 mm (12.5 mil)

# ---------------------------------------------------------------- board
BOARD_W = 96.0
BOARD_H = 127.2
BOARD_T = 1.6
CORNER_R = 3.0
TOP_ZONE = 44.0           # depth of the "console" zone (encoder / display / joystick)
PAIR_GAP = 0.0            # K13/K14 sit on the same pitch as the grid above them
BOTTOM_MARGIN = 7.0       # last key cell to the front board edge

KEY_X0 = (BOARD_W - 4 * P) / 2 + P / 2     # centre of column 0
KEY_Y0 = TOP_ZONE + P / 2                  # centre of row 0
CENTER_X = BOARD_W / 2


def snap_x(v):
    return KEY_X0 + round((v - KEY_X0) / G) * G


def snap_y(v):
    return KEY_Y0 + round((v - KEY_Y0) / G) * G


def snap(x, y):
    return (snap_x(x), snap_y(y))


# ---------------------------------------------------------------- keys
# name -> (x, y, matrix_row, matrix_col)
KEYS = {}
for _r in range(3):
    for _c in range(4):
        KEYS["K%d" % (_r * 4 + _c + 1)] = (KEY_X0 + _c * P, KEY_Y0 + _r * P, _r, _c)
PAIR_Y = KEY_Y0 + 3 * P + PAIR_GAP
KEYS["K13"] = (KEY_X0 + 1 * P, PAIR_Y, 3, 1)
KEYS["K14"] = (KEY_X0 + 2 * P, PAIR_Y, 3, 2)
KEY_ORDER = ["K%d" % i for i in range(1, 15)]

# Matrix positions of the two push switches (row 3 is K13, K14 and the pushes)
ENC_MATRIX = (3, 0)
JOY_MATRIX = (3, 3)

# LED chain: snake through the keys, then the 8 underglow LEDs.
# "STATUS" is the status light in the empty cell right of K14; it is LED 13 of the chain.
LED_KEY_CHAIN = ["K1", "K2", "K3", "K4", "K8", "K7", "K6", "K5",
                 "K9", "K10", "K11", "K12", "STATUS", "K14", "K13"]
STATUS_LED_INDEX = LED_KEY_CHAIN.index("STATUS") + 1
N_TOP_LEDS = len(LED_KEY_CHAIN)           # chain LEDs that shine upwards (keys + status)
# rotation (deg) of each per-key LED footprint so data flows along the snake
LED_KEY_ROT = {k: (0 if (k == "STATUS" or KEYS[k][2] in (1, 3)) else 180) for k in LED_KEY_CHAIN}
LED_KEY_OFFSET_Y = 4.7    # LED centre south of the switch centre (south-facing)
LED_CUTOUT = (3.4, 2.8)   # reverse-mount window for SK6812 MINI-E (under the Choc LED slot)
LED_CAP_DX = 5.3          # decoupling cap sits beside the LED, next to its VDD pad

# status light and microphone: the two free cells of the bottom row
STATUS_POS = (KEY_X0 + 3 * P, PAIR_Y)                     # LED centre = centre of the light window
MIC_CELL = (KEY_X0, PAIR_Y)
# Infineon IM69D130 (PG-LLGA-5-1) on the bottom side, sound port through the board.
# The footprint origin is shifted so that its small pads land on routing-grid columns.
MIC_PORT_DX = 0.68                                        # port from the footprint origin
MIC_POS = (snap_x(MIC_CELL[0]) + 0.68 - 1.47 + 4 * G, snap_y(MIC_CELL[1]))   # footprint origin (top view)
MIC_PORT = (MIC_POS[0] - MIC_PORT_DX, MIC_POS[1])         # port centre in the top view (x mirrored)
MIC_PORT_D = 0.8
MIC_CAP_POS = (MIC_POS[0] + 0.8 + 2 * G, MIC_POS[1] - 9 * G)


def led_chain_pos(name):
    if name == "STATUS":
        return STATUS_POS
    return (KEYS[name][0], KEYS[name][1] + LED_KEY_OFFSET_Y)


# underglow: (x, y, rotation), clockwise from the front left corner
UNDERGLOW = [
    snap(11.0, BOARD_H - 11.5) + (90,),
    snap(5.0, KEY_Y0 + 2.0 * P) + (90,),
    snap(5.0, KEY_Y0 + 0.5 * P) + (90,),
    snap(6.5, TOP_ZONE - 5.5) + (0,),
    snap(BOARD_W - 6.5, TOP_ZONE - 5.5) + (0,),
    snap(BOARD_W - 5.0, KEY_Y0 + 0.5 * P) + (270,),
    snap(BOARD_W - 5.0, KEY_Y0 + 2.0 * P) + (270,),
    snap(BOARD_W - 11.0, BOARD_H - 11.5) + (270,),
]

# ---------------------------------------------------------------- console zone
CONSOLE_Y = snap_y(22.0)
CONSOLE_DX = 36.0         # encoder / joystick centre distance from the board centre line
ENC_POS = (snap_x(CENTER_X - CONSOLE_DX), CONSOLE_Y)
JOY_POS = (snap_x(CENTER_X + CONSOLE_DX), CONSOLE_Y)

# Round display: 1.28" GC9A01 module with carrier board (LCDwiki MSP1281 class).
# The module lies rotated by 90 degrees: its 1x8 header is a north-south column on
# the west side, clear of the BlackPill pin rows under the board centre.
# Only the PCB size and the active diameter are from the published data; header
# inset, display position on the carrier and the heights are assumptions.
DISP_CENTER = (snap_x(CENTER_X), CONSOLE_Y)              # centre of the round display
DISP_PCB = (45.80, 38.03, 1.6)                           # carrier along x, along y, thickness
DISP_EAST = 19.0                                         # display centre to the far (east) carrier edge
DISP_HDR_INSET = 2.2                                     # header centre line to the west carrier edge
DISP_PCB_X1 = DISP_CENTER[0] + DISP_EAST - DISP_PCB[0]   # west carrier edge
DISP_PCB_X2 = DISP_CENTER[0] + DISP_EAST
DISP_HDR_POS = (snap_x(DISP_PCB_X1 + DISP_HDR_INSET), CONSOLE_Y)
DISP_ACTIVE_D = 32.4                                     # visible diameter
DISP_LCD_D = 35.6                                        # panel body diameter (approx.)
DISP_LCD_T = 1.8                                         # panel with backlight (approx.)
DISP_PCB_Z = 2.5          # underside of the carrier above the main PCB (soldered pin header)

# ---------------------------------------------------------------- BlackPill
# WeAct BlackPill F411 under the main PCB on low-profile socket strips, USB-C to the back.
# Its component side faces the main PCB, so the USB-C receptacle sits in the gap between
# the two boards instead of adding to the height.
BP_LEN = 52.81
BP_W = 20.78
BP_T = 1.6
BP_ROW_PITCH = 15.24
BP_ROW_PINS = 17                          # socketed positions per row, counted from the USB end
BP_PIN_INSET = 2.275                      # USB-end board edge to first pin centre
BP_PIN1_Y = KEY_Y0 - 161 * G              # first pin row (on the routing grid)
BP_CENTER = (CENTER_X, BP_PIN1_Y + 9.5 * 2.54)
BP_USB_EDGE_Y = BP_PIN1_Y - BP_PIN_INSET  # y of the module edge carrying USB-C
BP_STANDOFF = 3.94                        # board to board: Mill-Max 315 socket + 335 header (0.155 in)
BP_SOCKET_H = 2.11                        # socket strip above the main PCB surface
BP_TAIL = 0.8                             # solder joints / pin tails below the module
USB_C = (8.94, 7.35, 3.26)                # receptacle w, depth, h
USB_OVERHANG = 1.0                        # receptacle sticks out past the module edge
assert USB_C[2] + 0.5 <= BP_STANDOFF, "USB-C receptacle does not fit between the boards"

# ---------------------------------------------------------------- other parts
SHIFTER_POS = (snap_x(CENTER_X - 15.9), BP_PIN1_Y + 45 * G)
R_SERIES_POS = snap(CENTER_X - 21.0, 12.85)
C_SHIFTER_POS = snap(CENTER_X - 17.3, 7.7)
C_JOY_POS = snap(JOY_POS[0], JOY_POS[1] + 11.5)
BULK_POS = snap(CENTER_X - 18.0, 37.5)
BULK_CAP = (7.3, 4.3, 3.1)                # polymer tantalum, EIA 7343 (case D): l, w, max. height
DIODE_OFFSET = (7.3025, 0.3175)           # per-key diode centre from the key centre (23 G, 1 G)
ENC_DIODE_POS = snap(ENC_POS[0] - 4.0, ENC_POS[1] + 12.0)
JOY_DIODE_POS = snap(JOY_POS[0] - 6.0, JOY_POS[1] + 11.5)

# ---------------------------------------------------------------- mounting
MOUNT_DRILL = 2.2                         # M2 clearance
MOUNT_KEEPOUT_R = 2.7                     # spacer / standoff footprint on the copper
MOUNT_HOLES = [
    (4.5, 4.5), (BOARD_W - 4.5, 4.5),
    (4.5, KEY_Y0 + 1.0 * P), (BOARD_W - 4.5, KEY_Y0 + 1.0 * P),
    (4.5, BOARD_H - 4.5), (BOARD_W - 4.5, BOARD_H - 4.5),
]
# unscrewed PCB rests under the key field (at 4-key corner points)
SUPPORT_POSTS = [(CENTER_X, KEY_Y0 + 0.5 * P), (CENTER_X, KEY_Y0 + 1.5 * P)]

# ---------------------------------------------------------------- stack (z, PCB top = 0)
# Kailh Choc V1 (PG1350). Housing and plate numbers are the published nominal values;
# the keycap is a generic low-profile placeholder.
PLATE_T = 1.2                             # Choc plate: 1.2 mm
PLATE_TOP_Z = 2.2                         # plate top is 2.2 mm above PCB top
PLATE_CUTOUT = 13.8
SWITCH_BODY = 15.0                        # housing outline above the plate
SWITCH_TOP_Z = 5.0                        # top of the switch housing
SWITCH_TRAVEL = 3.0
STEM_TOP_Z = SWITCH_TOP_Z + 3.0
KEYCAP_H = 3.8                            # low-profile cap, approx.
KEYCAP_TOP_Z = STEM_TOP_Z + 1.6
KEYCAP_BOTTOM_Z = KEYCAP_TOP_Z - KEYCAP_H
KEYCAP_BASE = (17.5, 16.5)                # x, y
KEYCAP_TOP = (14.5, 13.5)
SOCKET_H = 1.8                            # Choc hotswap socket below the PCB
assert KEYCAP_BOTTOM_Z - SWITCH_TRAVEL > PLATE_TOP_Z, "pressed keycap would hit the plate"

assert abs(BOARD_H - (PAIR_Y + P / 2 + BOTTOM_MARGIN)) < 1e-6, "board height / key layout mismatch"


def rot_xy(x, y, deg):
    """Rotate like KiCad does in the top view (positive = counter-clockwise on screen)."""
    a = math.radians(deg)
    return (x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))

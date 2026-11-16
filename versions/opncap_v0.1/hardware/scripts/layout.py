# SPDX-License-Identifier: Apache-2.0
"""Single source of truth for the opncap mechanical layout.

Both the PCB generator (gen_pcb.py) and the enclosure (enclosure/opncap_case.py)
import this module, so the board and the case cannot drift apart.

Board frame: millimetres, origin at the top-left corner of the PCB outline,
x to the right, y towards the front (KiCad convention, top view).
"""
import math

# ---------------------------------------------------------------- grid
P = 19.05                 # MX key pitch (1u)
G = P / 60                # routing / placement grid = 0.3175 mm (12.5 mil)

# ---------------------------------------------------------------- board
BOARD_W = 102.0
BOARD_H = 137.0
BOARD_T = 1.6
CORNER_R = 3.0
TOP_ZONE = 50.0           # depth of the "console" zone (encoder / OLED / joystick)
PAIR_GAP = P / 4          # extra gap between the 3x4 grid and the K13/K14 pair

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
LED_KEY_CHAIN = ["K1", "K2", "K3", "K4", "K8", "K7", "K6", "K5",
                 "K9", "K10", "K11", "K12", "K14", "K13"]
# rotation (deg) of each per-key LED footprint so data flows along the snake
LED_KEY_ROT = {k: (0 if KEYS[k][2] in (1, 3) else 180) for k in LED_KEY_CHAIN}
LED_KEY_OFFSET_Y = 4.7    # LED centre south of the switch centre (south-facing)
LED_CUTOUT = (3.4, 2.8)   # reverse-mount window for SK6812 MINI-E
LED_CAP_DX = 5.3          # decoupling cap sits beside the LED, next to its VDD pad

# underglow: (x, y, rotation)
UNDERGLOW = [
    snap(10.0, 127.0) + (90,),
    snap(6.5, 93.0) + (90,),
    snap(6.5, 64.0) + (90,),
    snap(9.5, 44.5) + (0,),
    snap(92.5, 44.5) + (0,),
    snap(95.5, 64.0) + (270,),
    snap(95.5, 93.0) + (270,),
    snap(92.0, 127.0) + (270,),
]

# ---------------------------------------------------------------- console zone
CONSOLE_Y = snap_y(27.0)
ENC_POS = (snap_x(CENTER_X - 32.0), CONSOLE_Y)
JOY_POS = (snap_x(CENTER_X + 32.0), CONSOLE_Y)
OLED_HDR_POS = (snap_x(CENTER_X + 17.5), CONSOLE_Y)      # 1x4 header, east end
OLED_PCB = (38.0, 12.0, 1.2)                             # module PCB w, h, t
OLED_HDR_INSET = 1.5                                     # header centre to PCB edge
OLED_CENTER = (OLED_HDR_POS[0] - (OLED_PCB[0] / 2 - OLED_HDR_INSET), CONSOLE_Y)
OLED_ACTIVE = (22.4, 5.6)                                # visible area (approx.)
OLED_GLASS = (30.0, 11.5, 1.4)
OLED_PCB_Z = 7.5          # underside of module PCB above main PCB top (5 mm socket + 2.5 mm header)

# ---------------------------------------------------------------- BlackPill
# WeAct BlackPill F411, mounted upside-down on the bottom side, USB-C to the back.
BP_LEN = 52.81
BP_W = 20.78
BP_T = 1.6
BP_ROW_PITCH = 15.24
BP_PIN_INSET = 2.275                      # USB-end board edge to first pin centre
BP_PIN1_Y = KEY_Y0 - 180 * G              # first pin row (on the routing grid)
BP_CENTER = (CENTER_X, BP_PIN1_Y + 9.5 * 2.54)
BP_USB_EDGE_Y = BP_PIN1_Y - BP_PIN_INSET  # y of the module edge carrying USB-C
BP_STANDOFF = 2.5                         # pin header plastic between the two boards
USB_C = (8.94, 7.35, 3.26)                # receptacle w, depth, h
USB_OVERHANG = 1.0                        # receptacle sticks out past the module edge

# ---------------------------------------------------------------- other parts
SHIFTER_POS = (snap_x(CENTER_X - 14.6), BP_PIN1_Y + 37 * G)
R_SERIES_POS = snap(30.0, 12.85)
C_SHIFTER_POS = snap(33.7, 7.7)
C_JOY_POS = snap(JOY_POS[0], JOY_POS[1] + 11.5)
BULK_POS = snap(31.5, 42.0)
BULK_CAP = (6.3, 8.0)                     # diameter, height (placeholder; max 11 mm fits)
DIODE_OFFSET = (7.3025, 0.3175)           # per-key diode centre from the key centre (23 G, 1 G)
ENC_DIODE_POS = snap(ENC_POS[0] - 4.0, ENC_POS[1] + 12.0)
JOY_DIODE_POS = snap(JOY_POS[0] - 6.0, JOY_POS[1] + 11.5)

# ---------------------------------------------------------------- mounting
MOUNT_DRILL = 2.2                         # M2 clearance
MOUNT_KEEPOUT_R = 2.7                     # spacer / standoff footprint on the copper
MOUNT_HOLES = [
    (5.5, 5.5), (BOARD_W - 5.5, 5.5),
    (5.5, KEY_Y0 + P), (BOARD_W - 5.5, KEY_Y0 + P),
    (KEY_X0, PAIR_Y), (KEY_X0 + 3 * P, PAIR_Y),
]
# unscrewed PCB rests under the key field (at 4-key corner points)
SUPPORT_POSTS = [(CENTER_X, KEY_Y0 + 0.5 * P), (CENTER_X, KEY_Y0 + 1.5 * P)]

# ---------------------------------------------------------------- stack (z, PCB top = 0)
PLATE_T = 1.5
PLATE_TOP_Z = 5.0                         # MX: plate top is 5.0 mm above PCB top
PLATE_CUTOUT = 14.0
SWITCH_TOP_Z = PLATE_TOP_Z + 6.6          # top of the switch housing
STEM_TOP_Z = SWITCH_TOP_Z + 3.6
KEYCAP_BOTTOM_Z = SWITCH_TOP_Z + 0.4
KEYCAP_H = 7.4                            # DSA-like
KEYCAP_BASE = 18.3
KEYCAP_TOP = 12.7
SOCKET_H = 1.8                            # hotswap socket below the PCB

assert abs(BOARD_H - (PAIR_Y + P / 2 + 6.0375)) < 1e-6, "board height / key layout mismatch"


def rot_xy(x, y, deg):
    """Rotate like KiCad does in the top view (positive = counter-clockwise on screen)."""
    a = math.radians(deg)
    return (x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))

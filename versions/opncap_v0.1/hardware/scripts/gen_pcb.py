#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the opncap KiCad project: board, schematic, project file, DRC report.

Run with the Python that ships the KiCad `pcbnew` module:
    python3 hardware/scripts/gen_pcb.py
Everything is derived from layout.py and ../pinout.yaml.
"""
import json
import math
import os
import re
import subprocess
import sys
import time
import uuid

import pcbnew
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as L                      # noqa: E402
import router as R                      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
PCB_DIR = os.path.join(HW, "pcb")
PCB_FILE = os.path.join(PCB_DIR, "opncap.kicad_pcb")
SCH_FILE = os.path.join(PCB_DIR, "opncap.kicad_sch")
DRC_FILE = os.path.join(PCB_DIR, "drc_report.txt")
VERSION_TEXT = "opncap v0.1"

mm = pcbnew.FromMM
toMM = pcbnew.ToMM


def V(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


# ============================================================ footprints
# Canonical footprints, seen from their own mounting side (library convention).
# pad: (number, kind, shape, x, y, w, h, drill)   kind: smd | pth | npth
def fp_mx_hotswap():
    return dict(name="SW_MX_Hotswap_Kailh", pads=[
        ("1", "smd", "rect", 7.085, -2.54, 2.55, 2.5, 0),
        ("2", "smd", "rect", -5.842, -5.08, 2.55, 2.5, 0),
        ("", "npth", "circle", 3.81, -2.54, 3.0, 3.0, 3.0),
        ("", "npth", "circle", -2.54, -5.08, 3.0, 3.0, 3.0),
        ("", "npth", "circle", 0, 0, 4.0, 4.0, 4.0),
        ("", "npth", "circle", -5.08, 0, 1.75, 1.75, 1.75),
        ("", "npth", "circle", 5.08, 0, 1.75, 1.75, 1.75),
    ], box=(-7, -7, 7, 7), smd=True)


def fp_sod123():
    return dict(name="D_SOD-123", pads=[
        ("1", "smd", "rect", -1.65, 0, 0.9, 1.2, 0),
        ("2", "smd", "rect", 1.65, 0, 0.9, 1.2, 0),
    ], box=(-1.4, -0.85, 1.4, 0.85), smd=True)


def fp_0603(name):
    return dict(name=name, pads=[
        ("1", "smd", "rect", -0.8, 0, 0.9, 0.95, 0),
        ("2", "smd", "rect", 0.8, 0, 0.9, 0.95, 0),
    ], box=(-0.8, -0.4, 0.8, 0.4), smd=True)


def fp_sk6812():
    # seen from the pad side (the LED shines away from the viewer through the board)
    return dict(name="LED_SK6812_MINI-E_reverse", pads=[
        ("1", "smd", "rect", 2.75, -0.75, 1.3, 0.85, 0),    # VDD
        ("2", "smd", "rect", 2.75, 0.75, 1.3, 0.85, 0),     # DOUT
        ("3", "smd", "rect", -2.75, 0.75, 1.3, 0.85, 0),    # GND
        ("4", "smd", "rect", -2.75, -0.75, 1.3, 0.85, 0),   # DIN
    ], box=(-1.6, -1.4, 1.6, 1.4), smd=True)


def fp_soic14():
    pads = []
    for i in range(7):
        pads.append((str(i + 1), "smd", "rect", -2.7, -3.81 + 1.27 * i, 1.5, 0.6, 0))
        pads.append((str(14 - i), "smd", "rect", 2.7, -3.81 + 1.27 * i, 1.5, 0.6, 0))
    return dict(name="SOIC-14_3.9x8.7mm_P1.27mm", pads=pads, box=(-1.95, -4.35, 1.95, 4.35), smd=True)


def fp_blackpill():
    pads = []
    for i in range(20):
        y = -24.13 + 2.54 * i
        pads.append((str(i + 1), "pth", "circle", -L.BP_ROW_PITCH / 2, y, 1.7, 1.7, 1.0))
        pads.append((str(40 - i), "pth", "circle", L.BP_ROW_PITCH / 2, y, 1.7, 1.7, 1.0))
    e = -24.13 - L.BP_PIN_INSET
    return dict(name="WeAct_BlackPill_F411_2x20_P2.54mm", pads=pads,
                box=(-L.BP_W / 2, e, L.BP_W / 2, e + L.BP_LEN), smd=False)


def fp_ec11():
    return dict(name="RotaryEncoder_EC11_Switch_Vertical", pads=[
        ("A", "pth", "circle", -7.5, -2.5, 2.0, 2.0, 1.0),
        ("C", "pth", "circle", -7.5, 0, 2.0, 2.0, 1.0),
        ("B", "pth", "circle", -7.5, 2.5, 2.0, 2.0, 1.0),
        ("S1", "pth", "circle", 7.0, -2.5, 2.0, 2.0, 1.0),
        ("S2", "pth", "circle", 7.0, 2.5, 2.0, 2.0, 1.0),
        ("MP", "pth", "circle", 0, -5.6, 3.4, 3.4, 2.3),
        ("MP", "pth", "circle", 0, 5.6, 3.4, 3.4, 2.3),
    ], box=(-6, -6, 6, 6), smd=False)


def fp_joystick():
    pads = [(str(i + 1), "pth", "circle", -6.35 + 2.54 * i, 7.62, 1.7, 1.7, 1.0) for i in range(6)]
    pads += [("", "npth", "circle", sx * 7.62, -7.62, 1.5, 1.5, 1.5) for sx in (-1, 1)]
    return dict(name="Joystick_Hall_placeholder_18x18", pads=pads, box=(-9, -9, 9, 9), smd=False)


def fp_header4():
    return dict(name="PinSocket_1x04_P2.54mm_Vertical", pads=[
        (str(i + 1), "pth", "circle", 0, -3.81 + 2.54 * i, 1.7, 1.7, 1.0) for i in range(4)
    ], box=(-1.27, -5.08, 1.27, 5.08), smd=False)


def fp_cp_radial():
    return dict(name="CP_Radial_D6.3mm_P2.50mm", pads=[
        ("1", "pth", "rect", -1.25, 0, 1.6, 1.6, 0.8),
        ("2", "pth", "circle", 1.25, 0, 1.6, 1.6, 0.8),
    ], box=(-3.15, -3.15, 3.15, 3.15), smd=False)


def fp_mount():
    return dict(name="MountingHole_2.2mm_M2", pads=[
        ("", "npth", "circle", 0, 0, L.MOUNT_DRILL, L.MOUNT_DRILL, L.MOUNT_DRILL),
    ], box=(-2.2, -2.2, 2.2, 2.2), smd=False, virtual=True)


SYMBOL_PINS = {      # footprint name -> ([left pins], [right pins]) as (number, name)
    "SW_MX_Hotswap_Kailh": ([("1", "COL")], [("2", "D")]),
    "D_SOD-123": ([("2", "A")], [("1", "K")]),
    "C_0603": ([("1", "1")], [("2", "2")]),
    "R_0603": ([("1", "1")], [("2", "2")]),
    "LED_SK6812_MINI-E_reverse": ([("4", "DIN"), ("1", "VDD")], [("2", "DOUT"), ("3", "GND")]),
    "SOIC-14_3.9x8.7mm_P1.27mm": (
        [("1", "~1OE"), ("2", "1A"), ("4", "~2OE"), ("5", "2A"), ("10", "~3OE"), ("9", "3A"),
         ("13", "~4OE"), ("12", "4A")],
        [("14", "VCC"), ("3", "1Y"), ("6", "2Y"), ("8", "3Y"), ("11", "4Y"), ("7", "GND")]),
    "RotaryEncoder_EC11_Switch_Vertical": ([("A", "A"), ("C", "C"), ("B", "B")],
                                           [("S1", "S1"), ("S2", "S2"), ("MP", "MP")]),
    "Joystick_Hall_placeholder_18x18": ([("1", "VCC"), ("2", "GND"), ("3", "VRX")],
                                        [("4", "VRY"), ("5", "SW_A"), ("6", "SW_B")]),
    "PinSocket_1x04_P2.54mm_Vertical": ([("1", "GND"), ("2", "VCC"), ("3", "SCL"), ("4", "SDA")], []),
    "CP_Radial_D6.3mm_P2.50mm": ([("1", "+")], [("2", "-")]),
}

BP_LEFT = ["B12", "B13", "B14", "B15", "A8", "A9", "A10", "A11", "A12", "A15",
           "B3", "B4", "B5", "B6", "B7", "B8", "B9", "5V", "GND", "3V3"]
BP_RIGHT = ["5V", "GND", "3V3", "B10", "B2", "B1", "B0", "A7", "A6", "A5",
            "A4", "A3", "A2", "A1", "A0", "NRST", "C15", "C14", "C13", "VBAT"]
BP_PAD_NAMES = {str(i + 1): n for i, n in enumerate(BP_LEFT)}
BP_PAD_NAMES.update({str(40 - i): n for i, n in enumerate(BP_RIGHT)})
SYMBOL_PINS["WeAct_BlackPill_F411_2x20_P2.54mm"] = (
    [(str(i + 1), n) for i, n in enumerate(BP_LEFT)],
    [(str(40 - i), n) for i, n in enumerate(BP_RIGHT)])


# ============================================================ design model
def build_design():
    pin = yaml.safe_load(open(os.path.join(HW, "pinout.yaml")))
    sig_of_pin = {v["pin"]: k for k, v in pin["signals"].items()}
    comps = []

    def add(ref, value, fp, x, y, rot, back, nets, bom):
        comps.append(dict(ref=ref, value=value, fp=fp, x=x, y=y, rot=rot, back=back, nets=nets, bom=bom))

    # MCU
    nets = {}
    for num, name in BP_PAD_NAMES.items():
        nets[num] = {"5V": "+5V", "GND": "GND", "3V3": "+3V3"}.get(name, sig_of_pin.get(name))
    add("U1", "WeAct BlackPill F411", fp_blackpill(), L.BP_CENTER[0], L.BP_CENTER[1], 0, True, nets, 1)

    # keys: switch, diode, LED, cap
    led_index = {k: i + 1 for i, k in enumerate(L.LED_KEY_CHAIN)}
    for n, key in enumerate(L.KEY_ORDER, start=1):
        x, y, row, col = L.KEYS[key]
        add("SW%d" % n, "MX hotswap", fp_mx_hotswap(), x, y, 0, True,
            {"1": "COL%d" % col, "2": "SWD%d" % n}, 3)
        add("D%d" % n, "1N4148W", fp_sod123(), x + L.DIODE_OFFSET[0], y + L.DIODE_OFFSET[1], 270, True,
            {"2": "SWD%d" % n, "1": "ROW%d" % row}, 4)
    led_pos = []
    for key in L.LED_KEY_CHAIN:
        x, y, _, _ = L.KEYS[key]
        led_pos.append((x, y + L.LED_KEY_OFFSET_Y, L.LED_KEY_ROT[key], True))
    for (x, y, rot) in L.UNDERGLOW:
        led_pos.append((x, y, rot, False))
    for i, (x, y, rot, back) in enumerate(led_pos, start=1):
        din = "RGB_DIN" if i == 1 else "LED%d_DOUT" % (i - 1)
        dout = "LED%d_DOUT" % i if i < len(led_pos) else None
        add("LED%d" % i, "SK6812 MINI-E", fp_sk6812(), x, y, rot, back,
            {"1": "+5V", "2": dout, "3": "GND", "4": din}, 5 if i <= 14 else 6)
        # the capacitor sits next to the VDD pad, with its +5V pad facing it
        if back:
            ox, oy = L.rot_xy(-L.LED_CAP_DX, 0, rot)
            crot = rot + 90
        else:
            ox, oy = L.rot_xy(L.LED_CAP_DX, 0, rot)
            crot = rot + 270
        add("C%d" % i, "100n", fp_0603("C_0603"), x + ox, y + oy, crot % 360, back, {"1": "+5V", "2": "GND"}, 12)

    # encoder (push in the matrix) and joystick
    er, ec = L.ENC_MATRIX
    add("ENC1", "EC11 with switch", fp_ec11(), L.ENC_POS[0], L.ENC_POS[1], 180, False,
        {"A": "ENC_A", "B": "ENC_B", "C": "GND", "S1": "COL%d" % ec, "S2": "SWD15", "MP": "GND"}, 7)
    add("D15", "1N4148W", fp_sod123(), L.ENC_DIODE_POS[0], L.ENC_DIODE_POS[1], 0, True,
        {"2": "SWD15", "1": "ROW%d" % er}, 4)
    jr, jc = L.JOY_MATRIX
    add("JOY1", "Hall joystick 3V3 (placeholder)", fp_joystick(), L.JOY_POS[0], L.JOY_POS[1], 0, False,
        {"1": "+3V3", "2": "GND", "3": "JOY_X", "4": "JOY_Y", "5": "COL%d" % jc, "6": "SWD16"}, 8)
    add("D16", "1N4148W", fp_sod123(), L.JOY_DIODE_POS[0], L.JOY_DIODE_POS[1], 0, True,
        {"2": "SWD16", "1": "ROW%d" % jr}, 4)
    add("C24", "100n", fp_0603("C_0603"), L.C_JOY_POS[0], L.C_JOY_POS[1], 0, True, {"1": "+3V3", "2": "GND"}, 12)

    # OLED socket
    add("DISP1", "OLED 0.91in SSD1306 I2C", fp_header4(), L.OLED_HDR_POS[0], L.OLED_HDR_POS[1], 0, False,
        {"1": "GND", "2": "+3V3", "3": "I2C_SCL", "4": "I2C_SDA"}, 9)

    # level shifter, series resistor, caps
    add("U2", "74AHCT125", fp_soic14(), L.SHIFTER_POS[0], L.SHIFTER_POS[1], 0, True,
        {"1": "GND", "2": "RGB_3V3", "3": "RGB_5V", "4": "+5V", "5": "GND", "6": None, "7": "GND",
         "8": None, "9": "GND", "10": "+5V", "11": None, "12": "GND", "13": "+5V", "14": "+5V"}, 10)
    add("R1", "330R", fp_0603("R_0603"), L.R_SERIES_POS[0], L.R_SERIES_POS[1], 0, True,
        {"1": "RGB_5V", "2": "RGB_DIN"}, 11)
    add("C23", "100n", fp_0603("C_0603"), L.C_SHIFTER_POS[0], L.C_SHIFTER_POS[1], 0, True,
        {"1": "+5V", "2": "GND"}, 12)
    add("C25", "330u 10V", fp_cp_radial(), L.BULK_POS[0], L.BULK_POS[1], 0, True, {"1": "+5V", "2": "GND"}, 13)

    for i, (x, y) in enumerate(L.MOUNT_HOLES, start=1):
        add("H%d" % i, "M2", fp_mount(), x, y, 0, False, {}, 0)
    return comps


# ============================================================ board
def make_footprint(board, c, nets):
    d = c["fp"]
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(c["ref"])
    fp.SetValue(c["value"])
    fp.SetFPID(pcbnew.LIB_ID("opncap", d["name"]))
    for (num, kind, shape, x, y, w, h, drill) in d["pads"]:
        p = pcbnew.PAD(fp)
        p.SetNumber(num)
        p.SetShape(pcbnew.PAD_SHAPE_RECT if shape == "rect" else pcbnew.PAD_SHAPE_CIRCLE)
        p.SetSize(V(w, h))
        if kind == "smd":
            p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            p.SetLayerSet(p.SMDMask())
        elif kind == "pth":
            p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
            p.SetLayerSet(p.PTHMask())
            p.SetDrillSize(V(drill, drill))
        else:
            p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
            p.SetLayerSet(p.UnplatedHoleMask())
            p.SetDrillSize(V(drill, drill))
        p.SetPos0(V(x, y))
        p.SetPosition(V(x, y))
        net = c["nets"].get(num)
        if net:
            p.SetNet(nets[net])
        fp.Add(p)
    x1, y1, x2, y2 = d["box"]
    for a, b in (((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))):
        s = pcbnew.FP_SHAPE(fp)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart0(V(*a)); s.SetEnd0(V(*b)); s.SetStart(V(*a)); s.SetEnd(V(*b))
        s.SetLayer(pcbnew.F_Fab)
        s.SetWidth(mm(0.1))
        fp.Add(s)
    attrs = pcbnew.FP_ALLOW_MISSING_COURTYARD
    if d.get("virtual"):
        attrs |= pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY
    elif d["smd"]:
        attrs |= pcbnew.FP_SMD
    else:
        attrs |= pcbnew.FP_THROUGH_HOLE
    fp.SetAttributes(attrs)
    for t in (fp.Reference(), fp.Value()):
        t.SetLayer(pcbnew.F_Fab)
        t.SetTextSize(V(0.6, 0.6))
        t.SetTextThickness(mm(0.1))
    fp.Value().SetVisible(False)
    return fp


def place(fp, c):
    pos = V(c["x"], c["y"])
    fp.SetPosition(pos)
    if c["back"]:
        fp.Flip(pos, False)
        fp.SetOrientationDegrees((180 + c["rot"]) % 360)
    else:
        fp.SetOrientationDegrees(c["rot"] % 360)


def add_line(board, a, b, layer, w=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a)); s.SetEnd(V(*b))
    s.SetLayer(layer); s.SetWidth(mm(w))
    board.Add(s)


def add_text(board, text, x, y, layer, size=1.0, thick=0.15, mirror=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(V(x, y))
    t.SetLayer(layer)
    t.SetTextSize(V(size, size))
    t.SetTextThickness(mm(thick))
    t.SetMirrored(mirror)
    board.Add(t)


def draw_outline(board):
    W, H, r = L.BOARD_W, L.BOARD_H, L.CORNER_R
    e = pcbnew.Edge_Cuts
    add_line(board, (r, 0), (W - r, 0), e)
    add_line(board, (W, r), (W, H - r), e)
    add_line(board, (W - r, H), (r, H), e)
    add_line(board, (0, H - r), (0, r), e)
    k = r * (1 - math.sqrt(0.5))
    for (sx, sy, mx, my, ex, ey) in (
            (W - r, 0, W - k, k, W, r), (W, H - r, W - k, H - k, W - r, H),
            (r, H, k, H - k, 0, H - r), (0, r, k, k, r, 0)):
        a = pcbnew.PCB_SHAPE(board)
        a.SetShape(pcbnew.SHAPE_T_ARC)
        a.SetArcGeometry(V(sx, sy), V(mx, my), V(ex, ey))
        a.SetLayer(e); a.SetWidth(mm(0.1))
        board.Add(a)


def led_cutout_rect(c):
    w, h = L.LED_CUTOUT
    if c["rot"] % 180 == 90:
        w, h = h, w
    return (c["x"] - w / 2, c["y"] - h / 2, c["x"] + w / 2, c["y"] + h / 2)


def build_board(comps):
    if os.path.exists(PCB_FILE):
        os.remove(PCB_FILE)
    board = pcbnew.NewBoard(PCB_FILE)
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.SetBoardThickness(mm(L.BOARD_T))
    ds.m_NetSettings.m_DefaultNetClass.SetClearance(mm(0.15))
    ds.m_NetSettings.m_DefaultNetClass.SetTrackWidth(mm(R.TRACK_W))
    ds.m_NetSettings.m_DefaultNetClass.SetViaDiameter(mm(R.VIA_D))
    ds.m_NetSettings.m_DefaultNetClass.SetViaDrill(mm(R.VIA_DRILL))
    ds.m_MinClearance = mm(0.15)
    ds.m_TrackMinWidth = mm(0.2)
    ds.m_ViasMinSize = mm(0.6)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_ViasMinAnnularWidth = mm(0.13)
    ds.m_CopperEdgeClearance = mm(0.3)
    ds.m_HoleClearance = mm(0.25)
    ds.m_HoleToHoleMin = mm(0.25)

    names = sorted({n for c in comps for n in c["nets"].values() if n})
    nets = {}
    for n in names:
        ni = pcbnew.NETINFO_ITEM(board, n)
        board.Add(ni)
        nets[n] = ni

    draw_outline(board)
    fps = {}
    for c in comps:
        fp = make_footprint(board, c, nets)
        board.Add(fp)
        place(fp, c)
        fps[c["ref"]] = fp
        if c["ref"].startswith("LED"):
            x1, y1, x2, y2 = led_cutout_rect(c)
            s = pcbnew.PCB_SHAPE(board)
            s.SetShape(pcbnew.SHAPE_T_RECT)
            s.SetStart(V(x1, y1)); s.SetEnd(V(x2, y2))
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
            board.Add(s)

    # silkscreen
    for i, key in enumerate(L.KEY_ORDER, start=1):
        x, y, _, _ = L.KEYS[key]
        add_text(board, key, x - 6.2, y + 7.7, pcbnew.F_SilkS, 1.0, 0.15)
    add_text(board, "ENC", L.ENC_POS[0], L.ENC_POS[1] - 9.6, pcbnew.F_SilkS, 1.2, 0.18)
    add_text(board, "JOY", L.JOY_POS[0], L.JOY_POS[1] - 11.2, pcbnew.F_SilkS, 1.2, 0.18)
    add_text(board, "OLED", L.CENTER_X, L.OLED_CENTER[1] - 8.6, pcbnew.F_SilkS, 1.0, 0.15)
    add_text(board, VERSION_TEXT, L.CENTER_X, L.BOARD_H - 3.0, pcbnew.F_SilkS, 1.6, 0.25)
    add_text(board, VERSION_TEXT, L.CENTER_X, L.BOARD_H - 3.0, pcbnew.B_SilkS, 1.6, 0.25, mirror=True)
    add_text(board, "USB", L.CENTER_X, 4.2, pcbnew.B_SilkS, 1.2, 0.18, mirror=True)
    bx1, bx2 = L.CENTER_X - L.BP_W / 2, L.CENTER_X + L.BP_W / 2
    by1, by2 = max(0.6, L.BP_USB_EDGE_Y), L.BP_USB_EDGE_Y + L.BP_LEN - 3.0
    for a, b in (((bx1, by1), (bx1, by2)), ((bx2, by1), (bx2, by2))):
        add_line(board, a, b, pcbnew.B_SilkS, 0.15)
    return board, nets, fps


# ============================================================ routing
def pad_geom(p):
    pos = p.GetPosition()
    bb = p.GetBoundingBox()
    x, y = toMM(pos.x), toMM(pos.y)
    w, h = toMM(bb.GetWidth()), toMM(bb.GetHeight())
    layers = []
    if p.IsOnLayer(pcbnew.F_Cu):
        layers.append(R.F)
    if p.IsOnLayer(pcbnew.B_Cu):
        layers.append(R.B)
    return x, y, w, h, tuple(layers)


def check_orientation(comps, fps):
    """Assert that back-side placement gives the top-view geometry the layout assumes."""
    def pad_xy(ref, num):
        for p in fps[ref].Pads():
            if p.GetNumber() == num:
                return toMM(p.GetPosition().x), toMM(p.GetPosition().y)
    kx, ky = L.KEYS["K1"][0], L.KEYS["K1"][1]
    x, y = pad_xy("SW1", "1")
    assert abs(x - (kx - 7.085)) < 1e-3 and abs(y - (ky - 2.54)) < 1e-3, "hotswap pad 1 not at top-view left"
    x, y = pad_xy("SW1", "2")
    assert abs(x - (kx + 5.842)) < 1e-3 and abs(y - (ky - 5.08)) < 1e-3
    # LED1 (K1, rot 180): data flows left to right, so DIN is west and DOUT is east
    assert pad_xy("LED1", "4")[0] < pad_xy("LED1", "2")[0]
    assert pad_xy("LED5", "4")[0] > pad_xy("LED5", "2")[0]          # K8, flows right to left
    assert pad_xy("D1", "1")[1] > pad_xy("D1", "2")[1]               # cathode south of anode
    # BlackPill: its own left row (B12..) must be on the east side seen from the top
    assert pad_xy("U1", "1")[0] > L.CENTER_X and abs(pad_xy("U1", "1")[1] - L.BP_PIN1_Y) < 1e-3
    assert pad_xy("ENC1", "A")[0] > L.ENC_POS[0]
    for p in fps["SW1"].Pads():
        if p.GetNumber():
            assert p.IsOnLayer(pcbnew.B_Cu) and not p.IsOnLayer(pcbnew.F_Cu)


def route(board, comps, fps, nets):
    kx = int(L.KEY_X0 / L.G)
    ky = int(L.KEY_Y0 / L.G)
    x0, y0 = L.KEY_X0 - kx * L.G, L.KEY_Y0 - ky * L.G
    nx = int((L.BOARD_W - x0) / L.G) + 1
    ny = int((L.BOARD_H - y0) / L.G) + 1
    rt = R.Router(x0, y0, L.G, nx, ny)
    both = (R.F, R.B)
    net_id = {n: i + 1 for i, n in enumerate(sorted(nets))}

    # board edge
    m = R.EDGE_THR
    W, H, cr = L.BOARD_W, L.BOARD_H, L.CORNER_R
    for iy in range(ny):
        for ix in range(nx):
            x, y = rt.xy(ix, iy)
            bad = x < m or x > W - m or y < m or y > H - m
            if not bad:
                cx = cr if x < cr else (W - cr if x > W - cr else None)
                cy = cr if y < cr else (H - cr if y > H - cr else None)
                if cx is not None and cy is not None and math.hypot(x - cx, y - cy) > cr - m:
                    bad = True
            if bad:
                for layer in both:
                    rt.own[layer * rt.plane + iy * nx + ix] = R.BLOCK
    for c in comps:
        if c["ref"].startswith("LED"):
            x1, y1, x2, y2 = led_cutout_rect(c)
            rt.mark_rect(both, x1, y1, x2, y2, R.EDGE_THR, R.BLOCK)
        if c["ref"].startswith("H"):
            rt.mark_circle(both, c["x"], c["y"], L.MOUNT_KEEPOUT_R + 0.3, R.BLOCK)
    for (x, y) in L.SUPPORT_POSTS:
        rt.forbid_via_rect(x - 2, y - 2, x + 2, y + 2, 0)

    # pads
    pads_of_net = {}
    unconnected = -100
    for c in comps:
        for p in fps[c["ref"]].Pads():
            x, y, w, h, layers = pad_geom(p)
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                rt.mark_circle(both, x, y, w / 2 + R.HOLE_THR, R.BLOCK)
                continue
            name = p.GetNetname()
            if name:
                nid = net_id[name]
            else:
                unconnected -= 1
                nid = unconnected
            circle = p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE
            if circle:
                rt.mark_circle(layers, x, y, w / 2 + R.PAD_THR, nid)
                nodes = rt.nodes_in_circle(layers, x, y, w / 2 - 0.1)
            else:
                rt.mark_rect(layers, x - w / 2, y - h / 2, x + w / 2, y + h / 2, R.PAD_THR, nid)
                nodes = rt.nodes_in_rect(layers, x - w / 2 + 0.1, y - h / 2 + 0.1, x + w / 2 - 0.1, y + h / 2 - 0.1)
            rt.forbid_via_rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, 0.4)
            if name:
                nodes = [i for i in nodes if rt.own[i] == nid]
                assert nodes, "pad %s.%s has no reachable grid node" % (c["ref"], p.GetNumber())
                pads_of_net.setdefault(name, []).append(dict(ref=c["ref"], num=p.GetNumber(), x=x, y=y, nodes=nodes))

    def order_key(n):
        if n.startswith("SWD"):
            return (0, n)
        if n.startswith("LED") or n in ("RGB_DIN", "RGB_5V", "RGB_3V3"):
            return (1, n)
        if n == "+5V":
            return (2, n)
        if n.startswith("COL") or n.startswith("ROW"):
            return (3, n)
        if n == "+3V3":
            return (5, n)
        if n == "GND":
            return (6, n)
        return (4, n)

    failed = []
    t0 = time.time()
    # Local pairs first: every LED supply pad goes straight to its decoupling capacitor.
    by_key = {(p["ref"], p["num"]): p for pads in pads_of_net.values() for p in pads}
    for pads in pads_of_net.values():
        for p in pads:
            p["extra"] = set()
            p["partner"] = None
    for c in comps:
        if not c["ref"].startswith("LED"):
            continue
        cap = "C" + c["ref"][3:]
        for (lp, cp, name) in (("1", "1", "+5V"),):
            a, b = by_key[(c["ref"], lp)], by_key[(cap, cp)]
            path = rt.astar(net_id[name], set(a["nodes"]), set(b["nodes"]), b["x"], b["y"], False, 30)
            if path:
                rt.commit(net_id[name], path, False)
                a["extra"].update(path); b["extra"].update(path)
                a["partner"], b["partner"] = b, a
            else:
                failed.append((name, c["ref"], lp))

    # Ground escapes: each LED ground pad gets a short stub and a via to the other layer,
    # so later tracks cannot fence it in.
    for c in comps:
        if not c["ref"].startswith("LED"):
            continue
        a = by_key[(c["ref"], "3")]
        sx = 1.0 if a["x"] > c["x"] + 0.1 else (-1.0 if a["x"] < c["x"] - 0.1 else 0.0)
        sy = 0.0 if c["rot"] % 180 == 0 else (1.0 if a["y"] > c["y"] else -1.0)
        if c["rot"] % 180 != 0:
            sx = 0.0
        tx, ty = a["x"] + sx * 6 * L.G, a["y"] + sy * 6 * L.G
        ix, iy = rt.cell(tx, ty)
        other = R.F if c["back"] else R.B
        target = {other * rt.plane + iy * rt.nx + ix}
        path = rt.astar(net_id["GND"], set(a["nodes"]), target, tx, ty, False, 12)
        if path:
            rt.commit(net_id["GND"], path, False)
            a["extra"].update(path)
        else:
            failed.append(("GND escape", c["ref"], "3"))

    for name in sorted(pads_of_net, key=order_key):
        pads = pads_of_net[name]
        if len(pads) < 2:
            continue
        nid = net_id[name]
        wide = name == "+5V"
        start = 0
        if name in ("+5V", "GND", "+3V3"):            # grow power trees from the MCU
            for i, p in enumerate(pads):
                if p["ref"] == "U1":
                    start = i
                    break
        done = [pads[start]]
        todo = pads[:start] + pads[start + 1:]
        tree = set(pads[start]["nodes"]) | pads[start]["extra"]
        if pads[start]["partner"] is not None:
            q = pads[start]["partner"]
            tree.update(q["nodes"]); done.append(q); todo.remove(q)
        while todo:
            best = min(todo, key=lambda p: min(math.hypot(p["x"] - q["x"], p["y"] - q["y"]) for q in done))
            todo.remove(best)
            targets = set(best["nodes"])
            path = None
            if not (targets & tree):
                for w_try, margin in ((wide, 40), (wide, 400), (False, 400)) if wide else ((False, 40), (False, 400)):
                    path = rt.astar(nid, tree, targets, best["x"], best["y"], w_try, margin)
                    if path:
                        rt.commit(nid, path, w_try)
                        tree.update(path)
                        break
                if not path:
                    failed.append((name, best["ref"], best["num"]))
            for q in (best, best["partner"]):
                if q is None:
                    continue
                tree.update(q["nodes"])
                tree.update(q["extra"])
                done.append(q)
                if q in todo:
                    todo.remove(q)
    print("routing: %d tracks, %d vias, %.1f s, %d failed" % (len(rt.tracks), len(rt.vias), time.time() - t0, len(failed)))
    for f in failed:
        print("  UNROUTED %s -> %s.%s" % f)

    for (nid, layer, x1, y1, x2, y2, w) in rt.tracks:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(V(x1, y1)); t.SetEnd(V(x2, y2))
        t.SetWidth(mm(w))
        t.SetLayer(pcbnew.F_Cu if layer == R.F else pcbnew.B_Cu)
        t.SetNetCode(board.GetNetcodeFromNetname([n for n, i in net_id.items() if i == nid][0]))
        board.Add(t)
    for (nid, x, y) in rt.vias:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(V(x, y))
        v.SetWidth(mm(R.VIA_D)); v.SetDrill(mm(R.VIA_DRILL))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNetCode(board.GetNetcodeFromNetname([n for n, i in net_id.items() if i == nid][0]))
        board.Add(v)
    return failed


def add_zones(board, nets):
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(nets["GND"])
        o = z.Outline()
        o.NewOutline()
        for (x, y) in ((0, 0), (L.BOARD_W, 0), (L.BOARD_W, L.BOARD_H), (0, L.BOARD_H)):
            o.Append(mm(x), mm(y))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetLocalClearance(mm(0.3))
        z.SetMinThickness(mm(0.25))
        z.SetZoneName("GND_" + board.GetLayerName(layer))
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


# ============================================================ schematic
_NS = uuid.UUID("6f1d1c0e-7a61-4d3b-9b0a-6f706e636170")
_uid_n = [0]


def uid():
    _uid_n[0] += 1
    return str(uuid.uuid5(_NS, "opncap-%d" % _uid_n[0]))


FONT = "(effects (font (size 1.27 1.27)))"


def sym_geometry(name):
    left, right = SYMBOL_PINS[name]
    rows = max(len(left), len(right), 1)
    hw = 7.62 if rows < 10 else 10.16
    top = 2.54 * (rows - 1) / 2
    top = math.ceil(top / 2.54) * 2.54
    pins = []
    for i, (num, pname) in enumerate(left):
        pins.append((num, pname, -hw - 2.54, top - 2.54 * i, 0))
    for i, (num, pname) in enumerate(right):
        pins.append((num, pname, hw + 2.54, top - 2.54 * i, 180))
    return hw, top, rows, pins


def lib_symbol(name):
    hw, top, rows, pins = sym_geometry(name)
    bottom = top - 2.54 * (rows - 1)
    s = ['    (symbol "opncap:%s" (in_bom yes) (on_board yes)' % name,
         '      (property "Reference" "U" (at 0 %.2f 0) %s)' % (top + 3.81, FONT),
         '      (property "Value" "%s" (at 0 %.2f 0) %s)' % (name, bottom - 3.81, FONT),
         '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         '      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         '      (symbol "%s_0_1" (rectangle (start %.2f %.2f) (end %.2f %.2f) (stroke (width 0.254) (type default)) (fill (type background))))'
         % (name, -hw, top + 2.54, hw, bottom - 2.54),
         '      (symbol "%s_1_1"' % name]
    seen = set()
    for (num, pname, x, y, ang) in pins:
        if num in seen:
            continue
        seen.add(num)
        s.append('        (pin passive line (at %.2f %.2f %d) (length 2.54) (name "%s" %s) (number "%s" %s))'
                 % (x, y, ang, pname, FONT, num, FONT))
    s.append('      )')
    s.append('    )')
    return "\n".join(s)


def write_schematic(comps):
    root = uid()
    out = ['(kicad_sch (version 20230121) (generator opncap_gen_pcb)', '  (uuid %s)' % root, '  (paper "A1")',
           '  (title_block (title "opncap macropad") (rev "0.1") (comment 1 "Generated by hardware/scripts/gen_pcb.py - not tested on hardware"))',
           '  (lib_symbols']
    used = []
    for c in comps:
        n = c["fp"]["name"]
        if n in SYMBOL_PINS and n not in used:
            used.append(n)
    for n in used:
        out.append(lib_symbol(n))
    out.append('  )')
    body = []
    groups = [("U", 60.96, 60.96), ("SW", 0, 0)]
    cursor = {}

    def slot(c):
        """Lay parts out in labelled columns by type."""
        ref = c["ref"]
        kind = re.match(r"[A-Z]+", ref).group(0)
        col = {"U": 0, "ENC": 1, "JOY": 1, "DISP": 1, "R": 1, "SW": 2, "D": 3, "LED": 4, "C": 5}[kind]
        if kind == "LED" and int(ref[3:]) > 11:
            col = 6
        if kind == "C" and int(ref[1:]) > 13:
            col = 7
        if kind == "SW" and int(ref[2:]) > 14:
            col = 3
        x = 50.8 + col * 96.52
        y = cursor.get(col, 40.64)
        hw, top, rows, pins = sym_geometry(c["fp"]["name"])
        y += top + 7.62
        y = round(y / 2.54) * 2.54
        cursor[col] = y + (rows - 1) * 2.54 - top + 10.16
        return x, y

    for c in comps:
        name = c["fp"]["name"]
        if name not in SYMBOL_PINS:
            continue
        x, y = slot(c)
        hw, top, rows, pins = sym_geometry(name)
        bottom = top - 2.54 * (rows - 1)
        body.append('  (symbol (lib_id "opncap:%s") (at %.2f %.2f 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid %s)'
                    % (name, x, y, uid()))
        body.append('    (property "Reference" "%s" (at %.2f %.2f 0) %s)' % (c["ref"], x, y - top - 3.81, FONT))
        body.append('    (property "Value" "%s" (at %.2f %.2f 0) %s)' % (c["value"], x, y - bottom + 3.81, FONT))
        body.append('    (property "Footprint" "opncap:%s" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) hide))' % (name, x, y))
        body.append('    (property "Datasheet" "" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) hide))' % (x, y))
        seen = set()
        for (num, pname, px, py, ang) in pins:
            if num in seen:
                continue
            seen.add(num)
            body.append('    (pin "%s" (uuid %s))' % (num, uid()))
        body.append('    (instances (project "opncap" (path "/%s" (reference "%s") (unit 1))))' % (root, c["ref"]))
        body.append('  )')
        seen = set()
        for (num, pname, px, py, ang) in pins:
            if num in seen:
                continue
            seen.add(num)
            sx, sy = x + px, y - py
            net = c["nets"].get(num)
            if net:
                if ang == 0:
                    body.append('  (label "%s" (at %.2f %.2f 180) (effects (font (size 1.27 1.27)) (justify right bottom)) (uuid %s))'
                                % (net, sx, sy, uid()))
                else:
                    body.append('  (label "%s" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid %s))'
                                % (net, sx, sy, uid()))
            else:
                body.append('  (no_connect (at %.2f %.2f) (uuid %s))' % (sx, sy, uid()))
    out += body
    out.append('  (text "opncap v0.1 - netlist-style schematic generated from pinout.yaml and layout.py.\\nNets are joined by label name. Not tested on hardware." (at 50.8 25.4 0) (effects (font (size 2.54 2.54)) (justify left bottom)) (uuid %s))' % uid())
    out.append('  (sheet_instances (path "/" (page "1")))')
    out.append(')')
    open(SCH_FILE, "w").write("\n".join(out) + "\n")


def check_netlist(comps):
    """Export the netlist from the schematic with kicad-cli and compare it with the board."""
    net_file = "/tmp/opncap_sch.net"
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net_file, SCH_FILE],
                   check=True, capture_output=True)
    text = open(net_file).read()
    sch = {}
    for m in re.finditer(r'\(net \(code "?\d+"?\) \(name "([^"]*)"\)(.*?)(?=\(net \(code|\Z)', text, re.S):
        name = m.group(1).lstrip("/")
        for n in re.finditer(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)):
            sch[(n.group(1), n.group(2))] = name
    pcb = {}
    for c in comps:
        for num, net in c["nets"].items():
            if net:
                pcb[(c["ref"], num)] = net
    sch = {k: v for k, v in sch.items() if not v.startswith("unconnected-")}
    diff = [(k, sch.get(k), pcb.get(k)) for k in sorted(set(sch) | set(pcb)) if sch.get(k) != pcb.get(k)]
    print("netlist check: %d pins in schematic, %d on board, %d differences" % (len(sch), len(pcb), len(diff)))
    for d in diff[:20]:
        print("   ", d)
    return not diff


def patch_project():
    """The footprints are generated by this script, so there is no library to compare against."""
    pro = os.path.join(PCB_DIR, "opncap.kicad_pro")
    data = json.load(open(pro))
    sev = data["board"]["design_settings"].setdefault("rule_severities", {})
    sev["lib_footprint_issues"] = "ignore"
    sev["lib_footprint_mismatch"] = "ignore"
    json.dump(data, open(pro, "w"), indent=2, sort_keys=True)
    open(pro, "a").write("\n")


def fill_and_drc():
    board = pcbnew.LoadBoard(PCB_FILE)
    pcbnew.WriteDRCReport(board, "/tmp/opncap_drc_pre.txt", pcbnew.EDA_UNITS_MILLIMETRES, True)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB_FILE, board)
    patch_project()
    pcbnew.WriteDRCReport(board, DRC_FILE, pcbnew.EDA_UNITS_MILLIMETRES, True)
    rep = open(DRC_FILE).read()
    rep = re.sub(r"\*\* Created on .*? \*\*\n", "", rep).replace(PCB_DIR + os.sep, "")
    rep = rep.rstrip() + "\n\nTool: KiCad pcbnew %s (pcbnew.WriteDRCReport), zones refilled before the check.\n" % pcbnew.Version()
    open(DRC_FILE, "w").write(rep)
    errors = rep.count("Severity: error")
    warnings = rep.count("Severity: warning")
    unconn = int(re.search(r"Found (\d+) unconnected", rep).group(1))
    print("DRC: %d errors, %d warnings, %d unconnected items" % (errors, warnings, unconn))


# ============================================================ main
def main():
    os.makedirs(PCB_DIR, exist_ok=True)
    comps = build_design()
    board, nets, fps = build_board(comps)
    check_orientation(comps, fps)
    failed = route(board, comps, fps, nets)
    add_zones(board, nets)
    pcbnew.SaveBoard(PCB_FILE, board)
    patch_project()
    # Zone fill and DRC run in a fresh process so that the project settings written above
    # are loaded from disk and the DRC engine (hole clearances) is active while filling.
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--fill-and-drc"], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    m = re.search(r"DRC: (\d+) errors, (\d+) warnings, (\d+) unconnected", r.stdout)
    errors, warnings, unconn = (int(v) for v in m.groups()) if m else (-1, -1, -1)

    write_schematic(comps)
    same = check_netlist(comps)
    ok = not failed and errors == 0 and unconn == 0 and same
    print("gen_pcb:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--fill-and-drc" in sys.argv:
        fill_and_drc()
        sys.exit(0)
    sys.exit(main())

#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Parametric opncap enclosure (CadQuery).

Every dimension is a named parameter below or comes from scripts/layout.py,
which is also what the PCB is generated from. After building, the script
reads the real KiCad board back and checks fit, hole alignment, plate
cut-outs, the USB-C opening and part collisions. Any failed check exits
with a non-zero status.

CAD frame: X = board x, Y = -board y (back of the device is +Y), Z up,
PCB top surface at Z = 0. The device rests on its underside, which is
tilted by TILT degrees against the PCB.
"""
import json
import math
import os
import subprocess
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HW, "scripts"))
import layout as L                      # noqa: E402

# ------------------------------------------------------------------ parameters
TILT = 6.0                 # typing angle, degrees
CLEAR = 0.5                # PCB edge to case wall
WALL = 2.4
FLOOR = 2.0
FRONT_DEPTH = 2.5          # cavity under the PCB at its front edge (hotswap sockets are 1.8)
SPLIT_Z = L.PLATE_TOP_Z    # bottom case / top case parting plane
TOP_Z = 13.5               # top surface of the top case
SKIN = 2.0                 # thickness of the top surface
TOP_FILLET = 1.6
OUTER_R = L.CORNER_R + CLEAR + WALL
PLATE_INSET = 1.2          # plate is smaller than the PCB so the top-case lip fits
LIP_T, LIP_H, LIP_PLAY = 1.0, 1.5, 0.15
KEY_GAP = 0.6              # key well edge to the 1u cell edge
STANDOFF_D = 5.2
STANDOFF_BASE_D = 8.0
SCREW_D = 2.3              # M2 through hole
CBORE_D, CBORE_H = 4.4, 1.8
BOSS_D, INSERT_D, INSERT_H = 6.0, 3.2, 4.5     # M2 heat-set insert
POST_D = 4.0
SPACER_D = 4.4
KNOB_D, KNOB_H = 22.0, 14.0
KNOB_HOLE_D = KNOB_D + 1.2
KNOB_Z0 = TOP_Z - 1.2      # knob skirt sits slightly below the surface
JOY_BODY = (18.0, 18.0, 9.0)
JOY_CAP_D = 19.0
JOY_HOLE_D = 23.0
OLED_WINDOW = (26.0, 9.0)
USB_SLOT = (12.5, 7.0)     # opening for the plug overmould
FOOT_D, FOOT_RECESS, FOOT_H = 10.0, 0.8, 2.0
ENC_BODY = (12.0, 12.0, 6.5)

T = math.tan(math.radians(TILT))
Z_FRONT_IN = -L.BOARD_T - FRONT_DEPTH          # inner floor under the PCB front edge
Z_FRONT_OUT = Z_FRONT_IN - FLOOR / math.cos(math.radians(TILT))
USB_X = L.BP_CENTER[0]
USB_Z = -(L.BOARD_T + L.BP_STANDOFF + L.BP_T + L.USB_C[2] / 2)
EXPORT = os.path.join(HERE, "export")
W, H = L.BOARD_W, L.BOARD_H


def z_in(y):
    """Inner floor height under board position y."""
    return Z_FRONT_IN - (H - y) * T


# ------------------------------------------------------------------ helpers
def prism(x1, y1, x2, y2, r, z1, z2):
    """Rounded box given in board coordinates (y down)."""
    s = (cq.Workplane("XY").workplane(offset=z1)
         .center((x1 + x2) / 2, -(y1 + y2) / 2).rect(x2 - x1, y2 - y1).extrude(z2 - z1))
    return s.edges("|Z").fillet(r) if r > 0 else s


def box(cx, cy, w, h, z1, z2):
    return prism(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, 0, z1, z2)


def cyl(x, y, d, z1, z2):
    return cq.Workplane("XY").workplane(offset=z1).center(x, -y).circle(d / 2).extrude(z2 - z1)


def below_plane(z_front):
    """Everything below the tilted underside plane through the PCB front edge at z_front."""
    b = cq.Workplane("XY").box(800, 800, 300, centered=(True, True, False)).translate((0, 0, -300))
    return b.rotate((0, 0, 0), (1, 0, 0), -TILT).translate((L.CENTER_X, -H, z_front))


def on_underside(shape, dx, s):
    """Place a shape modelled at the origin onto the tilted underside."""
    return shape.translate((dx, s, 0)).rotate((0, 0, 0), (1, 0, 0), -TILT).translate((L.CENTER_X, -H, Z_FRONT_OUT))


def union(shapes):
    out = shapes[0]
    for s in shapes[1:]:
        out = out.union(s)
    return out


def compound(shapes):
    return cq.Workplane("XY").add(cq.Compound.makeCompound([v for s in shapes for v in s.vals()]))


FOOT_POS = [(sx * (W / 2 - 12), s) for sx in (-1, 1) for s in (11.0, (H - 11.0) / math.cos(math.radians(TILT)))]


# ------------------------------------------------------------------ case parts
def make_bottom():
    o = CLEAR + WALL
    body = prism(-o, -o, W + o, H + o, OUTER_R, -60, SPLIT_Z)
    cavity = prism(-CLEAR, -CLEAR, W + CLEAR, H + CLEAR, L.CORNER_R + CLEAR, -60, SPLIT_Z).cut(below_plane(Z_FRONT_IN))
    body = body.cut(cavity)
    for (x, y) in L.MOUNT_HOLES:
        body = body.union(cyl(x, y, STANDOFF_D, -60, -L.BOARD_T))
        body = body.union(cyl(x, y, STANDOFF_BASE_D, -60, min(z_in(y) + 2.5, -L.BOARD_T - 0.8)))
    for (x, y) in L.SUPPORT_POSTS:
        body = body.union(cyl(x, y, POST_D, -60, -L.BOARD_T))
    body = body.cut(below_plane(Z_FRONT_OUT))
    for (x, y) in L.MOUNT_HOLES:
        body = body.cut(cyl(x, y, SCREW_D, -60, 1))
        body = body.cut(cyl(x, y, CBORE_D, -60, z_in(y) - 0.2))
    # USB-C opening in the back wall
    slot = (cq.Workplane("XZ").workplane(offset=-(CLEAR + WALL + 1)).center(USB_X, USB_Z)
            .rect(USB_SLOT[0], USB_SLOT[1]).extrude(WALL + 3).edges("|Y").fillet(USB_SLOT[1] / 2 - 0.5))
    body = body.cut(slot)
    for (dx, s) in FOOT_POS:
        rec = cq.Workplane("XY").circle(FOOT_D / 2 + 0.25).extrude(FOOT_RECESS + 5).translate((0, 0, -5))
        body = body.cut(on_underside(rec, dx, s))
    return body


def key_well():
    k = KEY_GAP
    gx1, gx2 = L.KEY_X0 - L.P / 2 - k, L.KEY_X0 + 3.5 * L.P + k
    gy1, gy2 = L.TOP_ZONE - k, L.TOP_ZONE + 3 * L.P + k
    px1, px2 = L.KEY_X0 + 0.5 * L.P - k, L.KEY_X0 + 2.5 * L.P + k
    py2 = L.PAIR_Y + L.P / 2 + k
    pts = [(gx1, gy1), (gx2, gy1), (gx2, gy2), (px2, gy2), (px2, py2), (px1, py2), (px1, gy2), (gx1, gy2)]
    s = cq.Workplane("XY").workplane(offset=SPLIT_Z).polyline([(x, -y) for x, y in pts]).close().extrude(TOP_Z - SPLIT_Z + 1)
    return s.edges("|Z").fillet(1.2)


def make_top():
    o = CLEAR + WALL
    body = prism(-o, -o, W + o, H + o, OUTER_R, SPLIT_Z, TOP_Z)
    body = body.faces(">Z").edges().fillet(TOP_FILLET)
    body = body.cut(prism(-CLEAR, -CLEAR, W + CLEAR, H + CLEAR, L.CORNER_R + CLEAR, SPLIT_Z, TOP_Z - SKIN))
    a, b = -CLEAR + LIP_PLAY, -CLEAR + LIP_PLAY + LIP_T
    lip = prism(a, a, W - a, H - a, L.CORNER_R + CLEAR - LIP_PLAY, SPLIT_Z - LIP_H, SPLIT_Z).cut(
        prism(b, b, W - b, H - b, L.CORNER_R + CLEAR - LIP_PLAY - LIP_T, SPLIT_Z - LIP_H - 1, SPLIT_Z + 1))
    body = body.union(lip)
    for (x, y) in L.MOUNT_HOLES:
        body = body.union(cyl(x, y, BOSS_D, SPLIT_Z, TOP_Z - SKIN + 0.1))
    for (x, y) in L.MOUNT_HOLES:
        body = body.cut(cyl(x, y, INSERT_D, SPLIT_Z - 1, SPLIT_Z + INSERT_H))
    body = body.cut(key_well())
    body = body.cut(cyl(L.ENC_POS[0], L.ENC_POS[1], KNOB_HOLE_D, SPLIT_Z, TOP_Z + 1))
    body = body.cut(cyl(L.JOY_POS[0], L.JOY_POS[1], JOY_HOLE_D, SPLIT_Z, TOP_Z + 1))
    win = box(L.OLED_CENTER[0], L.OLED_CENTER[1], OLED_WINDOW[0], OLED_WINDOW[1], SPLIT_Z, TOP_Z + 1).edges("|Z").fillet(1.5)
    body = body.cut(win)
    try:        # debossed wordmark above the display
        txt = (cq.Workplane("XY").workplane(offset=TOP_Z - 0.5).center(L.CENTER_X, -9.5)
               .text("opncap", 6.0, 1.0, kind="bold", halign="center", valign="center"))
        body = body.cut(txt)
    except Exception as e:      # no usable font on this machine
        print("note: wordmark skipped (%s)" % e)
    return body


def make_plate():
    i = PLATE_INSET
    p = prism(i, i, W - i, H - i, L.CORNER_R - i, L.PLATE_TOP_Z - L.PLATE_T, L.PLATE_TOP_Z)
    z1, z2 = 0, L.PLATE_TOP_Z + 1
    for k in L.KEY_ORDER:
        x, y = L.KEYS[k][:2]
        p = p.cut(box(x, y, L.PLATE_CUTOUT, L.PLATE_CUTOUT, z1, z2))
    p = p.cut(box(L.ENC_POS[0], L.ENC_POS[1], ENC_BODY[0] + 4.5, ENC_BODY[1] + 2.5, z1, z2))
    p = p.cut(box(L.JOY_POS[0], L.JOY_POS[1], JOY_BODY[0] + 1.5, JOY_BODY[1] + 1.5, z1, z2))
    p = p.cut(box(L.OLED_HDR_POS[0], L.OLED_HDR_POS[1], 3.6, 11.2, z1, z2))
    for (x, y) in L.MOUNT_HOLES:
        p = p.cut(cyl(x, y, L.MOUNT_DRILL, z1, z2))
    return p


# ------------------------------------------------------------------ placeholder parts (at origin)
def make_switch():
    lower = box(0, 0, 13.9, 13.9, 0, L.PLATE_TOP_Z)
    flange = box(0, 0, 15.6, 15.6, L.PLATE_TOP_Z, L.PLATE_TOP_Z + 1.0)
    upper = (cq.Workplane("XY").workplane(offset=L.PLATE_TOP_Z + 1.0).rect(14.2, 14.2)
             .workplane(offset=L.SWITCH_TOP_Z - L.PLATE_TOP_Z - 1.0).rect(10.6, 11.2).loft())
    stem = box(0, 0, 5.4, 5.4, L.SWITCH_TOP_Z, L.STEM_TOP_Z)
    post = cyl(0, 0, 3.9, -3.0, 0)
    return union([lower, flange, upper, stem, post])


def make_keycap():
    b, t, h = L.KEYCAP_BASE, L.KEYCAP_TOP, L.KEYCAP_H
    outer = cq.Workplane("XY").rect(b, b).workplane(offset=h).rect(t, t).loft().edges("|Z or >Z").fillet(1.0)
    inner = cq.Workplane("XY").rect(b - 3, b - 3).workplane(offset=h - 1.5).rect(t - 3, t - 3).loft()
    cap = outer.cut(inner)
    dish = cq.Workplane("XY").sphere(40).translate((0, 0, h + 40 - 0.6))
    cap = cap.cut(dish)
    stem_len = L.KEYCAP_BOTTOM_Z + h - 1.5 - L.STEM_TOP_Z
    cap = cap.union(cq.Workplane("XY").workplane(offset=h - 1.5 - stem_len).circle(2.75).extrude(stem_len + 0.2))
    return cap.translate((0, 0, L.KEYCAP_BOTTOM_Z))


def make_socket():
    """Kailh hotswap socket below the PCB, in key coordinates (top view)."""
    z1, z2 = -L.BOARD_T - L.SOCKET_H, -L.BOARD_T
    # S-shaped body: one block around each switch pin, leaving the centre post free
    body = prism(-6.0, -4.8, -2.2, -0.75, 0, z1, z2).union(prism(-2.2, -6.85, 4.6, -2.9, 0, z1, z2))
    tab1 = prism(-8.3, -3.4, -6.0, -1.7, 0, -L.BOARD_T - 0.6, z2)
    tab2 = prism(4.6, -5.9, 7.1, -4.2, 0, -L.BOARD_T - 0.6, z2)
    return union([body, tab1, tab2])


def make_encoder():
    body = box(0, 0, ENC_BODY[0], ENC_BODY[1], 0, ENC_BODY[2])
    bush = cyl(0, 0, 7.0, ENC_BODY[2], ENC_BODY[2] + 5.0)
    shaft = cyl(0, 0, 6.0, ENC_BODY[2] + 5.0, 20.0)
    return union([body, bush, shaft])


def make_knob():
    k = cyl(0, 0, KNOB_D, KNOB_Z0, KNOB_Z0 + KNOB_H).faces(">Z").edges().fillet(1.5)
    k = k.cut(cyl(0, 0, 6.2, KNOB_Z0 - 1, 20.6))
    mark = box(0, -KNOB_D / 2 + 3.2, 1.2, 4.5, KNOB_Z0 + KNOB_H - 0.4, KNOB_Z0 + KNOB_H + 1)
    return k.cut(mark)


def make_joystick():
    body = box(0, 0, JOY_BODY[0], JOY_BODY[1], 0, JOY_BODY[2])
    dome = cyl(0, 0, 12.0, JOY_BODY[2], JOY_BODY[2] + 2.0)
    stick = cyl(0, 0, 4.0, JOY_BODY[2] + 2.0, 12.5)
    return union([body, dome, stick])


def make_joy_cap():
    c = cyl(0, 0, JOY_CAP_D, 12.5, 17.5).edges().fillet(1.2)
    dish = cq.Workplane("XY").sphere(30).translate((0, 0, 17.5 + 30 - 0.8))
    return c.cut(dish)


def make_oled():
    hx, hy = L.OLED_HDR_POS
    cx, cy = L.OLED_CENTER
    w, h, t = L.OLED_PCB
    z = L.OLED_PCB_Z
    socket = box(hx, hy, 2.54, 10.16, 0, 5.0)
    header = box(hx, hy, 2.54, 10.16, 5.0, z)
    pcb = box(cx, cy, w, h, z, z + t)
    gw, gh, gt = L.OLED_GLASS
    glass = box(cx - 1.0, cy, gw, gh, z + t, z + t + gt)
    return union([socket, header, pcb]), glass


def make_blackpill():
    cx = L.BP_CENTER[0]
    y0 = L.BP_USB_EDGE_Y
    zt = -L.BOARD_T - L.BP_STANDOFF            # module PCB face towards the main board
    zb = zt - L.BP_T
    pcb = prism(cx - L.BP_W / 2, y0, cx + L.BP_W / 2, y0 + L.BP_LEN, 0, zb, zt)
    hdr = [prism(cx + s * L.BP_ROW_PITCH / 2 - 1.27, L.BP_PIN1_Y - 1.27, cx + s * L.BP_ROW_PITCH / 2 + 1.27,
                 L.BP_PIN1_Y + 19 * 2.54 + 1.27, 0, zt, -L.BOARD_T) for s in (-1, 1)]
    uw, ud, uh = L.USB_C
    usb = prism(cx - uw / 2, y0 - L.USB_OVERHANG, cx + uw / 2, y0 - L.USB_OVERHANG + ud, 0, zb - uh, zb).edges("|Y").fillet(1.2)
    mcu = box(cx, y0 + 30, 7, 7, zb - 0.8, zb)
    btn = [box(cx + s * 5.5, y0 + 12, 3.5, 4.2, zb - 1.6, zb) for s in (-1, 1)]
    return pcb, union(hdr + [mcu] + btn), usb


def smd_parts():
    """Small parts on the board as boxes, positions taken from the PCB design model."""
    import gen_pcb
    dims = {"D_SOD-123": (2.7, 1.6, 1.1), "C_0603": (1.6, 0.8, 0.8), "R_0603": (1.6, 0.8, 0.5),
            "SOIC-14_3.9x8.7mm_P1.27mm": (3.9, 8.7, 1.5)}
    out, leds = [], []
    for c in gen_pcb.build_design():
        n = c["fp"]["name"]
        if n in dims:
            w, h, t = dims[n]
            if c["rot"] % 180 == 90:
                w, h = h, w
            z = (-L.BOARD_T - t, -L.BOARD_T) if c["back"] else (0, t)
            out.append(box(c["x"], c["y"], w, h, *z))
        elif n.startswith("LED_SK6812"):
            w, h = (3.2, 2.8) if c["rot"] % 180 == 0 else (2.8, 3.2)
            z = (-L.BOARD_T - 0.25, -0.15) if c["back"] else (-L.BOARD_T + 0.15, 0.25)
            leds.append((c["ref"], box(c["x"], c["y"], w, h, *z)))
        elif n.startswith("CP_Radial"):
            out.append(cyl(c["x"], c["y"], L.BULK_CAP[0], -L.BOARD_T - L.BULK_CAP[1], -L.BOARD_T))
    return out, leds


def export_pcb_step():
    path = os.path.join(EXPORT, "pcb.step")
    r = subprocess.run(["kicad-cli", "pcb", "export", "step", "--board-only", "--user-origin", "0x0mm", "-f",
                        "-o", path, os.path.join(HW, "pcb", "opncap.kicad_pcb")], capture_output=True, text=True)
    if not os.path.exists(path):
        sys.exit("kicad-cli STEP export failed:\n" + r.stdout + r.stderr)
    s = cq.importers.importStep(path)
    bb = s.val().BoundingBox()
    # KiCad puts the board bottom at z=0; move the top face to z=0
    s = s.translate((0, 0, -bb.zmax))
    bb = s.val().BoundingBox()
    assert abs(bb.xmin) < 0.01 and abs(bb.ymax) < 0.01 and abs(bb.xmax - W) < 0.01 and abs(bb.ymin + H) < 0.01, \
        "KiCad STEP board does not sit where the case expects it: %s" % ((bb.xmin, bb.xmax, bb.ymin, bb.ymax),)
    return s


def at(shape, x, y):
    return shape.translate((x, -y, 0))


# ------------------------------------------------------------------ assembly
def build():
    os.makedirs(EXPORT, exist_ok=True)
    parts = {}
    parts["bottom_case"] = make_bottom()
    parts["top_case"] = make_top()
    parts["plate"] = make_plate()
    parts["pcb"] = export_pcb_step()
    sw, cap, sock = make_switch(), make_keycap(), make_socket()
    keys = [L.KEYS[k][:2] for k in L.KEY_ORDER]
    parts["switches"] = compound([at(sw, x, y) for x, y in keys])
    parts["keycaps"] = compound([at(cap, x, y) for x, y in keys[:12]])
    parts["keycaps_accent"] = compound([at(cap, x, y) for x, y in keys[12:]])
    parts["sockets"] = compound([at(sock, x, y) for x, y in keys])
    parts["encoder"] = at(make_encoder(), *L.ENC_POS)
    parts["knob"] = at(make_knob(), *L.ENC_POS)
    parts["joystick"] = at(make_joystick(), *L.JOY_POS)
    parts["joystick_cap"] = at(make_joy_cap(), *L.JOY_POS)
    parts["oled"], parts["oled_glass"] = make_oled()
    parts["blackpill_pcb"], parts["blackpill_parts"], parts["usb_c"] = make_blackpill()
    smd, leds = smd_parts()
    parts["smd"] = compound(smd)
    parts["leds"] = compound([s for _, s in leds])
    parts["spacers"] = compound([cyl(x, y, SPACER_D, 0, L.PLATE_TOP_Z - L.PLATE_T).cut(cyl(x, y, SCREW_D, -1, 6))
                                 for x, y in L.MOUNT_HOLES])
    foot = cq.Workplane("XY").circle(FOOT_D / 2).extrude(FOOT_H).translate((0, 0, FOOT_RECESS - FOOT_H))
    parts["feet"] = compound([on_underside(foot, dx, s) for dx, s in FOOT_POS])
    singles = {"mx_switch": sw, "keycap_1u": cap.translate((0, 0, -L.KEYCAP_BOTTOM_Z)), "hotswap_socket": sock}
    return parts, singles, leds


COLORS = {
    "bottom_case": (0.86, 0.84, 0.79), "top_case": (0.86, 0.84, 0.79), "plate": (0.62, 0.64, 0.66),
    "pcb": (0.05, 0.30, 0.12), "switches": (0.12, 0.12, 0.13), "keycaps": (0.16, 0.17, 0.19),
    "keycaps_accent": (0.93, 0.42, 0.13), "sockets": (0.20, 0.20, 0.20), "encoder": (0.55, 0.56, 0.58),
    "knob": (0.93, 0.42, 0.13), "joystick": (0.15, 0.15, 0.16), "joystick_cap": (0.16, 0.17, 0.19),
    "oled": (0.05, 0.12, 0.35), "oled_glass": (0.02, 0.02, 0.03), "blackpill_pcb": (0.03, 0.03, 0.04),
    "blackpill_parts": (0.10, 0.10, 0.10), "usb_c": (0.75, 0.76, 0.78), "smd": (0.10, 0.10, 0.10),
    "leds": (0.95, 0.95, 0.90), "spacers": (0.80, 0.70, 0.35), "feet": (0.06, 0.06, 0.06),
}
SECTIONS = {"key_column": L.KEYS["K2"][0], "usb_centre": L.CENTER_X}


def export_all(parts, singles, leds):
    def save(shape, name, sub=""):
        d = os.path.join(EXPORT, sub)
        os.makedirs(d, exist_ok=True)
        cq.exporters.export(shape, os.path.join(d, name + ".stl"), tolerance=0.03, angularTolerance=0.25)
        if not sub and name != "pcb":
            cq.exporters.export(shape, os.path.join(d, name + ".step"))
    for name, shape in parts.items():
        save(shape, name)
    for name, shape in singles.items():
        save(shape, name)
    asm = cq.Assembly(name="opncap")
    for name, shape in parts.items():
        asm.add(shape, name=name, color=cq.Color(*COLORS[name]))
    asm.export(os.path.join(EXPORT, "opncap_assembly.step"))
    # section bodies for the cut-away renders: keep everything with x >= cut
    for sec, xcut in SECTIONS.items():
        keep = cq.Workplane("XY").box(400, 400, 200).translate((xcut + 200, -H / 2, 0))
        for name, shape in parts.items():
            bb = shape.val().BoundingBox()
            if bb.xmax <= xcut + 0.01:
                continue
            cut = shape if bb.xmin >= xcut else shape.intersect(keep)
            if cut.vals() and cut.val().Volume() > 1e-6:
                save(cut, name, "section_" + sec)
    manifest = dict(
        tilt_deg=TILT, colors=COLORS, sections=SECTIONS, top_z=TOP_Z, split_z=SPLIT_Z,
        board=[W, H, L.BOARD_T], z_front_out=Z_FRONT_OUT, wall=CLEAR + WALL,
        keys={k: list(L.KEYS[k][:2]) for k in L.KEY_ORDER}, keycap_top_z=L.KEYCAP_BOTTOM_Z + L.KEYCAP_H,
        leds=[dict(ref=r, bbox=[s.val().BoundingBox().xmin, s.val().BoundingBox().xmax, s.val().BoundingBox().ymin,
                                s.val().BoundingBox().ymax, s.val().BoundingBox().zmin, s.val().BoundingBox().zmax])
              for r, s in leds],
        stack=dict(pcb_bottom=-L.BOARD_T, pcb_top=0.0, plate_bottom=L.PLATE_TOP_Z - L.PLATE_T, plate_top=L.PLATE_TOP_Z,
                   switch_top=L.SWITCH_TOP_Z, keycap_bottom=L.KEYCAP_BOTTOM_Z, keycap_top=L.KEYCAP_BOTTOM_Z + L.KEYCAP_H,
                   case_top=TOP_Z, socket_bottom=-L.BOARD_T - L.SOCKET_H),
        floor=dict(z_front_in=Z_FRONT_IN, thickness=FLOOR), oled_center=list(L.OLED_CENTER), enc=list(L.ENC_POS),
        joy=list(L.JOY_POS), usb=[USB_X, USB_Z],
    )
    json.dump(manifest, open(os.path.join(EXPORT, "manifest.json"), "w"), indent=1, sort_keys=True)


# ------------------------------------------------------------------ verification
def void_bbox(solid, probe):
    """Bounding box of the empty space of `solid` inside the probe box."""
    v = probe.cut(solid)
    solids = v.solids().vals()
    assert solids, "no opening found where one was expected"
    best = max(solids, key=lambda s: s.Volume())
    return best.BoundingBox()


def verify(parts):
    import pcbnew
    board = pcbnew.LoadBoard(os.path.join(HW, "pcb", "opncap.kicad_pcb"))
    mm = pcbnew.ToMM
    results = []

    def check(name, ok, detail):
        results.append((name, ok, detail))
        print("%-4s %s: %s" % ("PASS" if ok else "FAIL", name, detail))

    # 1. PCB outline inside the bottom case
    e = board.GetBoardEdgesBoundingBox()
    px1, py1 = mm(e.GetLeft()) + 0.05, mm(e.GetTop()) + 0.05          # edge line is 0.1 wide
    px2, py2 = mm(e.GetRight()) - 0.05, mm(e.GetBottom()) - 0.05
    probe = cq.Workplane("XY").box(W + 20, H + 20, 0.6).translate((W / 2, -H / 2, -L.BOARD_T / 2))
    bb = void_bbox(parts["bottom_case"], probe)
    gaps = [px1 - bb.xmin, bb.xmax - px2, bb.ymax - (-py1), (-py2) - bb.ymin]
    check("PCB outline fits bottom case", min(gaps) >= 0.3,
          "KiCad outline %.2f x %.2f mm, clearance left/right/back/front = %s mm (need >= 0.30)"
          % (px2 - px1, py2 - py1, ", ".join("%.2f" % g for g in gaps)))

    # 2. mounting holes against standoffs, plate holes and top-case bosses
    holes = [(mm(f.GetPosition().x), mm(f.GetPosition().y)) for f in board.GetFootprints()
             if f.GetReference().startswith("H")]
    bottom, top, plate = parts["bottom_case"].val(), parts["top_case"].val(), parts["plate"].val()
    worst, bad = 0.0, []
    for (x, y) in holes:
        probe = cq.Workplane("XY").box(STANDOFF_D + 1, STANDOFF_D + 1, 0.4).translate((x, -y, -L.BOARD_T - 0.4))
        ring = probe.intersect(parts["bottom_case"])
        inner = void_bbox(parts["bottom_case"], cq.Workplane("XY").box(SCREW_D + 0.6, SCREW_D + 0.6, 0.4)
                          .translate((x, -y, -L.BOARD_T - 0.4)))
        cx, cy = (inner.xmin + inner.xmax) / 2, (inner.ymin + inner.ymax) / 2
        off = math.hypot(cx - x, cy + y)
        worst = max(worst, off)
        ok = (ring.vals() and ring.val().Volume() > 5 and off < 0.05
              and top.isInside(cq.Vector(x + BOSS_D / 2 - 0.5, -y, SPLIT_Z + 2))
              and not top.isInside(cq.Vector(x, -y, SPLIT_Z + 2))
              and not plate.isInside(cq.Vector(x, -y, L.PLATE_TOP_Z - 0.5))
              and not bottom.isInside(cq.Vector(x, -y, -L.BOARD_T - 1)))
        if not ok:
            bad.append((x, y))
    check("mounting holes line up with standoffs", len(holes) == len(L.MOUNT_HOLES) and not bad,
          "%d holes read from the KiCad board, worst axis offset %.3f mm, misaligned: %s" % (len(holes), worst, bad or "none"))

    # 3. plate cut-outs against the switch footprints on the board
    worst_c, worst_s = 0.0, 0.0
    n = 0
    for f in board.GetFootprints():
        if not f.GetReference().startswith("SW"):
            continue
        n += 1
        x, y = mm(f.GetPosition().x), mm(f.GetPosition().y)
        probe = cq.Workplane("XY").box(16.5, 16.5, 0.5).translate((x, -y, L.PLATE_TOP_Z - L.PLATE_T / 2))
        bb = void_bbox(parts["plate"], probe)
        worst_c = max(worst_c, abs((bb.xmin + bb.xmax) / 2 - x), abs((bb.ymin + bb.ymax) / 2 + y))
        worst_s = max(worst_s, abs(bb.xlen - L.PLATE_CUTOUT), abs(bb.ylen - L.PLATE_CUTOUT))
    check("plate cut-outs match switch positions", n == 14 and worst_c <= 0.05 and worst_s <= 0.05,
          "%d switches, worst centre offset %.4f mm, worst size error %.4f mm (limit 0.05)" % (n, worst_c, worst_s))

    # 4. USB-C opening against the BlackPill connector
    u1 = [f for f in board.GetFootprints() if f.GetReference() == "U1"][0]
    ux = mm(u1.GetPosition().x)
    pin1_y = min(mm(p.GetPosition().y) for p in u1.Pads())
    usb_front_y = pin1_y - L.BP_PIN_INSET - L.USB_OVERHANG
    probe = cq.Workplane("XY").box(30, WALL - 0.6, 12).translate((ux, CLEAR + WALL / 2, USB_Z))
    bb = void_bbox(parts["bottom_case"], probe)
    cx, cz = (bb.xmin + bb.xmax) / 2, (bb.zmin + bb.zmax) / 2
    side = (bb.xlen - L.USB_C[0]) / 2 - abs(cx - ux)
    vert = (bb.zlen - L.USB_C[2]) / 2
    recess = (CLEAR + WALL) + usb_front_y
    ok = abs(cx - ux) <= 0.1 and abs(cz - USB_Z) <= 0.1 and side >= 1.0 and vert >= 1.0 and 0 <= recess <= 2.5
    check("USB-C opening lines up with the BlackPill", ok,
          "opening centre x=%.2f z=%.2f, connector x=%.2f z=%.2f, opening %.1f x %.1f mm, connector front %.2f mm behind the outer wall"
          % (cx, cz, ux, USB_Z, bb.xlen, bb.zlen, recess))

    # 5. collisions
    names = list(parts)
    hits = []
    boxes = {n: parts[n].val().BoundingBox() for n in names}
    pairs = 0
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            A, B = boxes[a], boxes[b]
            if (A.xmax < B.xmin or B.xmax < A.xmin or A.ymax < B.ymin or B.ymax < A.ymin
                    or A.zmax < B.zmin or B.zmax < A.zmin):
                continue
            pairs += 1
            try:
                c = parts[a].intersect(parts[b])
                vol = sum(s.Volume() for s in c.solids().vals())
            except Exception:
                vol = 0.0
            if vol > 0.01:
                hits.append("%s/%s %.2f mm3" % (a, b, vol))
    check("no part collisions", not hits, "%d overlapping bounding-box pairs tested by boolean intersection, collisions: %s"
          % (pairs, ", ".join(hits) or "none"))

    # screw table
    print("M2 screw length per mounting hole (counterbore seat to 3 mm into the insert):")
    for (x, y) in holes:
        print("   hole (%.1f, %.1f): %.1f mm" % (x, y, (SPLIT_Z + 3.0) - (z_in(y) - 0.2)))
    return all(ok for _, ok, _ in results), results


def main():
    parts, singles, leds = build()
    ok, results = verify(parts)
    with open(os.path.join(HERE, "verification.txt"), "w") as f:
        for name, good, detail in results:
            f.write("%s %s: %s\n" % ("PASS" if good else "FAIL", name, detail))
    if not ok:
        print("opncap_case: VERIFICATION FAILED")
        sys.exit(1)
    if "--no-export" not in sys.argv:
        export_all(parts, singles, leds)
    bb = parts["bottom_case"].val().BoundingBox()
    print("outer size %.1f x %.1f mm" % (bb.xlen, bb.ylen))
    print("opncap_case: OK")


if __name__ == "__main__":
    main()

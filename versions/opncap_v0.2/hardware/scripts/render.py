#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Render the opncap views with Blender (bpy, Cycles on the CPU, headless).

Input: the STL groups and manifest.json written by enclosure/opncap_case.py and
the gerbv board images written by gen_fab.py. All camera and light settings are
in the SHOTS table below, so every image is reproducible:

    python hardware/scripts/render.py                # all stills
    python hardware/scripts/render.py --only 01,08   # selected stills
    python hardware/scripts/render.py --turntable    # turntable.mp4
"""
import json
import math
import os
import subprocess
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT = os.path.join(HW, "enclosure", "export")
OUT = os.path.join(HW, "renders")
MAN = json.load(open(os.path.join(EXPORT, "manifest.json")))
W, H, BT = MAN["board"]
SCALE = 0.01                      # millimetres to Blender units
RES = (1920, 1080)
SAMPLES = 28
PREVIEW = "--preview" in sys.argv      # quarter resolution, few samples, for checking framing

MATERIALS = {       # group -> (roughness, metallic)
    "bottom_case": (0.55, 0.0), "top_case": (0.55, 0.0), "plate": (0.35, 1.0), "pcb": (0.5, 0.0),
    "switches": (0.4, 0.0), "keycaps": (0.45, 0.0), "keycaps_accent": (0.45, 0.0), "sockets": (0.5, 0.0),
    "encoder": (0.3, 1.0), "knob": (0.3, 0.9), "joystick": (0.5, 0.0), "joystick_cap": (0.6, 0.0),
    "display": (0.5, 0.0), "display_glass": (0.05, 0.0), "blackpill_pcb": (0.5, 0.0), "blackpill_parts": (0.4, 0.0),
    "usb_c": (0.25, 1.0), "smd": (0.5, 0.0), "spacers": (0.3, 1.0), "feet": (0.8, 0.0),
}
ALL = list(MATERIALS) + ["leds"]
BOARD = ["pcb", "sockets", "smd", "leds", "spacers", "blackpill_pcb", "blackpill_parts", "usb_c",
         "encoder", "joystick", "display", "display_glass"]

# Camera positions and targets are in Blender units (1 unit = 100 mm), device centred on the origin,
# +Y is the back of the device. "explode" maps groups to a vertical offset in millimetres.
SHOTS = {
    "01_outside_hero": dict(groups=ALL, cam=(1.45, -1.95, 1.35), target=(0.0, 0.02, 0.12), lens=40, ground=True),
    "02_outside_top": dict(groups=ALL, cam=(0, 0, 4), target=(0, 0, 0), ortho=2.75, ground=True, legends=True,
                           up=(0, 1, 0)),
    "03_outside_back": dict(groups=ALL, cam=(1.5, 2.6, -1.5), target=(0.0, 0.0, 0.1), lens=40, ground=False,
                            under_light=True),
    "04_exploded": dict(groups=ALL, cam=(4.2, -5.4, 3.4), target=(0.0, 0.0, 1.0), lens=50, ground=True,
                        explode={"blackpill_pcb": 22, "blackpill_parts": 22, "usb_c": 22,
                                 "pcb": 48, "sockets": 48, "smd": 48, "leds": 48, "spacers": 48, "encoder": 48,
                                 "joystick": 48, "display": 48, "display_glass": 48,
                                 "plate": 80, "switches": 104, "top_case": 136,
                                 "keycaps": 172, "keycaps_accent": 172, "knob": 172, "joystick_cap": 172}),
    "05_inside_pcb_in_case": dict(groups=ALL, section="usb_centre", cam=(-2.15, 0.75, 1.05),
                                  target=(0.05, 0.05, 0.16), lens=60, ground=True),
    "06_pcb_top_3d": dict(groups=BOARD, cam=(0.6, -1.9, 2.3), target=(0.0, 0.0, 0.0), lens=40, ground=True,
                          glow=2.2, world=0.35),
    "07_pcb_bottom_3d": dict(groups=BOARD, cam=(0.7, -1.7, -2.4), target=(0.0, 0.0, 0.0), lens=40, ground=False,
                             under_light=True, glow=2.2, flat=True),
    "08_section_side": dict(groups=ALL, section="key_column", cam=(-4, None, None), ortho=1.0, ground=False,
                            flat=True, annotate=True, side_light=True),
}


# ------------------------------------------------------------------ scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.max_bounces = 4
    try:
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 25 if PREVIEW else 100
    if PREVIEW:
        sc.cycles.samples = 6
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "Standard"
    return sc


def root_matrix(flat):
    """CAD millimetres -> world. The device is rotated so that its tilted underside lies on z = 0."""
    centre = Matrix.Translation((-W / 2, H / 2, 0))
    if flat:
        m = centre
    else:
        pivot = Vector((0, -H, MAN["z_front_out"]))
        rot = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(MAN["tilt_deg"]), 4, "X") @ Matrix.Translation(-pivot)
        lift = Matrix.Translation((0, 0, -MAN["z_front_out"] + 1.2))
        m = centre @ lift @ rot
    return Matrix.Scale(SCALE, 4) @ m


def material(name, color, rough=0.5, metal=0.0, emission=None, strength=0.0, image=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    if image:
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(image)
        m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def import_group(name, folder, root, dz=0.0):
    path = os.path.join(folder, name + ".stl")
    if not os.path.exists(path):
        return None
    bpy.ops.wm.stl_import(filepath=path)
    ob = bpy.context.selected_objects[0]
    ob.name = name
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    except Exception:
        pass
    ob.parent = root
    ob.location = (0, 0, dz)
    rough, metal = MATERIALS[name]
    ob.data.materials.append(material(name, MAN["colors"][name], rough, metal))
    return ob


def quad(name, pts, uvs, mat, root, dz):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(pts, [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new()
    for i, c in enumerate(uvs):
        uv.data[i].uv = c
    mesh.materials.append(mat)
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = root
    ob.location = (0, 0, dz)
    return ob


def add_board_faces(root, dz, xmin=0.0):
    """Lay the gerbv renders of the real Gerbers onto both faces of the board."""
    u0 = xmin / W
    top = material("pcb_top", (0, 0.3, 0.1), 0.45, image=os.path.join(OUT, "pcb_top.png"))
    quad("pcb_face_top", [(xmin, -H, 0.03), (W, -H, 0.03), (W, 0, 0.03), (xmin, 0, 0.03)],
         [(u0, 0), (1, 0), (1, 1), (u0, 1)], top, root, dz)
    bot = material("pcb_bottom", (0, 0.3, 0.1), 0.45, image=os.path.join(OUT, "pcb_bottom.png"))
    quad("pcb_face_bottom", [(xmin, 0, -BT - 0.03), (W, 0, -BT - 0.03), (W, -H, -BT - 0.03), (xmin, -H, -BT - 0.03)],
         [(1 - u0, 1), (0, 1), (0, 0), (1 - u0, 0)], bot, root, dz)


def add_leds(root, dz, strength, xmin=-1e9):
    """One small emissive box per LED, colour running through the hue circle along the data chain."""
    import colorsys
    n = len(MAN["leds"])
    for i, led in enumerate(MAN["leds"]):
        x1, x2, y1, y2, z1, z2 = led["bbox"]
        if x2 <= xmin:
            continue
        x1 = max(x1, xmin)
        col = colorsys.hsv_to_rgb(i / n, 0.9, 1.0)
        base = tuple(c * 0.25 for c in col) if strength else (0.9, 0.9, 0.85)
        mat = material(led["ref"], base, 0.3, emission=col if strength else None, strength=strength)
        z1, z2 = min(z1, -BT - 0.08), max(z2, 0.08)
        v = [(x, y, z) for z in (z1, z2) for (x, y) in ((x1, y1), (x2, y1), (x2, y2), (x1, y2))]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        mesh = bpy.data.meshes.new(led["ref"])
        mesh.from_pydata(v, [], f)
        mesh.materials.append(mat)
        ob = bpy.data.objects.new(led["ref"], mesh)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = root
        ob.location = (0, 0, dz)


def add_legends(root, dz):
    mat = material("legend", (0.85, 0.85, 0.82), 0.6)
    for name, (x, y) in MAN["keys"].items():
        cu = bpy.data.curves.new(name, "FONT")
        cu.body = name
        cu.size = 3.4
        cu.align_x = "CENTER"
        cu.align_y = "CENTER"
        cu.extrude = 0.02
        cu.materials.append(mat)
        ob = bpy.data.objects.new("legend_" + name, cu)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = root
        ob.location = (x, -y, MAN["keycap_top_z"] - 0.5 + dz)


def add_display_face(root, dz):
    """A lit ring and a short status text so the round panel reads as a switched-on display."""
    cx, cy = MAN["display_center"]
    z = MAN["stack"]["display_top"] + 0.03 + dz
    mat = material("display_px", (0, 0, 0), 0.3, emission=(0.55, 0.85, 1.0), strength=4.0)
    accent = material("display_accent", (0, 0, 0), 0.3, emission=(1.0, 0.45, 0.12), strength=4.0)
    r = MAN["display_d"] / 2
    for name, radius, minor, m in (("ring", r - 2.2, 0.35, mat), ("ring_accent", r - 4.0, 0.22, accent)):
        bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=minor, major_segments=96, minor_segments=8)
        ob = bpy.context.object
        ob.name = "display_" + name
        ob.scale = (1, 1, 0.05)
        ob.data.materials.append(m)
        ob.parent = root
        ob.location = (cx, -cy, z)
    for body, size, off, m in (("L0", 7.0, 2.2, mat), ("idle", 3.2, -4.6, accent)):
        cu = bpy.data.curves.new("display_text", "FONT")
        cu.body = body
        cu.size = size
        cu.align_x = "CENTER"
        cu.align_y = "CENTER"
        cu.materials.append(m)
        ob = bpy.data.objects.new("display_text_" + body, cu)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = root
        ob.location = (cx, -cy + off, z)


def lights(sc, shot):
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.93, 0.93, 0.94, 1)
    bg.inputs["Strength"].default_value = shot.get("world", 0.75) * 0.8
    sc.world = world
    k = shot.get("world", 0.75) / 0.75

    def area(name, loc, size, power):
        d = bpy.data.lights.new(name, "AREA")
        d.size = size
        d.energy = power * k
        ob = bpy.data.objects.new(name, d)
        sc.collection.objects.link(ob)
        ob.location = loc
        look_at(ob, (0, 0, 0))
    area("key", (-2.2, -2.0, 3.6), 3.0, 90)
    area("fill", (2.8, -0.5, 2.2), 2.5, 30)
    area("rim", (0.5, 3.0, 2.0), 2.0, 40)
    if shot.get("side_light"):
        area("side", (-4.0, 0.0, 0.6), 4.0, 110)
    if shot.get("under_light"):
        area("under", (0.8, -1.0, -3.0), 3.0, 80)
        area("under2", (-1.5, 2.0, -2.0), 2.5, 40)


def look_at(ob, target, up=None):
    d = Vector(target) - Vector(ob.location)
    q = d.to_track_quat("-Z", "Y")
    ob.rotation_euler = q.to_euler()
    if up is not None:              # straight-down views: choose the image "up" direction
        ob.rotation_euler = (0, 0, 0)


def camera(sc, shot):
    cd = bpy.data.cameras.new("cam")
    ob = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(ob)
    sc.camera = ob
    cd.clip_start, cd.clip_end = 0.05, 100
    if "ortho" in shot:
        cd.type = "ORTHO"
        cd.ortho_scale = shot["ortho"]
    else:
        cd.lens = shot["lens"]
    return ob


def build(name, shot, turn=0.0):
    sc = reset()
    flat = shot.get("flat", False)
    root = bpy.data.objects.new("root", None)
    sc.collection.objects.link(root)
    root.matrix_world = Matrix.Rotation(turn, 4, "Z") @ root_matrix(flat)
    sec = shot.get("section")
    folder = os.path.join(EXPORT, "section_" + sec) if sec else EXPORT
    xcut = MAN["sections"][sec] if sec else 0.0
    explode = shot.get("explode", {})
    for g in shot["groups"]:
        dz = explode.get(g, 0.0)
        if g == "leds":
            add_leds(root, dz, shot.get("glow", 0.0), xcut if sec else -1e9)
            continue
        import_group(g, folder, root, dz)
        if g == "pcb":
            add_board_faces(root, dz, xcut)
    if "display_glass" in shot["groups"] and not sec:
        add_display_face(root, explode.get("display_glass", 0.0))
    if shot.get("legends") or name.startswith(("01", "04")):
        add_legends(root, explode.get("keycaps", 0.0))
    if shot.get("ground"):
        bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
        bpy.context.object.data.materials.append(material("ground", (0.80, 0.80, 0.81), 0.9))
    lights(sc, shot)
    cam = camera(sc, shot)
    if shot.get("annotate"):
        # orthographic side view, looking along +x at the cut face, centred on K6 / K10
        ky = (MAN["keys"]["K6"][1] + MAN["keys"]["K10"][1]) / 2
        c = root.matrix_world @ Vector((xcut, -ky, 2.0))
        cam.location = (-4, c.y, c.z)
        cam.rotation_euler = (math.radians(90), 0, math.radians(-90))
    else:
        cam.location = shot["cam"]
        look_at(cam, shot["target"], shot.get("up"))
    bpy.context.view_layer.update()
    return sc, root, cam


def to_pixel(sc, cam, root, p):
    v = world_to_camera_view(sc, cam, root.matrix_world @ Vector(p))
    return (v.x * RES[0], (1 - v.y) * RES[1])


def annotate(path, sc, cam, root, xcut):
    """Draw the stack dimensions onto the section render."""
    from PIL import Image, ImageDraw, ImageFont
    st = MAN["stack"]
    im = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except Exception:
        font = small = ImageFont.load_default()
    ky = MAN["keys"]["K6"][1]
    floor_in = MAN["floor"]["z_front_in"] - (H - ky) * math.tan(math.radians(MAN["tilt_deg"]))
    levels = [("keycap top", st["keycap_top"]), ("keycap bottom", st["keycap_bottom"]),
              ("switch housing top", st["switch_top"]), ("plate top", st["plate_top"]),
              ("plate bottom", st["plate_bottom"]), ("PCB top", st["pcb_top"]), ("PCB bottom", st["pcb_bottom"]),
              ("hotswap socket", st["socket_bottom"]), ("case floor (inside)", floor_in)]
    spans = [("keycap %.1f", st["keycap_bottom"], st["keycap_top"]),
             ("switch above plate %.1f", st["plate_top"], st["switch_top"]),
             ("plate %.1f", st["plate_bottom"], st["plate_top"]),
             ("plate to PCB %.1f", st["pcb_top"], st["plate_bottom"]),
             ("PCB %.1f", st["pcb_bottom"], st["pcb_top"]),
             ("socket %.1f", st["socket_bottom"], st["pcb_bottom"]),
             ("clear to floor %.1f", floor_in, st["socket_bottom"])]
    ink = (20, 20, 24)
    # the dimension line stands in the gap between K2 and K6
    x_line = to_pixel(sc, cam, root, (xcut, -(ky - 9.525), 0))[0]
    for _, z in levels:
        px, py = to_pixel(sc, cam, root, (xcut, -ky, z))
        d.line([(x_line - 16, py), (x_line + 16, py)], fill=ink, width=3)
    for i, (label, z1, z2) in enumerate(spans):
        y1 = to_pixel(sc, cam, root, (xcut, -ky, z1))[1]
        y2 = to_pixel(sc, cam, root, (xcut, -ky, z2))[1]
        d.line([(x_line, y1), (x_line, y2)], fill=(200, 60, 20), width=4)
        text = label % (z2 - z1) + " mm"
        tw = d.textlength(text, font=small)
        ty = (y1 + y2) / 2 - 13 + (0 if abs(y1 - y2) > 26 else (-12 if i % 2 else 12))
        tx = x_line - 34 - tw
        d.rounded_rectangle([tx - 8, ty - 3, tx + tw + 8, ty + 28], radius=6, fill=(255, 255, 255))
        d.text((tx, ty), text, fill=ink, font=small)
    d.text((40, 30), "Section through key column 2 (K2, K6, K10, K13). Flat case, no typing angle.",
           fill=ink, font=font)
    d.text((40, 66), "Heights are relative to the PCB top. Stack measured at K6.", fill=ink, font=small)
    total = st["keycap_top"] - floor_in
    d.text((40, RES[1] - 92), "keycap top to inner floor: %.1f mm" % total, fill=ink, font=small)
    d.text((40, RES[1] - 60), "case underside to top surface: %.1f mm, to keycap top: %.1f mm (without feet)"
           % (st["case_top"] - st["case_bottom"], st["keycap_top"] - st["case_bottom"]), fill=ink, font=small)
    im.save(path)


def render_still(name):
    shot = SHOTS[name]
    sc, root, cam = build(name, shot)
    path = os.path.join("/tmp/opncap_preview" if PREVIEW else OUT, name + ".png")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    if shot.get("annotate") and not PREVIEW:
        annotate(path, sc, cam, root, MAN["sections"][shot["section"]])
    print("rendered", path)


def render_turntable(frames=36):
    tmp = os.path.join(OUT, "_frames")
    os.makedirs(tmp, exist_ok=True)
    shot = dict(SHOTS["01_outside_hero"])
    for i in range(frames):
        sc, root, cam = build("01_turn", shot, turn=2 * math.pi * i / frames)
        add_legends(root, 0.0)
        sc.render.resolution_x, sc.render.resolution_y = 960, 540
        sc.cycles.samples = 20
        sc.render.filepath = os.path.join(tmp, "f%03d.png" % i)
        bpy.ops.render.render(write_still=True)
    out = os.path.join(OUT, "turntable.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "12", "-i", os.path.join(tmp, "f%03d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", out], check=True)
    print("rendered", out)


def main():
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    if "--turntable" in args:
        render_turntable()
        return
    only = None
    if "--only" in args:
        only = args[args.index("--only") + 1].split(",")
    for name in SHOTS:
        if only is None or any(name.startswith(o) for o in only):
            render_still(name)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Export fabrication data from hardware/pcb/opncap.kicad_pcb.

Gerbers and Excellon drill files come from kicad-cli, the BOM from the same
design model the board was built from, and the PNG previews are rendered from
the exported Gerbers with gerbv (not from the board file), to prove the
Gerbers themselves are readable.
"""
import csv
import glob
import os
import re
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_pcb                          # noqa: E402
import layout as L                      # noqa: E402

HW = gen_pcb.HW
PCB = gen_pcb.PCB_FILE
GERBER_DIR = os.path.join(HW, "pcb", "gerbers")
RENDERS = os.path.join(HW, "renders")
LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"

BOM_DESC = {
    1: "MCU module, on 2x20 pin headers (bom.md #1, headers #16)",
    3: "Kailh MX hotswap socket; carries one MX switch each (bom.md #2 and #3)",
    4: "Matrix diode SOD-123",
    5: "Per-key RGB LED, reverse mount",
    6: "Underglow RGB LED, reverse mount",
    7: "Rotary encoder with push switch",
    8: "Hall-effect joystick with push, placeholder footprint",
    9: "OLED module on 1x4 socket",
    10: "Level shifter SOIC-14",
    11: "LED data series resistor 0603",
    12: "Decoupling capacitor 0603",
    13: "LED supply bulk capacitor, radial D6.3 P2.5",
}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("FAILED: %s\n%s%s" % (" ".join(cmd), r.stdout, r.stderr))
    return r.stdout


def export_gerbers():
    shutil.rmtree(GERBER_DIR, ignore_errors=True)
    os.makedirs(GERBER_DIR)
    run(["kicad-cli", "pcb", "export", "gerbers", "-o", GERBER_DIR + "/", "-l", LAYERS,
         "--no-x2", "--no-netlist", "--subtract-soldermask", PCB])
    run(["kicad-cli", "pcb", "export", "drill", "-o", GERBER_DIR + "/", "--format", "excellon",
         "--excellon-units", "mm", "--excellon-zeros-format", "decimal", "--excellon-separate-th",
         "--drill-origin", "absolute", PCB])
    for f in glob.glob(os.path.join(GERBER_DIR, "*.gbrjob")):
        os.remove(f)
    files = sorted(os.listdir(GERBER_DIR))
    need = ["F_Cu.gtl", "B_Cu.gbl", "F_Mask.gts", "B_Mask.gbs", "F_Silkscreen.gto", "B_Silkscreen.gbo",
            "Edge_Cuts.gm1", "-PTH.drl", "-NPTH.drl"]
    for n in need:
        assert any(f.endswith(n) for f in files), "missing gerber output %s (have %s)" % (n, files)
    for f in files:
        head = open(os.path.join(GERBER_DIR, f), errors="replace").read(2000)
        if f.endswith(".drl"):
            assert head.startswith("M48"), f + " is not an Excellon file"
        else:
            assert "%FSLAX46Y46*%" in head and "%MOMM*%" in head, f + " is not RS-274X"
    zpath = os.path.join(HW, "pcb", "opncap_gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            info = zipfile.ZipInfo(f, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, open(os.path.join(GERBER_DIR, f), "rb").read())
    print("gerbers: %d files -> %s" % (len(files), os.path.relpath(zpath, HW)))
    return files


def gerber(name):
    return glob.glob(os.path.join(GERBER_DIR, "*" + name))[0]


def render_gerbers():
    """Render the exported Gerbers with gerbv. Also used as board textures by render.py."""
    from PIL import Image
    os.makedirs(RENDERS, exist_ok=True)
    for side, cu, mask, silk in (("top", "F_Cu.gtl", "F_Mask.gts", "F_Silkscreen.gto"),
                                 ("bottom", "B_Cu.gbl", "B_Mask.gbs", "B_Silkscreen.gbo")):
        out = os.path.join(RENDERS, "pcb_%s.png" % side)
        # first file is drawn on top
        cmd = ["gerbv", "-x", "png", "-D", "600", "-B", "0", "-a", "-b", "#14401f", "-o", out,
               "-f", "#101010ff", gerber("-NPTH.drl"),
               "-f", "#101010ff", gerber("-PTH.drl"),
               "-f", "#f2f2f2ff", gerber(silk),
               "-f", "#d9b23cff", gerber(mask),
               "-f", "#2e8f4aff", gerber(cu),
               "-f", "#e8e8e8ff", gerber("Edge_Cuts.gm1")]
        run(cmd)
        im = Image.open(out).convert("RGB")
        if side == "bottom":
            im = im.transpose(Image.FLIP_LEFT_RIGHT)      # view from below
            im.save(out)
        w, h = im.size
        ratio = (w / h) / (L.BOARD_W / L.BOARD_H)
        assert 0.97 < ratio < 1.03, "gerber render has the wrong aspect ratio (%s)" % ratio
        colours = len(im.resize((200, 268)).getcolors(100000))
        assert colours > 20, "gerber render looks empty"
        print("gerbv render: %s %dx%d" % (os.path.relpath(out, HW), w, h))


def export_positions():
    out = os.path.join(HW, "pcb", "positions.csv")
    run(["kicad-cli", "pcb", "export", "pos", "-o", out, "--format", "csv", "--units", "mm", "--side", "both", PCB])
    rows = list(csv.DictReader(open(out)))
    jlc = os.path.join(HW, "pcb", "positions_jlcpcb.csv")
    with open(jlc, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Val", "Package", "Mid X", "Mid Y", "Rotation", "Layer"])
        for r in rows:
            w.writerow([r["Ref"], r["Val"], r["Package"], r["PosX"], r["PosY"], r["Rot"], r["Side"]])
    print("positions: %d placements" % len(rows))
    return rows


def write_bom(comps, positions):
    groups = {}
    for c in comps:
        if c["bom"] == 0:
            continue
        key = (c["bom"], c["value"], c["fp"]["name"])
        groups.setdefault(key, []).append(c["ref"])
    out = os.path.join(HW, "pcb", "bom.csv")

    def refkey(r):
        m = re.match(r"([A-Z]+)(\d+)", r)
        return (m.group(1), int(m.group(2)))
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bom.md #", "Qty", "Designators", "Value", "Footprint", "Description"])
        for (item, value, fp), refs in sorted(groups.items()):
            w.writerow([item, len(refs), " ".join(sorted(refs, key=refkey)), value, fp, BOM_DESC[item]])
    # cross-check against hardware/bom.md
    expected = {}
    for line in open(os.path.join(HW, "bom.md")):
        m = re.match(r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|", line)
        if m:
            expected[int(m.group(1))] = int(m.group(2))
    qty = {}
    for (item, _, _), refs in groups.items():
        qty[item] = qty.get(item, 0) + len(refs)
    qty[2] = qty[3]                                 # one switch per socket
    bad = []
    for item in range(1, 14):
        if item == 12:
            ok = qty[item] <= expected[item]        # bom.md keeps one spare 100 nF
        else:
            ok = qty.get(item) == expected[item]
        if not ok:
            bad.append((item, qty.get(item), expected[item]))
    assert not bad, "bom.csv does not match bom.md: %s" % bad
    placed = {r["Ref"] for r in positions}
    missing = [c["ref"] for c in comps if c["bom"] and c["ref"] not in placed]
    assert not missing, "parts missing from positions.csv: %s" % missing
    print("bom: %d lines, quantities match bom.md (100 nF: %d used of %d listed)" % (len(groups), qty[12], expected[12]))


def export_schematic_pdf():
    out = os.path.join(HW, "pcb", "opncap_schematic.pdf")
    run(["kicad-cli", "sch", "export", "pdf", "-o", out, gen_pcb.SCH_FILE])
    print("schematic pdf: %s" % os.path.relpath(out, HW))


def main():
    comps = gen_pcb.build_design()
    export_schematic_pdf()
    export_gerbers()
    render_gerbers()
    pos = export_positions()
    write_bom(comps, pos)
    print("gen_fab: OK")


if __name__ == "__main__":
    main()

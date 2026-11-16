<!-- SPDX-License-Identifier: Apache-2.0 -->
# opncap hardware

**Status: everything here is generated and checked in software only. Nothing is ordered or tested on real hardware.**

The PCB, the fabrication files, the enclosure and the renders are all produced by the scripts in this folder. `scripts/layout.py` holds the mechanical layout once; the board generator and the enclosure both import it, and the enclosure script then reads the finished KiCad board back to check the fit.

## Results of the last run

| Check | Result |
|---|---|
| KiCad DRC (7.0.11) | 0 violations, 0 unconnected pads (`pcb/drc_report.txt`) |
| Schematic netlist against board | 267 pins, 0 differences |
| BOM against `bom.md` | quantities match |
| PCB outline in bottom case | 0.50 mm clearance on all sides (limit 0.30) |
| Mounting holes against standoffs | 6 of 6, offset 0.000 mm |
| Plate cut-outs against switches | 14 of 14, offset 0.000 mm (limit 0.05) |
| USB-C opening against BlackPill | centred, connector front 2.0 mm behind the outer wall |
| Part collisions | none (boolean intersection of all overlapping part pairs) |

The six enclosure checks are written to `enclosure/verification.txt` on every run. The case script exits with an error if one of them fails.

## Regenerate

From the repository root:

```sh
make hardware-venv    # once: two virtualenvs (KiCad + CadQuery, and Blender)
make hardware         # pinout, PCB, fabrication files, enclosure, renders, turntable
```

Single steps:

```sh
.venv/bin/python hardware/scripts/gen_pinout.py        # pinout.md, docs/pinout.md
.venv/bin/python hardware/scripts/gen_pcb.py           # board, schematic, project, DRC report
.venv/bin/python hardware/scripts/gen_fab.py           # Gerbers, drill, zip, BOM, positions, Gerber previews
.venv/bin/python hardware/enclosure/opncap_case.py     # STEP/STL, checks
.venv-render/bin/python hardware/scripts/render.py     # the eight stills
.venv-render/bin/python hardware/scripts/render.py --turntable
```

System packages needed: `kicad` (with `kicad-cli` and the `pcbnew` Python module), `gerbv`, `ffmpeg`. On Ubuntu 24.04: `apt-get install kicad gerbv ffmpeg`.

## Tool versions used

| Tool | Version | Used for |
|---|---|---|
| KiCad (`pcbnew`, `kicad-cli`) | 7.0.11 | board, DRC, Gerber, drill, positions, netlist, board STEP |
| gerbv | 2.10.0 | PNG previews rendered from the Gerbers |
| CadQuery | 2.8.0 | enclosure, placeholder parts, collision check |
| Blender (`bpy`) | 5.3.0, Cycles on CPU | renders |
| Python | 3.12 (KiCad, CadQuery), 3.13 (Blender) | |
| ffmpeg | system | turntable video |

## Deliverable status

| Deliverable | Status |
|---|---|
| KiCad project | Real KiCad files, but written by **KiCad 7.0.11, not 8+** as asked: version 8 and later could not be installed in the build environment. KiCad 8 and later open and convert these files. |
| DRC | Real KiCad DRC engine (7.0.11) through `pcbnew.WriteDRCReport`. Run it once more in your KiCad version. |
| Schematic | **Approximate.** A netlist-style sheet: every part with net labels on its pins, no drawn wires. Netlist equals the board. ERC not run. |
| Gerbers and drill | Real, from `kicad-cli`: RS-274X with Protel extensions, Excellon in mm, PTH and NPTH separate. Read back and rendered with gerbv. Not uploaded to any manufacturer. |
| BOM and positions | Real exports. Rotations are not adapted to JLCPCB conventions. |
| Enclosure | Real CadQuery solids, STEP and STL. Not reviewed for printing. |
| Part models | **Approximate** by design: simple placeholders with nominal dimensions. The joystick is a guess (datasheet unconfirmed). The display module is modelled from its published carrier size; header and panel position are assumed. |
| Renders | Real Blender Cycles renders of the exported geometry. The copper on the board faces is the gerbv image of the Gerbers. Key legends and the display content are added in the render script. |

See `DESIGN_NOTES.md` for the decisions taken, the assumptions to verify and the known gaps.

## File map

```
hardware/
  README.md               this file
  DESIGN_NOTES.md         decisions, assumptions, known gaps, design language
  bom.md                  source of truth for parts and quantities
  pinout.yaml             source of truth for the pin assignment
  pinout.md               generated from pinout.yaml (also docs/pinout.md)
  Makefile                regeneration targets
  scripts/
    layout.py             shared mechanical layout (board, keys, parts, stack heights)
    router.py             two-layer grid router
    gen_pcb.py            board, schematic, project file, DRC, netlist check
    gen_fab.py            Gerbers, drill, zip, BOM, positions, gerbv previews
    gen_pinout.py         pinout documents
    render.py             Blender renders and turntable
  pcb/
    opncap.kicad_pro / .kicad_sch / .kicad_pcb
    drc_report.txt
    gerbers/              11 files: copper, mask, paste, silkscreen, edge cuts, PTH and NPTH drill
    opncap_gerbers.zip    the same files, ready to upload
    bom.csv
    bom_jlcpcb.csv        parts with LCSC numbers, in the JLCPCB upload layout
    positions.csv         KiCad pick-and-place export
    positions_jlcpcb.csv  same data with JLCPCB column names
  enclosure/
    opncap_case.py        parametric case, plate, placeholder parts, checks, export
    verification.txt      result of the last check run
    export/
      bottom_case, top_case, plate          .step and .stl
      pcb.step / pcb.stl                    board exported by KiCad
      choc_switch, keycap_1u, hotswap_socket  single placeholder parts
      switches, keycaps, keycaps_accent, sockets, encoder, knob, joystick,
      joystick_cap, display, display_glass, blackpill_pcb, blackpill_parts, usb_c,
      smd, leds, spacers, feet              placed part groups, .step and .stl
      opncap_assembly.step                  everything assembled, with colours
      section_key_column/, section_usb_centre/   cut bodies for the section renders
      manifest.json                         colours and heights for render.py
  renders/
    pcb_top.png, pcb_bottom.png             rendered from the Gerbers with gerbv
    01_outside_hero.png ... 08_section_side.png
    turntable.mp4
```

## Dimensions

- PCB 102 x 137 x 1.6 mm, corner radius 3 mm, two layers.
- Case 101.8 x 133.0 x 16.9 mm, flat (no typing angle), shell on a translucent base. 19.7 mm to the keycap tops; feet add 1.2 mm. Knob and joystick stand above that.
- Kailh Choc V1 hotswap, key pitch 19.05 mm. Plate 1.2 mm, top 2.2 mm above the PCB top.
- Round 1.28" GC9A01 display behind a 33 mm window.
- PDM microphone (IM69D130) left of K13 and a status light right of K14. The microphone needs firmware that does not exist yet.
- `DESIGN_NOTES.md` has the height budget and what would make the case flatter.

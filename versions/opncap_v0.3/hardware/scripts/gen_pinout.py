#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Render hardware/pinout.md and docs/pinout.md from hardware/pinout.yaml."""
import os

import yaml

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HW)


def main():
    d = yaml.safe_load(open(os.path.join(HW, "pinout.yaml")))
    out = ["<!-- SPDX-License-Identifier: Apache-2.0 -->",
           "<!-- Generated from hardware/pinout.yaml by hardware/scripts/gen_pinout.py. Do not edit. -->",
           "# opncap pinout", "",
           "MCU: %s. Mounting: %s." % (d["mcu"]["board"], d["mcu"]["mounting"]), "",
           "Status: generated, not tested on hardware.", "",
           "| Signal | STM32 pin | Function | Note |", "|---|---|---|---|"]
    for name, s in d["signals"].items():
        out.append("| %s | %s | %s | %s |" % (name, s["pin"], s["function"], s.get("note", "")))
    out += ["", "## Power", "", "| Net | Source and use |", "|---|---|"]
    for k, v in d["power"].items():
        out.append("| %s | %s |" % (k, v))
    out += ["", "## Reserved pins", "", "| STM32 pin | Reason |", "|---|---|"]
    for k, v in d["reserved"].items():
        out.append("| %s | %s |" % (k, v))
    out += ["", "## Matrix (COL2ROW)", "", "| | " + " | ".join(d["matrix"]["cols"]) + " |",
            "|---|" + "---|" * len(d["matrix"]["cols"])]
    for row, cells in zip(d["matrix"]["rows"], d["matrix"]["layout"]):
        out.append("| %s | %s |" % (row, " | ".join(cells)))
    out += ["", "## LED chain", "",
            "Per key, in data order: " + ", ".join(d["led_chain"]["per_key"]) + ".", "",
            "Then underglow: " + ", ".join(d["led_chain"]["underglow"]) + ".", "",
            "## Layout", "", "```", d["layout_ascii"].rstrip("\n"), "```", ""]
    text = "\n".join(out)
    for path in (os.path.join(HW, "pinout.md"), os.path.join(ROOT, "docs", "pinout.md")):
        open(path, "w").write(text)
    print("gen_pinout: OK")


if __name__ == "__main__":
    main()

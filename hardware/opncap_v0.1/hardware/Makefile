# SPDX-License-Identifier: Apache-2.0
# Regenerate all opncap hardware files. Run from the repository root: make hardware
PY      ?= .venv/bin/python
PY_BPY  ?= .venv-render/bin/python
HW      := hardware

.PHONY: hardware venv pinout pcb fab case renders turntable

hardware: pinout pcb fab case renders turntable

venv:
	uv venv --python /usr/bin/python3.12 --system-site-packages .venv
	uv pip install --python .venv/bin/python cadquery pyyaml pillow numpy
	uv venv --python /usr/bin/python3.13 .venv-render
	uv pip install --python .venv-render/bin/python bpy pillow numpy

pinout:
	$(PY) $(HW)/scripts/gen_pinout.py

pcb:
	$(PY) $(HW)/scripts/gen_pcb.py

fab:
	$(PY) $(HW)/scripts/gen_fab.py

case:
	$(PY) $(HW)/enclosure/opncap_case.py

renders:
	$(PY_BPY) $(HW)/scripts/render.py

turntable:
	$(PY_BPY) $(HW)/scripts/render.py --turntable

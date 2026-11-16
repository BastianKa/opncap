<!-- SPDX-License-Identifier: Apache-2.0 -->
# opncap software

Reference hardware is `hardware/opncap_v0.3`. See `spec.md` and `features.md` for the plan.

| Path | Content | Status |
|---|---|---|
| `protocol/` | Raw HID protocol v1 (YAML source, generator, shared test vectors) | built, tested in CI |
| `host/` | Python host package (`opncap_host`), protocol bindings are generated | protocol only |
| `firmware/` | QMK userspace for the BlackPill F411 (keys, layers, encoder, joystick, raw HID) | written; builds in CI (pinned QMK), **not tested on hardware** |
| `docs/` | Licensing and other docs | started |

```sh
cd software
make gen    # regenerate the C header and the Python module after editing protocol.yaml
make test   # check generated files, run Python and C tests
```

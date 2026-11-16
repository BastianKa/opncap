# opncap — Spezifikation

> **Kontext:** Ein quelloffenes, kabelgebundenes und später BLE-fähiges Makropad mit eigenem Design, inspiriert von der Idee eines kompakten Schreibtisch-Controllers. Es soll KI-Coding-Agenten (Status-LEDs, Radial-Menü) und alltägliche App-Shortcuts bedienen. Diese Spezifikation stammt aus der Planungsdiskussion; mit **[prüfen]** markierte Punkte wurden noch nicht gegen QMK-, ChibiOS-, Zephyr- oder MCUboot-Quellen verifiziert.

## Überblick

opncap ist ein Makropad mit 14 Tasten, einem Drehregler (mit Druckfunktion), einem Hall-Effekt-Joystick (mit Druckfunktion), einem kleinen OLED sowie Per-Key-RGB und Underglow. Es arbeitet über USB und später über BLE. Eine Companion-App (zuerst als CLI) setzt LED-Zustände aus Tools wie Claude Code oder Codex, zeigt ein vom Joystick gesteuertes Radial-Menü als Overlay und wechselt Layer und LED-Farben abhängig von der aktiven Anwendung. Es ist kein Klon eines kommerziellen Produkts: Gehäuse, Name, Branding und Konfigurations-App sind eigenständig.

---

## Ziele

- Phase 1 (kabelgebunden): ein QMK-Keyboard auf einem WeAct BlackPill F411 mit 14 Tasten, Encoder, Joystick, OLED, RGB Matrix und Raw HID, dessen Build in der CI grün ist.
- Ein versioniertes, CRC-gesichertes Raw-HID-Protokoll (v1) mit einer einzigen YAML-Quelle, aus der C-Header und Python-Modul generiert werden.
- Eine CLI `micro-state idle|thinking|done|input|error`, die Agent-Status-LEDs unter Linux, macOS und Windows setzt.
- Ein dokumentierter Weg zu Phase 2: BLE über eine nRF52840-Brücke und Firmware-Updates per USB-DFU, später über die Brücke.
- Jede Aussage in der Doku ist als „gebaut (CI)" oder „auf Hardware getestet" gekennzeichnet; Hardware-Tests führt der Maintainer durch.
- Die Lizenzierung ist klar getrennt: GPL-2.0-or-later für QMK-Teile, Apache-2.0 für alles andere.

---

## Nutzerrollen

### Besitzer / Endnutzer
- Nutzt das Pad, bearbeitet Keymaps und Layer, wählt LED-Stromprofile, führt CLI und Companion-App aus.
- Verbindet per USB (Phase 1) oder BLE (Phase 2); die Ausgabe läuft über USB, wenn eingesteckt, sonst über BLE.

### Entwickler / Contributor
- Baut die Firmware, erweitert das Protokoll, schreibt App-Code.
- Arbeitet im Repo, die CI ist der Gatekeeper; Protokolländerungen laufen über die YAML-Quelle.

### Agent-Tool (Claude Code, Codex, Skripte)
- Ruft `micro-state` aus Hooks auf, um den LED-Zustand zu setzen. Hat keinen weiteren Zugriff auf das Gerät.

---

## Kernfunktionen

### 1. Tasten, Matrix und Layer

14 MX-Hotswap-Tasten (K1–K12 in einem 3x4-Raster, K13 und K14 als untere Zweiergruppe) in einer 4x4-Diodenmatrix (`COL2ROW`, eine Diode pro Taste). Die Matrix hat 16 Positionen: 14 Tasten plus Encoder-Push plus Joystick-Push, sie ist also voll belegt. 6 Layer. K13 und K14 haben standardmäßig denselben Keycode (wie eine geteilte Leertaste) und lassen sich in der Keymap getrennt belegen.

### 2. Drehregler

Ein Encoder mit Push, pro Layer über die QMK-`ENCODER_MAP` belegbar. Der Push ist eine Matrix-Taste.

### 3. Hall-Effekt-Joystick

Zwei ADC-Kanäle (X/Y) plus Push in der Matrix. Software-Kalibrierung: Mittelpunkt beim Start, Totzone, Min/Max-Tracking. Sendet ein Event mit 8 Richtungen plus Mitte und einen Radial-Slot-Index (7 Slots) an die Companion-App. Der Prototyp geht von einem 3,3-V-Analogmodul mit Push aus (z. B. aus der Klasse FJH10K-S3D; Datenblatt, Spannung und Pinbelegung müssen vor der Bestellung beim Verkäufer bestätigt werden). Das finale Modul wird gewählt, sobald der Prototyp läuft; 5-V-Teile (z. B. Alps RKJXM1015004) erfordern Pegelanpassung und eine Stromprüfung.

### 4. RGB und LED-Stromprofile

Eine WS2812/SK6812-LED pro Taste plus Underglow, angesteuert über QMK RGB Matrix. Der Nutzer wählt ein Stromprofil: `full` (Per-Key-Feedback, Standard am Kabel), `reduced` (gedimmt, nur aktive Tasten) und `minimal` (nur Status-LED, Standard im Akkubetrieb). Phase 1 setzt die Profile in der RGB-Logik um; das automatische Umschalten nach Stromquelle folgt in Phase 2. Das Protokoll reserviert dafür ein Feld.

### 5. OLED

Ein kleines I²C-OLED (Klasse SSD1306, 128x32 oder 128x64) zwischen Encoder (links) und Joystick (rechts). Es zeigt Layer und Agent-Zustand an. Gilt in Phase 2 als Akku-Risiko.

### 6. Raw-HID-Protokoll v1

Feste 32-Byte-Frames, little-endian: Magic, Version, Befehl/Event, Sequenznummer, Länge, Payload, CRC (CRC-16/CCITT-FALSE, endgültige Wahl im Review). Befehle: `get_version`, `set_led`, `set_state`. Events: Joystick-Richtung (mit Radial-Slot), Encoder, Layer-Wechsel. Spezifiziert als Markdown unter `protocol/`, generiert aus einer YAML-Datei in einen C-Header (QMK) und ein Python-Modul (später ein Rust-Crate). Getestet mit gemeinsamen Testvektoren (CRC, Roundtrip, fehlerhafte Frames); der C-Code wird auf dem Host kompiliert und ausgeführt.

### 7. Companion-App und CLI `micro-state`

Phase 1: eine Python-CLI mit `hidapi`, die das Gerät über VID/PID und Usage Page auswählt, mit den Optionen `--device` und `--timeout` und aussagekräftigen Exit-Codes. Läuft unter Linux (udev-Regeln werden mitgeliefert), macOS (die Berechtigung „Input Monitoring" ist ein bekanntes Risiko) und Windows **[prüfen]**. Hook-Beispiele für Claude Code und Codex sind dokumentiert. Später: Radial-Menü-Overlay und App-Presets pro Anwendung (aktive App erkennen, Layer und LED-Farbe wechseln). Ein Rust-Rewrite ist geplant, sobald die Python-Version stabil ist.

### 8. BLE-Brücke (Phase 2, in Phase 1 nicht gebaut)

Ein nRF52840-Modul (z. B. Raytac MDBT50Q) mit Zephyr nimmt HID-Reports vom STM32 per UART entgegen und sendet sie als BLE HID. Ein eigener GATT-Dienst transportiert Konfiguration, LED-Status und Radial-Menü-Daten, weil Raw HID über BLE unter Windows und macOS kaum nutzbar ist. Die Ausgabe läuft über USB, wenn eingesteckt, sonst über BLE.

### 9. Firmware-Updates (Phase 2, unbestätigtes Konzept)

STM32: USB-DFU über BOOT0 oder OTA über die Brücke (UART plus ST-ROM-Bootloader, die Brücke steuert BOOT0 und NRST). nRF52840: MCUboot mit Serial Recovery und BLE-DFU (mcumgr/SMP). Machbarkeit und Risiken stehen in `docs/risks.md`: Abbruch während des Updates (Brick-Risiko), die vom ROM-Bootloader der gewählten Variante erwarteten UART-Pins und die Update-Dauer bei BLE-Durchsatz.

### 10. Repository, CI und Lizenzen

Struktur: `firmware/qmk/`, `firmware/bridge/`, `protocol/`, `app/`, `hardware/`, `docs/` (mit ADRs), `.github/workflows/`. CI: QMK-Build, Protokoll-Tests, Python-Lint und -Tests auf Ubuntu-, macOS- und Windows-Runnern sowie ein Platzhalter-Workflow für Zephyr. Jede Datei trägt einen SPDX-Header; `docs/licensing.md` erklärt die Grenze zwischen GPL und Apache. Code aus dem Keychron-QMK-Fork bleibt GPL und wird gekennzeichnet. Commits sind konventionell und klein; Code, Kommentare, Commits und Doku sind auf Englisch.

### 11. Pinout und Hardware-Doku

Eine Quelldatei (`hardware/pinout.yaml`) erzeugt `hardware/pinout.md` und `docs/pinout.md`. KiCad-Projekt und Stückliste beginnen als Platzhalter. Das Layout mit 14 Tasten:

```
 ( ENC )    [  OLED  ]    ( JOY )
 (push )                  ( hall)

        [K1]  [K2]  [K3]  [K4]
        [K5]  [K6]  [K7]  [K8]
        [K9]  [K10] [K11] [K12]

               [K13] [K14]
```

---

## Technischer Stack

- **Haupt-MCU** — STM32F411 (WeAct BlackPill) für den Prototyp; ein Low-Power-STM32 (L4-Serie) für die finale Platine, Support in QMK/ChibiOS **[prüfen]**
- **Tastatur-Firmware** — QMK-Userspace (GPL-2.0-or-later), fest gepinnte QMK-Version
- **BLE-Brücke** — nRF52840-Modul, Zephyr, MCUboot (Phase 2)
- **Protokoll** — Raw HID, YAML-Quelle mit generierten C- und Python-Bindings (später Rust)
- **Companion-App** — Python-CLI (`hidapi`), später Rust, optional Tauri für die GUI
- **CI** — GitHub Actions (Ubuntu, macOS, Windows)
- **Hardware** — KiCad, MX-Hotswap, SK6812/WS2812, SSD1306-OLED, Hall-Effekt-Joystick

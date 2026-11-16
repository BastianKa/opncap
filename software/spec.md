# opncap Software — Spezifikation

> **Kontext:** Software-Teil des quelloffenen Makropads opncap (Hardware: `hardware/opncap_v0.3`). Die Funktionen orientieren sich am Konzept des Codex Micro (Agent Keys mit Status-LEDs, Command Keys, Analog-Stick, Drehregler, Sprachsteuerung), sind aber eigenständig und nicht auf eine Anwendung festgelegt. Mit **[prüfen]** markierte Punkte sind noch nicht gegen die jeweilige Dokumentation oder Hardware verifiziert.

## Überblick

Die Software besteht aus vier Teilen: der QMK-Firmware auf dem Pad, einem versionierten Raw-HID-Protokoll, einem Host-Dienst mit CLI `micro-state` und einer Konfigurations-App. Der Host-Dienst nimmt Zustände von KI-Agenten entgegen, zeigt sie auf Tasten-LEDs und Display, und übersetzt Eingaben des Pads (Tasten, Joystick, Encoder, Sprache) über Adapter in Aktionen. Der erste Adapter ist Claude Code, danach folgen Codex und die ChatGPT-Desktop-App.

---

## Ziele

- Phase 1 (kabelgebunden): Firmware, Protokoll v1, Host-Dienst und CLI laufen unter Linux und macOS, die CI ist grün; Windows folgt nach der stabilen Python-Version.
- Der Zustand von Claude-Code-Sitzungen erscheint ohne Fensterwechsel auf den Agent Keys.
- Eine Aktions-Engine mit Adapterschnittstelle, sodass Codex und die ChatGPT-Desktop-App ohne Umbau des Kerns folgen können.
- Eine Konfigurations-App, in der alle Belegungen geändert werden, ohne Firmware neu zu bauen.
- Ein dokumentierter Weg zu Phase 2: BLE-Brücke und Firmware-Updates.
- Jede Aussage in der Doku ist als „gebaut (CI)" oder „auf Hardware getestet" gekennzeichnet.
- Lizenzen: GPL-2.0-or-later für QMK-Teile, Apache-2.0 für alles andere.

---

## Nutzerrollen

### Besitzer / Endnutzer
- Nutzt das Pad mit Claude Code (später Codex und ChatGPT), ändert Belegungen, Layer und Beleuchtung in der Konfigurations-App.

### Entwickler / Contributor
- Baut Firmware und Host, erweitert Protokoll und Adapter; die CI ist der Gatekeeper und Protokolländerungen laufen über die YAML-Quelle.

### Agent-Tool (Claude Code, Codex, Skripte)
- Meldet Zustände über Hooks oder `micro-state` an den Host-Dienst und hat keinen weiteren Zugriff auf das Gerät.

---

## Kernfunktionen

### 1. Repository, Lizenzen und CI

Ordner `software/` mit `firmware/`, `protocol/`, `host/`, `app/` und `docs/`. CI auf Ubuntu und macOS (Windows später): Firmware-Build, Protokoll-Tests, Lint und Tests der Host-Software. SPDX-Header in jeder Datei, `docs/licensing.md` beschreibt die Grenze zwischen GPL und Apache. Code, Kommentare, Commits und Doku sind auf Englisch.

### 2. Raw-HID-Protokoll v1

Feste 32-Byte-Frames, little-endian: Magic, Version, Befehl/Event, Sequenznummer, Länge, Payload, CRC-16/CCITT-FALSE. Befehle: `get_version`, `set_led`, `set_state`, `set_agent_state`, `set_display`, `set_config`. Events: Taste, Encoder, Joystick (Richtung und Radial-Slot), Layer, Mikrofon. Einzige Quelle ist eine YAML-Datei, daraus entstehen C-Header und Python-Modul. Gemeinsame Testvektoren prüfen CRC, Roundtrip und fehlerhafte Frames.

### 3. Firmware-Grundlage

QMK-Userspace auf dem WeAct BlackPill F411 in fester Version. 14 Tasten in einer 4x4-Matrix, sechs Layer, Encoder mit Push, Hall-Joystick mit Kalibrierung (Mittelpunkt beim Start, Totzone, Min/Max), RGB Matrix, rundes SPI-Display und PDM-Mikrofon (IM69D130) laut `hardware/opncap_v0.3/hardware/pinout.md`. Die Firmware hält die Belegung und sendet Events an den Host.

### 4. Host-Dienst und CLI `micro-state`

Hintergrunddienst in Python mit `hidapi`, Auswahl des Geräts über VID/PID und Usage Page. CLI `micro-state idle|thinking|done|input|error` mit `--device`, `--timeout` und klaren Exit-Codes. Linux mit mitgelieferten udev-Regeln, macOS mit Berechtigung „Input Monitoring". Windows ist in Phase 1 nicht unterstützt. Später ein Rust-Rewrite.

### 5. Agent-Status und Agent Keys

Sechs Agent Keys (K1–K6) zeigen den Zustand einer Sitzung: weiß inaktiv, blau arbeitet, grün fertig und ungelesen, orange Eingabe oder Freigabe nötig, rot Fehler, aus keine Zuordnung. Die Taste der gewählten Sitzung pulsiert. Sitzungen werden nach Aktualität zugeordnet, angepinnte, aktive und wartende haben Vorrang, eigene Zuordnungen sind möglich. Druck wechselt die Sitzung, Doppeldruck innerhalb von 350 ms holt zusätzlich das Fenster nach vorn, eine freie Taste öffnet eine neue Sitzung.

### 6. Command Keys und Aktionskatalog

Sechs Tasten (K7–K12) mit Standardbelegung: Fast Mode, Anfrage genehmigen, ablehnen, in neuem Chat fortsetzen, Push-to-Talk, Nachricht senden. Weitere Aktionen aus einem Katalog: Browser, Terminal, Änderungen prüfen, Git, Pull Request, Anhänge, Plugins, geplante Tasks, Reasoning-Aufwand, Skills, eigene Tastenkürzel. Eine belegte Taste tauscht beim Neubelegen den Platz mit der alten Aktion.

### 7. Aktions-Engine und Adapter

Die Engine schlägt zu jedem Event die Belegung im aktiven Profil nach und führt sie über einen Adapter aus. Reihenfolge der Adapter: Claude Code zuerst, dann Codex, dann die ChatGPT-Desktop-App, dazu Terminal und generischer Tastenkürzel-Sender. Eine dokumentierte Adapterschnittstelle erlaubt neue Ziele. Fehler führen zu einem roten Signal am Pad und einem Protokolleintrag.

#### Claude-Code-Adapter (Phase 1)

Zustände kommen über Claude-Code-Hooks (laut Hooks-Dokumentation geprüft, Stand der Recherche), die `micro-state` oder den Host-Dienst aufrufen. Jede Hook-Eingabe enthält `session_id` und `cwd`; damit werden parallele Sitzungen getrennt und beim `SessionStart` einer Agent-Taste zugeordnet.

| Hook-Ereignis | LED-Zustand |
|---|---|
| `SessionStart` | weiß |
| `UserPromptSubmit`, `PreToolUse` | blau |
| `PermissionRequest`, `Notification` mit `permission_prompt` oder `idle_prompt` | orange |
| `Stop` | grün |
| `StopFailure` (API-Fehler) | rot |
| `PostToolUseFailure` | kurzes rotes Blinken, Zustand bleibt blau |
| `SessionEnd` | aus |

Freigabe und Ablehnung laufen über einen `PermissionRequest`-Hook, der eine Entscheidung zurückgeben kann (Command- oder HTTP-Hook). Der Host-Dienst hält die Anfrage offen, bis der Nutzer die Freigabe- oder Ablehnen-Taste drückt, und liefert dann `allow` oder `deny`. Einen dokumentierten Weg, Tastenanschläge von außen in eine laufende interaktive Sitzung zu schicken, gibt es nicht.

Offen und vor dem Bau zu testen **[prüfen]**: genaue Form der `deny`-Antwort, Verhalten bei Zeitüberschreitung des Hooks (Rückfall auf die normale Abfrage im Terminal muss funktionieren), Timeout-Standardwert (Dokumentation widersprüchlich, daher `timeout` explizit setzen), Matcher-Syntax für `PermissionRequest`. Außerdem feuert `Stop` nicht bei einem Abbruch durch den Nutzer; der Adapter braucht deshalb eine Zeitüberwachung, damit eine Taste nicht dauerhaft blau bleibt.

#### Codex-Adapter (Phase 1b)

Nutzt dieselbe Engine, Protokolle und Zustandsmodelle. Neu ist nur die Anbindung der Zustandsquelle (Hooks oder Benachrichtigungsmechanismus von Codex **[prüfen]**) und der Tastenanschläge. Der Aufwand ist daher klein bis mittel, solange der Claude-Code-Adapter sauber hinter der Adapterschnittstelle liegt.

#### ChatGPT-Desktop-Adapter (später)

Steuerung über Tastenkürzel und Betriebssystem-Automatisierung der Desktop-App. Hängt von den dort verfügbaren Befehlen und Berechtigungen ab **[prüfen]**.

### 8. Joystick und Radial-Menü

Vier Richtungsaktionen mit Standard: Plan Mode, Seitenleiste, Verlauf zurück und vorwärts. Gedrückt gehaltener Joystick öffnet ein Radial-Menü mit sieben Slots auf Display und als Bildschirm-Overlay. Das Event enthält 8 Richtungen, Mitte und den Slot-Index.

### 9. Drehregler

Vier Modi: Composer-Navigation, nur Reasoning, Konversations-Scrollen, eigene Belegung (Links, Rechts, kurzer und langer Druck). Langer Druck öffnet die Einstellungen. Der aktuelle Modus und Wert erscheinen auf dem Display.

### 10. Sprachsteuerung

Push-to-Talk auf K13 (halten), Dauermodus per Doppeldruck innerhalb von 350 ms, Senden über eine Command Key, Sprachchat und Stummschaltung auf K14. **Phase 1 nutzt das Mikrofon des Rechners:** die Tasten lösen das Diktat des Rechners oder der Anwendung aus. Das Pad hat zwar ein PDM-Mikrofon (IM69D130 an B3/B5 über I2S3), aber dafür fehlt die Firmware: Der PDM-Strom müsste gelesen, zu PCM gefiltert und als USB-Audio-Schnittstelle neben der Tastatur angeboten werden, und QMK bietet dafür keine Unterstützung. Das ist ein eigenes späteres Firmware-Projekt. Bis dahin ist das Mikrofon nur Hardware-Vorbereitung. LED-Rückmeldung: türkis bei Aufnahme, bewegtes Weiß bei Verarbeitung, Weiß bei bereitem Text.

### 11. Display und Beleuchtung

Das runde GC9A01-Display zeigt Uhrzeit, Layer, Agent-Zustand, Radial-Menü, Pegel und Akku. Helligkeit, Auto-Dimming, Abschaltintervall von 30 Sekunden bis eine Stunde (Standard drei Minuten) und Stromprofile `full`, `reduced`, `minimal` sind einstellbar. Statusänderungen und Eingaben schalten die Beleuchtung wieder ein. **Risiko [prüfen]:** Ob das Quantum Painter von QMK das GC9A01 auf dem STM32F411 mit dem begrenzten RAM (ein 240x240-Vollbild in RGB565 belegt etwa 115 KB) und neben Tastenscan, RGB-Updates und Raw HID ruckelfrei betreiben kann, ist nicht geprüft. Fallback: nur Teilbereiche zeichnen oder ein eigener schlanker Treiber.

### 12. Konfigurations-App und Profile

Grafische App für Linux und macOS (zuerst Python, später optional Tauri **[prüfen]**). Ansicht mit Pad-Grafik, Belegung pro Taste, Encoder und Joystick-Richtung, Layer und anwendungsabhängige Profile. Bis zu fünf zusätzliche Layer über den KI-Layer hinaus. Zurücksetzen setzt Command Keys und Joystick auf Standard, die Agent-Key-Zuordnung bleibt. Export und Import als Datei.

### 13. Einrichtung und Diagnose

Assistent für Verbindung, Berechtigungen und Firmware-Version, dazu ein Diagnosemodus, der jeden Eingang live zeigt, und ein exportierbares Diagnoseprotokoll.

### 14. BLE-Brücke (Phase 2, nicht in Phase 1 gebaut)

nRF52840 mit Zephyr nimmt HID-Reports per UART entgegen und sendet BLE HID. Ein eigener GATT-Dienst transportiert Konfiguration, LED-Status und Radial-Menü-Daten. Drei Bluetooth-Kanäle, Wechsel zwischen USB und BLE. Ist das Pad an USB angeschlossen, wird dorthin gesendet, sonst über BLE.

### 15. Firmware-Updates (Phase 2, unbestätigtes Konzept)

STM32 über USB-DFU, später per Brücke (UART und ST-ROM-Bootloader, Brücke steuert BOOT0 und NRST). nRF52840 über MCUboot und BLE-DFU. Risiken (Abbruch, Pin-Erwartungen, Update-Dauer) stehen in `docs/risks.md`.

---

## Technischer Stack

- **Firmware** — QMK-Userspace (GPL-2.0-or-later), STM32F411, gepinnte QMK-Version
- **Protokoll** — Raw HID, YAML-Quelle mit generierten C- und Python-Bindings
- **Host** — Python mit `hidapi`, später Rust
- **Konfigurations-App** — zuerst Python, optional Tauri
- **Adapter** — Claude Code (Hooks), Codex, ChatGPT-Desktop-App
- **BLE (Phase 2)** — nRF52840, Zephyr, MCUboot
- **CI** — GitHub Actions (Ubuntu, macOS; Windows später)

# opncap — Features

---

## 1. Repository, Lizenzen und CI

Das Grundgerüst, auf dem alle weiteren Features aufbauen, für Entwickler und Contributor.

**User flow**
1. Der Entwickler klont das Repo und sieht die Struktur `firmware/`, `protocol/`, `app/`, `hardware/`, `docs/` und `.github/workflows/`.
2. Er öffnet `docs/licensing.md` und erfährt, welche Teile GPL-2.0-or-later und welche Apache-2.0 sind.
3. Er pusht einen Commit oder Pull Request.
4. Die CI baut die QMK-Firmware, führt Protokoll-Tests aus und prüft die Python-CLI auf Ubuntu, macOS und Windows.
5. Er sieht das Ergebnis als grünen oder roten Status am Commit.

**UI overview**
Es gibt keine Oberfläche außer der Repo-Struktur, der README und den GitHub-Actions-Statusanzeigen. Jede Datei trägt einen SPDX-Lizenzheader. Der Zephyr-Workflow existiert als Platzhalter und ist in Phase 1 deaktiviert.

---

## 2. Pinout und Hardware-Doku

Eine verlässliche Belegung aller Pins des BlackPill-Prototyps für Entwickler und Hardware-Tester.

**User flow**
1. Der Entwickler öffnet `hardware/pinout.md` oder `docs/pinout.md`.
2. Er sieht die Zuordnung von Matrix-Zeilen und -Spalten, Encoder, Joystick-ADC, WS2812-Datenpin und I²C-Pins des OLED.
3. Er ändert bei Bedarf nur `hardware/pinout.yaml`.
4. Die beiden Markdown-Dateien werden daraus erzeugt und bleiben so identisch.

**UI overview**
Tabellen mit Signalname, STM32-Pin, Funktion und Bemerkung, dazu das Tastenlayout als ASCII-Skizze. Stückliste und KiCad-Projekt sind zunächst Platzhalter.

---

## 3. Tasten, Matrix und Layer

Die 14 Tasten mit sechs Layern als Grundfunktion des Pads, für den Endnutzer.

**User flow**
1. Der Nutzer verbindet das Pad per USB mit dem Rechner.
2. Er drückt K1 bis K14 und löst die im aktiven Layer belegten Keycodes aus.
3. Er wechselt den Layer über eine dafür belegte Taste.
4. Er bindet K13 und K14 in der Keymap entweder auf denselben Keycode oder auf getrennte Aktionen.

**UI overview**
Eine 3x4-Tastengruppe plus ein Tastenpaar darunter. Jede Taste hat eine Diode in der Matrix und eine eigene LED. Die Keymap wird als QMK-Quelldatei gepflegt, eine grafische Oberfläche gibt es in Phase 1 nicht.

---

## 4. Drehregler

Ein Encoder mit Push, der pro Layer eigene Aktionen auslöst, für den Endnutzer.

**User flow**
1. Der Nutzer dreht den Encoder nach links oder rechts.
2. Das Pad sendet die für den aktiven Layer in der `ENCODER_MAP` hinterlegten Keycodes.
3. Er drückt den Encoder und löst die Matrix-Taste des Push aus.
4. Er wechselt den Layer und erhält andere Encoder-Aktionen.

**UI overview**
Ein physischer Drehregler links neben dem OLED. Das Verhalten wird in der Keymap festgelegt, das OLED zeigt den aktiven Layer.

---

## 5. Hall-Effekt-Joystick

Ein analoger Joystick mit Push, der Richtungen und Radial-Slots erzeugt, für den Endnutzer.

**User flow**
1. Der Nutzer schaltet das Pad ein, der Joystick kalibriert den Mittelpunkt beim Start.
2. Er bewegt den Joystick in eine Richtung.
3. Das Pad erkennt eine von acht Richtungen oder die Mitte und berechnet daraus den Radial-Slot (1 bis 7).
4. Es sendet die Richtung und den Slot als Event an die Companion-App.
5. Er drückt den Joystick und löst die Matrix-Taste des Push aus.

**UI overview**
Ein Hall-Joystick rechts neben dem OLED. Totzone und Min/Max-Werte wirken im Hintergrund. Das Radial-Menü selbst zeigt erst die Companion-App in einer späteren Phase.

---

## 6. RGB und LED-Stromprofile

Per-Key-RGB, Underglow und Profile für den Stromverbrauch, für den Endnutzer.

**User flow**
1. Der Nutzer steckt das Pad per Kabel an und sieht Per-Key-Feedback im Profil `full`.
2. Er drückt eine Taste und die zugehörige LED reagiert.
3. Er wählt das Profil `reduced` oder `minimal`, um den Verbrauch zu senken.
4. Im Profil `minimal` leuchtet nur die Status-LED.

**UI overview**
Pro Taste eine WS2812/SK6812-LED plus ein Underglow-Streifen. Die Profile werden in Phase 1 per Keymap-Taste oder Protokollbefehl umgeschaltet. Das automatische Umschalten nach Stromquelle folgt in Phase 2.

---

## 7. OLED-Anzeige

Ein kleines Display für Layer und Agent-Zustand, für den Endnutzer.

**User flow**
1. Der Nutzer schaltet das Pad ein und sieht den aktiven Layer auf dem OLED.
2. Er wechselt den Layer und die Anzeige aktualisiert sich.
3. Die Companion-App setzt einen Agent-Zustand und das OLED zeigt ihn an.

**UI overview**
Ein SSD1306-Display (128x32 oder 128x64) per I²C zwischen Encoder und Joystick. Es zeigt Text und einfache Symbole, keine Animationen.

---

## 8. Raw-HID-Protokoll v1

Eine versionierte Schnittstelle mit CRC zwischen Firmware und App, für Entwickler.

**User flow**
1. Der Entwickler ändert Befehle oder Events in der YAML-Quelle.
2. Ein Generator erzeugt den C-Header für QMK und das Python-Modul.
3. Er startet die Protokoll-Tests mit den gemeinsamen Testvektoren.
4. Die Tests prüfen CRC, Roundtrip und fehlerhafte Frames, auch für den auf dem Host kompilierten C-Code.
5. Er liest die Spezifikation unter `protocol/` als Referenz.

**UI overview**
Keine Oberfläche, sondern Markdown-Spezifikation, YAML-Quelle und generierte Dateien. Befehle sind `get_version`, `set_led` und `set_state`, Events sind Joystick-Richtung, Encoder und Layer-Wechsel.

---

## 9. CLI `micro-state`

Eine Kommandozeile, die den Agent-Status am Pad setzt, für Agent-Tools und Endnutzer.

**User flow**
1. Der Nutzer installiert die CLI und, unter Linux, die mitgelieferten udev-Regeln.
2. Er führt `micro-state thinking` aus.
3. Die CLI findet das Pad über VID/PID und Usage Page und sendet `set_state`.
4. Das Pad zeigt die Farbe des Zustands an.
5. Ein Hook von Claude Code oder Codex ruft die CLI bei Beginn, Ende oder Fehler auf.

**UI overview**
Rein textbasiert, mit den Zuständen `idle`, `thinking`, `done`, `input` und `error` sowie den Optionen `--device` und `--timeout`. Die Exit-Codes unterscheiden Erfolg, Gerät nicht gefunden und Zeitüberschreitung. Linux, macOS und Windows werden unterstützt, macOS braucht die Berechtigung „Input Monitoring".

---

## 10. Companion-App mit Radial-Menü und App-Presets

Die spätere grafische Begleit-App, für den Endnutzer.

**User flow**
1. Der Nutzer startet die App, die das Pad verbindet und die Events empfängt.
2. Er bewegt den Joystick und die App zeigt das Radial-Menü mit sieben Slots als Overlay.
3. Er lässt den Joystick in einem Slot los und die zugeordnete Aktion wird ausgeführt.
4. Er wechselt die aktive Anwendung und die App erkennt sie.
5. Die App schaltet Layer und LED-Farbe entsprechend dem hinterlegten Preset um.

**UI overview**
Ein Overlay-Fenster mit sieben Segmenten und ein Einstellungsfenster für Presets pro App. Die erste Version ist Python (CLI), die GUI folgt später, ein Rust-Rewrite ist danach vorgesehen.

---

## 11. BLE-Brücke (Phase 2)

Eine kabellose Verbindung über einen nRF52840, für den Endnutzer.

**User flow**
1. Der Nutzer koppelt das Pad über Bluetooth mit seinem Rechner.
2. Er trennt das USB-Kabel und tippt weiter, die Ausgabe wechselt auf BLE.
3. Er steckt das Kabel wieder ein und die Ausgabe wechselt auf USB.
4. Die Companion-App verbindet sich über einen eigenen GATT-Dienst und liest Konfiguration und Radial-Menü-Daten.

**UI overview**
Keine neue Bedienoberfläche am Pad, nur ein Kopplungsvorgang im Bluetooth-Menü des Betriebssystems. In Phase 1 ist dieses Feature nicht gebaut.

---

## 12. Firmware-Updates (Phase 2)

Updates für STM32 und nRF52840, für Endnutzer und Entwickler.

**User flow**
1. Der Entwickler startet den STM32 per BOOT0 im DFU-Modus und flasht die Firmware über USB.
2. Später startet der Nutzer ein Update über die Brücke, die BOOT0 und NRST steuert und die Firmware per UART in den ST-ROM-Bootloader überträgt.
3. Der nRF52840 wird über MCUboot mit Serial Recovery oder per BLE-DFU (mcumgr/SMP) aktualisiert.
4. Bei einem Abbruch greift der Wiederherstellungsweg, die Risiken stehen in `docs/risks.md`.

**UI overview**
Zuerst Kommandozeilen-Werkzeuge, später ein Update-Dialog in der Companion-App. Das Konzept ist unbestätigt und wird auf Machbarkeit geprüft.

---

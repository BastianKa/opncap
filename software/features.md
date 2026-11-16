# opncap Software — Features

---

## 1. Software-Repository, Lizenzen und CI

Das Grundgerüst für alle Software-Teile (Firmware, Protokoll, Host-Dienst, Konfigurations-App), für Entwickler und Contributor.

**User flow**
1. Der Entwickler klont das Repo und öffnet den Ordner `software/` mit den Unterordnern `firmware/`, `protocol/`, `host/`, `app/` und `docs/`.
2. Er liest `docs/licensing.md` und erfährt, welche Teile GPL-2.0-or-later (QMK) und welche Apache-2.0 sind.
3. Er pusht einen Commit oder Pull Request.
4. Die CI baut die Firmware, führt die Protokoll- und Host-Tests auf Ubuntu, macOS und Windows aus und prüft Lint und Format.
5. Er sieht das Ergebnis als grünen oder roten Status am Commit.

**UI overview**
Es gibt keine Oberfläche außer Repo-Struktur, README und den GitHub-Actions-Statusanzeigen. Jede Datei trägt einen SPDX-Header. Die Hardware-Referenz ist immer `hardware/opncap_v0.3`, ältere Hardware-Stände sind nur Archiv.

---

## 2. Raw-HID-Protokoll v1

Eine versionierte, CRC-gesicherte Schnittstelle zwischen Pad und Rechner, aus der alle weiteren Features Befehle und Events beziehen, für Entwickler.

**User flow**
1. Der Entwickler öffnet die YAML-Quelle unter `protocol/` und sieht alle Befehle, Events und Felder.
2. Er ergänzt einen Befehl oder ein Event, zum Beispiel `set_agent_state` oder `dial_event`.
3. Er startet den Generator, der daraus den C-Header für QMK und das Python-Modul für den Host erzeugt.
4. Er führt die gemeinsamen Testvektoren aus (CRC, Roundtrip, fehlerhafte Frames).
5. Er sieht, dass Firmware und Host dieselbe Protokollversion sprechen, oder eine klare Fehlermeldung bei Abweichung.

**UI overview**
Eine Markdown-Spezifikation mit Frame-Tabelle (32 Byte, Magic, Version, Befehl, Sequenznummer, Länge, Payload, CRC-16) und eine YAML-Datei als einzige Quelle. Der Generator läuft als einzelner Befehl auf der Kommandozeile.

---

## 3. Firmware-Grundlage: Tasten, Layer, Encoder und Joystick

Die QMK-Firmware für den BlackPill F411, die alle Eingaben des Pads erfasst und als Events bereitstellt, für Endnutzer und Entwickler.

**User flow**
1. Der Nutzer schließt das Pad per USB-C an und es meldet sich als Tastatur und als Raw-HID-Gerät.
2. Er drückt K1 bis K14 und löst die im aktiven Layer belegten Aktionen aus.
3. Er dreht den Encoder oder drückt ihn und erhält Layer-abhängige Aktionen.
4. Er bewegt den Joystick, der beim Start den Mittelpunkt kalibriert und Totzone sowie Min/Max verfolgt, und erhält Richtungs-Events.
5. Der Host empfängt Tasten-, Encoder-, Joystick- und Layer-Events über das Protokoll.

**UI overview**
Keine eigene Oberfläche. Rückmeldung geben die Tasten-LEDs und das Display. Das Layout ist 3x4-Tasten, darunter K13 und K14, links der Encoder, rechts der Joystick, in der Mitte das runde Display.

---

## 4. Host-Dienst und CLI `micro-state`

Ein Hintergrunddienst und eine Kommandozeile, die das Pad finden, verbinden und Zustände setzen, für Endnutzer und Agent-Tools.

**User flow**
1. Der Nutzer installiert die Host-Software und der Dienst startet beim Login.
2. Der Dienst findet das Pad über VID/PID und Usage Page und verbindet sich.
3. Der Nutzer oder ein Hook ruft `micro-state idle|thinking|done|input|error` auf.
4. Die CLI beendet sich mit einem klaren Exit-Code und einer Fehlermeldung, wenn das Gerät fehlt oder nicht antwortet.
5. Er nutzt `--device` und `--timeout`, um ein bestimmtes Pad oder ein kürzeres Zeitlimit zu wählen.

**UI overview**
Kommandozeile und Statusanzeige in der Menüleiste oder im Systemtray mit Verbindungsstatus. Unter Linux werden udev-Regeln mitgeliefert, unter macOS führt eine Anleitung durch die Berechtigung „Input Monitoring".

---

## 5. Agent-Status-LEDs

Die Statusfarben der KI-Agenten auf den Tasten, damit der Nutzer den Zustand auf einen Blick sieht, für Endnutzer und Agent-Tools.

**User flow**
1. Ein Agent (Claude Code, Codex, Skript) meldet seinen Zustand an den Host-Dienst.
2. Der Dienst sendet den Zustand an die zugeordnete Agent-Taste.
3. Die Taste leuchtet weiß (inaktiv), blau (arbeitet), grün (fertig, ungelesen), orange (Eingabe oder Freigabe nötig), rot (Fehler) oder ist aus (kein Chat zugeordnet).
4. Die Taste des ausgewählten Chats pulsiert in der Farbe ihres Zustands.
5. Der Nutzer liest den Zustand ab, ohne das Fenster zu wechseln.

**UI overview**
Sechs Tasten-LEDs im Pad, zusätzlich die Status-LED in der transluzenten Bodenplatte und die Statusanzeige auf dem Display. Das Farbschema ist in den Einstellungen sichtbar und für Farbsehschwäche anpassbar.

---

## 6. Agent Keys: Chats per Taste steuern

Sechs Tasten, die jeweils einem Chat oder einer Agent-Sitzung zugeordnet sind, für Endnutzer.

**User flow**
1. Der Nutzer startet mehrere Claude-Code-Sitzungen (später Codex-Sitzungen und Chats der ChatGPT-Desktop-App).
2. Die Software ordnet sie automatisch den Tasten K1 bis K6 zu, sortiert nach Aktualität, mit Vorrang für angepinnte, aktive und auf Antwort wartende Chats.
3. Er drückt eine Taste und wechselt zu diesem Chat.
4. Er drückt die Taste zweimal innerhalb von 350 ms und die Anwendung kommt zusätzlich in den Vordergrund.
5. Er drückt eine nicht zugeordnete Taste und ein neuer Chat öffnet sich.
6. Er legt in den Einstellungen eigene Zuordnungen fest oder belegt eine Taste mit einer Aktion oder einem Skill.

**UI overview**
Sechs Tasten mit Status-LED, belegt als K1 bis K6. Das Display zeigt den Namen des gewählten Chats. In der Konfigurations-App erscheint eine Liste der Chats mit Zuordnung, Pin-Markierung und Priorität.

---

## 7. Command Keys und Aktionskatalog

Sechs frei belegbare Tasten für häufige Aktionen mit einem einheitlichen Aktionskatalog, für Endnutzer.

**User flow**
1. Der Nutzer nutzt die Standardbelegung auf K7 bis K12: Fast Mode umschalten, Anfrage genehmigen, Anfrage ablehnen, Chat in neuem Chat fortsetzen, Push-to-Talk, Nachricht absenden.
2. Er öffnet die Einstellungen und wählt aus dem Katalog eine andere Aktion, zum Beispiel Browser, Terminal, Änderungen prüfen, Git-Aktion, Pull Request, Datei oder Foto anhängen, Plugins, geplante Tasks, Reasoning-Aufwand, Skills oder ein eigenes Tastenkürzel.
3. Wählt er eine Taste, die schon belegt ist, tauschen beide Belegungen die Plätze.
4. Er speichert und die Belegung gilt sofort auf dem Pad.

**UI overview**
Eine Tastenansicht mit sechs Feldern, jedes mit Aktionsname und Symbol, daneben ein durchsuchbarer Aktionskatalog. Konflikte werden als Tausch angezeigt, bevor der Nutzer bestätigt.

---

## 8. Aktions-Engine und Adapter

Die Schicht, die Pad-Eingaben in konkrete Aktionen für Anwendungen übersetzt, für Endnutzer und Entwickler.

**User flow**
1. Das Pad sendet ein Event, zum Beispiel „K8 gedrückt".
2. Der Host-Dienst schlägt die Belegung für das aktive Profil nach.
3. Er wählt den passenden Adapter: zuerst Claude Code, danach Codex, später die ChatGPT-Desktop-App, dazu Terminal und ein generischer Tastenkürzel-Sender.
4. Der Adapter führt die Aktion aus, etwa Anfrage genehmigen, Tastenkürzel senden oder einen Skill starten.
5. Meldet der Adapter einen Fehler, zeigt das Pad ein rotes Signal und der Host schreibt ein Protokoll.

**UI overview**
Keine eigene Oberfläche. Die Einstellungen zeigen die Liste der verfügbaren Adapter mit Status, Version und Berechtigungsprüfung. Entwickler schreiben neue Adapter über eine dokumentierte Schnittstelle.

---

## 9. Joystick: Richtungsaktionen und Radial-Menü

Der Hall-Effekt-Joystick als Navigation und Auswahlmenü, für Endnutzer.

**User flow**
1. Der Nutzer bewegt den Joystick nach oben, unten, links oder rechts und löst die Standardaktionen aus: Plan Mode umschalten, Seitenleiste ein- und ausblenden, im Verlauf zurück oder vorwärts.
2. Er belegt in den Einstellungen jede der vier Richtungen mit einer beliebigen Aktion oder einem Skill.
3. Er hält den Joystick gedrückt und ein Radial-Menü mit sieben Slots erscheint auf dem Display und als Overlay am Bildschirm.
4. Er bewegt den Joystick auf einen Slot und lässt los, um die Aktion auszuführen.

**UI overview**
Auf dem runden Display ein Ring mit sieben Segmenten und Beschriftung, das gewählte Segment ist hervorgehoben. Der Bildschirm zeigt dasselbe Overlay mittig. Die Kalibrierung und die Totzone sind in den Einstellungen einsehbar.

---

## 10. Drehregler mit vier Modi

Der Encoder mit Push als Steuerung ohne Maus, für Endnutzer.

**User flow**
1. Der Nutzer wählt in den Einstellungen oder per Taste einen der vier Modi: Composer-Navigation, nur Reasoning, Konversations-Scrollen oder eigene Belegung.
2. In der Composer-Navigation dreht er durch die Elemente des Eingabefelds und drückt, um die Auswahl zu öffnen.
3. Im Modus Reasoning stellt er den Reasoning-Aufwand ein und öffnet erweiterte Optionen.
4. Im Scroll-Modus scrollt er den Chat und springt per Druck zur neuesten Nachricht.
5. In der eigenen Belegung legt er je eine Aktion für Links, Rechts, kurzen und langen Druck fest.
6. Er hält den Encoder lange gedrückt und öffnet die Pad-Einstellungen.

**UI overview**
Das Display zeigt den aktiven Modus und den aktuellen Wert, zum Beispiel die Reasoning-Stufe als Balken. Der Modus lässt sich in der App und per Taste wechseln. Während Composer-Menüs offen sind, leuchtet die Abbrechen-Taste rot.

---

## 11. Sprachsteuerung mit eingebautem Mikrofon

Diktat und Sprachchat über das Pad, für Endnutzer.

**User flow**
1. Der Nutzer hält K13 gedrückt und spricht.
2. Beim Loslassen endet die Aufnahme und der Text erscheint im Eingabefeld.
3. Er drückt K13 zweimal innerhalb von 350 ms und startet eine dauerhafte Aufnahme, die ein weiterer Druck beendet.
4. Er drückt die Senden-Taste und der erkannte Text wird abgeschickt.
5. Er startet über K14 einen Sprachchat, schaltet das Mikrofon dort stumm oder beendet ihn mit langem Druck.
6. Er wählt in den Einstellungen, ob das Mikrofon des Pads oder das des Rechners verwendet wird.

**UI overview**
Türkises Licht während der Aufnahme, bewegtes weißes Licht bei der Verarbeitung, dauerhaft weiß, wenn der Text bereit ist. Das Display zeigt eine Pegelanzeige. K13 und K14 sind getrennt belegbar.

---

## 12. Display-Oberfläche

Das runde Display als Statusfläche, für Endnutzer.

**User flow**
1. Der Nutzer sieht im Ruhezustand Uhrzeit, aktiven Layer und Agent-Zustand.
2. Er wechselt den Layer und das Display zeigt dessen Namen und Farbe.
3. Er startet eine Aktion und sieht eine kurze Bestätigung oder Fehlermeldung.
4. Er öffnet das Radial-Menü oder einen Einstellungswert und das Display wechselt in die passende Ansicht.
5. Nach der Ruhezeit dimmt es und schaltet sich aus.

**UI overview**
Rundes 1,28-Zoll-Display mit Kreisgrafik, zentralem Text und Randanzeige für Akku und Verbindung. Helligkeit und Ruhezeit folgen den Beleuchtungseinstellungen, die Darstellung ist ein austauschbares Theme.

---

## 13. Beleuchtung und LED-Stromprofile

Anpassbare Helligkeit, automatisches Dimmen und Stromprofile für Pad und Underglow, für Endnutzer.

**User flow**
1. Der Nutzer stellt in den Einstellungen die Helligkeit ein.
2. Er schaltet automatisches Dimmen ein oder aus und wählt ein Abschaltintervall zwischen 30 Sekunden und einer Stunde, Standard drei Minuten.
3. Er wählt ein Stromprofil: `full`, `reduced` oder `minimal`.
4. Das Pad schaltet bei Nutzung oder bei einer Statusänderung eines Agenten wieder auf volle Beleuchtung.
5. Das Pad wechselt in Phase 2 abhängig von der Stromquelle automatisch das Profil.

**UI overview**
Ein Bereich „Beleuchtung" in den Einstellungen mit Regler, Schalter, Auswahl für das Zeitintervall und Profilwahl. Eine Vorschau auf dem Pad folgt der Änderung sofort.

---

## 14. Konfigurations-App

Eine grafische Oberfläche, in der der Nutzer alle Belegungen und Einstellungen ändert, für Endnutzer.

**User flow**
1. Der Nutzer öffnet die App, sie verbindet sich mit dem Pad und zeigt ein Abbild des Layouts.
2. Er klickt auf eine Taste, den Encoder oder eine Joystick-Richtung und wählt die Aktion.
3. Er wechselt zwischen Agent Keys, Command Keys, Joystick, Drehregler, Sprache und Beleuchtung.
4. Er speichert, und die Konfiguration landet auf dem Pad.
5. Er setzt das Layout zurück: Command Keys und Joystick gehen auf Standard, die Agent-Key-Zuordnung bleibt erhalten.
6. Er exportiert oder importiert die Konfiguration als Datei.

**UI overview**
Fenster mit Pad-Grafik links und Detailbereich rechts. Geänderte, nicht gespeicherte Werte sind markiert. Die App läuft unter Linux, macOS und Windows und nutzt dieselben Befehle wie die CLI.

---

## 15. Layer und App-Profile

Mehrere Ebenen und anwendungsabhängige Profile, damit das Pad mehr als einen Zweck erfüllt, für Endnutzer.

**User flow**
1. Der Nutzer arbeitet im ersten Layer mit den KI-Agenten.
2. Er legt bis zu fünf weitere Layer an, zum Beispiel für Browser, Videoschnitt oder Medien.
3. Er verknüpft ein Profil mit einer Anwendung.
4. Der Host-Dienst erkennt die aktive Anwendung und wechselt Layer und LED-Farbe.
5. Er wechselt den Layer jederzeit manuell per Taste.

**UI overview**
Eine Liste der Layer mit Name, Farbe und verknüpfter Anwendung. Das Display und die Tasten-LEDs zeigen den aktiven Layer an. Profile lassen sich duplizieren und teilen.

---

## 16. Einrichtung, Berechtigungen und Diagnose

Ein geführter Einstieg und ein Testmodus, damit das Pad ohne Vorwissen funktioniert, für Endnutzer und Contributor.

**User flow**
1. Der Nutzer startet nach der Installation den Einrichtungsassistenten.
2. Der Assistent prüft die Verbindung, die Berechtigungen (udev, „Input Monitoring" unter macOS) und die Firmware-Version.
3. Er testet Tasten, Encoder, Joystick, LEDs, Display und Mikrofon in einem Diagnosemodus.
4. Bei einem Fehler zeigt der Assistent die Ursache und den nächsten Schritt.
5. Er exportiert ein Diagnoseprotokoll für Fehlerberichte.

**UI overview**
Ein Schritt-für-Schritt-Dialog mit Haken pro Prüfung. Der Diagnosemodus zeigt jeden Eingang live und hebt ihn hervor, sobald das Pad ihn meldet.

---

## 17. BLE-Verbindung und Akkubetrieb (Phase 2)

Kabellose Nutzung über eine nRF52840-Brücke mit Akkuanzeige, für Endnutzer.

**User flow**
1. Der Nutzer startet das Pairing per Taste und verbindet das Pad per Bluetooth.
2. Er speichert bis zu drei Verbindungen und wechselt zwischen ihnen.
3. Er steckt das USB-C-Kabel an und das Pad lädt und wechselt auf die USB-Ausgabe.
4. Er sieht den Akkustand auf dem Display und in der App.
5. Im Akkubetrieb schaltet das Pad auf das Profil `minimal`.

**UI overview**
Eine Verbindungsliste mit drei Kanälen, Status und Name des Rechners. Das Display zeigt Verbindungsart und Akkustand am Rand. Konfiguration und Radial-Menü laufen über einen eigenen GATT-Dienst. In Phase 1 ist dieses Feature nicht gebaut.

---

## 18. Firmware-Updates (Phase 2)

Aktualisierung der Firmware über die App, für Endnutzer.

**User flow**
1. Die App erkennt, dass eine neuere Firmware vorliegt.
2. Der Nutzer bestätigt das Update.
3. Die App überträgt die Firmware per USB-DFU, später über die Brücke.
4. Sie zeigt den Fortschritt und prüft das Ergebnis.
5. Bei einem Abbruch bleibt das Pad im Wiederherstellungsmodus erreichbar.

**UI overview**
Ein Dialog mit Versionsvergleich, Fortschrittsbalken und deutlichem Hinweis, das Pad während des Updates angeschlossen zu lassen. Risiken sind in `docs/risks.md` beschrieben.

---

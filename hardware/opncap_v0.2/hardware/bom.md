<!-- SPDX-License-Identifier: Apache-2.0 -->
# opncap – Stückliste (Phase 1, kabelgebunden, Hardware v0.2 flach)

Status: **Entwurf. Nichts ist bestellt oder an echter Hardware getestet.** Die Teilenummern sind am 2026-11-15 gegen die Händlerseiten geprüft (Quellen am Ende). Lagerbestand und Preise ändern sich und stehen deshalb nicht hier.

## So liest du die Tabelle

- **Hersteller-Nr.** ist die eindeutige Bezeichnung des Herstellers. Damit findest du das Teil bei jedem Händler.
- **LCSC-Nr.** (beginnt mit C) ist die Bestellnummer bei LCSC und zugleich die Teilenummer für die Bestückung bei JLCPCB.
- **Bauform** (z. B. 0603, SOD-123, SOIC-14) ist die Gehäusegröße. Sie muss exakt stimmen, sonst passt das Teil nicht auf die Lötflächen.
- **Menge** ist der Bedarf pro Gerät. **Bestellen** enthält eine Reserve, weil kleine Teile leicht verloren gehen.
- Die Spalten `#` und `Menge` werden vom Skript `gen_fab.py` gegen die Platine geprüft. Bitte nicht umbenennen.

## Wer lötet was

Die Platine hat SMD-Teile auf beiden Seiten: 64 unten, 16 oben (die 8 Underglow-LEDs und ihre 8 Kondensatoren).

| Weg | Was JLCPCB bestückt | Was du lötest |
|---|---|---|
| A: JLCPCB bestückt beide Seiten | # 4, 5, 6, 10, 11, 12, 13 | Hotswap-Sockel, Encoder, Joystick, Display, Sockelleisten |
| B: JLCPCB bestückt nur unten (günstiger) | wie A, ohne die 16 Teile oben | zusätzlich 8 LEDs und 8 Kondensatoren oben |
| C: alles selbst | nichts | alles; 0603 und die LEDs brauchen eine feine Lötspitze, Pinzette und Flussmittel |

Für JLCPCB liegen bereit: `pcb/opncap_gerbers.zip`, `pcb/bom_jlcpcb.csv`, `pcb/positions_jlcpcb.csv`. Die Drehwinkel in der Positionsdatei sind nicht an JLCPCB angepasst. Prüfe in der Bestückungsvorschau von JLCPCB jedes Teil, besonders LEDs, Dioden und den Pegelwandler.

## A. Elektronik auf der Platine (SMD)

| # | Menge | Bestellen | Bauteil | Exakte Spezifikation | Bauform | Hersteller-Nr. | LCSC-Nr. | Worauf achten |
|---|---|---|---|---|---|---|---|---|
| 4 | 16 | 20 | Schaltdiode | 75 V, 150 mA, schnelle Kleinsignaldiode | SOD-123 | 1N4148W (ST Semtech) | C81598 | Jede 1N4148W in SOD-123 passt, egal von welchem Hersteller. Nicht 1N4148WS (SOD-323, kleiner) und nicht die bedrahtete 1N4148. Der Strich auf dem Gehäuse markiert die Kathode und muss zum Strich auf der Platine zeigen. |
| 5 | 14 | 30 (zusammen mit # 6) | RGB-LED, adressierbar | SK6812 MINI-E, 5 V, 3,2 x 2,8 x 1,78 mm, Rückseitenmontage (leuchtet durch ein Loch in der Platine) | SMD, 4 Beinchen | SK6812MINI-E (OPSCO) | C5149201 | Muss genau **MINI-E** heißen. SK6812 MINI (ohne E), SK6812 (5050) und WS2812B passen nicht. Nicht SK6812MINI-EA (anderer Strom). Hitzeempfindlich: beim Handlöten höchstens 280 °C und kurz. |
| 6 | 8 | siehe # 5 | RGB-LED, Underglow | wie # 5 | wie # 5 | SK6812MINI-E (OPSCO) | C5149201 | Diese 8 sitzen auf der Oberseite. |
| 10 | 1 | 2 | Pegelwandler | 4-fach-Bustreiber, 5 V Versorgung, TTL-Eingänge (erkennt 3,3 V als High) | SOIC-14 (3,9 mm breit) | SN74AHCT125DR (Texas Instruments) | C155176 | Die Buchstaben **AHCT** oder **HCT** sind entscheidend. 74AHC125 oder 74HC125 (ohne T) funktionieren hier nicht zuverlässig. Gleichwertig: 74AHCT125D (Nexperia), 74AHCT125S14-13 (Diodes Inc.). Nicht TSSOP-14 (schmaler). |
| 11 | 1 | 10 | Widerstand | 330 Ω, ±1 %, 0,1 W, Dickschicht | 0603 | 0603WAF3300T5E (UNI-ROYAL) | C23138 | Jeder 330 Ω in 0603 passt, ±5 % reicht auch. Aufdruck „3300“ oder „331“. |
| 12 | 24 | 30 | Keramikkondensator | 100 nF (= 0,1 µF), **50 V**, X7R, ±10 % | 0603 | CL10B104KB8NNNC (Samsung) | C1591 | Die Schaltung hat 5 V. Jede Spannungsfestigkeit ab 16 V ist in Ordnung, 50 V ist der gängige Standard. Material X7R oder X5R, nicht Y5V. Gleichwertig: Murata GRM188R71H104KA93, Yageo CC0603KRX7R9BB104. |
| 13 | 1 | 2 | Pufferkondensator für die LEDs | 220 µF, 10 V, ±20 %, Polymer-Tantal, höchstens 3,1 mm hoch | EIA 7343 (Baugröße D), 7,3 x 4,3 mm | T520D227M010ATE040 (KEMET) | C212691 | **Gepolt:** Der Balken auf dem Gehäuse ist Plus und muss zur Plus-Markierung. Falsch herum eingebaut kann er platzen. Gleichwertig: Panasonic 10TPB220ML, Kyocera AVX TCJY227M010R0040. Bei LCSC war er zuletzt nicht lagernd; Ersatz dort: Kyocera AVX TAJD227K010RNJ (C8024, normales Tantal, gleiche Baugröße). |

## B. Module und Bedienteile (von Hand zu löten oder zu stecken)

| # | Menge | Bestellen | Bauteil | Exakte Spezifikation | Suchbegriff / Hersteller-Nr. | Worauf achten |
|---|---|---|---|---|---|---|
| 1 | 1 | 1 | Mikrocontroller-Board | WeAct „BlackPill“ mit STM32F411CEU6, USB-C, 2 x 20 Pins im Raster 2,54 mm, Platine 52,8 x 20,8 mm | „WeAct STM32F411CEU6 BlackPill V3“ | **Stiftleisten nicht vorgelötet** kaufen. Die Stifte kommen bei diesem Gerät auf die Bauteilseite, siehe `DESIGN_NOTES.md`. Genau **F411CEU6**, nicht F401. Beim WeAct-Originalshop kaufen, es gibt Nachbauten mit anderer Pinbelegung. Die Variante ohne zusätzlichen Flash-Speicher reicht. |
| 2 | 14 | 15 | Taster | Kailh Choc V1 (PG1350), Low Profile | „Kailh Choc V1 PG1350 switch“ | Farbe nach Geschmack: Red (linear), Brown (spürbarer Druckpunkt), White (Klick). Nicht Choc V2 und nicht Choc Mini, die haben andere Füße. |
| 3 | 14 | 16 | Hotswap-Sockel | Kailh Choc Hotswap | CPG135001S30 („Kailh Choc hotswap socket“) | Nicht die MX-Sockel (CPG151101S11), die sind höher und haben andere Lötflächen. Große Lötflächen, gut von Hand zu löten. |
| 7 | 1 | 1 | Drehencoder mit Taster | Bauart EC11, stehend (vertikal), Achse 6 mm mit Abflachung (D-Achse), Achslänge 20 mm, mit Drucktaster, 5 Pins + 2 Haltelaschen | Alps Alpine EC11E18244AU (36 Rastungen, 18 Impulse) oder „EC11 encoder 20mm D-shaft with switch“ | Die Zahl der Rastungen ist frei wählbar und wird in der Firmware eingestellt; 20 oder 30 Rastungen fühlen sich gröber an als 36. Achslänge 20 mm einhalten, sonst sitzt der Knopf zu tief oder zu hoch. Die Haltelaschen können eng in den runden Löchern sitzen. |
| 8 | 1 | 1 | Hall-Joystick mit Taster | 2 Achsen analog, 3,3 V, mit Drucktaster | Kandidat: Klasse FJH10K-S3D | **Nicht geklärt.** Datenblatt, Maße und Pinbelegung sind unbestätigt, die Lötflächen auf der Platine sind ein Platzhalter (18 x 18 mm, 1 x 6 Pins). Erst den Joystick auswählen und vermessen, dann die Platine anpassen und bestellen. |
| 9 | 1 | 1 | Rundes Display | 1,28 Zoll, 240 x 240, IPS, Treiber GC9A01, SPI, 3,3 V, Trägerplatine 38,03 x 45,80 mm mit 8-poliger Stiftleiste (GND, VCC, SCL, SDA, RES, DC, CS, BLK) | LCDwiki / QD-TECH **MSP1281** („1.28 inch round TFT GC9A01 8 pin“) | Vor dem Kauf die Maße der Trägerplatine im Angebot prüfen. Andere GC9A01-Module (runde Platine, Waveshare mit Kabelstecker, 7-polig) passen nicht. Die Lage von Stiftleiste und Display auf dem Träger ist in der Konstruktion angenommen: nach Lieferung nachmessen, bevor du die Platine bestellst. |
| 16 | 2 | 2 | Sockelleiste für das BlackPill, extra flach | 1-reihig, Raster 2,54 mm, 2,11 mm hoch, gedrehte Kontakte | Mill-Max 315-43-1**20**-41-004000 (20-polig), auf 19 Pole kürzen | Normale Buchsenleisten (8,5 mm) passen nicht ins flache Gehäuse. Teuer und nicht überall lagernd (DigiKey, Mouser). Die zwei Ziffern nach „1“ sind die Polzahl. |
| 17 | 2 | 2 | Stiftleiste für das BlackPill, extra flach | passend zu # 16, ergibt 3,94 mm Platinenabstand | Mill-Max 335-10-1**20**-00-160000 (20-polig), auf 19 Pole kürzen | Nur diese Kombination ergibt die 3,94 mm, auf die das Gehäuse ausgelegt ist. Normale Stiftleisten sind zu dick für die Sockel. |
| 18 | 1 | 1 | Stiftleiste für das Display | 1 x 8, Raster 2,54 mm, gerade, 2,5 mm Kunststoffhöhe | „pin header 1x8 2.54“ | Liegt dem Display meist bei. |
| 14 | 1 | 1 | USB-C-Kabel | Datenkabel, USB 2.0 | | Kein reines Ladekabel. Der Steckerkörper darf höchstens 12,5 x 7 mm groß sein. |

## C. Mechanik

| Nr. | Menge | Bauteil | Exakte Spezifikation | Worauf achten |
|---|---|---|---|---|
| M1 | 14 | Tastenkappen | Choc V1, 1u, höchstens 17,5 x 16,5 mm | Zum Beispiel MBK. MX-Kappen passen nicht auf Choc V1. |
| M2 | 1 | Drehknopf | für 6 mm D-Achse, Außendurchmesser höchstens 22 mm, etwa 14 mm hoch | Mit Madenschraube oder Klemmsitz. |
| M3 | 1 | Joystick-Kappe | passend zum gewählten Joystick, Durchmesser bis 19 mm | Hängt an # 8. |
| M4 | 6 | Schraube | M2 x 14 mm, Zylinderkopf mit Innensechskant (DIN 912 / ISO 4762), Kopf höchstens 4 mm Durchmesser | Stahl verzinkt oder Edelstahl. |
| M5 | 6 | Gewindeeinsatz zum Einschmelzen | M2, Messing, 3,0 mm lang, Außendurchmesser 3,5 mm (für 3,2-mm-Loch) | Wird mit dem Lötkolben ins Oberteil eingeschmolzen. Nicht länger als 3 mm, das Oberteil ist dünn. |
| M6 | 6 | Distanzscheibe | M2 (Innen 2,2 mm), außen höchstens 4,4 mm, 1,0 mm dick, Kunststoff | Sitzt zwischen Platine und Platte. |
| M7 | 4 | Gummifuß | selbstklebend, Durchmesser 10 mm, 2 mm hoch | |
| M8 | 1 | Gehäuse-Unterteil | 3D-Druck aus `enclosure/export/bottom_case.stl` | Druckbarkeit ist nicht geprüft. |
| M9 | 1 | Gehäuse-Oberteil | 3D-Druck aus `enclosure/export/top_case.stl` | Der Rand am Displayfenster ist nur 0,7 mm stark. |
| M10 | 1 | Tastenplatte | 1,2 mm dick, aus `enclosure/export/plate.step` | Am besten 1,2 mm FR4 oder Aluminium, gefräst oder gelasert. Gedruckt ist sie bei 1,2 mm sehr weich. |
| M11 | 1 | Platine | 2 Lagen, 1,6 mm, 102 x 137 mm, aus `pcb/opncap_gerbers.zip` | Standardoptionen des Fertigers genügen. |

## Strom

22 LEDs ziehen bei vollem Weiß zusammen etwa 1,3 A. Ein normaler USB-Anschluss garantiert nur 0,5 A. Die Firmware muss die Helligkeit begrenzen (Profile `full` / `reduced` / `minimal`). Das Display braucht mit Hintergrundlicht etwa 30 bis 50 mA aus dem 3,3-V-Regler des BlackPill.

## Vor der Bestellung offen

1. **Joystick (# 8)** ist nicht festgelegt. Ohne ihn ist die Platine nicht bestellreif.
2. **Display (# 9):** Maße des gelieferten Moduls gegen die Annahmen in `DESIGN_NOTES.md` prüfen.
3. **Sockel- und Stiftleisten (# 16, # 17):** Lieferbarkeit der 20-poligen Ausführung prüfen; die Bestellnummer ist aus dem Nummernschema des Herstellers gebildet.
4. **LED-Lötflächen und Choc-Lötflächen** sind nicht gegen die Maßzeichnungen der Hersteller geprüft.

## Nicht Teil von Phase 1

| Teil | Phase | Hinweis |
|---|---|---|
| nRF52840-Modul (z. B. Raytac MDBT50Q) | 2 | BLE-Brücke. |
| LiPo-Akku, Lade- und Schutz-IC | 2 | Hängt von der endgültigen STM32-Variante und dem LED-Strombudget ab. |
| Stromsparender STM32 (L4-Familie) | Endplatine | QMK-Unterstützung für die genaue Variante ist zu klären. |

## Quellen der Teilenummern

- 100 nF: https://www.lcsc.com/product-detail/C1591.html
- SK6812MINI-E: https://www.lcsc.com/product-detail/C5149201.html
- 1N4148W: https://jlcpcb.com/partdetail/C81598
- SN74AHCT125DR: https://www.lcsc.com/product-detail/C155176.html
- 330 Ω: https://jlcpcb.com/partdetail/C23138
- 220 µF: https://www.digikey.com/en/products/detail/kemet/T520D227M010ATE040/818908
- EC11E18244AU: https://my.element14.com/alps/ec11e18244au/encoder-vertical-11mm-36det-18ppr/dp/2064988
- Mill-Max 315 / 335: https://www.mill-max.com/new_products/detail/176
- Display MSP1281: https://lcdwiki.com/1.28inch_IPS_Module

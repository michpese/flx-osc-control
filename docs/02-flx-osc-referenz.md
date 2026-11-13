# 02 – OSC-Referenz FLX S24

Diese Datei ist die **einzige Quelle** für OSC-Adressen in diesem Repo. Code, Mappings und Anleitungen verwenden nur, was hier steht.

## Eckdaten

| Punkt | Wert |
| --- | --- |
| Mindestversion | ZerOS 7.14 (Juli 2023) |
| Einschalten | Setup → Triggers → OSC |
| Port | 8830, änderbar im Feld „Receive Port Number" |
| Transport | UDP (Standard) oder TCP (SLIP); muss zum Sender passen |
| IP-Adresse | für OSC statisch oder per DHCP einstellbar |
| Richtung | nur Empfang; das Pult sendet kein OSC |
| Werte | stehen im Adresspfad; dieselben Werte als Argumente gehen auch |
| Master Playback | Playback 0 |
| Playbacks FLX S24 | 97, also Nummern 0 bis 96 |

## Status-Stufen

| Status | Bedeutung | Darf im Code vorkommen |
| --- | --- | --- |
| **belegt** | steht im ZerOS-Handbuch | ja |
| **Forum** | im Herstellerforum genannt, nicht im Handbuch nachgelesen | ja, im Hilfetext als „ungetestet" markiert |
| **offen** | Funktion existiert, Schreibweise hier noch nicht eingetragen | nein |

Die Spalte „Am Pult getestet" füllst du in Teststufe 2 mit Datum und ZerOS-Version.

## Befehle

| ID | Funktion | Adresse | Beispiel | Status | Am Pult getestet |
| --- | --- | --- | --- | --- | --- |
| `cue_go` | Cue auf einem Playback starten | `/zeros/cue/go/<playback>/<cue>` | `/zeros/cue/go/1/5` | belegt | |
| `cue_go_current` | Cue im gerade angezeigten Playback starten | `/zeros/cue/go/<cue>` | `/zeros/cue/go/4` | Forum | |
| `cue_go_next` | nächsten Cue starten | `/zeros/cue/go` | `/zeros/cue/go` | Forum | |
| `macro` | Makro auslösen | `/zeros/macro/<nummer>` | `/zeros/macro/1` | Forum | |
| `cue_pause` | Cue anhalten | `/zeros/cue/pause/<playback>` | `/zeros/cue/pause/1` | Forum | |
| `cue_next` | nächsten Cue vorwählen | `/zeros/cue/next/<playback>/<cue>` | `/zeros/cue/next/1/6` | Forum | |
| `playback_go` | Playback starten | `/zeros/playback/go/<playback>` | `/zeros/playback/go/1` | Forum | |
| `playback_pause` | Playback anhalten | `/zeros/playback/pause/<playback>` | `/zeros/playback/pause/1` | Forum | |
| `playback_level` | Playback-Level setzen, optional mit Fade-Zeit | `/zeros/playback/level/<playback>/<level>` *(bzw. `/<fade>`)* | `/zeros/playback/level/1/100` *(bzw. `/zeros/playback/level/1/100/2`)* | Forum | |
| `playback_release` | Playback freigeben | `/zeros/playback/release/<playback>` | `/zeros/playback/release/1` | Forum | |
| `playback_view` | Playback anzeigen | `/zeros/playback/view/<playback>` | `/zeros/playback/view/1` | Forum | |
| `grand_master` | Grand Master setzen, optional mit Fade-Zeit | `/zeros/grandmaster/<level>` *(bzw. `/<fade>`)* | `/zeros/grandmaster/100` *(bzw. `/zeros/grandmaster/0/3`)* | Forum | |
| `blackout` | Blackout schalten | `/zeros/blackout/<wert>` | `/zeros/blackout/1` *(an)* / `/zeros/blackout/0` *(aus)* | Forum | |

### Wertebereiche & Einheiten

- **Level (`playback_level`, `grand_master`):** Ganzzahl in Prozent von `0` bis `100` (bei separaten Float-Argumenten `0.0` bis `1.0`).
- **Fade-Zeit (`<fade>`):** Optionales letztes Pfadsegment in **Sekunden** (z. B. `2` oder `2.5`). Ohne Angabe nutzt ZerOS die am Playback hinterlegten Raise-/Lower-Zeiten; `0` erzwingt einen harten Sprung.
- **Blackout (`<wert>`):** `1` (ein) oder `0` (aus) – alternativ akzeptiert ZerOS auch `on`/`off` oder `true`/`false`.

## Gleichwertige Schreibweisen

Das Handbuch nennt für „Cue 5 auf Playback 1" vier gleichwertige Formen:

| Form | Adresse | Argumente |
| --- | --- | --- |
| alles im Pfad | `/zeros/cue/go/1/5` | keine |
| Cue als Argument | `/zeros/cue/go/1` | `"5"` |
| beides als Argumente | `/zeros/cue/go` | `"1"`, `"5"` |
| ein Argument mit Schrägstrich | `/zeros/cue/go` | `"1/5"` |

Dieses Repo sendet immer die erste Form: alles im Pfad, keine Argumente.

Kurzform: `/lx/q/go` ist gleichbedeutend mit `/zeros/cue/go`. Dieses Repo verwendet die Langform.

## Wird vom Pult ignoriert

- Nachrichten mit **Wildcards** in der Adresse
- **Bundles mit Zeitstempel**; Bundles gehen nur mit dem Zeitwert „sofort"

In beiden Fällen verwirft ZerOS die ganze Nachricht.

## Bekannte Eigenheiten

- **Keine Rückmeldung.** UDP bestätigt nichts. Ein falscher Port sieht für den Sender genauso aus wie ein Erfolg. Kontrolle: Event Monitor am Pult.
- **Master Playback.** Ein Anwender berichtet, dass `/zeros/cue/go/0/4` auf einem FLX S48 ignoriert wurde, `/zeros/cue/go/4` aber funktionierte. In Teststufe 2 prüfen.
- **Makros.** User-Makros gibt es auf FLX-S-Pulten nicht, nur Fixture-Makros. Die Steuerung baut deshalb auf Cues auf.
- **Kein „Release all".** Laut Forum muss jedes Playback einzeln freigegeben werden.
- **Nicht Teil der Schnittstelle:** einzelne Kanäle, Farben, Programmieren, Abfragen des Pultzustands.

## Quellen

- [ZerOS-Handbuch: OSC](https://www.zero88.com/manuals/zeros/setup/triggers/osc)
- [ZerOS-Handbuch: OSC Examples](https://www.zero88.com/manuals/zeros/setup/triggers/osc-examples)
- [ZerOS-Handbuch: Macros](https://www.zero88.com/manuals/zeros/macros)
- [ZerOS & OSC Guide, PDF](https://vari-lite.s3.eu-west-1.amazonaws.com/graphics/technical/documents/zeros-osc-guide.pdf)
- [Zero 88 Forum: OSC und Master Playback auf dem FLX S48](https://www.zero88.com/forum/topic/11559-using-osc-to-trigger-the-master-playback-cues-on-the-flx-s48/)

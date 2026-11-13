# integrations/companion

Optional. Bitfocus Companion kann zwei Aufgaben übernehmen:

1. **Notfalltasten.** Tasten auf einem Stream Deck oder im Web-Panel, die über das Modul „Generic OSC" direkt einen Cue am Pult starten. Nützlich, wenn die Bridge ausfällt.
2. **Bridge ohne Programmieren.** Companion liest ProPresenter über dessen API-Modul und sendet bei einem Folienwechsel OSC ans Pult.

## Einrichtung „Generic OSC"

| Einstellung | Wert |
| --- | --- |
| Target IP | IP-Adresse des Pults, zum Beispiel 192.168.1.10 |
| Target Port | 8830 |
| OSC-Pfad einer Taste | Adresse aus `docs/02-flx-osc-referenz.md`, zum Beispiel `/zeros/cue/go/10/1` |
| Argumente | keine |

## Was hier liegt

Die exportierte Companion-Konfiguration, sobald sie eingerichtet ist. So lässt sie sich auf einem zweiten Rechner wiederherstellen.

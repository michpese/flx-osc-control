# 06 – Testplan

Getestet wird in sieben Stufen von innen nach außen: erst das Protokoll, dann das Pult, dann die Quellen, zuletzt die ganze Kette. Jede Stufe beginnt erst, wenn die vorige bestanden ist.

## Stufen

| Stufe | Geprüft wird | Womit | Bestanden, wenn |
| --- | --- | --- | --- |
| 0 Protokoll | Die Bridge erzeugt korrekte OSC-Pakete | `mock-console`, automatische Tests | jede Adresse aus `mapping.yaml` kommt unverändert an |
| 1 Simulator | ZerOS versteht die Befehle | Phantom ZerOS als FLX S24, `flxctl` | der Event Monitor zeigt den Befehl ohne Fehler und der Cue läuft |
| 2 Pult direkt | Netz und echte Hardware | `flxctl` vom Laptop | jeder Befehl der Referenz wurde einmal ausgelöst und das Ergebnis notiert |
| 3 Quelle einzeln | ProPresenter → Bridge und Ableton → Bridge | Bridge-Log, OSC-Monitor, `mock-console` | eine Note erzeugt genau eine OSC-Nachricht |
| 4 Ende zu Ende | Die ganze Kette mit echten Show-Dateien | Pult, ProPresenter, Ableton | Folie oder Clip löst den richtigen Cue aus, ohne spürbare Verzögerung |
| 5 Störfälle | Kabel ziehen, Bridge neu starten, Doppeltrigger, Pult aus | von Hand | die Bridge verbindet sich neu und die Show bleibt am Pult bedienbar |
| 6 Generalprobe | Kompletter Ablauf | [Checkliste](07-betrieb-checkliste.md) | kein Eingriff am Rechner nötig |

## Hinweise

- **Stufe 1 ist ein offener Punkt.** Phantom ZerOS ist kostenlos und läuft auf Windows 10. Das Handbuch sagt nichts zu OSC im Simulator; im Herstellerforum beschreibt ein Anwender die OSC-Steuerung eines Phantom FLX S24. Prüfe das zuerst. Klappt es nicht, entfällt Stufe 1 und Stufe 2 wird gründlicher.
- **Stufe 2 füllt die Referenz.** Hier klärst du die offenen Schreibweisen aus [02-flx-osc-referenz.md](02-flx-osc-referenz.md) und das Verhalten von Playback 0.
- **Stufe 3 braucht kein Pult.** Die `mock-console` ersetzt es.
- **Stufe 5 ist Pflicht.** Weil UDP nichts bestätigt, merkst du einen Ausfall nur am Licht.

## Stufe 2: Befehle am Pult

Für jeden Befehl der Referenz eine Zeile.

| Befehl | Gesendete Adresse | Im Event Monitor | Wirkung am Pult | Datum |
| --- | --- | --- | --- | --- |
| `cue_go` | `/zeros/cue/go/10/1` | | | |
| `cue_go` auf Playback 0 | `/zeros/cue/go/0/1` | | | |
| `cue_go_current` | `/zeros/cue/go/1` | | | |
| `cue_go_next` | `/zeros/cue/go` | | | |
| `macro` | `/zeros/macro/1` | | | |

## Stufe 5: Störfälle

| Störfall | Erwartet | Ergebnis | Datum |
| --- | --- | --- | --- |
| Netzwerkkabel am Rechner ziehen und wieder stecken | Bridge läuft weiter, nächste Note löst wieder aus | | |
| Netzwerkkabel am Pult ziehen | Pult bleibt bedienbar, Bridge stürzt nicht ab | | |
| Bridge beenden und neu starten | Start in wenigen Sekunden, Port wird gefunden | | |
| MIDI-Port schließen (loopMIDI oder IAC aus) | Bridge meldet den Verlust und verbindet sich neu | | |
| Dieselbe Folie fünfmal schnell anklicken | genau ein Befehl innerhalb der Sperrzeit | | |
| ProPresenter und Ableton lösen gleichzeitig aus | beide Befehle kommen an, Reihenfolge im Log sichtbar | | |
| Fehlerhafte `mapping.yaml` speichern | altes Mapping bleibt aktiv, Log nennt den Fehler | | |
| Pult aus- und einschalten | Befehle wirken nach dem Start wieder | | |

## Verzögerung messen

Die Bridge schreibt für jede Note den Zeitpunkt des Empfangs und des Versands ins Log. Zielwert: unter 20 ms in der Bridge.

| Messung | Wert | Datum |
| --- | --- | --- |
| Bridge, Mittel über 50 Noten | | |
| Bridge, größter Wert | | |
| Sichtprüfung Folie → Licht | | |

## Abnahme

- [ ] Stufen 0 bis 6 bestanden
- [ ] Alle getesteten Befehle sind in der Referenz mit Datum eingetragen
- [ ] Alle Störfälle sind durchgespielt
- [ ] Mindestens zwei Personen können auf Handbetrieb wechseln

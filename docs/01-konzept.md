# 01 – Konzept

ProPresenter und Ableton senden MIDI-Noten an eine kleine Bridge, die daraus OSC-Befehle für das FLX S24 macht.

## Zielbild

```text
ProPresenter ── MIDI, Kanal 15 ──┐
                                 ├──► MIDI-Port „LX Bridge" ──► midi-bridge ── OSC über UDP 8830 ──► FLX S24
Ableton Live ── MIDI, Kanal 16 ──┘                                  ▲
                                                               mapping.yaml
```

Die Pfeile laufen nur in eine Richtung: Das Pult meldet nichts zurück.
ProPresenter läuft auf einem Windows-PC, Ableton auf einem Mac. Die Bridge läuft deshalb auf beiden Rechnern mit derselben `mapping.yaml`: unter Windows mit loopMIDI, auf dem Mac mit dem IAC-Treiber.

## Warum dieser Weg

- Das FLX S24 empfängt OSC ab ZerOS 7.14.
- ProPresenter kann kein OSC senden. Als Ausgabe an Fremdgeräte bleibt MIDI; unter Windows ist MIDI das einzige verfügbare Gerät.
- Ableton sendet OSC nur über Max for Live. MIDI-Noten sendet jede Edition.
- Ein gemeinsamer Weg bedeutet: ein Werkzeug, eine Mapping-Datei, ein Testaufbau.

## Kernentscheidungen

1. **Nur Cues auslösen.** Lichtstimmungen werden am Pult programmiert. Von außen kommt nur „Go Cue X auf Playback Y".
2. **Ein Weg für beide Programme.** ProPresenter und Ableton nutzen dieselbe Bridge und dieselbe Mapping-Datei.
3. **Einbahnstraße einplanen.** Ob ein Befehl ankam, zeigen der Event Monitor am Pult und das Log der Bridge.
4. **Eigenes, kabelgebundenes Netz.** Eigener Switch, feste IP-Adressen, kein Internet, kein WLAN im Signalweg.
5. **Das Pult hat immer Vorrang.** Fader und Tasten bleiben bedienbar. Fällt die Bridge aus, läuft die Show von Hand weiter.

## MIDI-Konvention

| MIDI | Bedeutung |
| --- | --- |
| Kanal 15 | ProPresenter |
| Kanal 16 | Ableton |
| Note 0–127 | Eintrag in `mapping.yaml` |
| Velocity | ohne Bedeutung, mindestens 1 |
| Note Off | wird ignoriert |

Gerechnet wird immer mit der Notennummer 0–127, nie mit dem Notennamen. Programme zählen Oktaven verschieden.

## Schema der Mapping-Datei

Die Zuordnung von MIDI-Note zu OSC-Befehl steht in genau einer Datei je Show. Vorlage: [`shows/mapping.example.yaml`](../shows/mapping.example.yaml).

| Feld | Typ | Pflicht | Bedeutung |
| --- | --- | --- | --- |
| `console.host` | Text | ja | IP-Adresse des Pults |
| `console.port` | Zahl | ja | OSC-Port des Pults, Standard 8830 |
| `console.transport` | `udp` oder `tcp-slip` | ja | muss zur Einstellung am Pult passen |
| `sources.<name>.midi_port` | Text | ja | Name des MIDI-Eingangs, zum Beispiel „LX Bridge" |
| `sources.<name>.channel` | 1–16 | ja | MIDI-Kanal dieser Quelle; die Kombination aus `midi_port` und `channel` darf nur einmal vorkommen |
| `debounce_ms` | endliche Zahl ab 0 | nein | Sperrzeit für Wiederholungen derselben Note von derselben Quelle, Standard 250 |
| `cues[].note` | 0–127 | ja | MIDI-Note; jede Note höchstens einmal |
| `cues[].name` | Text | ja | Name für Log und Spickzettel |
| `cues[].osc` | Text | ja | OSC-Adresse aus [02-flx-osc-referenz.md](02-flx-osc-referenz.md) |
| `cues[].sources` | Liste | nein | beschränkt den Eintrag auf einzelne Quellen; ohne Angabe gilt er für alle |

Regeln:

- Eine Note gilt für alle Quellen gleich, sofern `sources` nichts anderes sagt.
- Adressen müssen zu einem Befehl der Referenz passen. `flxctl map check` prüft das.
- Notennummern werden nie neu vergeben. Neue Einträge bekommen neue Nummern.

## Die Programme

| Paket | Aufgabe | Priorität |
| --- | --- | --- |
| `zeros-osc` mit CLI `flxctl` | ZerOS-Befehle bauen, prüfen und senden; Mapping prüfen | 1 |
| `mock-console` | Pult-Attrappe für Tests | 1 |
| `midi-bridge` | MIDI-Note in OSC übersetzen | 1 |
| `propresenter-watcher` | OSC aus der ProPresenter-API ableiten | optional |
| Max-for-Live-Device „LX Cue Send" | OSC direkt aus Ableton | optional |

Abhängigkeiten zeigen in eine Richtung: `midi-bridge`, `mock-console` und `propresenter-watcher` hängen von `zeros-osc` ab. `zeros-osc` hängt von keinem anderen Paket ab.

## OSC in einem Satz

Eine OSC-Nachricht ist ein kleines UDP-Paket mit einer Adresse wie `/zeros/cue/go/10/2` und optionalen Werten. Der Sender schickt es an IP und Port des Pults und erfährt nicht, ob es ankam.

## Quellen

- [ZerOS-Handbuch: OSC](https://www.zero88.com/manuals/zeros/setup/triggers/osc)
- [ZerOS-Handbuch: OSC Examples](https://www.zero88.com/manuals/zeros/setup/triggers/osc-examples)
- [ZerOS-Handbuch: Macros](https://www.zero88.com/manuals/zeros/macros)
- [ZerOS-Handbuch: Phantom ZerOS](https://www.zero88.com/manuals/zeros/phantom-zeros)
- [Renewed Vision: Communication Devices in ProPresenter](https://support.renewedvision.com/hc/en-us/articles/360058141114-Communication-Devices-in-ProPresenter)
- [Renewed Vision: Devices: MIDI: ProPresenter Setup](https://support.renewedvision.com/hc/en-us/articles/1500000020301)
- [Renewed Vision: TCP/IP Connections with ProPresenter API](https://support.renewedvision.com/hc/en-us/articles/31606866768147-TCP-IP-Connections-with-ProPresenter-API)
- [Ableton: Connection Kit](https://www.ableton.com/en/packs/connection-kit/)
- [Claude-Dokumentation: Effort](https://platform.claude.com/docs/build-with-claude/effort)

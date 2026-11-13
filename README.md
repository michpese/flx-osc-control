# flx-osc-control

Lichtstimmungen auf einem **Zero 88 FLX S24** aus **ProPresenter** und **Ableton Live** auslösen – über MIDI-Noten, eine kleine Bridge und OSC (Open Sound Control).

> **Stand:** Konzept und Dokumentation stehen. Der Code unter `packages/` ist noch nicht geschrieben. Die Bauaufträge dafür liegen fertig unter [`prompts/`](prompts/README.md).

## So funktioniert es

```text
ProPresenter ── MIDI, Kanal 15 ──┐
                                 ├──► MIDI-Port „LX Bridge" ──► midi-bridge ── OSC über UDP 8830 ──► FLX S24
Ableton Live ── MIDI, Kanal 16 ──┘                                  ▲
                                                               mapping.yaml
```

1. Eine Folie in ProPresenter oder eine Note in einem Ableton-Clip sendet eine **MIDI-Note**.
2. Die Note landet auf einem virtuellen MIDI-Port namens „LX Bridge".
3. Die **midi-bridge** schlägt Kanal und Note in `mapping.yaml` nach.
4. Sie sendet den zugehörigen **OSC-Befehl** ans Pult, zum Beispiel `/zeros/cue/go/10/2`.
5. Das Pult startet den Cue. Es meldet nichts zurück.

Warum der Umweg über MIDI? Das Pult empfängt OSC, aber ProPresenter kann kein OSC senden und Ableton nur mit Max for Live. MIDI-Noten können beide.

## Was liegt wo

| Ordner | Inhalt |
| --- | --- |
| [`docs/`](docs/) | Konzept, OSC-Referenz, Einrichtung, Testplan, Checkliste |
| [`packages/`](packages/) | die selbst entwickelten Programme, je ein Unterordner |
| [`shows/`](shows/) | Mapping-Dateien und ZerOS-Showfiles je Ort oder Anlass |
| [`integrations/`](integrations/) | Dateien und Anleitungen für Ableton, ProPresenter und Companion |
| [`prompts/`](prompts/) | fertige Bauaufträge für Claude Opus 5.5 |
| [`tests/e2e/`](tests/e2e/) | Tests über die ganze Kette |
| [`CLAUDE.md`](CLAUDE.md) | Projektregeln, die für jede Opus-Sitzung gelten |

## Dokumentation

| Datei | Wofür |
| --- | --- |
| [01-konzept.md](docs/01-konzept.md) | Zielbild, Architektur, MIDI-Konvention, Schema der Mapping-Datei |
| [02-flx-osc-referenz.md](docs/02-flx-osc-referenz.md) | **die eine Quelle** für alle OSC-Adressen des Pults |
| [03-setup-flx.md](docs/03-setup-flx.md) | Netzwerk, Pult-Einstellungen, Showfile-Regeln |
| [04-setup-propresenter.md](docs/04-setup-propresenter.md) | Einstellungen in ProPresenter |
| [05-setup-ableton.md](docs/05-setup-ableton.md) | Einstellungen in Ableton Live |
| [06-testplan.md](docs/06-testplan.md) | sieben Teststufen mit Protokoll zum Ausfüllen |
| [07-betrieb-checkliste.md](docs/07-betrieb-checkliste.md) | Start-Checkliste und Notfallplan für den Einsatz |

## Die Programme

| Paket | Aufgabe | Stand |
| --- | --- | --- |
| [`zeros-osc`](packages/zeros-osc/README.md) | ZerOS-Befehle bauen, prüfen und senden; Kommandozeile `flxctl` | geplant |
| [`mock-console`](packages/mock-console/README.md) | Pult-Attrappe für Tests ohne Hardware | geplant |
| [`midi-bridge`](packages/midi-bridge/README.md) | MIDI-Note in OSC übersetzen | geplant |
| `propresenter-watcher` | OSC aus der ProPresenter-API ableiten | optional, später |
| Max-for-Live-Device „LX Cue Send" | OSC direkt aus Ableton | optional, später |

Technik: Python ab 3.11 mit `python-osc`, `mido` samt `python-rtmidi`, `PyYAML` und `pytest`.

## Erste Schritte

1. **Pult vorbereiten** nach [docs/03-setup-flx.md](docs/03-setup-flx.md): ZerOS ab 7.14, OSC einschalten, feste IP-Adressen.
2. **Referenz vervollständigen:** die offenen Befehle in [docs/02-flx-osc-referenz.md](docs/02-flx-osc-referenz.md) aus dem ZerOS-Handbuch übertragen.
3. **Code bauen lassen:** die Prompts unter [`prompts/`](prompts/README.md) der Reihe nach an Opus 5.5 geben.
4. **Ersten Cue vom Laptop auslösen** mit `flxctl` (Teststufen 1 und 2 im [Testplan](docs/06-testplan.md)).
5. **ProPresenter und Ableton anschließen** nach [docs/04](docs/04-setup-propresenter.md) und [docs/05](docs/05-setup-ableton.md).
6. **Störfälle üben und Generalprobe** (Teststufen 5 und 6).

## Entwicklung

Voraussetzung: [uv](https://docs.astral.sh/uv/). uv holt bei Bedarf selbst ein passendes Python ab 3.11.

Alle drei Pakete liegen in einem uv-Workspace; `mock-console` und `midi-bridge` hängen von `zeros-osc` ab, das aus `packages/zeros-osc` eingebunden wird.

Installieren (legt `.venv/` an, alle Pakete editierbar, dazu pytest und ruff):

```text
uv sync --all-packages
```

Testen und prüfen:

```text
uv run pytest                     alle Tests
uv run pytest packages/zeros-osc  nur ein Paket
uv run ruff check .               Lint
uv run ruff format --check .      Formatierung prüfen (ohne --check: formatieren)
```

Die CI (`.github/workflows/ci.yml`) führt dieselben Schritte auf macOS und Windows mit Python 3.11 und 3.13 aus.

## Offene Punkte

- [ ] Exakte OSC-Schreibweise für Playback Level, Release, Pause, Grand Master und Blackout aus dem ZerOS-Handbuch übertragen und am Pult testen
- [ ] Tatsächliche IP-Adresse des Pults und die OSC-Adresseinstellung prüfen
- [ ] Prüfen, ob Phantom ZerOS OSC empfängt
- [ ] Prüfen, ob `/zeros/cue/go/0/<cue>` auf dem Master Playback funktioniert
- [ ] Klären, ob ProPresenter und Ableton auf demselben Rechner laufen und unter welchem Betriebssystem
- [ ] Klären, welche Ableton-Edition vorhanden ist und ob Max for Live dabei ist
- [ ] Klären, ob in der ProPresenter-Lizenz MIDI-Geräte verfügbar sind
- [ ] Lizenz für dieses Repo festlegen

## Grundregeln

- **Das Pult hat immer Vorrang.** Fällt die Bridge aus, läuft die Show von Hand weiter.
- **Cue-Nummern sind ein Vertrag.** Ferngesteuerte Cues werden nie umnummeriert.
- **OSC-Adressen stehen nur in `docs/02`** und als Konstanten in `zeros-osc`.
- **Eigenes, kabelgebundenes Netz** für Pult und Zuspielrechner, ohne Internet.

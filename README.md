# flx-osc-control

Lichtstimmungen auf einem **Zero 88 FLX S24** aus **ProPresenter** und **Ableton Live** auslösen – über MIDI-Noten, eine kleine Bridge und OSC (Open Sound Control).

> **Stand:** `zeros-osc`, `mock-console` und `midi-bridge` sind gebaut und in der CI getestet. Am Pult, mit ProPresenter und mit Ableton ist noch nichts getestet. Wie du baust und testest, steht unter [Bauen und testen](#bauen-und-testen--schritt-für-schritt).

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
| [`zeros-osc`](packages/zeros-osc/README.md) | ZerOS-Befehle bauen, prüfen und senden; Kommandozeile `flxctl` | 0.1.0, am Pult ungetestet |
| [`mock-console`](packages/mock-console/README.md) | Pult-Attrappe für Tests ohne Hardware | gebaut |
| [`midi-bridge`](packages/midi-bridge/README.md) | MIDI-Note in OSC übersetzen | gebaut, am Pult ungetestet |
| `propresenter-watcher` | OSC aus der ProPresenter-API ableiten | optional, später |
| Max-for-Live-Device „LX Cue Send" | OSC direkt aus Ableton | optional, später |

Technik: Python ab 3.11 mit `python-osc`, `mido` samt `python-rtmidi`, `PyYAML` und `pytest`.

## Was du brauchst

| Wofür | Was | Kosten |
| --- | --- | --- |
| Bauen und alle automatischen Tests | ein Rechner mit Windows, macOS oder Linux, Internet, [Git](https://git-scm.com/) und [uv](https://docs.astral.sh/uv/) | frei |
| Test mit MIDI, noch ohne Show-Programme | zusätzlich ein virtueller MIDI-Port: unter Windows das Programm loopMIDI, am Mac der eingebaute IAC-Treiber | frei |
| Test mit den Show-Programmen | ProPresenter mit MIDI-Gerät (Windows-PC), Ableton Live (Mac) | vorhanden |
| Test am Pult | FLX S24 mit ZerOS ab 7.14, Netzwerk-Switch, Netzwerkkabel | vorhanden |

Python musst du nicht selbst installieren. uv lädt eine passende Version.

## Bauen und testen – Schritt für Schritt

Die Anleitung hat vier Stufen. **Stufe A und B gehen ohne Pult, ohne ProPresenter und ohne Ableton.** Jeder Befehl in Stufe A ist auf einem Linux-Rechner ausgeführt worden; die gezeigte Ausgabe stammt aus diesen Läufen. Stufe B bis D sind bisher an keinem echten Gerät gelaufen.

Alle Befehle gelten für die PowerShell unter Windows und für das Terminal unter macOS und Linux.

### Stufe A: ein Rechner, sonst nichts

**1. Git und uv installieren**

Windows, in der PowerShell:

```bash
winget install --id Git.Git -e
```
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS, im Terminal:

```bash
xcode-select --install
```
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Linux: Git über die Paketverwaltung, uv mit demselben `curl`-Befehl wie am Mac.

Danach das Fenster schließen und neu öffnen. Kontrolle: `git --version` und `uv --version` zeigen je eine Versionsnummer.

**2. Repo holen**

```bash
git clone https://github.com/michpese/flx-osc-control.git
```
```bash
cd flx-osc-control
```

Das Repo ist privat. Git fragt beim ersten Mal nach deiner GitHub-Anmeldung.

**3. Bauen**

```bash
uv sync --all-packages
```

Das legt den Ordner `.venv/` an und installiert die drei Pakete samt Abhängigkeiten. Danach gibt es die Befehle `flxctl`, `mock-console` und `midi-bridge`, jeweils mit `uv run` davor.

Nur unter Linux: Bricht der Befehl mit `Dependency "alsa" not found` ab, fehlt für deine Python-Version ein fertiges Paket der MIDI-Bibliothek. Dann hilft:

```bash
uv sync --all-packages --python 3.12
```

**4. Automatische Tests laufen lassen**

```bash
uv run pytest
```

Erwartet wird am Ende eine Zeile wie `213 passed, 3 skipped`. Die Zahl wächst mit dem Code. Wichtig ist: kein `failed`. Die drei übersprungenen Tests brauchen einen virtuellen MIDI-Port, den es unter Windows und auf Rechnern ohne MIDI-System nicht gibt; die Zeile darunter nennt den Grund.

**5. Einen Befehl trocken ausgeben**

```bash
uv run flxctl --host 127.0.0.1 cue go 10 2 --dry-run
```

```text
… adresse=/zeros/cue/go/10/2 ziel=127.0.0.1:8830/udp DRY-RUN nicht gesendet
```

Ohne `--host` oder `--config` sendet `flxctl` nichts und meldet `kein Ziel`.

**6. An die Pult-Attrappe senden**

Die `mock-console` spielt das Pult. Öffne ein **zweites** Fenster im selben Ordner und starte sie dort:

```bash
uv run mock-console --host 127.0.0.1
```

```text
mock-console lauscht auf 127.0.0.1:8830/udp
```

Im ersten Fenster:

```bash
uv run flxctl --host 127.0.0.1 cue go 10 2
```
```bash
uv run flxctl --host 127.0.0.1 blackout on
```

Im Fenster der Attrappe erscheint je Befehl eine Zeile:

```text
… adresse=/zeros/cue/go/10/2 argumente=[] akzeptiert befehl=cue_go pfad=/zeros/cue/go/10/2 status=belegt
… adresse=/zeros/blackout/1 argumente=[] akzeptiert befehl=blackout pfad=/zeros/blackout/1 status=vermutet HINWEIS: …
```

`akzeptiert` heißt: Die Adresse steht in der Referenz. Bei `status=vermutet` ist die Schreibweise unbestätigt; das echte Pult kann sie ablehnen. Die Attrappe beendest du mit Strg+C.

**7. Mapping prüfen und Spickzettel erzeugen**

```bash
uv run flxctl map check shows/mapping.example.yaml
```

```text
OK: shows/mapping.example.yaml (0 Hinweise)
```

```bash
uv run flxctl map doc shows/mapping.example.yaml
```

Das gibt eine Tabelle aller Noten mit Name und OSC-Adresse aus, gedacht für die Bediener.

Damit ist Stufe A bestanden: Die Software baut, die Tests laufen, und ein Befehl kommt als OSC-Paket bei einer Gegenstelle an.

### Stufe B: mit MIDI, ohne Show-Programme

Hier läuft die ganze Software-Kette: Testnote → MIDI-Port → Bridge → Attrappe.

**1. Virtuellen MIDI-Port anlegen**

- Windows: loopMIDI installieren, unten links „LX Bridge" eintragen, mit „+" anlegen.
- macOS: Audio-MIDI-Setup → Fenster → MIDI-Studio einblenden → Doppelklick auf „IAC-Treiber" → „Gerät ist online" → mit „+" einen Port „LX Bridge" anlegen → Anwenden.

**2. Portnamen ablesen**

```bash
uv run midi-bridge --list-ports
```

Unter Windows steht dort etwa `LX Bridge 1`, am Mac etwa `IAC-Treiber LX Bridge`. Den Namen brauchst du gleich zweimal.

**3. Test-Mapping anlegen**

```bash
cp shows/mapping.example.yaml shows/test.local.yaml
```

Öffne `shows/test.local.yaml` in einem Editor und ändere zwei Dinge:

- `console.host` auf `127.0.0.1`, damit an die Attrappe gesendet wird
- bei der Quelle deines Rechners `midi_port` auf den Namen aus Schritt 2 (unter Windows reicht `"LX Bridge"`)

Speichere die Datei als **UTF-8**. Dateien mit der Endung `.local.yaml` landen nicht im Repo.

**4. Attrappe starten** (Fenster 2)

```bash
uv run mock-console --host 127.0.0.1
```

**5. Bridge starten** (Fenster 1)

```bash
uv run midi-bridge --mapping shows/test.local.yaml
```

Die Bridge meldet, dass sie läuft und welchen Port sie geöffnet hat. Dass der Port des jeweils anderen Rechners fehlt, ist harmlos.

**6. Testnote senden** (Fenster 3)

Zuerst den Namen des MIDI-Ausgangs ablesen:

```bash
uv run python -c "import mido; print(mido.get_output_names())"
```

Dann eine Note senden. Setze den abgelesenen Namen ein. `channel=14` ist MIDI-Kanal 15 (ProPresenter), `channel=15` ist Kanal 16 (Ableton); Python zählt ab 0.

```bash
uv run python -c "import mido; mido.open_output('LX Bridge 1').send(mido.Message('note_on', channel=14, note=1, velocity=127))"
```

**7. Ergebnis ablesen**

Im Fenster der Bridge:

```text
… quelle=propresenter kanal=15 note=1 name="Einlass" adresse=/zeros/cue/go/10/1 dauer_ms=0.4 gesendet
```

Im Fenster der Attrappe steht dieselbe Adresse mit `akzeptiert`. Sendest du die Note innerhalb einer Viertelsekunde zweimal, steht beim zweiten Mal `entprellt`.

Beide Programme beendest du mit Strg+C.

### Stufe C: mit ProPresenter und Ableton

1. ProPresenter einrichten nach [docs/04-setup-propresenter.md](docs/04-setup-propresenter.md), Ableton nach [docs/05-setup-ableton.md](docs/05-setup-ableton.md).
2. Auf jedem der beiden Rechner Stufe A, Schritte 1 bis 3, und Stufe B, Schritte 1 bis 5, ausführen.
3. Bridge zuerst mit `--dry-run` starten, dann eine Folie mit Licht-Makro anklicken beziehungsweise einen Clip mit Note abspielen. Erwartet wird genau eine Zeile mit `DRY-RUN nicht gesendet`.

Die Einzelschritte je Betriebssystem stehen im [README der midi-bridge](packages/midi-bridge/README.md).

### Stufe D: am Pult

1. Pult und Netz vorbereiten nach [docs/03-setup-flx.md](docs/03-setup-flx.md).
2. Eigenes Mapping anlegen: `shows/mapping.example.yaml` nach `shows/<ort>/mapping.yaml` kopieren und `console.host` auf die IP-Adresse des Pults setzen.
3. Einen Cue vom Rechner auslösen und im Event Monitor des Pults kontrollieren:
   ```bash
   uv run flxctl --config shows/<ort>/mapping.yaml cue go 10 1
   ```
4. Die Tabellen der Teststufen 2 und 5 in [docs/06-testplan.md](docs/06-testplan.md) abarbeiten und ausfüllen.
5. Bridge ohne `--dry-run` starten und mit [docs/07-betrieb-checkliste.md](docs/07-betrieb-checkliste.md) in die Generalprobe gehen.

## Bekannte Einschränkungen

Stand des Prüfberichts vom 13.11.2026 zu Commit `6e3cf48`. Bis die Punkte behoben sind, gilt im Betrieb:

- **`mapping.yaml` immer als UTF-8 speichern.** Eine Datei in anderer Kodierung, etwa ANSI aus dem Windows-Editor, beendet die laufende Bridge.
- **UDP verwenden,** nicht `tcp-slip`. Bei TCP geht nach einem Neustart des Pults die erste Note still verloren.
- **Am Mac den Portnamen aus `--list-ports` eintragen.** „LX Bridge" allein passt dort vermutlich nicht.
- **Unter Windows nicht ins Fenster der Bridge klicken.** Markierter Text hält dort vermutlich die Ausgabe und damit die Bridge an.
- **Nur eine Bridge je Rechner starten.** Zwei senden jede Note doppelt.
- **Keinen zweiten MIDI-Port anlegen, dessen Name mit „LX Bridge" beginnt.** Die Bridge öffnet dann keinen.
- **Kein Befehl ist bisher am Pult getestet.** Neun stehen auf „vermutet". Im Einsatz nur verwenden, was Teststufe 2 bestätigt hat; das Beispiel-Mapping nutzt nur den belegten Befehl `cue go`.

## Entwicklung

Alle drei Pakete liegen in einem uv-Workspace; `mock-console` und `midi-bridge` hängen von `zeros-osc` ab.

```text
uv run pytest                     alle Tests
uv run pytest packages/zeros-osc  nur ein Paket
uv run ruff check .               Lint
uv run ruff format --check .      Formatierung prüfen (ohne --check: formatieren)
```

Die CI (`.github/workflows/ci.yml`) führt dieselben Schritte auf macOS und Windows mit Python 3.11 und 3.13 aus. Neue Pakete entstehen über die Bauaufträge unter [`prompts/`](prompts/README.md); die Regeln dafür stehen in [`CLAUDE.md`](CLAUDE.md).

## Offene Punkte

- [ ] Die neun Befehle mit Status „vermutet" (Cue Pause und Next, Playback Go, Pause, Level, Release und View, Grand Master, Blackout) mit dem ZerOS-Handbuch abgleichen und am Pult testen
- [ ] Tatsächliche IP-Adresse des Pults und die OSC-Adresseinstellung prüfen
- [ ] Prüfen, ob Phantom ZerOS OSC empfängt
- [ ] Prüfen, ob `/zeros/cue/go/0/<cue>` auf dem Master Playback funktioniert
- [x] Geklärt: ProPresenter läuft auf einem Windows-PC, Ableton auf einem Mac; die Bridge läuft auf beiden
- [ ] Klären, welche Ableton-Edition vorhanden ist und ob Max for Live dabei ist
- [ ] Klären, ob in der ProPresenter-Lizenz MIDI-Geräte verfügbar sind

## Grundregeln

- **Das Pult hat immer Vorrang.** Fällt die Bridge aus, läuft die Show von Hand weiter.
- **Cue-Nummern sind ein Vertrag.** Ferngesteuerte Cues werden nie umnummeriert.
- **OSC-Adressen stehen nur in `docs/02`** und als Konstanten in `zeros-osc`.
- **Eigenes, kabelgebundenes Netz** für Pult und Zuspielrechner, ohne Internet.

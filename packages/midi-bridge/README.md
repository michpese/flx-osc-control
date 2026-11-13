# midi-bridge

> **Stand:** Version 0.1.0. Gebaut und mit der `mock-console` getestet, noch nicht mit ProPresenter, Ableton oder dem Pult.

Ein Dauerläufer, der MIDI-Noten in OSC-Befehle für das FLX S24 übersetzt. Gesendet wird ausschließlich über `zeros-osc` an `console.host` aus der `mapping.yaml`.

## Was es tut

1. Liest `mapping.yaml` und prüft sie mit der Prüfung aus `zeros-osc` (dieselbe wie `flxctl map check`). Mit Fehlern startet die Bridge nicht.
2. Öffnet die MIDI-Eingänge aus `sources.<name>.midi_port`. Teilen sich mehrere Quellen einen Port, wird er nur einmal geöffnet.
3. Bei Note On mit Velocity größer 0 sucht sie die Quelle über Port und Kanal, dann die Note im Mapping.
4. Sendet die Adresse über `zeros-osc` und schreibt eine Zeile ins Log.

Note Off, Note On mit Velocity 0 und alle anderen MIDI-Nachrichten werden ohne Log-Zeile ignoriert.

## Verhalten im Betrieb

| Fall | Verhalten |
| --- | --- |
| Dieselbe Note von derselben Quelle innerhalb von `debounce_ms` | löst nur einmal aus, die Wiederholung steht als `entprellt` im Log. Gemessen wird mit dem Zeitpunkt des Empfangs, nicht der Verarbeitung. Die Sperrzeit beginnt erst nach einem erfolgreichen Senden: Scheitert das Senden, geht ein sofortiger zweiter Versuch durch |
| Note beim Verarbeiten älter als 2 s, zum Beispiel weil das Senden hing | wird verworfen und nicht nachgesendet, Log: `verworfen: … s alt` |
| MIDI-Port verschwindet | Log-Zeile, dann alle 2 s ein neuer Versuch, ohne Absturz. Weitere Fehlversuche stehen nicht im Log, erst wieder das erfolgreiche Öffnen |
| `mapping.yaml` geändert | wird innerhalb einer Sekunde erkannt, vollständig geprüft und übernommen, ohne Neustart. Erkannt wird jede Änderung am Inhalt, auch wenn Größe und Zeitstempel gleich bleiben. Ist die neue Datei fehlerhaft oder nicht als UTF-8 gespeichert, bleibt die alte aktiv und das Log nennt jeden Fehler einmal |
| Senden scheitert, zum Beispiel weil das Netz fehlt | Log `FEHLER beim Senden`, die Bridge läuft weiter. Bei `tcp-slip` gilt ein Zeitlimit von 1 s je Verbindungsversuch |
| Fehler beim Verarbeiten einer Nachricht | Log `FEHLER bei der Verarbeitung`, die nächste Note wird normal verarbeitet |
| Verarbeitungs-Thread bricht trotzdem ab | Log `FEHLER: Verarbeitungs-Thread ist beendet … Licht von Hand fahren.`, die Bridge beendet sich mit Exit-Code 1 |
| Strg+C | Ports zu, Noten in der Warteschlange werden verworfen (je eine Log-Zeile), dann Ende |

Beim Start und nach jedem Neuladen zeigt die Bridge die Hinweise der Mapping-Prüfung, zum Beispiel für Befehle mit Status „vermutet“ oder „Forum“.

### Portnamen

`midi_port` in der `mapping.yaml` ist der **Anfang** des Namens, den das System für den MIDI-Eingang anzeigt. Gibt es einen Eingang mit genau diesem Namen, gilt er. Sonst muss genau ein Eingang mit diesem Text beginnen. Beginnen mehrere damit, öffnet die Bridge keinen und nennt im Log alle Kandidaten.

Welche Namen dein System anzeigt, zeigt `midi-bridge --list-ports`. Einen Port mit dem Namen „LX Bridge“ zeigen die Systeme verschieden an:

| System | Angezeigter Name (Beispiel) | passt zu `midi_port: "LX Bridge"` |
| --- | --- | --- |
| Windows, loopMIDI | `LX Bridge 1` (Windows hängt eine Nummer an) | ja |
| macOS, IAC-Treiber | `IAC-Treiber LX Bridge` (bzw. auf einem englischen System `IAC Driver LX Bridge`) | **nein** |

Auf dem Mac beginnt der Name also mit dem Namen des IAC-Treibers, und der hängt von der Systemsprache ab. Prüfe ihn mit `--list-ports`. Weil ProPresenter nur unter Windows und Ableton nur auf dem Mac läuft, reicht trotzdem eine gemeinsame `mapping.yaml`: Jede Quelle bekommt den Portnamen ihres Rechners.

```yaml
sources:
  propresenter:
    midi_port: "LX Bridge"              # Windows, loopMIDI
    channel: 15
  ableton:
    midi_port: "IAC-Treiber LX Bridge"  # Mac, so wie --list-ports ihn zeigt
    channel: 16
```

Jede Bridge meldet dann einmal, dass der Port des anderen Rechners nicht gefunden wurde, und versucht es still weiter. Das ist harmlos.

## Einrichtung unter macOS (Ableton-Rechner)

1. **IAC-Port anlegen.** Programm „Audio-MIDI-Setup“ öffnen → Fenster → MIDI-Studio einblenden → Doppelklick auf „IAC-Treiber“ → „Gerät ist online“ aktivieren → mit „+“ einen Port anlegen und „LX Bridge“ nennen → Anwenden.
2. **uv installieren.** Im Terminal:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Danach das Terminal neu öffnen. uv lädt bei Bedarf auch Python 3.11 oder neuer.
3. **Repo holen** und in den Ordner wechseln:
   ```bash
   git clone https://github.com/michpese/flx-osc-control.git
   ```
   ```bash
   cd flx-osc-control
   ```
4. **Abhängigkeiten installieren:**
   ```bash
   uv sync --all-packages
   ```
5. **Portnamen ablesen:**
   ```bash
   uv run midi-bridge --list-ports
   ```
   Erwartet wird eine Zeile wie `IAC-Treiber LX Bridge`. Fehlt sie, ist der IAC-Treiber nicht online (Schritt 1).
6. **Mapping anlegen.** `shows/mapping.example.yaml` nach `shows/<ort>/mapping.yaml` kopieren, `console.host` auf die IP des Pults setzen und bei `ableton.midi_port` den Namen aus Schritt 5 eintragen (siehe „Portnamen“).
7. **Mapping prüfen:**
   ```bash
   uv run flxctl map check shows/<ort>/mapping.yaml
   ```
8. **Trocken testen:**
   ```bash
   uv run midi-bridge --mapping shows/<ort>/mapping.yaml --dry-run
   ```
   In Ableton eine Note auf der Spur „LX“ abspielen (Einrichtung: [docs/05-setup-ableton.md](../../docs/05-setup-ableton.md)). Im Log muss genau eine Zeile mit `DRY-RUN nicht gesendet` erscheinen.
9. **Echt starten:** derselbe Befehl ohne `--dry-run`. Ob der Befehl am Pult ankam, zeigt nur der Event Monitor am Pult. Beenden mit Strg+C.

## Einrichtung unter Windows (ProPresenter-Rechner)

1. **loopMIDI installieren** (Tobias Erichsen), unten links den Namen „LX Bridge“ eintragen, mit „+“ anlegen. loopMIDI in den Autostart legen.
2. **uv installieren.** In der PowerShell:
   ```bash
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   Danach die PowerShell neu öffnen.
3. **Repo holen** (mit Git oder als ZIP von GitHub) und in der PowerShell in den Ordner `flx-osc-control` wechseln.
4. **Abhängigkeiten installieren:**
   ```bash
   uv sync --all-packages
   ```
5. **Portnamen ablesen:**
   ```bash
   uv run midi-bridge --list-ports
   ```
   Erwartet wird eine Zeile wie `LX Bridge 1`. Fehlt sie, läuft loopMIDI nicht.
6. **Mapping anlegen** wie unter macOS, Schritt 6. Bei `propresenter.midi_port` reicht `"LX Bridge"`.
7. **Mapping prüfen:**
   ```bash
   uv run flxctl map check shows/<ort>/mapping.yaml
   ```
8. **Trocken testen:**
   ```bash
   uv run midi-bridge --mapping shows/<ort>/mapping.yaml --dry-run
   ```
   In ProPresenter eine Folie mit MIDI-Aktion auslösen (Einrichtung: [docs/04-setup-propresenter.md](../../docs/04-setup-propresenter.md)). Im Log muss genau eine Zeile mit `DRY-RUN nicht gesendet` erscheinen.
9. **Echt starten:** derselbe Befehl ohne `--dry-run`. Beenden mit Strg+C.

## Aufruf

```text
midi-bridge --mapping shows/x/mapping.yaml             Dauerbetrieb
midi-bridge --mapping shows/x/mapping.yaml --dry-run   nichts senden, nur anzeigen
midi-bridge --list-ports                               alle MIDI-Eingänge anzeigen
```

Ohne Installation des Befehls geht auch `uv run python -m midi_bridge …`.

## Log

Eine Zeile je Ereignis mit Empfangszeit, Quelle, Kanal, Note, Name, Adresse und der Dauer zwischen Empfang und Versand in Millisekunden:

```text
2026-11-13 19:02:11.482 quelle=propresenter kanal=15 note=2 name="Musik ruhig" adresse=/zeros/cue/go/10/2 dauer_ms=0.4 gesendet
2026-11-13 19:02:11.590 quelle=propresenter kanal=15 note=2 name="Musik ruhig" adresse=/zeros/cue/go/10/2 dauer_ms=- entprellt
2026-11-13 19:02:14.003 quelle=ableton kanal=16 note=9 name=- adresse=- dauer_ms=- ignoriert: Note nicht im Mapping
```

Statuszeilen beginnen nach dem Zeitstempel mit `midi-bridge:`, zum Beispiel beim Öffnen eines Ports oder nach dem Neuladen des Mappings.

## Aufbau

- **MIDI-Callback** (ein Thread je offenem Port, gehört zu rtmidi): stempelt die Empfangszeit und legt die Nachricht in eine unbegrenzte Warteschlange (`queue.SimpleQueue`). Sonst nichts.
- **Verarbeitungs-Thread** (genau einer): arbeitet die Warteschlange der Reihe nach ab und sendet. Jede Nachricht läuft in einem eigenen try/except.
- **Haupt-Thread:** prüft jede Sekunde die `mapping.yaml`, alle 2 s die MIDI-Eingänge und in jeder Runde, ob der Verarbeitungs-Thread noch lebt.

Das Mapping ist ein unveränderliches Objekt. Ein neues wird erst vollständig geprüft und dann mit einer Zuweisung eingesetzt. Der Verarbeitungs-Thread liest die Referenz einmal pro Nachricht und sieht so nie ein halbes Mapping.

## Tests

- `packages/midi-bridge/tests`: alle Abläufe ohne echten MIDI-Port. Nachrichten gehen direkt in die Warteschlange oder über ein Ersatz-Backend, gesendet wird echt an die `mock-console` auf 127.0.0.1. Läuft überall.
- `tests/e2e`: virtueller MIDI-Port → Bridge → `mock-console`. Läuft nur, wo rtmidi virtuelle Ports anlegen kann: macOS und Linux mit ALSA-Sequencer. Unter Windows wird es übersprungen, weil rtmidi dort keine virtuellen Ports kann. `pytest -rs` zeigt den Grund.

## Grenzen

- Keine grafische Oberfläche.
- Kein eigenes Senden an `zeros-osc` vorbei.
- Keine Annahmen über Portnamen außerhalb der Konfiguration.
- Noten, die gesendet werden, während der Port fehlt, kommen nie an. Das kann keine Software auffangen.

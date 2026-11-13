# midi-bridge

> **Stand:** geplant, noch kein Code. Bauauftrag: [`prompts/04-midi-bridge.md`](../../prompts/04-midi-bridge.md).

Ein Dauerläufer, der MIDI-Noten in OSC-Befehle für das FLX S24 übersetzt.

## Was es tut

1. Liest `mapping.yaml` und prüft sie.
2. Öffnet den MIDI-Eingang „LX Bridge" und wartet.
3. Kommt ein Note On, sucht es Kanal und Note im Mapping.
4. Sendet die zugehörige Adresse über `zeros-osc` ans Pult.
5. Schreibt jede Aktion mit Zeiten ins Log.

Es unterdrückt Wiederholungen derselben Note innerhalb von `debounce_ms`, öffnet den Port neu, wenn er verschwindet, und übernimmt Änderungen am Mapping ohne Neustart.

## Geplante Nutzung

```text
midi-bridge --mapping shows/x/mapping.yaml
midi-bridge --mapping shows/x/mapping.yaml --dry-run
midi-bridge --list-ports
```

## Beispiel für eine Log-Zeile

```text
2026-11-13T19:02:11.482 propresenter ch15 note2 "Musik ruhig" -> /zeros/cue/go/10/2 (3 ms)
```

## Grenzen

- Keine grafische Oberfläche.
- Kein eigenes Senden an `zeros-osc` vorbei.
- Keine Annahmen über Portnamen außerhalb der Konfiguration.

## Fertig, wenn

- `tests/e2e` mit einem virtuellen MIDI-Port und der `mock-console` zeigt: eine Note erzeugt genau eine Nachricht, Entprellen greift, ein Port-Verlust wird überstanden
- dieses README die Einrichtung auf macOS und Windows Schritt für Schritt beschreibt

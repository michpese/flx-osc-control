# mock-console

> **Stand:** geplant, noch kein Code. Bauauftrag: [`prompts/03-mock-console.md`](../../prompts/03-mock-console.md).

Eine Attrappe des FLX S24 für Tests ohne Hardware.

## Was es tut

Das Programm lauscht auf Port 8830 und verhält sich wie das Pult, soweit dokumentiert. Es schreibt jede Nachricht mit Zeitstempel mit und markiert, was ZerOS ignorieren würde: Wildcards, Bundles mit Zeitstempel und unbekannte Adressen. In automatischen Tests ist es die Gegenstelle für `zeros-osc` und `midi-bridge`.

## Geplante Nutzung

```text
mock-console                        lauscht auf 0.0.0.0:8830
mock-console --port 9000            anderer Port
mock-console --jsonl empfang.jsonl  zusätzlich in eine Datei schreiben
```

In Tests startet eine pytest-Fixture die Attrappe auf einem freien Port und gibt die empfangenen Nachrichten zurück.

## Grenzen

- Keine Simulation von Licht oder Cue-Zuständen.
- Bewertet wird nur nach [docs/02-flx-osc-referenz.md](../../docs/02-flx-osc-referenz.md).

## Fertig, wenn

- Tests alle vier Schreibweisen von „Cue 5 auf Playback 1" als gleichwertig erkennen
- Tests die drei Ablehnungsgründe abdecken: Wildcard, Zeitstempel-Bundle, unbekannte Adresse

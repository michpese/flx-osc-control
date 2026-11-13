# tests/e2e

Tests über die ganze Software-Kette: virtueller MIDI-Port → `midi-bridge` → `mock-console`.

> **Stand:** leer. Die Tests entstehen mit [`prompts/04-midi-bridge.md`](../../prompts/04-midi-bridge.md).

## Was hier geprüft wird

- Eine Note erzeugt genau eine OSC-Nachricht mit der Adresse aus dem Mapping.
- Dieselbe Note innerhalb der Sperrzeit erzeugt keine zweite Nachricht.
- Verschwindet der MIDI-Port, verbindet sich die Bridge neu.
- Eine fehlerhafte `mapping.yaml` ersetzt das laufende Mapping nicht.

## Was hier nicht geprüft wird

Alles mit echter Hardware. Das steht in [docs/06-testplan.md](../../docs/06-testplan.md), Stufen 1, 2, 4, 5 und 6.

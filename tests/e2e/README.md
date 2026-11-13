# tests/e2e

Tests über die ganze Software-Kette: virtueller MIDI-Port → `midi-bridge` → `mock-console`.

> **Stand:** [`test_midi_bridge_e2e.py`](test_midi_bridge_e2e.py) prüft eine Note, das Entprellen und einen Port-Verlust. Die Tests brauchen einen virtuellen MIDI-Port: Sie laufen auf macOS und auf Linux mit ALSA-Sequencer. Unter Windows werden sie übersprungen, weil rtmidi dort keine virtuellen Ports anlegen kann. `pytest -rs` zeigt den Grund. Dieselbe Logik prüfen die Tests in [`packages/midi-bridge/tests`](../../packages/midi-bridge/tests) ohne echten Port.

## Was hier geprüft wird

- Eine Note erzeugt genau eine OSC-Nachricht mit der Adresse aus dem Mapping.
- Dieselbe Note innerhalb der Sperrzeit erzeugt keine zweite Nachricht.
- Verschwindet der MIDI-Port, verbindet sich die Bridge neu.
- Eine fehlerhafte `mapping.yaml` ersetzt das laufende Mapping nicht. Das prüfen nur die Tests in `packages/midi-bridge/tests`, weil dafür kein MIDI-Port nötig ist.

## Was hier nicht geprüft wird

Alles mit echter Hardware. Das steht in [docs/06-testplan.md](../../docs/06-testplan.md), Stufen 1, 2, 4, 5 und 6.

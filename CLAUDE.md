# flx-osc-control

Zweck: ProPresenter und Ableton lösen per MIDI-Note über eine Bridge
OSC-Befehle auf einem Zero 88 FLX S24 (ZerOS ab 7.14) aus.

Lies vor jeder Aufgabe `docs/01-konzept.md` und `docs/02-flx-osc-referenz.md`.

## Regeln

- OSC-Adressen kommen ausschließlich aus `docs/02-flx-osc-referenz.md`.
  Fehlt dort ein Befehl oder steht er auf „offen": nachfragen, nicht erfinden.
- ZerOS: UDP, Port 8830, Werte im Adresspfad, keine Wildcards,
  keine Bundles mit Zeitstempel, keine Rückmeldung vom Pult.
- Python ab 3.11, `python-osc`, `mido` mit `python-rtmidi`, `PyYAML`, `pytest`, `ruff`.
  Alles läuft auf macOS und Windows.
- Pakete liegen unter `packages/`. Nur `zeros-osc` sendet Netzwerkpakete,
  alle anderen Pakete benutzen `zeros-osc`.
- `zeros-osc` hängt von keinem anderen Paket dieses Repos ab.
- Jede Änderung hat Tests. Netzwerktests laufen gegen `mock-console`
  auf 127.0.0.1, nie gegen ein echtes Pult.
- Gesendet wird nur an `console.host` aus der Konfiguration.
- Log: eine Zeile pro Ereignis mit Zeitstempel, Quelle, Kanal, Note, Name, Adresse.
- Show-Daten (Mappings, Showfiles) liegen unter `shows/`, nie in einem Paket.
- Code und Kommentare auf Englisch, Dokumentation auf Deutsch.

## Arbeitsweise

- Ein Branch pro Aufgabe, am Ende ein Pull Request.
- Ändert sich das Verhalten, wird das README des Pakets im selben Schritt angepasst.
- Ergebnisse von Tests am echten Pult gehören in `docs/02` (Spalte „Am Pult getestet")
  und in `docs/06-testplan.md`.

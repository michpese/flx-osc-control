# flx-osc-control

Zweck: ProPresenter und Ableton lösen per MIDI-Note über eine Bridge
OSC-Befehle auf einem Zero 88 FLX S24 (ZerOS ab 7.14) aus.

Lies vor jeder Aufgabe `docs/01-konzept.md` und `docs/02-flx-osc-referenz.md`.

## Regeln

- OSC-Adressen kommen ausschließlich aus `docs/02-flx-osc-referenz.md`.
  Fehlt dort ein Befehl oder steht er auf „offen": nachfragen, nicht erfinden.
- Die Befehlstabelle in `docs/02` ändert nur ein Mensch. Trage dort keine
  Adresse, kein Beispiel und keinen Status ein und stufe keinen Status hoch,
  außer der Auftrag verlangt es ausdrücklich und nennt die Quelle.
- Befehle mit Status „vermutet" haben keine Quelle. Baue nichts, das sich auf
  ihre Schreibweise verlässt, ohne den Hinweis „vermutet" sichtbar zu machen.
- Fehlt in der Referenz ein Wertebereich: lege ihn nicht still fest. Schlage
  ihn vor und trage ihn nach Zustimmung unter „Festlegungen dieses Repos" in
  `docs/02` ein.
- ZerOS: UDP, Port 8830, Werte im Adresspfad, keine Wildcards,
  keine Bundles mit Zeitstempel, keine Rückmeldung vom Pult.
- Python ab 3.11, `python-osc`, `mido` mit `python-rtmidi`, `PyYAML`, `pytest`, `ruff`.
  Alles läuft auf macOS und Windows.
- Pakete liegen unter `packages/`. Nur `zeros-osc` sendet Netzwerkpakete,
  alle anderen Pakete benutzen `zeros-osc`.
- `zeros-osc` hängt von keinem anderen Paket dieses Repos ab.
- Jede Änderung hat Tests. Netzwerktests laufen nur auf 127.0.0.1, nie gegen
  ein echtes Pult: in `zeros-osc` gegen einen einfachen lokalen Socket, in
  allen anderen Paketen gegen `mock-console`.
- Gesendet wird nur an `console.host` aus der Konfiguration.
- Log: eine Zeile pro Ereignis mit Zeitstempel, Quelle, Kanal, Note, Name, Adresse.
- Show-Daten (Mappings, Showfiles) liegen unter `shows/`, nie in einem Paket.
- Code und Kommentare auf Englisch, Dokumentation auf Deutsch.

## Arbeitsweise

- Starte jede Aufgabe von aktuellem `main` (`git switch main && git pull`) und
  lege davon einen Branch an. Fehlt auf `main` eine Vorarbeit, auf der die
  Aufgabe aufbaut: halte an und sage es, statt auf einem ungemergten Branch
  weiterzubauen.
- Ein Branch pro Aufgabe, am Ende ein Pull Request gegen `main`.
- „Fertig" heißt: die CI des Pull Requests ist grün. Sie läuft auf macOS und
  Windows mit den echten Abhängigkeiten.
- Lässt sich eine Abhängigkeit nicht installieren, melde es zuerst. Ersetze sie
  nicht durch einen Nachbau. Läuft ein Test nur mit einem Ersatz, nenne ihn
  ungeprüft und nicht grün.
- Kannst du in deiner Umgebung nicht pushen, keinen Branch wechseln oder keine
  Dateien löschen: halte an, lass den Arbeitsordner wie er ist und nenne die
  Befehle, die der Mensch im Terminal ausführen soll. Lege keine
  Ausweichordner an.
- Ändert sich das Verhalten, wird das README des Pakets im selben Schritt angepasst.
- Nenne am Ende jede Entscheidung, die der Auftrag offen ließ.
- Ergebnisse von Tests am echten Pult gehören in `docs/02` (Spalte „Am Pult getestet")
  und in `docs/06-testplan.md`.

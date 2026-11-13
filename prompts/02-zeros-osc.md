# Prompt 2: zeros-osc und flxctl

**Effort:** `medium`

```text
Baue das Paket zeros-osc. Lies CLAUDE.md, docs/02-flx-osc-referenz.md
und packages/zeros-osc/README.md vollständig, bevor du Code schreibst.

Anforderungen
1. Für jeden Befehl der Referenz mit Status "belegt" oder "Forum" eine
   Funktion, die die OSC-Adresse als String liefert und die Zahlen
   prüft: Playback 0 bis 96, Cue größer 0, Punkt-Cues erlaubt.
2. Ein Client, der eine Adresse per UDP an host:port sendet.
   TCP (SLIP) als zweite, getrennte Option.
3. CLI flxctl mit einem Unterkommando je Befehl sowie --host, --port
   und --dry-run. Beispiel: flxctl cue go 10 2
4. flxctl map check <datei> prüft eine mapping.yaml nach dem Schema in
   docs/01-konzept.md und meldet doppelte Noten, fehlende Namen und
   Adressen, die zu keinem Befehl der Referenz passen.
   flxctl map doc <datei> schreibt eine Markdown-Tabelle für Bediener.

Grenzen
- Keine Befehle, die in der Referenz fehlen oder auf "offen" stehen.
  Liste mir am Ende auf, welche Befehle du deshalb ausgelassen hast.
- Befehle mit Status "Forum" kennzeichnet der Hilfetext als ungetestet.
- Gesendet wird immer die Form "alles im Pfad, keine Argumente".

Fertig, wenn: Unit-Tests jede Adresse gegen die Beispiele der Referenz
prüfen, ein Test das gesendete UDP-Paket auf 127.0.0.1 empfängt und
dekodiert, flxctl map check die Datei shows/mapping.example.yaml ohne
Fehler annimmt, und das README des Pakets drei Anwendungsbeispiele
zeigt.
```

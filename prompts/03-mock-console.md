# Prompt 3: mock-console

**Effort:** `medium`

```text
Baue das Paket mock-console: eine Attrappe des FLX S24 für Tests.
Lies CLAUDE.md, docs/02-flx-osc-referenz.md und
packages/mock-console/README.md.

Anforderungen
1. Lauscht per UDP auf einem wählbaren Port, Standard 8830.
2. Schreibt jede Nachricht mit Zeitstempel, Absender, Adresse und
   Argumenten ins Log und optional in eine JSON-Lines-Datei.
3. Bewertet jede Nachricht wie ZerOS laut Referenz: akzeptiert bekannte
   Adressen in allen vier gleichwertigen Schreibweisen, markiert
   Wildcards, Bundles mit Zeitstempel und unbekannte Adressen als
   "ignoriert" mit Grund.
4. Schreibt zu jeder akzeptierten Nachricht den Status des Befehls aus
   der Referenz dazu (belegt, Forum, vermutet). Bei "vermutet" steht im
   Log ausdrücklich, dass die Attrappe die Schreibweise nur annimmt,
   weil sie in der Referenz steht, und dass das echte Pult sie
   ablehnen kann.
5. Bietet eine Python-Fixture für pytest, die die Attrappe auf einem
   freien Port startet und die empfangenen Nachrichten samt Status
   zurückgibt.

Grenzen: keine Simulation von Licht oder Cue-Zuständen. Die Liste der
bekannten Adressen und ihr Status kommen aus zeros-osc, nicht aus einer
zweiten Kopie. Ändere die Befehlstabelle in docs/02 nicht.

Fertig, wenn: Tests alle vier Schreibweisen von "Cue 5 auf Playback 1"
als gleichwertig erkennen, die drei Ablehnungsgründe abdecken und für
je einen Befehl mit Status belegt, Forum und vermutet den Status im
Ergebnis prüfen; das README des Pakets Start und Fixture mit je einem
Beispiel zeigt; und die CI des Pull Requests grün ist.
```

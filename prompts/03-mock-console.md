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
4. Bietet eine Python-Fixture für pytest, die die Attrappe auf einem
   freien Port startet und die empfangenen Nachrichten zurückgibt.

Grenzen: keine Simulation von Licht oder Cue-Zuständen. Die Liste der
bekannten Adressen kommt aus zeros-osc, nicht aus einer zweiten Kopie.

Fertig, wenn: Tests alle vier Schreibweisen von "Cue 5 auf Playback 1"
als gleichwertig erkennen und die drei Ablehnungsgründe abdecken, und
das README des Pakets Start und Fixture mit je einem Beispiel zeigt.
```

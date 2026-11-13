# Prompt 5: Review vor dem Live-Einsatz

**Effort:** `xhigh`

```text
Prüfe das gesamte Repo flx-osc-control vor dem ersten Einsatz in einer
Live-Veranstaltung. Du änderst nichts, du berichtest.

Lies alle Dateien unter docs/, packages/ und tests/.

Suche gezielt nach:
1. Wegen, auf denen eine Note verloren geht oder doppelt auslöst.
2. Zuständen, in denen die Bridge hängt oder abstürzt: Port weg,
   Netz weg, fehlerhaftes Mapping, sehr viele Noten gleichzeitig.
3. Abweichungen zwischen Code und docs/02-flx-osc-referenz.md.
4. Stellen, die auf Windows oder macOS anders laufen.
5. Testlücken gemessen an docs/06-testplan.md.

Ergebnis: eine nach Schwere sortierte Liste. Je Fund: Datei und Zeile,
was passiert, wie man es auslöst, Vorschlag zur Behebung. Trenne
belegte Fehler von Vermutungen.
```

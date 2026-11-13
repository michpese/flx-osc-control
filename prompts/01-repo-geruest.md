# Prompt 1: Repo-Gerüst

**Effort:** `medium`

Dokumentation, `CLAUDE.md`, `README.md`, `shows/`, `integrations/` und die README-Dateien der Pakete liegen bereits im Repo. Dieser Prompt ergänzt das Python-Gerüst und die CI.

```text
Ergänze das Repo flx-osc-control um das Python-Gerüst.
Lies zuerst CLAUDE.md, README.md und docs/01-konzept.md.

Bereits vorhanden und nicht zu überschreiben: docs/, shows/,
integrations/, prompts/, CLAUDE.md, README.md sowie die README-Dateien
unter packages/ und tests/e2e/.

Erstelle:
- einen Python-Workspace im Wurzelverzeichnis mit den Paketen
  zeros-osc, mock-console und midi-bridge unter packages/
- je Paket: pyproject, src-Layout, tests/ mit einem Platzhaltertest,
  noch ohne Fachlogik
- die Abhängigkeit von mock-console und midi-bridge auf zeros-osc
- eine gemeinsame ruff- und pytest-Konfiguration
- .github/workflows/ci.yml, die ruff und pytest auf macOS und Windows
  ausführt

Schreibe noch keine Fachlogik.

Fertig, wenn: Installation und pytest mit je einem Platzhaltertest pro
Paket durchlaufen, und du mir den Verzeichnisbaum und die Befehle zum
Installieren und Testen zeigst. Trage diese Befehle in einen Abschnitt
"Entwicklung" im README.md ein.
```

# prompts

Fertige Bauaufträge für Claude Opus 5.5. Jeder Prompt baut ein Paket.

## Reihenfolge und Effort

| Nr. | Datei | Baut | Effort |
| --- | --- | --- | --- |
| 1 | [01-repo-geruest.md](01-repo-geruest.md) | Python-Workspace, Paket-Gerüste, CI | `medium` |
| 2 | [02-zeros-osc.md](02-zeros-osc.md) | Bibliothek und CLI `flxctl` | `medium` |
| 3 | [03-mock-console.md](03-mock-console.md) | Pult-Attrappe | `medium` |
| 4 | [04-midi-bridge.md](04-midi-bridge.md) | MIDI → OSC | `high` |
| 5 | [05-review.md](05-review.md) | Prüfung vor dem ersten Live-Einsatz | `xhigh` |
| 6 | [06-propresenter-watcher.md](06-propresenter-watcher.md) | optional: OSC aus der ProPresenter-API | `high` |
| 7 | [07-max-for-live.md](07-max-for-live.md) | optional: OSC direkt aus Ableton | `high` |

Für Doku, Spickzettel und kleine Korrekturen reicht `low`. `max` braucht dieses Projekt nicht.

Opus 5.5 kennt fünf Stufen: `low`, `medium`, `high`, `xhigh` und `max`. `medium` ist der Standard. Die Denktiefe steuerst du nur über Effort; das Denken selbst lässt sich nicht abschalten. In der API heißt der Parameter `output_config.effort`. Quelle: [Claude-Dokumentation, Effort](https://platform.claude.com/docs/build-with-claude/effort).

## Arbeitsweise

- **Ein Prompt pro Paket, eine neue Sitzung pro Prompt.** So bleibt der Kontext klein.
- **Ein Branch pro Prompt,** von aktuellem `main`, am Ende ein Pull Request.
- **Erst die Referenz, dann Code.** Jeder Prompt lässt Opus `CLAUDE.md` und `docs/02` lesen.
- **Nichts erfinden lassen.** Adressen kommen nur aus `docs/02-flx-osc-referenz.md`.
- **Abnahme steht im Prompt.** Jeder Prompt endet mit „Fertig, wenn …".

## Vor jedem Prompt

1. Der Pull Request des vorigen Prompts ist gemergt. Jeder Prompt baut auf `main` auf.
2. Lokal auf den neuen Stand gehen: `git switch main && git pull`.
3. Neuen Branch anlegen, zum Beispiel `git switch -c feat/mock-console`.
4. Erst dann die Opus-Sitzung im Repo-Ordner starten.

Beim Mergen „Create a merge commit" wählen, nicht „Squash". Baut doch einmal ein Branch auf einem ungemergten auf, vermeidet das Konflikte.

## Was die Umgebung können muss

| Fähigkeit | Wofür | Wenn sie fehlt |
| --- | --- | --- |
| Zugriff auf PyPI | Abhängigkeiten installieren, Tests mit den echten Paketen | Opus meldet es; maßgeblich ist dann die CI des Pull Requests |
| Zugriff auf GitHub | pushen, Pull Request öffnen | selbst im Terminal: `git push -u origin <branch>` |
| Dateien löschen im Repo-Ordner | Git ersetzt beim Branch-Wechsel und Commit Dateien | Branch-Wechsel und Commits selbst im Terminal machen |

„Fertig" ist ein Paket erst, wenn die CI des Pull Requests grün ist. Sie läuft auf macOS und Windows mit den echten Abhängigkeiten.

## Stand der Referenz

Die Befehlstabelle in `docs/02-flx-osc-referenz.md` ändert nur ein Mensch. Was dort auf „offen" steht, baut Opus nicht. Was auf „vermutet" steht, baut Opus mit sichtbarem Hinweis. Stufe einen Befehl erst auf „belegt" hoch, wenn du die Schreibweise im ZerOS-Handbuch nachgelesen hast, und passe dann die Konstante in `packages/zeros-osc/src/zeros_osc/commands.py` im selben Schritt an.

## So benutzt du eine Datei

Kopiere den Text im Codeblock unverändert in eine neue Sitzung im Repo-Ordner und stelle den Effort wie angegeben ein.

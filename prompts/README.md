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
- **Ein Branch pro Prompt,** am Ende ein Pull Request.
- **Erst die Referenz, dann Code.** Jeder Prompt lässt Opus `CLAUDE.md` und `docs/02` lesen.
- **Nichts erfinden lassen.** Adressen kommen nur aus `docs/02-flx-osc-referenz.md`.
- **Abnahme steht im Prompt.** Jeder Prompt endet mit „Fertig, wenn …".

## Vor Prompt 2

Trage die offenen Befehle in `docs/02-flx-osc-referenz.md` ein, soweit du sie brauchst. Was dort auf „offen" steht, baut Opus nicht.

## So benutzt du eine Datei

Kopiere den Text im Codeblock unverändert in eine neue Sitzung im Repo-Ordner und stelle den Effort wie angegeben ein.

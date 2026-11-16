# playback-panel (`flx-panel`)

> **Stand:** Version 0.1.0. Gebaut und mit `mock-console` getestet, noch nicht am echten Pult.

Grafische Windows-Bedienoberfläche zum direkten Ein- und Ausschalten von Playbacks auf einem **Zero 88 FLX S48** über OSC – gedacht für kleinere Events, bei denen Lichtstimmungen per Maus- oder Touch-Klick ohne ProPresenter, Ableton oder Cue-Listen geschaltet werden sollen.

Gesendet wird ausschließlich über [`zeros-osc`](../zeros-osc/README.md) an `console.host` aus der geladenen Konfigurationsdatei. Bestehende Pakete (`zeros-osc`, `midi-bridge`, `mock-console`) bleiben vollständig unverändert.

## Funktionsumfang

- **Bis zu 12 Playbacks/Buttons mit je EIN und AUS:** Im Bedienfenster werden dynamisch **nur die tatsächlich aktiven Buttons** angezeigt (sind z. B. 4 Buttons programmiert, erscheint ein aufgeräumtes 2×2-Raster ohne leere Platzhalter).
- **Komfortabler Konfigurationsdialog in der Oberfläche:** Alle 12 Plätze, Kurzbeschreibungen, Farbakzente, Pult-IP/Port, Fenstermodus und Autostart lassen sich direkt in der App bearbeiten und als UTF-8-YAML speichern.
- **Vier flexible Programmier-Modi je Button:**
  1. **`playback_level` (Standard):** **EIN** setzt ein Playback (0–96) auf den gewünschten Wert (Standard `100` %), **AUS** setzt **automatisch dasselbe Playback** auf `0` % (oder einen frei wählbaren Restwert), optional mit Überblendzeit (`fade` in Sekunden).
  2. **`playback_go_release`:** **EIN** startet das Playback (`/zeros/playback/go/<pb>`), **AUS** gibt es frei (`release`) oder hält es an (`pause`).
  3. **`cue_pair` (am Pult belegt):** **EIN** startet Cue X, **AUS** startet Cue Y auf demselben Playback (`/zeros/cue/go/<pb>/<cue>` – im ZerOS-Handbuch belegt und am FLX S48 getestet).
  4. **`custom` (Frei programmierbar & Mehrfachbefehle):** Beliebige Befehle aus [`docs/02-flx-osc-referenz.md`](../../docs/02-flx-osc-referenz.md) inklusive interaktivem Befehls-Baukasten; auch mehrere OSC-Befehle pro Klick auf EIN oder AUS.
- **Hinweis auf unbestätigte Befehle (`[vermutet]`):** Befehle wie `playback_level`, `playback_go` oder `playback_release` stehen in [`docs/02-flx-osc-referenz.md`](../../docs/02-flx-osc-referenz.md) auf Status `vermutet`. Sowohl `--check` als auch die Vorschau und die Karten zeigen diesen Hinweis sichtbar an. Falls das Pult eine `vermutet`-Adresse ablehnt, kann jeder Button jederzeit im Dialog auf `cue_pair` (`[belegt]`) umgestellt werden.
- **Event- & Kiosk-Funktionen:**
  - **Windows-Autostart** per Haken im Einstellungs-Tab oder per CLI (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, keine Administratorrechte nötig).
  - **Letzte Konfiguration merken:** Beim Start ohne Parameter öffnet `flx-panel.exe` automatisch die zuletzt verwendete YAML-Datei (`%APPDATA%\flx-playback-panel\settings.json`).
  - **Bediensperre (`[Gesperrt]` / `Entsperrt`):** Schützt Konfiguration, Dateimenü und Testmodus vor versehentlichem Verstellen während der Veranstaltung (`ui.start_locked: true`).
  - **Start-Automatik:** Einzelne Buttons können mit `auto_on_at_startup: true` nach einer einstellbaren Wartezeit (`ui.startup_delay_s`) beim Programmstart automatisch eingeschaltet werden.
  - **Sammelbutton „Alle Aus“:** Sendet den AUS-Befehl aller aktiven Buttons nacheinander (da ZerOS keinen eigenen „Release All“-OSC-Befehl besitzt).
  - **Live-Neuladen:** Externe Änderungen an der YAML-Datei werden am Dateiinhalt erkannt und im laufenden Betrieb übernommen; fehlerhafte Änderungen werden abgewiesen, ohne die laufende Konfiguration zu verlieren.

## Starten in der Entwicklungsumgebung

Aus dem Wurzelverzeichnis des Repos:

```bash
uv sync --all-packages
```

Oberfläche mit der Beispiel-Konfiguration im Testmodus (ohne Netzwerkversand) starten:

```bash
uv run flx-panel --config shows/playbacks.example.yaml --dry-run
```

Konfigurationsdatei auf der Kommandozeile prüfen:

```bash
uv run flx-panel --check shows/playbacks.example.yaml
```

Mit der Pult-Attrappe (`mock-console`) lokal auf `127.0.0.1` testen:

```bash
# Fenster 1:
uv run mock-console --host 127.0.0.1

# Fenster 2 (nachdem console.host in einer Kopie *.local.yaml auf 127.0.0.1 gesetzt wurde):
uv run flx-panel --config shows/test-playbacks.local.yaml
```

## Als eigenständige Windows-`.exe` bauen

### Weg 1: Lokal unter Windows (ein Befehl in der PowerShell)

Im Wurzelverzeichnis des Repos:

```powershell
.\packages\playback-panel\scripts\build_exe.ps1
```

Oder direkt über `uv`:

```powershell
uv run --package playback-panel --extra build flx-panel-build
```

Danach liegt die fertige Einzeldatei ohne Konsolenfenster unter:

```text
dist\flx-panel.exe
```

Sie benötigt auf dem Ziel-PC keine separate Python-Installation. Kopiere `flx-panel.exe` zusammen mit deiner `.yaml`-Konfiguration in einen festen Ordner (z. B. `C:\Licht\flx-panel.exe` und `C:\Licht\event.yaml`), öffne dort einmal die Datei und aktiviere bei Bedarf im Reiter **„2 | Pult, Fenster & Autostart“** den Windows-Autostart.

### Weg 2: Automatisch über GitHub Actions

Die Workflow-Datei [`.github/workflows/build-flx-panel-exe.yml`](../../.github/workflows/build-flx-panel-exe.yml) baut `dist/flx-panel.exe` auf `windows-latest`, prüft das Binary mit `--check shows/playbacks.example.yaml` und stellt `flx-panel-windows-exe` als herunterladbares Artifact bereit.

## Schema der Konfigurationsdatei

Vorlage: [`shows/playbacks.example.yaml`](../../shows/playbacks.example.yaml). Immer als **UTF-8** speichern (der eingebaute Dialog speichert automatisch als UTF-8).

| Feld | Typ | Pflicht | Bedeutung |
| --- | --- | --- | --- |
| `title` | Text | nein | Überschrift im Kopfbereich des Fensters |
| `console.host` | Text | ja | IP-Adresse des FLX S48 |
| `console.port` | 1–65535 | nein | OSC-Port am Pult (Standard `8830`) |
| `console.transport` | `udp` \| `tcp-slip` | nein | Transportprotokoll (Standard `udp`) |
| `ui.start_locked` | `bool` | nein | startet gesperrt im Bedienmodus (Standard `false`) |
| `ui.always_on_top` | `bool` | nein | hält das Fenster immer im Vordergrund (Standard `false`) |
| `ui.window_mode` | `normal` \| `maximized` \| `fullscreen` | nein | Fenstergröße beim Start (`F11` wechselt Vollbild, `Esc` verlässt Vollbild) |
| `ui.show_all_off` | `bool` | nein | blendet „Alle Aus“ in der Kopfzeile ein (Standard `true`) |
| `ui.startup_delay_s` | `0`–`300` | nein | Wartezeit in Sekunden vor `auto_on_at_startup` (Standard `2.0`) |
| `ui.language` | `de` \| `en` \| `ro` | nein | Startsprache der Oberfläche (`Deutsch`, `English`, `Română`; auch live über `DE \| EN \| RO` umschaltbar) |
| `buttons` | Liste (max. 12) | ja | konfigurierte Button-Plätze |
| `buttons[].name` | Text | ja | Titel auf der Karte |
| `buttons[].description` | Text | nein | Kurzbeschreibung unter dem Titel |
| `buttons[].enabled` | `bool` | nein | `false` blendet den Platz im Bedienfenster aus (Standard `true`) |
| `buttons[].color` | Text | nein | `amber`, `emerald`, `blue`, `violet`, `rose`, `cyan` oder `slate` |
| `buttons[].on_label` / `off_label` | Text | nein | Beschriftung der Tasten (Standard `EIN`/`ON`/`PORNIT` bzw. `AUS`/`OFF`/`OPRIT` je nach Sprache) |
| `buttons[].auto_on_at_startup` | `bool` | nein | sendet beim Programmstart automatisch den EIN-Befehl |
| `buttons[].mode` | Text | nein | `playback_level` (Standard), `playback_go_release`, `cue_pair` oder `custom` |

### Modus-spezifische Felder unter `buttons[]`

- **`playback_level`:** `playback` (`0`–`96`), `on_level` (`0`–`100`, Standard `100`), `off_level` (`0`–`100`, Standard `0` auf demselben Playback), optional `fade` (oder getrennt `on_fade` / `off_fade` in Sekunden).
- **`playback_go_release`:** `playback` (`0`–`96`), `off_action` (`release` oder `pause`, Standard `release`).
- **`cue_pair`:** `playback` (`0`–`96`), `on_cue` (größer `0`, Punkt-Cues erlaubt), `off_cue` (größer `0`).
- **`custom`:** `on_commands` (eine OSC-Adresse oder Liste von OSC-Adressen), `off_commands` (eine OSC-Adresse oder Liste von OSC-Adressen).

## Kommandozeilen-Optionen

```text
flx-panel [--config DATEI] [--dry-run] [--locked] [--edit] [--lang {de,en,ro}]
flx-panel --check DATEI
flx-panel --autostart {status,enable,disable} [--config DATEI]
flx-panel --version
```

Ereignisse werden im Format aus `CLAUDE.md` protokolliert (in der ausklappbaren Protokoll-Ansicht unten im Fenster, auf der Konsole sowie rotierend unter `%APPDATA%\flx-playback-panel\events.log`).

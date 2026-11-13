# zeros-osc

> **Stand:** Version 0.1.0. Alle Befehle der Referenz mit Status „belegt" oder „Forum" sind umgesetzt; am Pult getestet ist noch keiner.

Bibliothek und Kommandozeile `flxctl`: ZerOS-Befehle bauen, prüfen und senden.

Dieses Paket ist das einzige im Repo, das Netzwerkpakete sendet. Alle anderen benutzen es. Es hängt von keinem anderen Paket dieses Repos ab.

## Installation

Im Repo-Wurzelverzeichnis:

```text
uv sync --all-packages
uv run flxctl --help
```

## Anwendungsbeispiele

### 1. Einen Cue auslösen

Erst trocken prüfen, dann an das Pult senden:

```text
$ flxctl cue go 10 2 --dry-run
2026-11-13 11:10:23.970 quelle=flxctl kanal=- note=- name=- adresse=/zeros/cue/go/10/2 ziel=- DRY-RUN nicht gesendet

$ flxctl --host 192.168.1.10 cue go 10 2
2026-11-13 11:10:31.412 quelle=flxctl kanal=- note=- name=- adresse=/zeros/cue/go/10/2 ziel=192.168.1.10:8830/udp gesendet
```

„gesendet" heißt nur: Das Paket hat den Rechner verlassen. Das Pult antwortet nie. Ob der Befehl ankam, zeigt der Event Monitor am Pult.

Statt `--host` kann `--config` das Ziel aus der Show-Datei lesen (`console.host`, `.port`, `.transport`). Punkt-Cues gehen auch: `flxctl --config shows/kirche/mapping.yaml cue go 10 2.5`.

### 2. Eine Mapping-Datei vor der Show prüfen

```text
$ flxctl map check shows/kirche/mapping.yaml
Fehler: cues[4] (Note 1): doppelte Note 1, schon in cues[0]
Fehler: cues[5] (Note 6): name fehlt
Fehler: cues[6] (Note 7): Adresse /zeros/release/all passt zu keinem Befehl der Referenz
Hinweis: cues[3] (Note 5): /zeros/blackout/1: blackout ist ungetestet (Status vermutet, Schreibweise nicht belegt)
3 Fehler in shows/kirche/mapping.yaml
```

Geprüft wird nach dem Schema in [docs/01-konzept.md](../../docs/01-konzept.md): doppelte Noten, fehlende Namen, Adressen außerhalb der Referenz oder mit Werten außerhalb der Bereiche, außerdem `console`, `sources` und `debounce_ms`. Fehler ergeben Exit-Code 1, Hinweise nicht.

### 3. Einen Spickzettel für Bediener erzeugen

```text
$ flxctl map doc shows/mapping.example.yaml -o shows/mapping.example.md
```

Ergebnis (gekürzt):

```markdown
| Note | Name | Befehl | OSC-Adresse | Quellen | Hinweis |
| ---: | --- | --- | --- | --- | --- |
| 1 | Einlass | Cue auf einem Playback starten | `/zeros/cue/go/10/1` | alle |  |
| 2 | Musik ruhig | Cue auf einem Playback starten | `/zeros/cue/go/10/2` | alle |  |
```

Eine fehlerhafte Datei ergibt keinen Spickzettel, sondern die Fehlerliste.

### Aus Python

```python
from zeros_osc import UdpClient, cue_go

address = cue_go(playback=10, cue=2)  # "/zeros/cue/go/10/2"
with UdpClient("192.168.1.10", 8830) as client:
    client.send(address)
```

## Befehle

Quelle: [docs/02-flx-osc-referenz.md](../../docs/02-flx-osc-referenz.md). Gesendet wird immer die Form „alles im Pfad, keine Argumente".

| Funktion | flxctl | Adresse | Status |
| --- | --- | --- | --- |
| `cue_go(playback, cue)` | `cue go P C` | `/zeros/cue/go/<playback>/<cue>` | belegt |
| `cue_go_current(cue)` | `cue go-current C` | `/zeros/cue/go/<cue>` | ungetestet |
| `cue_go_next()` | `cue go-next` | `/zeros/cue/go` | ungetestet |
| `cue_pause(playback)` | `cue pause P` | `/zeros/cue/pause/<playback>` | vermutet |
| `cue_next(playback, cue)` | `cue next P C` | `/zeros/cue/next/<playback>/<cue>` | vermutet |
| `macro(number)` | `macro N` | `/zeros/macro/<nummer>` | ungetestet |
| `playback_go(playback)` | `playback go P` | `/zeros/playback/go/<playback>` | vermutet |
| `playback_pause(playback)` | `playback pause P` | `/zeros/playback/pause/<playback>` | vermutet |
| `playback_level(playback, level, fade=None)` | `playback level P L [--fade S]` | `/zeros/playback/level/<playback>/<level>[/<fade>]` | vermutet |
| `playback_release(playback)` | `playback release P` | `/zeros/playback/release/<playback>` | vermutet |
| `playback_view(playback)` | `playback view P` | `/zeros/playback/view/<playback>` | vermutet |
| `grand_master(level, fade=None)` | `grandmaster L [--fade S]` | `/zeros/grandmaster/<level>[/<fade>]` | vermutet |
| `blackout(value)` | `blackout on\|off\|1\|0` | `/zeros/blackout/<1\|0>` | vermutet |

„ungetestet" = Status „Forum" in der Referenz: im Herstellerforum genannt. „vermutet" = ohne Quelle eingetragen; die Schreibweise ist unbestätigt, bis sie am Pult geprüft ist. `flxctl` zeigt beides im Hilfetext und gibt beim Senden einen Hinweis aus.

### Wertebereiche

| Wert | Erlaubt | Beispiel |
| --- | --- | --- |
| Playback | ganze Zahl 0 bis 96 (0 = Master) | `10` |
| Cue | Zahl größer 0, Punkt-Cues erlaubt | `2`, `2.5` |
| Makro | ganze Zahl ab 1 | `1` |
| Level | ganze Zahl 0 bis 100 (Prozent) | `80` |
| Fade | Sekunden ab 0, Dezimalstellen erlaubt | `2`, `2.5` |
| Blackout | `1`/`on`/`true` oder `0`/`off`/`false`; gesendet wird `1` oder `0` | `on` |

Zahlen werden normalisiert gesendet: `3.0` wird zu `3`, `2.50` zu `2.5`. Falsche Werte ergeben in Python `ZerosValueError`, in `flxctl` Exit-Code 2, und es wird nichts gesendet.

## Transport

| `--transport` | Klasse | Rahmung |
| --- | --- | --- |
| `udp` (Standard) | `UdpClient` | ein OSC-Paket pro Datagramm |
| `tcp-slip` | `TcpSlipClient` | SLIP nach OSC 1.1 (END-Byte am Anfang und Ende) |

Der `TcpSlipClient` prüft vor jedem Senden, ob die Gegenseite die Verbindung geschlossen hat, und verbindet dann zuerst neu. Scheitert schon der Verbindungsaufbau, versucht er es bei diesem Senden kein zweites Mal; ein Aufruf wartet so höchstens ein Zeitlimit.

`flxctl` prüft das Ziel vor dem Senden: `host` muss Text sein, `port` eine ganze Zahl von 1 bis 65535, auch mit `--dry-run` und bei Werten aus `--config`. Zahlen in Adressen mit absurd großem Exponenten wie `1e9999999` werden abgelehnt, bevor sie ausgeschrieben werden.

Die Einstellung muss zum Feld „Transport" am Pult passen. Beide Clients prüfen jede Adresse vor dem Senden gegen die Referenz und verweigern alles andere.

## Grenzen

- Nur Befehle, die in der Referenz stehen und nicht „offen" sind. Kurzform `/lx/...`, Wildcards und Argument-Schreibweisen werden nicht gesendet und von `map check` abgelehnt.
- `/zeros/cue/go/0/<cue>` (Master Playback) ist erlaubt, `map check` gibt aber einen Hinweis aus: Laut Forum wurde das auf einem FLX S48 ignoriert.
- FLX-S-Pulte haben keine User-Makros, nur Fixture-Makros (siehe Referenz).

## Tests

```text
uv run pytest packages/zeros-osc
```

Die Tests prüfen jede Adresse gegen die Beispiele der Referenz und lesen dafür auch die Tabelle in `docs/02` direkt ein: Kommt dort ein Befehl hinzu oder ändert sich ein Status, schlägt ein Test fehl. Die Netzwerktests empfangen UDP- und TCP-SLIP-Pakete auf 127.0.0.1 und dekodieren sie mit `python-osc`. Sie laufen gegen einen einfachen lokalen Socket, nicht gegen `mock-console`, weil `zeros-osc` von keinem anderen Paket abhängen darf.

# mock-console

> **Stand:** Version 0.1.0. Lauscht per UDP, protokolliert und bewertet jede Nachricht nach der Referenz. TCP (SLIP) wird nicht nachgebildet.

Eine Attrappe des FLX S24 für Tests ohne Hardware.

## Was es tut

Das Programm lauscht per UDP, standardmäßig auf Port 8830, und verhält sich wie das Pult, soweit [docs/02-flx-osc-referenz.md](../../docs/02-flx-osc-referenz.md) es beschreibt. Es antwortet nie, wie das echte Pult.

Jede Nachricht wird bewertet:

| Ergebnis | Wann |
| --- | --- |
| akzeptiert | Adresse gehört zu einem Befehl der Referenz, in einer der vier gleichwertigen Schreibweisen oder in der Kurzform `/lx/q/go` |
| ignoriert, Grund `wildcard` | Adresse enthält `*`, `?`, `[`, `]`, `{` oder `}` |
| ignoriert, Grund `bundle_timetag` | Nachricht steckt in einem Bundle mit Zeitstempel; nur „sofort“ (Zeitwert 1) wird ausgeführt. Alle Nachrichten des Bundles werden verworfen, auch verschachtelte |
| ignoriert, Grund `unknown_address` | Adresse passt zu keinem Befehl der Referenz, Werte außerhalb der Bereiche oder Argumente ohne Zahl oder Text |
| ignoriert, Grund `invalid` | Datagramm ist kein gültiges OSC-Paket |

Für die Bewertung werden Argumente als Pfadsegmente angehängt. Alle vier Formen von „Cue 5 auf Playback 1“ ergeben `/zeros/cue/go/1/5`:

| Adresse | Argumente |
| --- | --- |
| `/zeros/cue/go/1/5` | keine |
| `/zeros/cue/go/1` | `"5"` |
| `/zeros/cue/go` | `"1"`, `"5"` |
| `/zeros/cue/go` | `"1/5"` |

Text- und Ganzzahl-Argumente gehen beide. Gleitkomma-Argumente werden auf sieben gültige Stellen gebracht, weil OSC sie mit 32 Bit überträgt: `5.0` zählt als `5`, ein Punkt-Cue `2.3` als `2.3`. Ein Level als Bruchteil zwischen 0.0 und 1.0 wird nicht umgerechnet und deshalb abgelehnt; diese Form steht in der Referenz nur als Vermutung. Die Adresse muss danach in der Schreibweise vorliegen, die `zeros-osc` sendet: `/zeros/cue/go/1/05` wird nicht akzeptiert.

Zu jeder akzeptierten Nachricht steht der Status des Befehls aus der Referenz dabei: belegt, Forum oder vermutet. Bei „vermutet“ steht im Log ausdrücklich, dass die Attrappe die Schreibweise nur annimmt, weil sie in der Referenz steht, und dass das echte Pult sie ablehnen kann. Die Liste der Befehle und ihr Status kommen aus `zeros-osc`; dieses Paket hat keine eigene Kopie.

## Start

Im Repo-Wurzelverzeichnis nach `uv sync --all-packages`:

```text
uv run mock-console                        lauscht auf 0.0.0.0:8830
uv run mock-console --port 9000            anderer Port
uv run mock-console --jsonl empfang.jsonl  zusätzlich in eine Datei schreiben
```

Beenden mit Strg+C. Beispiel mit `flxctl` in einem zweiten Terminal:

```text
$ uv run mock-console --host 127.0.0.1 --port 9123
mock-console lauscht auf 127.0.0.1:9123/udp

$ uv run flxctl --host 127.0.0.1 --port 9123 blackout 1
```

Die Attrappe schreibt dann eine Zeile pro Nachricht:

```text
2026-11-13 11:12:07.713 quelle=127.0.0.1:50102 kanal=- note=- name=- adresse=/zeros/blackout/1 argumente=[] akzeptiert befehl=blackout pfad=/zeros/blackout/1 status=vermutet HINWEIS: Schreibweise nur angenommen, weil sie in der Referenz steht (Status vermutet); das echte Pult kann sie ablehnen HINWEIS: blackout ist ungetestet (Status vermutet, Schreibweise nicht belegt)
2026-11-13 11:12:07.798 quelle=127.0.0.1:45487 kanal=- note=- name=- adresse=/zeros/cue/go/*/1 argumente=[] ignoriert grund=wildcard (Adresse /zeros/cue/go/*/1 enthält Wildcards)
```

`kanal`, `note` und `name` gehören zur MIDI-Seite und sind der Attrappe unbekannt; sie stehen nur für das einheitliche Log-Format da.

Mit `--jsonl` wird jede Nachricht zusätzlich als JSON-Zeile angehängt, mit den Feldern `time`, `sender`, `address`, `args`, `result` (`accepted` oder `ignored`), `reason`, `detail`, `command`, `status`, `path`, `values`, `notes` und `bundle_timetag`.

## Fixture für pytest

Ist das Paket installiert, steht die Fixture `mock_console` in jedem Test zur Verfügung, ohne Import. Sie startet die Attrappe auf `127.0.0.1` mit einem freien Port und hält sie nach dem Test an.

```python
from zeros_osc import Status, UdpClient, cue_go


def test_cue_kommt_an(mock_console):
    with UdpClient(mock_console.host, mock_console.port) as client:
        client.send(cue_go(1, 5))

    (nachricht,) = mock_console.wait_for(1)  # wartet höchstens 2 s
    assert nachricht.accepted
    assert nachricht.path == "/zeros/cue/go/1/5"
    assert nachricht.status is Status.BELEGT
```

Weitere Zugriffe: `mock_console.messages` (alle bisher empfangenen Nachrichten), `.accepted`, `.ignored`, `.clear()`. Jede Nachricht hat `reason` (`Reason.WILDCARD`, `Reason.BUNDLE_TIMETAG`, `Reason.UNKNOWN_ADDRESS`, `Reason.INVALID` oder `None`), `detail`, `command_id`, `status`, `notes`, `address`, `args` und `sender`.

Tests, die Argumentformen, Wildcards oder Bundles senden müssen, bauen die Datagramme mit `mock_console.testing.message(...)` und `mock_console.testing.bundle(...)`, denn `zeros-osc` baut nur die Pfadform.

## Grenzen

- Keine Simulation von Licht oder Cue-Zuständen.
- Nur UDP, kein TCP (SLIP).
- Bewertet wird nur nach [docs/02-flx-osc-referenz.md](../../docs/02-flx-osc-referenz.md). Was die Attrappe akzeptiert, muss das echte Pult nicht akzeptieren, vor allem bei Befehlen mit Status „vermutet“.

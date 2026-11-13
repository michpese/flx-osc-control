# zeros-osc

> **Stand:** geplant, noch kein Code. Bauauftrag: [`prompts/02-zeros-osc.md`](../../prompts/02-zeros-osc.md).

Bibliothek und Kommandozeile `flxctl`: ZerOS-Befehle bauen, prüfen und senden.

## Was es tut

Die Bibliothek kennt jeden Befehl aus [docs/02-flx-osc-referenz.md](../../docs/02-flx-osc-referenz.md) als Funktion, zum Beispiel `cue_go(playback=10, cue=2)`. Sie prüft die Zahlen, baut die Adresse und verschickt das Paket per UDP. `flxctl` ist dieselbe Funktion als Kommandozeile.

Dieses Paket ist das einzige im Repo, das Netzwerkpakete sendet. Alle anderen benutzen es.

## Geplante Befehle

```text
flxctl cue go 10 2                  Cue 2 auf Playback 10 starten
flxctl cue go 10 2 --dry-run        nur anzeigen, was gesendet würde
flxctl --host 192.168.1.10 cue go 10 2
flxctl map check shows/x/mapping.yaml
flxctl map doc shows/x/mapping.yaml
```

## Grenzen

- Nur Befehle, die in der Referenz stehen und nicht „offen" sind.
- Befehle mit Status „Forum" sind im Hilfetext als ungetestet markiert.
- Keine Abhängigkeit zu anderen Paketen dieses Repos.

## Fertig, wenn

- Unit-Tests jede Adresse gegen die Beispiele der Referenz prüfen
- ein Test das gesendete UDP-Paket auf 127.0.0.1 empfängt und dekodiert
- dieses README drei echte Anwendungsbeispiele zeigt

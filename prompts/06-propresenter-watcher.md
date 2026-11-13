# Prompt 6: propresenter-watcher (optional)

**Effort:** `high`

Vorher: In ProPresenter unter Settings → Network den Knopf „API Documentation" öffnen und die Beschreibung nach `integrations/propresenter/api/` exportieren.

```text
Baue das Paket propresenter-watcher. Lies CLAUDE.md und die
API-Beschreibung in integrations/propresenter/api/, die ich aus
ProPresenter exportiert habe.

Der Dienst hält eine Streaming-Verbindung zur ProPresenter-API offen,
bekommt jeden Folienwechsel als JSON-Zeile und sucht in den
Foliennotizen nach einem Kürzel der Form [lx:<note>]. Findet er eines,
löst er den Eintrag mit dieser Note aus mapping.yaml über zeros-osc aus.

Nutze nur Endpunkte, die in der exportierten API-Beschreibung stehen,
und nenne mir, welchen du für den Folienstatus gewählt hast und ob er
die Notizen enthält. Enthält er sie nicht, halte an und frage nach.
Verbindungsabbrüche: neu verbinden mit wachsender Wartezeit.

Fertig, wenn: Tests gegen einen kleinen nachgebauten API-Server zeigen,
dass ein Folienwechsel mit Kürzel genau eine Nachricht auslöst und ein
Verbindungsabbruch überstanden wird.
```

# 07 – Betrieb: Checkliste und Notfallplan

Eine Seite zum Ausdrucken für das Technikpult.

## Vor der Veranstaltung

- [ ] Netzwerkkabel stecken an Pult, Switch und Rechnern
- [ ] Pult ist an, das richtige Showfile ist geladen
- [ ] Der MIDI-Port „LX Bridge" ist vorhanden (Windows: loopMIDI läuft)
- [ ] Die Bridge läuft und zeigt den MIDI-Port und das geladene Mapping
- [ ] Test vom Laptop: `uv run flxctl --config shows/<ort>/mapping.yaml cue go 10 1` erscheint im Event Monitor
- [ ] Test-Folie in ProPresenter löst den richtigen Cue aus
- [ ] Test-Clip in Ableton löst den richtigen Cue aus
- [ ] Pro Song ist klar, ob Ableton oder ProPresenter das Licht führt

## Während der Veranstaltung

- Am Pult bleibt jemand, der eingreifen kann.
- Niemand ändert Cue-Nummern oder das Mapping.
- Das Bridge-Fenster bleibt sichtbar. Jede ausgelöste Note erscheint dort als Zeile.

## Notfallplan

**Das Licht reagiert nicht oder falsch:**

1. Am Pult von Hand weiterfahren. Fader und Tasten haben immer Vorrang.
2. Bridge beenden, damit keine weiteren Befehle kommen.
3. Nach der Veranstaltung das Bridge-Log sichern.

**Erst danach suchen:**

| Symptom | Wahrscheinliche Ursache | Prüfen |
| --- | --- | --- |
| Keine Zeile im Bridge-Log | Note kommt nicht an | MIDI-Port, Routing in ProPresenter oder Ableton, Kanal |
| Zeile im Log, nichts im Event Monitor | Paket kommt nicht an | Kabel, IP-Adresse, Port 8830, Firewall |
| Zeile im Event Monitor mit Fehler | Adresse passt nicht | Mapping gegen die Referenz prüfen |
| Falscher Cue | falsche Note oder umnummerierter Cue | Mapping und Showfile vergleichen |
| Cue löst doppelt aus | zwei Quellen senden | festlegen, wer das Licht führt |

## Nach der Veranstaltung

- [ ] Bridge-Log sichern, wenn etwas auffällig war
- [ ] Geändertes Showfile auf USB speichern und ins Repo legen
- [ ] Geändertes Mapping einchecken

## Wer bekommt was

| Rolle | Unterlage |
| --- | --- |
| Lichtbediener | Liste der ferngesteuerten Cues aus `flxctl map doc` |
| ProPresenter-Bediener | Makroliste aus `integrations/propresenter/` |
| Ableton-Bediener | Template-Set und Notentabelle aus `integrations/ableton/` |
| Alle | diese Seite |

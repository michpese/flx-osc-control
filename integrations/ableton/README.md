# integrations/ableton

Unterlagen für die Ableton-Seite. Einrichtung: [docs/05-setup-ableton.md](../../docs/05-setup-ableton.md).

## Was hier liegt

- diese Notentabelle
- das Template-Set `LX-Template.als`, sobald es in Ableton angelegt ist
- optional später das Max-for-Live-Device „LX Cue Send"

## Template-Set anlegen

1. Leeres Live-Set öffnen.
2. MIDI-Spur „LX" anlegen, ohne Instrument.
3. „MIDI To" auf „LX Bridge", Kanal 16.
4. Einen Beispiel-Clip mit je einer Note pro Stimmung anlegen.
5. Als `LX-Template.als` in diesen Ordner speichern.

## Notentabelle

Notennummer und Stimmung müssen zu `mapping.yaml` passen.

| Note | Stimmung | Anzeige in Ableton |
| --- | --- | --- |
| 1 | Einlass | C#-2 |
| 2 | Musik ruhig | D-2 |
| 3 | Musik kräftig | D#-2 |
| 4 | Rede | E-2 |

Ableton zeigt Note 0 als C-2 an. Maßgeblich ist immer die Nummer.

## Regeln für Bediener

- Lichtnoten liegen nur auf der Spur „LX".
- An jedem Song-Anfang und an jeder Sprungmarke steht eine Note für die dort gültige Stimmung.
- Pro Song ist festgelegt, ob Ableton oder ProPresenter das Licht führt.

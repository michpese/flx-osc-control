# integrations/propresenter

Unterlagen für die ProPresenter-Seite. Einrichtung: [docs/04-setup-propresenter.md](../../docs/04-setup-propresenter.md).

## Was hier liegt

- diese Makroliste
- Screenshots der Geräte-Einstellungen, sobald eingerichtet
- `api/` mit der exportierten API-Beschreibung, falls der optionale `propresenter-watcher` gebaut wird

## Makroliste

Pro Lichtstimmung ein Makro mit einer Aktion „MIDI Note On". Name und Note müssen zu `mapping.yaml` passen.

| Makro | MIDI-Kanal | Note | Velocity | Stimmung im Mapping |
| --- | --- | --- | --- | --- |
| LX – Einlass | 15 | 1 | 127 | Einlass |
| LX – Musik ruhig | 15 | 2 | 127 | Musik ruhig |
| LX – Musik kräftig | 15 | 3 | 127 | Musik kräftig |
| LX – Rede | 15 | 4 | 127 | Rede |

## Geräte-Einstellungen

| Einstellung | Wert |
| --- | --- |
| Gerät | MIDI |
| Destinations | LX Bridge |
| Sources | leer |
| Auto Reconnect | ein |

## Regeln für Bediener

- Licht-Makros heißen immer `LX – <Stimmung>`.
- Ein Makro wird auf die Folie gezogen, auf der die Stimmung beginnen soll.
- Neue Stimmungen entstehen zuerst am Pult und im Mapping, dann als Makro.

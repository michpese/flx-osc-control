# 04 – Einrichtung ProPresenter

ProPresenter kann kein OSC senden. Der zuverlässige Weg ist eine MIDI-Note als Aktion auf Folie oder Makro, die die Bridge in OSC übersetzt.

Die Geräteliste von ProPresenter nennt DMX, MIDI, AMP, CITP, GlobalCache, GVG100, RossTalk, Sony BVS, Sony BVW und VDCP. OSC fehlt, und unter Windows gibt es nur MIDI.

## Drei Wege

| Weg | Ablauf | Geeignet, wenn |
| --- | --- | --- |
| **A: MIDI-Aktion** (Empfehlung) | Folie oder Makro → MIDI Note On → Port „LX Bridge" → Bridge → OSC | Standardfall, läuft auf Mac und Windows |
| B: Bitfocus Companion | Companion liest ProPresenter über dessen API-Modul und sendet über das Modul „Generic OSC" | ihr Companion oder ein Stream Deck ohnehin nutzt |
| C: API-Watcher | Ein eigener Dienst liest die ProPresenter-API mit und sendet OSC anhand eines Kürzels in den Foliennotizen | spätere Ausbaustufe ohne MIDI-Aktionen |

## Weg A einrichten

Voraussetzung: Der virtuelle MIDI-Port „LX Bridge" existiert, siehe [03-setup-flx.md](03-setup-flx.md).

1. **MIDI-Gerät hinzufügen.** ProPresenter → Settings → Devices → „+" → MIDI.
2. **Auto Reconnect** einschalten.
3. **Destinations:** „LX Bridge" auswählen.
4. **Sources leer lassen.** ProPresenter hört beim Empfang auf allen Kanälen. Liegt derselbe Port auch als Quelle an, lösen die Noten aus Ableton Befehle der MIDI Map in ProPresenter aus.
5. **Connect** klicken.
6. **Makros anlegen.** Pro Lichtstimmung ein Makro, zum Beispiel „LX – Musik ruhig". Rechtsklick auf das Makro → Add Action → Communication → MIDI → MIDI Note On.
7. **Werte eintragen:** Kanal 15, Note laut Mapping, Velocity 127.
8. **Makro auf die Folie legen.** So steht die Notennummer nur an einer Stelle.
9. **Testen.** Folie anklicken und im Bridge-Log die Zeile mit Kanal, Note und gesendeter OSC-Adresse prüfen.

Direkt auf der Folie geht es auch: Rechtsklick auf die Folie → Add Action → Communication → MIDI → MIDI Note On.

## Namensregel für Makros

`LX – <Name der Stimmung>`, mit demselben Namen wie in `mapping.yaml`. Die Liste der Makros pflegst du in [`integrations/propresenter/README.md`](../integrations/propresenter/README.md).

## Stolperfallen

- **Notennamen.** Programme zählen Oktaven verschieden. Rechne immer mit der Notennummer 0–127, nie mit dem Namen.
- **Kein Note Off nötig.** Die Bridge reagiert nur auf Note On.
- **Wiederholtes Anklicken.** Jeder Klick auf die Folie sendet erneut. Die Bridge unterdrückt Wiederholungen innerhalb von `debounce_ms`.
- **Doppeltes Auslösen.** Steuert Ableton die Folien und tragen diese Folien Licht-Makros, löst derselbe Moment zweimal aus. Siehe [05-setup-ableton.md](05-setup-ableton.md).

## Weg B und C: Netzwerkzugriff einschalten

1. Settings → Network → „Enable Network" einschalten.
2. Den angezeigten Port notieren.
3. Die Beschreibung aller Endpunkte öffnet der Knopf „API Documentation" unten im Network-Tab.
4. Für Weg C: Anfragen mit `"chunked": true` liefern laufende Aktualisierungen, eine JSON-Zeile pro Änderung. Welche Status-Endpunkte das unterstützen, steht in der API-Dokumentation.

## Kontrolle

- [ ] MIDI-Gerät ist verbunden, „LX Bridge" steht unter Destinations
- [ ] Sources ist leer
- [ ] Für jede Stimmung im Mapping gibt es ein Makro
- [ ] Eine Test-Folie löst genau eine Zeile im Bridge-Log aus

## Quellen

- [Renewed Vision: Communication Devices in ProPresenter](https://support.renewedvision.com/hc/en-us/articles/360058141114-Communication-Devices-in-ProPresenter)
- [Renewed Vision: Devices: MIDI: ProPresenter Setup](https://support.renewedvision.com/hc/en-us/articles/1500000020301)
- [Renewed Vision: TCP/IP Connections with ProPresenter API](https://support.renewedvision.com/hc/en-us/articles/31606866768147-TCP-IP-Connections-with-ProPresenter-API)

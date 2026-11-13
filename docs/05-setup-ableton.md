# 05 – Einrichtung Ableton Live

Ableton sendet OSC nur über Max for Live. Einfacher und in jeder Live-Edition möglich ist eine MIDI-Spur, deren Noten über den Port „LX Bridge" an die Bridge gehen.

## Drei Wege

| Weg | Ablauf | Voraussetzung |
| --- | --- | --- |
| **A: MIDI-Spur → Bridge** (Empfehlung) | Note im Clip → Port „LX Bridge" → Bridge → OSC | keine Zusatzlizenz |
| B: Eigenes Max-for-Live-Device | Note im Clip → Device schlägt die Adresse nach → `udpsend` direkt ans Pult | Live Suite oder Standard mit Max for Live |
| C: Fertige Devices | zum Beispiel „OSC Message Sender" von Live Theatre Works | Max for Live, kleines Entgelt |

Das Connection Kit von Ableton passt nicht gut: Sein „OSC Send" wandelt Live-Parameter in OSC-Werte um, während ZerOS feste Befehle mit Nummern im Adresspfad erwartet. Ableton führt das Pack außerdem als eingestellt.

## Weg A einrichten

Voraussetzung: Der virtuelle MIDI-Port „LX Bridge" existiert, siehe [03-setup-flx.md](03-setup-flx.md).

1. **MIDI-Ausgang freigeben.** Settings → Link, Tempo & MIDI. Beim Ausgang „LX Bridge" den Schalter „Track" einschalten, „Sync" und „Remote" aus lassen.
2. **Spur anlegen.** Neue MIDI-Spur mit dem Namen „LX", ohne Instrument.
3. **Routing:** „MIDI To" auf „LX Bridge", Kanal 16.
4. **Noten setzen.** Pro Lichtwechsel eine kurze Note an der Stelle im Song. Die Notennummer kommt aus `mapping.yaml`.
5. **Vorlauf einstellen.** Soll eine Überblendung auf dem Schlag fertig sein, setze die Note um die Fade-Zeit früher. Ein negatives Track Delay verschiebt alle Noten der Spur gemeinsam.
6. **Als Vorlage speichern.** Die leere Spur mit Routing kommt als Template-Set nach [`integrations/ableton/`](../integrations/ableton/README.md).

## Arrangement oder Session

- **Arrangement:** Die Noten liegen auf der Zeitachse des Songs. Passend, wenn der Song fest durchläuft.
- **Session:** Jede Szene bekommt einen Clip mit der Note am Anfang. Passend, wenn Songteile frei abgerufen werden.

## Stolperfallen

- **Eine Quelle pro Lichtwechsel.** Steuert Ableton bereits die Folien in ProPresenter und tragen diese Folien Licht-Makros, löst derselbe Moment zweimal aus. Lege pro Song fest, ob Ableton oder ProPresenter das Licht führt.
- **Zwei Rechner.** Ableton läuft auf einem Mac, ProPresenter auf einem Windows-PC. Die Bridge startet auf beiden Rechnern mit derselben `mapping.yaml`. UDP erlaubt mehrere Absender.
- **Stopp und Sprung.** Springt jemand im Song, fehlen die übersprungenen Noten. Setze an jeden Song-Anfang und jede Sprungmarke eine Note für die dort gültige Stimmung.
- **Notennamen.** Rechne mit der Notennummer 0–127. Die Anzeige als Notenname unterscheidet sich zwischen Programmen um eine Oktave.
- **Schleifen.** Ein geloopter Clip sendet seine Note bei jedem Durchlauf. Die Sperrzeit `debounce_ms` hilft nur bei kurzen Abständen.

## Kontrolle

- [ ] „Track" ist beim Ausgang „LX Bridge" eingeschaltet
- [ ] Die Spur „LX" sendet auf Kanal 16 an „LX Bridge"
- [ ] Eine Test-Note löst genau eine Zeile im Bridge-Log aus
- [ ] Pro Song ist festgelegt, wer das Licht führt

## Quellen

- [Ableton: Connection Kit](https://www.ableton.com/en/packs/connection-kit/)
- [Live Theatre Works: OSC Message Sender](https://livetheatreworks.gumroad.com/l/ltw-oms)

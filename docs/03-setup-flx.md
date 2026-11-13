# 03 – Einrichtung FLX S24 und Netzwerk

Vor dem ersten Trigger brauchst du drei Dinge: ein sauberes Netz, das eingeschaltete OSC am Pult und feste Cue-Nummern im Showfile.

## Netzwerk

1. Stelle einen eigenen Switch nur für Licht und Zuspieler auf. ZerOS-Pulte sind für ein eigenständiges lokales Netz gedacht, ohne Internet.
2. Verbinde Pult und Rechner per Kabel. Kein WLAN im Signalweg.
3. Vergib feste Adressen nach dem Plan unten.
4. Erlaube in der Firewall der Rechner ausgehendes UDP auf Port 8830.
5. Prüfe die Verbindung mit `ping 192.168.1.10` vom Rechner zum Pult.

| Gerät | IP-Adresse (Vorschlag) | Subnetz |
| --- | --- | --- |
| FLX S24 | 192.168.1.10 | 255.255.255.0 |
| ProPresenter-Rechner (Windows) | 192.168.1.20 | 255.255.255.0 |
| Ableton-Rechner (Mac) | 192.168.1.21 | 255.255.255.0 |

Der Plan ist ein Vorschlag. Prüfe die tatsächliche Adresse des Pults in Setup und trage die echten Werte hier ein.

## Pult

1. **Softwarestand prüfen:** Z → System Information. Nötig ist ZerOS 7.14 oder neuer.
2. **Bei älterem Stand:** zuerst das Showfile auf USB sichern, dann ZerOS per USB-Stick aktualisieren.
3. **OSC einschalten:** Setup → Triggers → OSC.
4. **Port:** „Receive Port Number" auf 8830 lassen.
5. **Transport:** UDP.
6. **IP-Adresse:** statisch, passend zum Adressplan.
7. **Event Monitor öffnen.** Dort erscheinen eingehende Befehle, auch fehlerhafte.

Eingetragene Werte dieses Pults:

| Einstellung | Wert |
| --- | --- |
| ZerOS-Version | |
| IP-Adresse für OSC | |
| Port | |
| Transport | |
| Geprüft am | |

## Showfile

- **Ein Steuer-Playback.** Lege die ferngesteuerten Stimmungen als Cues auf ein eigenes Playback, zum Beispiel Playback 10.
- **Nummern sind ein Vertrag.** Cue-Nummern werden nie umnummeriert. Neue Stimmungen kommen hinten dran. Nutze ganze Zahlen.
- **Zeiten gehören in den Cue.** Die Überblendzeit steht im Cue, nicht im Trigger.
- **Mehr als ein Playback.** Soll ein Cue ein Lauflicht starten oder beenden, nutze die Cue-Einstellung „Macros…". Damit triggert oder released ein Cue ein anderes Playback.
- **Sichern.** Showfile nach jeder Änderung auf USB speichern und unter `shows/<ort-oder-anlass>/` ins Repo legen.

Beispiel für ein Steuer-Playback:

| Playback | Cue | Stimmung | OSC-Adresse |
| --- | --- | --- | --- |
| 10 | 1 | Einlass | `/zeros/cue/go/10/1` |
| 10 | 2 | Musik ruhig | `/zeros/cue/go/10/2` |
| 10 | 3 | Musik kräftig | `/zeros/cue/go/10/3` |
| 10 | 4 | Rede | `/zeros/cue/go/10/4` |

## Virtueller MIDI-Port auf den Rechnern

Der Port heißt auf jedem Rechner „LX Bridge". Das System zeigt ihn aber unterschiedlich an: unter Windows etwa als `LX Bridge 1`, am Mac etwa als `IAC-Treiber LX Bridge`. Welcher Name gilt, zeigt `uv run midi-bridge --list-ports`. Am Mac gehört dieser angezeigte Name in die `mapping.yaml`; Einzelheiten stehen im [README der midi-bridge](../packages/midi-bridge/README.md).

**macOS** (Ableton-Rechner)

1. Programm „Audio-MIDI-Setup" öffnen.
2. Fenster → MIDI-Studio einblenden.
3. Doppelklick auf „IAC-Treiber".
4. „Gerät ist online" aktivieren.
5. Einen Port mit dem Namen „LX Bridge" anlegen.

**Windows** (ProPresenter-Rechner)

1. loopMIDI installieren.
2. Einen Port mit dem Namen „LX Bridge" anlegen.
3. loopMIDI in den Autostart legen.

## Kontrolle

- [ ] `ping` zum Pult antwortet
- [ ] OSC ist eingeschaltet, Port und Transport sind notiert
- [ ] Ein Test-Cue liegt auf dem Steuer-Playback
- [ ] Der Port „LX Bridge" existiert auf jedem Zuspielrechner
- [ ] Das Showfile ist gesichert

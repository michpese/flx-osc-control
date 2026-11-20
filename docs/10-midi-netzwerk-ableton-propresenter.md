# 10 – Ableton (Mac) als Haupt-PC: Licht per OSC und ProPresenter (Windows) per Netzwerk-MIDI

Diese Anleitung beschreibt Schritt für Schritt das Setup, in dem der **Mac mit Ableton Live der Haupt-PC** ist:

1. **Lokal auf dem Mac → Licht (FLX S48):** Ableton sendet MIDI-Noten an sich selbst über den eingebauten **IAC-Treiber** (`LX Bridge`). Die auf demselben Mac laufende `midi-bridge` übersetzt diese Noten direkt in **OSC** (UDP Port `8830`) und schickt sie ans Lichtpult.
2. **Mac → Netzwerk → ProPresenter (Windows):** Ableton sendet über eine zweite MIDI-Spur MIDI-Noten über das **eingebaute macOS Netzwerk-MIDI (RTP-MIDI)** ins LAN. Auf dem Windows-PC empfängt **`rtpMIDI`** diese Signale und reicht sie direkt an **ProPresenter** weiter.

## Signalfluss im Überblick

```text
┌────────────────────────────────────────────────────────────────────┐
│  Mac (Haupt-PC, z. B. 192.168.1.21)                                │
│                                                                    │
│  Ableton Live                                                      │
│   ├── Spur „LX" (Kanal 16)                                         │
│   │     └─► IAC-Treiber „LX Bridge" (lokal)                        │
│   │           └─► midi-bridge ──► OSC (UDP 8830) ──► FLX S48       │
│   │                                                 (192.168.1.10) │
│   └── Spur „ProPresenter" (z. B. Kanal 1)                          │
│         └─► macOS Netzwerk-MIDI / RTP-MIDI (UDP 5004/5005)         │
└─────────────────────────┼──────────────────────────────────────────┘
                          │ Ethernet-Kabel über Switch
                          ▼
┌────────────────────────────────────────────────────────────────────┐
│  Windows-PC (ProPresenter, z. B. 192.168.1.20)                     │
│                                                                    │
│  rtpMIDI (Tobias Erichsen) ──► ProPresenter (MIDI-Device: Sources) │
└────────────────────────────────────────────────────────────────────┘
```

**Warum zwei getrennte MIDI-Wege am Mac?**

- Licht-Noten bleiben lokal auf dem Mac (`IAC-Treiber` → `midi-bridge` → OSC) und gelangen nie versehentlich in ProPresenter.
- ProPresenter-Noten gehen gezielt über das Netzwerk (`RTP-MIDI`) an den Windows-PC und lösen nie versehentlich die `midi-bridge` aus.
- Es können keine MIDI-Schleifen zwischen beiden Programmen entstehen.
- Solange der Mac das komplette Licht steuert, brauchst du auf dem Windows-PC **weder `loopMIDI` noch `midi-bridge`**. *(Für den Mischbetrieb, falls ProPresenter zusätzlich eigene Licht-Makros auslösen soll, siehe [Optionaler Mischbetrieb](#optionaler-mischbetrieb-propresenter-steuert-zusätzlich-licht).)*

---

## Voraussetzungen und Netzwerk-Check

1. **Kabelgebundenes Netz:** Mac, Windows-PC und FLX S48 hängen per **Netzwerkkabel** am selben Switch im selben Subnetz (kein WLAN im Signalweg, siehe [03-setup-flx.md](03-setup-flx.md)).
2. **Feste IP-Adressen:** Alle drei Geräte haben statische IPs im selben Subnetz (Vorschlag aus [03-setup-flx.md](03-setup-flx.md)):

| Gerät | IP-Adresse (Beispiel) | Subnetzmaske |
| --- | --- | --- |
| FLX S48 | `192.168.1.10` | `255.255.255.0` |
| ProPresenter-PC (Windows) | `192.168.1.20` | `255.255.255.0` |
| Ableton-Mac (Haupt-PC) | `192.168.1.21` | `255.255.255.0` |

3. **Erreichbarkeit kurz prüfen:**
   - Am Mac im Terminal: `ping -c 3 192.168.1.10` (Pult) und `ping -c 3 192.168.1.20` (Windows-PC).
   - Am Windows-PC in der PowerShell: `ping 192.168.1.21` (Mac).
   - *Hinweis:* Antwortet Windows nicht auf `ping`, blockiert oft nur die Windows-Firewall ICMP. Entscheidend für die Funktion sind die UDP-Ports unten.

4. **Benötigte Netzwerk-Ports im Überblick:**

| Richtung | Protokoll & Ports | Zweck |
| --- | --- | --- |
| Mac → FLX S48 | **UDP `8830`** | OSC-Befehle aus der `midi-bridge` ans Lichtpult |
| Mac ↔ Windows | **UDP `5004` und `5005`** | RTP-MIDI Session 1 (Steuer- und Datenport; jede RTP-MIDI-Session belegt immer ein aufeinanderfolgendes Port-Paar) |
| LAN (optional) | **UDP `5353`** | Bonjour / mDNS zur automatischen Anzeige der Sessions im lokalen Netz |

---

## Schritt 1 (Mac): MIDI im Netzwerk verfügbar machen (Audio-MIDI-Setup)

macOS bringt den Netzwerk-MIDI-Treiber (**RTP-MIDI**, Standard RFC 6295) von Haus aus mit – es ist keine Zusatzsoftware auf dem Mac nötig.

1. **Audio-MIDI-Setup öffnen:** Spotlight (`⌘ + Leertaste`) → `Audio-MIDI-Setup` eingeben und starten (liegt in `Programme → Dienstprogramme`).
2. **MIDI-Studio einblenden:** In der Menüleiste **Fenster → MIDI-Studio einblenden** (`⌘ + 2`).
3. **MIDI-Netzwerk-Konfiguration öffnen:**
   - In der Symbolleiste des MIDI-Studio-Fensters auf das **Globus-Symbol („Netzwerk-Treiber konfigurieren" / *Configure Network Driver*)** klicken.
   - *(Bei älteren macOS-Versionen: Doppelklick auf das Symbol **„Netzwerk"** im MIDI-Studio.)*
4. **Neue Session anlegen:**
   - Links oben unter **„Meine Sessions"** (*My Sessions*) auf **`+`** klicken.
   - **Wichtig ab macOS 15 (Sequoia) und neuer:** Fragt macOS nach dem Session-Typ (**RTP** vs. **Network MIDI 2.0**), unbedingt **RTP** wählen. `rtpMIDI` unter Windows unterstützt das klassische RTP-MIDI-Protokoll, nicht Network MIDI 2.0.
5. **Session benennen und aktivieren:**
   - Die neue Session markieren und aktivieren (Häkchen links neben dem Namen bzw. rechts **„Aktiviert"** / *Enabled* einschalten).
   - **Lokaler Name** (*Local Name*): `ProPresenter-Netz` eintragen. *(Unter diesem Namen erscheint der Ausgang gleich in Ableton Live.)*
   - **Bonjour-Name** bzw. **Netzwerkname** (*Bonjour Name* / *Network Name*): `Ableton-Mac` eintragen. *(Unter diesem Namen sieht der Windows-PC den Mac im Netz.)*
   - **Port:** `5004` stehen lassen. *(macOS belegt damit automatisch UDP `5004` und `5005`.)*
6. **Verbindungsrichtlinie setzen:**
   - Unten links bei **„Wer darf sich mit mir verbinden"** (*Who may connect to me*) auf **„Jeder"** (*Anyone*) stellen.
   - *(Im isolierten Show-Netz ohne Internet unkritisch; alternativ nach dem ersten Verbinden auf „Nur Computer in meinem Verzeichnis" einschränken.)*
7. **Live-Routings leer lassen:**
   - Rechts unten im Bereich **„Live-Routings"** beide Auswahlfelder leer lassen (keinen IAC-Port und kein Hardware-Interface hier verknüpfen).
   - *Grund:* Ableton sendet direkt an die Netzwerk-Session. Ein Live-Routing zum IAC-Treiber würde Licht-Noten an ProPresenter weiterleiten oder MIDI-Schleifen erzeugen.
8. **macOS-Firewall prüfen:**
   - Unter **Systemeinstellungen → Netzwerk → Firewall** prüfen: Ist die Firewall aktiv, darf *„Alle eingehenden Verbindungen blockieren"* **nicht** eingeschaltet sein.

---

## Schritt 2 (Windows): Netzwerk-MIDI empfangen mit `rtpMIDI`

Windows hat keinen eingebauten RTP-MIDI-Treiber. Das kostenlose Gegenstück zu Apples Netzwerk-MIDI ist **rtpMIDI** von Tobias Erichsen (derselbe Entwickler wie bei `loopMIDI`). Es läuft als Windows-Dienst im Hintergrund und startet künftig automatisch mit Windows.

1. **Apple Bonjour prüfen / installieren:**
   - `rtpMIDI` verwendet Apples **Bonjour** (*Zero-Config*), damit Mac und Windows sich automatisch im LAN sehen.
   - Ist Bonjour noch nicht auf dem Windows-PC installiert, weist der `rtpMIDI`-Installer darauf hin. Installiere dann vorab **Bonjour Print Services for Windows** und führe den `rtpMIDI`-Installer danach aus.
2. **`rtpMIDI` installieren:**
   - Von [tobias-erichsen.de/software/rtpmidi](https://www.tobias-erichsen.de/software/rtpmidi.html) herunterladen und installieren.
3. **Empfangs-Session unter Windows anlegen:**
   - **rtpMIDI** über das Startmenü öffnen.
   - Links unter **„My Sessions"** auf **`+`** klicken.
   - Rechts unter **„Local name"** z. B. `Ableton-Netz` eintragen. *(Unter diesem Namen erscheint der MIDI-Eingang gleich in ProPresenter.)*
   - **Port:** `5004` stehen lassen.
   - Das Häkchen bei **„Enabled"** setzen (sowie links das Häkchen neben der Session).
   - Unten links bei **„Who may connect to me"** auf **„Anyone"** stellen.
4. **Windows mit dem Mac verbinden:**
   - **Variante A – Automatisch über Bonjour (Standard):**
     1. Unten links im Feld **„Directory"** erscheint nach wenigen Sekunden der Mac (`Ableton-Mac`).
     2. Den Eintrag markieren und auf **„Connect"** klicken.
     3. Rechts unter **„Participants"** erscheint der Mac samt Latenzanzeige (im Kabelnetz typischerweise `0–2 ms`). Gleichzeitig zeigt der Mac im Audio-MIDI-Setup den Windows-PC unter **„Teilnehmer"** an.
   - **Variante B – Manuell über feste IP (wenn Bonjour im Netz nicht sichtbar ist):**
     1. Unten links unter **„Directory"** auf **`+`** klicken.
     2. **Name:** `Ableton-Mac`, **Address:** `192.168.1.21` (IP des Macs), **Port:** `5004` → **OK**.
     3. Den neu angelegten Eintrag markieren und auf **„Connect"** klicken.
   - *Praxis-Tipp zum automatischen Wiederverbinden:* Wird die Verbindung von Windows (`rtpMIDI`) aus hergestellt, versucht `rtpMIDI` nach jedem Windows-Neustart automatisch, sich wieder mit dem Mac zu verbinden – solange die Session am Mac aktiviert ist. Lass daher immer eine feste Seite (am besten Windows `rtpMIDI`) die Verbindung initiieren und klicke nicht auf beiden Rechnern gleichzeitig auf *Connect*.
   - Das Konfigurationsfenster von `rtpMIDI` kannst du danach schließen – der Windows-Dienst hält die Verbindung im Hintergrund aktiv.
5. **Windows-Firewall freigeben:**
   - In einem isolierten Show-Netz ohne Internet stuft Windows das LAN oft als **„Öffentliches Netzwerk"** ein und blockiert eingehendes UDP.
   - Stelle das Netzwerkprofil in Windows unter **Einstellungen → Netzwerk und Internet → Ethernet** auf **Privates Netzwerk** um, oder lege in der Windows Defender Firewall eine Regel an, die **UDP `5004` und `5005`** (sowie optional `5353` für Bonjour) eingehend und ausgehend zulässt.

---

## Schritt 3 (Mac): Lokalen MIDI→OSC-Weg für das Licht einrichten

Auf demselben Mac wandelt `midi-bridge` die Licht-Noten aus Ableton lokal in OSC um. (Ausführliche Details zur Bridge stehen im [README der midi-bridge](../packages/midi-bridge/README.md).)

1. **IAC-Port anlegen:**
   - Im **Audio-MIDI-Setup → MIDI-Studio** Doppelklick auf **„IAC-Treiber"**.
   - **„Gerät ist online"** aktivieren.
   - Mit **`+`** einen Port namens **`LX Bridge`** anlegen → **Anwenden**.
2. **Exakten Portnamen ablesen:**
   - Im Terminal im Ordner `flx-osc-control`:
     ```bash
     uv run midi-bridge --list-ports
     ```
   - Merke dir die Zeile des IAC-Ports, z. B. `IAC-Treiber LX Bridge` (deutsches macOS) oder `IAC Driver LX Bridge` (englisches macOS).
   - *Wichtig:* Der Netzwerk-Port (`Netzwerk ProPresenter-Netz`) taucht dort eventuell ebenfalls auf – trage ihn **nicht** in der `mapping.yaml` ein.
3. **`mapping.yaml` anpassen:**
   - Kopiere `shows/mapping.example.yaml` nach `shows/<ort>/mapping.yaml` und speichere sie als **UTF-8**.
   - Trage die IP des FLX S48 und den exakten IAC-Portnamen ein:
     ```yaml
     console:
       host: 192.168.1.10
       port: 8830
       transport: udp

     sources:
       ableton:
         midi_port: "IAC-Treiber LX Bridge"   # exakter Name aus --list-ports
         channel: 16
     ```
   - *(Hinweis: Bleibt ein `propresenter`-Block aus einer gemeinsamen `mapping.yaml` stehen, meldet die Bridge beim Start einmalig, dass der Windows-Port fehlt, und ignoriert ihn – das ist harmlos.)*
4. **Mapping prüfen und Bridge starten:**
   ```bash
   uv run flxctl map check shows/<ort>/mapping.yaml
   ```
   Zuerst im Trockenlauf testen:
   ```bash
   uv run midi-bridge --mapping shows/<ort>/mapping.yaml --dry-run
   ```
   Für den echten Betrieb am Pult danach denselben Befehl **ohne `--dry-run`** starten.

---

## Schritt 4 (Mac): Ableton Live mit zwei MIDI-Spuren konfigurieren

1. **MIDI-Ausgänge aktivieren:**
   - In Ableton Live: **Settings → Link, Tempo & MIDI** öffnen.
   - Unter **MIDI Ports** für die beiden **Ausgänge (Output)** jeweils nur **Track** einschalten:

| MIDI-Port (Output) | Track | Sync | Remote | Wofür |
| --- | --- | --- | --- | --- |
| `IAC-Treiber (LX Bridge)` | **EIN** | aus | aus | Lokal an `midi-bridge` → OSC → FLX S48 |
| `Netzwerk (ProPresenter-Netz)` *(bzw. `Network (ProPresenter-Netz)`)* | **EIN** | aus | aus | Über RTP-MIDI an Windows ProPresenter |

   - Alle **Input**-Schalter (Track, Sync, Remote) für beide Ports **aus** lassen, damit keine MIDI-Schleifen entstehen.

2. **Spur 1 – Licht (`LX`):**
   - Neue MIDI-Spur anlegen, ohne Instrument, Name: **`LX`**.
   - **MIDI From:** `No Input`.
   - **MIDI To:** `IAC-Treiber (LX Bridge)`, **Kanal `16`**.
   - Noten entsprechend `mapping.yaml` an die gewünschten Stellen im Song setzen (siehe [05-setup-ableton.md](05-setup-ableton.md)).

3. **Spur 2 – ProPresenter (`ProPresenter`):**
   - Neue MIDI-Spur anlegen, ohne Instrument, Name: **`ProPresenter`**.
   - **MIDI From:** `No Input`.
   - **MIDI To:** `Netzwerk (ProPresenter-Netz)`, **Kanal `1`**.
   - *(Ein eigener Kanal getrennt von Kanal 15/16 hält das Setup übersichtlich. ProPresenter hört beim Empfang standardmäßig auf allen Kanälen.)*
   - Noten entsprechend der **MIDI Map** in ProPresenter (Schritt 5) auf diese Spur legen.

> **Wichtig zur Noten-Zählweise:** Ableton zeigt MIDI-Note `0` als `C-2` an, andere Programme als `C-1` oder `C0`. Rechne deshalb sowohl für das Licht-Mapping als auch für ProPresenter immer mit der **Notennummer `0–127`**.

---

## Schritt 5 (Windows): ProPresenter für den MIDI-Empfang einrichten

1. **MIDI-Gerät hinzufügen:**
   - ProPresenter öffnen → **Settings → Devices → `+` → MIDI**.
   - Namen vergeben, z. B. `Ableton-Netz`.
   - **Auto Reconnect:** **EIN**.
   - **Sources:** die Windows-`rtpMIDI`-Session auswählen (`Ableton-Netz`).
   - **Destinations:** **leer lassen** *(außer im Mischbetrieb – siehe unten)*.
   - Auf **Connect** klicken – der Status muss auf **Connected** wechseln.
   - *Hinweis:* Taucht die `rtpMIDI`-Session nicht unter *Sources* auf, ProPresenter einmal komplett schließen und neu starten (nachdem die Session in `rtpMIDI` aktiviert wurde).

2. **MIDI Map prüfen (Zuordnung Note → ProPresenter-Aktion):**
   - Unter **Settings → Devices → MIDI → MIDI Map** ablesen oder festlegen, welche MIDI-Note welche Funktion auslöst (z. B. *Next Slide*, *Previous Slide*, *Select Playlist*, *Select Playlist Item*, *Trigger Slide*, *Clear All*, *Trigger Macro*).
   - Bei Befehlen mit Auswahl (z. B. *Select Playlist*, *Select Playlist Item*, *Trigger Slide*) wählt die **Notennummer** den Befehl und die **Velocity (`1–127`)** den Index (z. B. Velocity `1` = Folie 1, Velocity `2` = Folie 2).
   - Mit **Auto Fill** (Startnote z. B. `0`) belegt ProPresenter alle Funktionen fortlaufend ab Note `0`. Wenn du ein fertiges ProPresenter-MIDI-Cue-Template für Ableton verwendest, prüfe, dass die Startnote in der MIDI Map exakt zum Template passt.
   - **Versatz bei Befehlsfolgen:** Sollen nacheinander *Select Playlist*, *Select Playlist Item* und *Trigger Slide* ausgelöst werden, platziere die Noten in Ableton leicht versetzt (z. B. ein Sechzehntel oder wenige Millisekunden Abstand), nicht exakt auf denselben Zeitpunkt.

---

## Schritt 6: Beide Signalwege testen

Prüfe zuerst jeden Weg einzeln und anschließend die Trennung:

1. **Netzwerk-MIDI (Mac → Windows ProPresenter):**
   - In Windows `rtpMIDI` prüfen: Der Mac steht unter **Participants** (Latenz `0–2 ms`).
   - In ProPresenter prüfen: MIDI-Gerät zeigt **Connected**.
   - In Ableton eine einzelne Note auf der Spur **`ProPresenter`** abspielen (z. B. die Note für *Next Slide*).
   - **Erwartet:** ProPresenter schaltet sofort eine Folie weiter.

2. **Lokal MIDI → OSC (Mac → FLX S48):**
   - `midi-bridge` zunächst mit `--dry-run` laufen lassen.
   - In Ableton eine Note auf der Spur **`LX`** abspielen (z. B. Note `1` auf Kanal 16).
   - **Erwartet:** Im Bridge-Fenster erscheint genau eine Zeile:
     `… quelle=ableton kanal=16 note=1 name="Einlass" adresse=/zeros/cue/go/10/1 … DRY-RUN nicht gesendet`.
   - Danach `midi-bridge` **ohne `--dry-run`** starten, Note erneut abspielen → im **Event Monitor** am FLX S48 erscheint der OSC-Befehl und der Cue startet.

3. **Saubere Trennung prüfen:**
   - Eine Note auf der Spur **`LX`** darf **keine** Aktion in ProPresenter auslösen.
   - Eine Note auf der Spur **`ProPresenter`** darf **keine** Zeile im Log der `midi-bridge` erzeugen.

---

## Optionaler Mischbetrieb: ProPresenter steuert zusätzlich Licht

Wenn Ableton nur bei Songs läuft, aber z. B. bei Einlass, Moderation oder Predigt weiterhin Folien-Makros in ProPresenter das Licht umschalten sollen:

- **Empfohlene Lösung:** Richte auf dem Windows-PC zusätzlich den lokalen Weg aus [04-setup-propresenter.md](04-setup-propresenter.md) ein (`loopMIDI` mit Port `LX Bridge` + zweite `midi-bridge`-Instanz mit Kanal 15 auf Windows).
  - In ProPresenter steht dann unter **Sources** die `rtpMIDI`-Session (`Ableton-Netz`) und unter **Destinations** `LX Bridge` (`loopMIDI`).
  - Beide Bridges senden per UDP an dasselbe FLX S48 (`192.168.1.10:8830`). UDP erlaubt mehrere Absender problemlos.
- **Keine Doppeltrigger:** Folien, die von Ableton per Netzwerk-MIDI getriggert werden, dürfen **kein** Licht-Makro tragen (oder Ableton sendet in diesem Song kein Licht). Lege pro Song fest, wer das Licht führt.
- **Keine Rückleitung über dieselbe `rtpMIDI`-Session:** Sende keine ProPresenter-Licht-Makros über die bestehende `rtpMIDI`-Session zurück an den Mac, um Schleifen und Fehltrigger zu vermeiden.

---

## Häufige Fehler und schnelle Hilfe

| Symptom | Wahrscheinliche Ursache | Lösung |
| --- | --- | --- |
| Mac erscheint nicht in Windows `rtpMIDI` (*Directory*) | Bonjour fehlt/gestoppt, Session am Mac nicht aktiviert, oder ab macOS 15 falscher Typ (*Network MIDI 2.0* statt *RTP*) | Session am Mac auf Typ **RTP** prüfen und aktivieren; Bonjour-Dienst unter Windows prüfen oder Mac **manuell mit IP + Port `5004`** im Directory hinzufügen |
| Verbindung bricht ab oder klappt auch mit IP nicht | Windows-Firewall blockiert UDP `5004`/`5005` (Netz steht auf *Öffentlich*) oder macOS-Firewall blockiert | Windows-Netzwerkprofil auf **Privat** stellen bzw. UDP `5004` und `5005` freigeben; macOS-Firewall prüfen |
| `rtpMIDI`-Port fehlt in ProPresenter unter *Sources* | Session wurde erst nach dem Start von ProPresenter aktiviert | Session in `rtpMIDI` aktivieren, danach ProPresenter neu starten |
| ProPresenter löst falsche Aktion oder Folie aus | Oktav-Versatz bei Notennamen oder MIDI Map passt nicht | Mit Notennummern `0–127` vergleichen; MIDI Map und Velocity-Werte prüfen |
| Licht-Noten schalten Folien (oder Folien-Noten schalten Licht) | *Live-Routings* im macOS Audio-MIDI-Setup gesetzt oder falsches *MIDI To* in Ableton | *Live-Routings* am Mac komplett leeren; *MIDI To* beider Ableton-Spuren prüfen |
| `midi-bridge` am Mac öffnet keinen Port | In `mapping.yaml` steht nur `"LX Bridge"` statt des vollen IAC-Namens | Exakten Namen aus `uv run midi-bridge --list-ports` eintragen (z. B. `"IAC-Treiber LX Bridge"`) |
| Nach Neustart kommen keine Noten mehr in ProPresenter an | `rtpMIDI`-Verbindung oder ProPresenter-Device nicht verbunden | In `rtpMIDI` prüfen, ob der Mac unter *Participants* steht (sonst *Connect*); in ProPresenter *Auto Reconnect* einschalten |

---

## Kurz-Checkliste vor der Veranstaltung

- [ ] Netzwerkkabel stecken an Mac, Windows-PC, FLX S48 und Switch
- [ ] Mac: Im Audio-MIDI-Setup ist die RTP-Session aktiviert und Windows steht unter **Teilnehmer**
- [ ] Mac: IAC-Treiber ist online (`LX Bridge`), `midi-bridge` läuft ohne `--dry-run`
- [ ] Windows: `rtpMIDI` zeigt den Mac unter **Participants** (Latenz `0–2 ms`)
- [ ] Windows: ProPresenter MIDI-Device zeigt **Connected** (*Sources* = `rtpMIDI`-Session)
- [ ] Test-Note auf Spur **`ProPresenter`** schaltet Folie weiter (ohne Log-Zeile in der `midi-bridge`)
- [ ] Test-Note auf Spur **`LX`** löst Cue am FLX S48 aus (ohne Reaktion in ProPresenter)

---

## Quellen

- [Apple Support: Share MIDI information over a network in Audio MIDI Setup on Mac](https://support.apple.com/guide/audio-midi-setup/share-midi-information-over-a-network-ams1012/mac)
- [Tobias Erichsen: rtpMIDI Tutorial](https://www.tobias-erichsen.de/software/rtpmidi/rtpmidi-tutorial.html)
- [Renewed Vision: How to Automate Lyrics in ProPresenter 7 with Ableton](https://www.renewedvision.com/blog/how-to-automate-lyrics-in-propresenter-7-with-ableton)

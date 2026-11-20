# 09 – Scheinwerfer einstellen (Performer 2000 RGBAL & Flat Pro 12)

Diese Anleitung erklärt Schritt für Schritt, was du **am Lichtmixer (FLX S48)** und was du **direkt an den Scheinwerfern** einstellst – vor allem, um Fades möglichst weich ohne sichtbare Stufen hinzubekommen.

## Kurz vorweg: IP-Adresse oder DMX-Adresse?

Eure Scheinwerfer haben **keine IP-Adresse** und keinen Netzwerkanschluss. Sie werden über **DMX-512** (XLR-Kabel) mit einer **DMX-Startadresse (`001`–`512`)** gesteuert:

```text
FLX S48 ──► Netzwerkkabel (Art-Net) ──► Art-Net-Node ──► XLR-Kabel (DMX) ──► Scheinwerfer
```

Eine IP-Adresse haben deshalb nur das **FLX S48** und der **Art-Net-Node**:

- **IP des Art-Net-Nodes nachsehen:** Am FLX S48 **`Setup`** drücken → Reiter **`Devices`**. Ist Art-Net unter `Setup → Universes` aktiviert, zeigt ZerOS dort erkannte Art-Net-Nodes samt Name und IP-Adresse an.
- **IP des FLX S48 nachsehen:** Am FLX S48 **`Setup → Universes → Art-Net`** (bzw. für OSC unter **`Setup → Triggers → OSC`**, siehe [03-setup-flx.md](03-setup-flx.md)).

## Eure beiden Scheinwerfer im Vergleich

| Gerät | Typ / Code | Dimm-Auflösung | Was bringt weichere Fades? |
| --- | --- | --- | --- |
| **Showtec Performer 2000 RGBAL** | 240 W Theater-Spot (`33038`) | **16 Bit** im Mode `TR16` (19 Ch), sonst 8 Bit | Mode **`TR16`** (19 Ch) + Dimm4-Glättung (**`DIM1–DIM4`**) |
| **Cameo FLAT PRO 12** (`8Ch`) | 12×10 W RGBWA PAR (`CLPFLATPRO12`) | nur **8 Bit** (256 Stufen) | im 8Ch-Modus hardwareseitig begrenzt; im ganz dunklen Bereich (0–15 %) bleiben Stufen bei sehr langsamen Fades normal |

---

## Teil 1: Zuerst am FLX S48 prüfen (ohne Leiter)

Bevor du an einen Scheinwerfer kletterst, prüfe zuerst diese Punkte am Pult:

1. **Showfile sichern:** **`Z → Save Show`** oder **`Setup → Save Show`** auf FAT32-USB-Stick (siehe [08-bedienung-flx-s48.md](08-bedienung-flx-s48.md)).
2. **Aktuellen Patch ablesen:** **`Setup`** drücken → du siehst die Patchübersicht (**Fixture Schedule**).
   Notiere für deine *Performer 2000 RGBAL*:
   - welchen **Mode** sie aktuell haben (`HSIC` 8 Ch, `SSP` 10 Ch, `TOUR` 13 Ch oder schon `TR16` 19 Ch),
   - welche **DMX-Adresse** und welches **Universe** eingetragen sind.
3. **Dimmer-Glättung direkt vom Pult aus testen:**
   1. Einen *Performer 2000 RGBAL* auswählen (Taste unter dem Fader drücken).
   2. Am Touchscreen oben **`Beam`** antippen (bei Bedarf mehrfach auf **`Beam`** tippen, um durch die Seiten zu blättern).
   3. Prüfen, ob ein Encoder **`Dimmer Speed`** (o. ä.) anzeigt:
      - DMX `0–9`: übernimmt die Einstellung aus dem Scheinwerfer-Menü.
      - DMX `10–29`: `Linear dimmer` (hart/ungeglättet).
      - DMX `70–129` (`Non-linear dimmer 2`) bzw. `130–189` (`Non-linear dimmer 3`) bzw. `190–255` (`Non-linear dimmer 4`): weiches Dimmen von schnell nach langsam.
   4. Testweise **`Non-linear dimmer 2`** oder **`3`** wählen und einen Cue-Fade testen. Wenn das bereits weicher fadet, per **`Update`** im Cue speichern (oder als Default im Pult ablegen).

---

## Teil 2: Showtec Performer 2000 RGBAL einstellen

Auf der Rückseite des Scheinwerfers liegen das OLED-Display und vier Tasten: **`MENU`**, **`UP`**, **`DOWN`**, **`ENTER`**.

> **Displaysperre aufheben:** Wenn das Display `PASS CODE` anzeigt, drücke nacheinander:
> **`UP` → `DOWN` → `UP` → `DOWN` → `ENTER`**

### Schritt A (einfach & risikolos): Nur Dimm-Glättung und PWM einstellen

Hierbei bleiben **DMX-Adresse und Kanalmodus unverändert** – eure bestehende Show auf dem FLX S48 läuft sofort weiter.

1. **`MENU`** drücken, um ins Hauptmenü zu kommen (bei `PASS CODE`: `UP, DOWN, UP, DOWN, ENTER`).
2. Mit **`UP` / `DOWN`** auf **`Setting`** (Menüpunkt 7) gehen → **`ENTER`**.
3. Passcode erneut eingeben: **`UP` → `DOWN` → `UP` → `DOWN` → `ENTER`**.
4. **`DIMMER`** wählen → **`ENTER`**.
5. Mit **`UP` / `DOWN`** von **`OFF`** auf **`DIM2`** oder **`DIM3`** wechseln (`DIM1` = schnell bis `DIM4` = sehr weich/halogenähnlich) → **`ENTER`**.
6. *(Optional gegen Flimmern auf der Videokamera)* Im selben **`Setting`**-Menü auf **`PWM_RATE`** → **`ENTER`** → gewünschte Frequenz wählen (z. B. **`4000Hz`**, **`6000Hz`** oder **`25000Hz`**) → **`ENTER`**.
7. Mit **`MENU`** wieder herausgehen.

*Hinweis:* Damit `DIM2`/`DIM3` greift, darf das Pult auf dem `Dimmer Speed`-DMX-Kanal nicht fest `Linear dimmer` (`10–29`) senden, sondern `0–9` (*Preset from menu*) oder ebenfalls `Non-linear`.

### Schritt B (maximale Feinheit): Auf 16-Bit (`TR16`, 19 Kanäle) wechseln

Wenn die Performer aktuell auf 8, 10 oder 13 Kanälen laufen, bekommst du die feine **16-Bit-Auflösung** erst, wenn **Scheinwerfer und FLX S48** auf **`TR16` (19 Kanäle)** stehen.

> **Wichtig vor dem Umstellen:**
> - Jeder Spot belegt dann **19 DMX-Kanäle** (`Startadresse` bis `Startadresse + 18`). Prüfe vorher im **`Fixture Schedule`** am Pult, ob bis zum nächsten Gerät genug Platz ist.
> - Hand-Fader am FLX S48 steuern mit 8 Bit – die feinen **16 Bit** wirken beim **Abspielen von Cues** mit Fade-Zeit.

**1. Am Scheinwerfer umstellen:**

1. Hauptmenü öffnen (Passcode: `UP, DOWN, UP, DOWN, ENTER`).
2. Mit **`UP` / `DOWN`** auf **`Personality`** (Menüpunkt 6) → **`ENTER`**.
3. **`TR16`** (`19 channels`) auswählen → **`ENTER`**.
4. Falls eine neue Startadresse nötig ist: ins Hauptmenü → **`Address`** (Menüpunkt 4) → **`ENTER`** → neue DMX-Adresse (`001`–`494`) wählen → **`ENTER`**.

**2. Am FLX S48 nachziehen:**

1. Showfile sichern (falls in Teil 1 noch nicht geschehen).
2. **`Setup`** drücken (du bist im **Fixture Schedule**).
3. Den umgestellten Performer markieren → **`Change Fixtures`** wählen → beim **`Performer 2000 RGBAL`** den Mode **`TR16` (19 Ch)** auswählen.
4. Bei Bedarf in der Adressspalte die passende DMX-Startadresse und das Universe eintragen (`OK`).
5. Erst an **einem** Spot mit einem 10-Sekunden-Cue-Fade testen, bevor du alle Geräte umstellst.

*(Hinweis zu RDM/RigSync: Das FLX S48 unterstützt unter `Setup → Universes → RDM` auch **RigSync**, was über Art-Net aber nur funktioniert, wenn euer Art-Net-Node RDM durchlässt. Bei bestehenden Shows ist manuelles Umstellen im Fixture Schedule sicherer als automatisches Neu-Patchen.)*

---

## Teil 3: Cameo FLAT PRO 12 (`8Ch`) einstellen

Auf der Rückseite befinden sich ein Display und vier Tasten: **`MODE`**, **`ENTER`**, **`UP` / `DOWN`** (Value Up/Down).

1. **DMX-Adresse prüfen/einstellen:** **`MODE`** so oft drücken, bis im Display die DMX-Adresse (`DMX ADDR` o. ä.) steht → **`ENTER`** → mit `UP`/`DOWN` Startadresse setzen → **`ENTER`**.
2. **DMX-Modus prüfen/einstellen:** **`MODE`** drücken bis zur Modus-Wahl (`DMX MODE` o. ä.) → **`ENTER`** → **`8-CH`** wählen → **`ENTER`**.
3. **Kanalbelegung im 8-CH-Modus** (falls im Pult etwas komisch reagiert):
   - **CH 1:** Master Dimmer (`0–255`, 8 Bit)
   - **CH 2:** Strobe (`0` = aus)
   - **CH 3–7:** Red, Green, Blue, White, Amber (je 8 Bit)
   - **CH 8:** Color Macro / Auto (`0–4` lässt normale RGBWA-Mischung vom Pult zu)

**Grenze dieses Modells:** Der *FLAT PRO 12* (1. Generation) hat in keinem seiner Modi (2 / 3-1 / 3-2 / 5 / 8 Ch) einen 16-Bit-Dimmer. Fades bleiben daher bauartbedingt auf 256 Schritte begrenzt.

---

## Teil 4: Schneller Check – liegt das Stufen an der Lampe oder an Art-Net?

Wenn dir ein Fade weiterhin ruckelig vorkommt, grenze die Ursache in vier Schritten ein:

1. **Lampen gegeneinander testen:** Lege einen langsamen 10-Sekunden-Cue-Fade (0 % → 100 %) an.
   - Stuft es **nur beim Flat Pro 12**, während der **Performer 2000 RGBAL (`TR16` + `DIM2/DIM3`)** sauber fadet → alles normal (8-Bit-Grenze beim Flat Pro 12).
   - Stuft **auch der Performer 2000 RGBAL** trotz `TR16` + `DIM2/DIM3` → weiter bei Punkt 2.
2. **Direkt per DMX gegenprüfen:** Einen Performer testweise **direkt per XLR-Kabel** an den DMX-Ausgang des FLX S48 anschließen (ohne Art-Net-Node). Fadet er dort flüssig, liegt das Problem auf der **Art-Net-Strecke oder im Art-Net-Node**.
3. **Netzwerk & Art-Net prüfen:** Am Pult **`Setup → Universes → Art-Net`** kontrollieren (`Transmit Mode`), WLAN im Art-Net-Pfad vermeiden und sicherstellen, dass kein zweiter Art-Net-Sender auf demselben Universe sendet.
4. **Cue-Zeiten am Pult kontrollieren:** Mit **`View` + Playback-Taste** im Cues-Fenster ([08-bedienung-flx-s48.md](08-bedienung-flx-s48.md)) prüfen, ob die gewünschte Zeit bei **`Fade Up` / `Fade Down`** *und* bei **`Colour`** steht.

## Quellen

- [Showtec Performer 2000 RGBAL Bedienungsanleitung V2 (deutsch, Art. 33038)](https://www.showandstage.de/mediafiles/Anleitungen/HL-33038.pdf)
- [Showtec Performer 2000 RGBAL User Manual V3 (englisch, Art. 33038)](https://www.jpleisure.co.uk/Data/showtec_performer2000-rgbal_manual.pdf)
- [Cameo CLPFLATPRO12 DMX-Chart (8-Channel)](https://www.hitlight.app/fixtures/cameo/clpflatpro12)
- [ZerOS-Handbuch: Change Fixtures (Fixture Schedule)](https://www.zero88.com/manuals/zeros/patching/fixture-schedule/change-fixture)
- [ZerOS-Handbuch: Art-Net](https://www.zero88.com/manuals/zeros/setup/universes/art-net)
- [ZerOS Art-Net Devices (IP-Anzeige unter Setup → Devices)](https://manuals.plus/zero-88/art-net-devices-dmx-artnet-lighting-console-manual)

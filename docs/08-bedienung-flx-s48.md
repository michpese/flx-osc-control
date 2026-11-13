# 08 – Bedienung FLX S48: Cues, Playbacks und mehr

Diese Anleitung erklärt die Arbeit am Pult selbst: Scheinwerfer einstellen, Cues aufnehmen, ändern und abspielen, Playbacks einrichten, Gruppen, Paletten, Effekte, Patch und Showfiles. Für die Fernsteuerung per OSC gelten weiter [02-flx-osc-referenz.md](02-flx-osc-referenz.md) und [03-setup-flx.md](03-setup-flx.md).

> **Grundlage:** offizielles Handbuch „FLX S24 & FLX S48 User Manual" (Stand ZerOS 7.9.3). Aktuell ist ZerOS 8.0.1 (März 2026). Menünamen können sich in neueren Versionen leicht verschieben. Tastennamen stehen so da, wie sie auf dem Pult gedruckt sind (englisch).

## Das Pult in Kürze

| Punkt | FLX S48 |
| --- | --- |
| Fader | 48 Multifunktionsfader, jeweils als Kanal oder Playback nutzbar |
| Seiten | **Page** schaltet zwischen Fader 1–48 und 49–96 |
| Playbacks | 97 (Nummern 0 bis 96, Playback 0 ist das Master Playback) |
| Cues | bis zu 10.000 insgesamt |
| Gruppen / Paletten | 96 Gruppen, je 96 Paletten für Colour, Beamshape, Position, Effect |
| Bildschirm | 7"-Touch intern, dazu externer Monitor (DVI-D, auch Touch) möglich |
| **View** | wechselt zwischen Cues- und Faders-Fenster; **Shift + View** zurück zum Output-Fenster |
| **Z** | Schnellmenü: Save Show, Copy, Speed Override, Programmer Time, Lock |

> **Achtung, Unstimmigkeit im Repo:** `docs/02` und `docs/03` sprechen vom FLX S24, nennen aber 97 Playbacks. Laut Handbuch hat der **S24 49 Playbacks**, der **S48 97**. Bitte klären, welches Pult im Einsatz ist, und `docs/02` von Hand korrigieren.

## Grundbegriffe

| Begriff | Bedeutung |
| --- | --- |
| **Cue** | eine gespeicherte Lichtstimmung mit Zeiten |
| **Playback** | Speicherplatz für einen oder viele Cues. Ein Playback mit einem Cue arbeitet wie ein Submaster, mit mehreren wie eine Cue-Liste |
| **Master Playback** | Playback 0, rechts mit eigenem Fader und leiser Go-Taste ► |
| **Programmer** | was du gerade eingestellt, aber noch nicht gespeichert hast |
| **HTP / LTP** | Highest Takes Precedence (höchster Wert gewinnt, typisch Helligkeit) / Latest Takes Precedence (letzter Befehl gewinnt, typisch Farbe, Position) |
| **Tracking** | ein Wert bleibt in folgenden Cues erhalten, bis ein Cue ihn ändert |
| **Grüner Balken** | aktiver Cue im Playback-Fenster |
| **Gelber Balken** | nächster Cue |

## Vor jedem Programmieren

1. **Clear** zweimal drücken. Das leert die Kommandozeile und den Programmer.
2. Mit **Fader Function** festlegen, ob die Fader gerade Kanäle oder Playbacks sind.
3. Mit **Page** die richtige Faderseite wählen.

## Scheinwerfer auswählen und einstellen

Über die Select-Tasten unter den Fadern, über Gruppen oder per Befehlszeile:

| Eingabe | Wirkung |
| --- | --- |
| `1 @ 1 0 0 Enter` | Gerät 1 auf 100 % |
| `5 Thru 10 Except 7 @ 6 5 Enter` | Geräte 5 bis 10 ohne 7 auf 65 % |
| `@ @` | ausgewählte Geräte auf 100 % |
| `@ .` | ausgewählte Geräte auf 0 % |
| `Enter Enter` | alle Geräte über 0 % auswählen |

Farbe, Beam und Position stellst du über die Attribut-Tabs am Touchscreen und die Encoder ein. Mit mehreren Fingern auf Farbwähler oder Pan/Tilt-Raster fächerst du Werte auf: erster und letzter Finger bestimmen erstes und letztes Gerät.

## Gruppen

| Aufgabe | Bedienung |
| --- | --- |
| automatisch anlegen | Gruppen-Fenster öffnen, „Automatically create groups" |
| aufnehmen | Geräte wählen, **Record**, leere Gruppe antippen |
| abrufen | Gruppe doppelt antippen; nochmal doppelt antippen schaltet sie auf 0 % |
| ändern | neue Auswahl, **Update**, Gruppe antippen (Name bleibt) |
| löschen | **Delete**, Gruppe antippen, bestätigen |
| benennen | **Setup** halten, Gruppe antippen, Name eingeben, **OK** |

Eine Gruppe speichert auch die Reihenfolge der Geräte. Das ist wichtig fürs Auffächern und für Effekte.

## Paletten

Paletten sind gespeicherte Farben, Beams, Positionen oder Effekte. Cues, die eine Palette nutzen, ändern sich mit, wenn die Palette geändert wird. Das spart Arbeit, wenn sich am Ort etwas verschiebt.

| Aufgabe | Bedienung |
| --- | --- |
| aufnehmen | Geräte wählen, Attribut einstellen, **Record**, leere Palette im passenden Tab antippen |
| abrufen | Geräte wählen, Palette antippen |
| ändern | Palette aktivieren, Werte ändern, **Update**, Palette antippen |
| löschen | **Delete**, Palette antippen, bestätigen. Cues behalten die Werte, verlieren aber die Verknüpfung |
| benennen | **Setup** halten, Palette antippen, Name, **OK** |

Beim Patchen legt ZerOS automatische Paletten aus den Gerätedaten an, zum Beispiel Shutter „Open" und „Closed".

## Effekte

1. Geräte auswählen.
2. **Effect** drücken. Die Encoder zeigen zuerst die globalen Werte: Speed, Size, Offset, Rotation.
3. Weiteres Drücken von **Effect** springt zu den einzelnen Effekten.
4. Für Auffächern **Shift** halten und den Encoder eines Effektparameters drehen, oder die Offset-Tasten im Effekt-Fenster nutzen.

Standardwerte: Speed 25, Size 20, Offset 0, Rotation 0. Bei Intensity-, Colour-, Iris- und Focus-Effekten setzt ZerOS die Basis auf 50 %.

## Cues aufnehmen

1. Stimmung einstellen.
2. **Record** drücken.
3. Die Encoder zeigen jetzt **Up Fade, Up Delay, Down Fade, Down Delay**. Zeiten drehen oder die mittlere Encodertaste drücken und eintippen.
4. Die **Go-Taste des Ziel-Playbacks** drücken, für das Master Playback die Taste ►.

Der Cue landet hinten im Playback. Ein Punkt-Cue wie 5.5 liegt zwischen 5 und 6. So fügst du später etwas ein, ohne die Nummern zu verschieben.

> **Am Pult prüfen:** die Eingabe einer bestimmten Cue-Nummer beim Aufnehmen (**Record**, Nummer eintippen, Go-Taste). Das Handbuch beschreibt Punkt-Cues, nennt die Tastenfolge aber nicht wörtlich.

### Record-Fenster

**Record** gedrückt halten statt antippen öffnet das Record-Fenster am internen Bildschirm.

| Option | Wirkung |
| --- | --- |
| **Snapshot** (auch **Shift + Record**) | speichert jeden Parameter jedes Geräts, ein „Block-Cue". Gut als sauberer Neustart einer Szene |
| **Smart Tag** | speichert nur, was sich gegenüber vorher geändert hat. Geräte auf 0 % werden nicht gespeichert |
| **Track Forward / Track Backward / Track Both / Cue Only** | wie sich die Änderung auf folgende oder vorherige Cues auswirkt. **Cue Only** ändert nur diesen einen Cue |
| **Filter** | nur bestimmte Geräte, Parameter oder Attribute speichern |
| **Remove** | Werte aus einem Cue entfernen |

## Zeiten nachträglich ändern

1. Im Playback-Fenster die Zeitzelle des Cues antippen.
2. Mit den Encodern ändern oder mit der mittleren Encodertaste exakt eintippen.

Für die Fernsteuerung gilt: **Die Zeit gehört in den Cue, nicht in den Trigger** (siehe `docs/03`).

## Cues ändern (Update)

1. Den Cue abspielen, er muss grün im angezeigten Playback stehen.
2. Änderungen machen.
3. **Update** drücken. Die Zeiten erscheinen wie beim Aufnehmen auf den Encodern.
4. Die **Go-Taste** des Playbacks drücken.

Den Namen änderst du per Doppeltipp auf das Feld „Name" im Playback-Fenster.

## Cue-Einstellungen

Im Playback-Fenster in der Spalte „Settings" die Taste des Cues drücken. Es öffnet sich „Cue Setup".

| Einstellung | Wirkung |
| --- | --- |
| **Trigger** | **Go** (Standard), **Auto with previous cue** oder **Auto after previous cue**, jeweils mit Wait Time |
| **Next** | welcher Cue als nächster kommt. Leer heißt der Reihe nach |
| **Don't Move on Dark** | schließt für diesen Cue einzelne Attribute vom Vorbereiten im Dunkeln aus |
| **Macros** | startet oder beendet beim Erreichen des Cues **andere Playbacks**. „Add" drücken, Playback wählen, **OK** |

Beispiel: Ein Lauflicht liegt auf Playback 20. Cue 3 im Steuer-Playback startet es über „Macros", Cue 4 beendet es wieder. So braucht die Fernsteuerung nur Cue-Befehle.

## Cues kopieren und löschen

**Kopieren:**

1. **Z** drücken, **Copy** wählen, „Cue" muss ausgewählt sein.
2. Im Feld „from" die Quelle eintippen und die Taste des Quell-Playbacks drücken.
3. Im Feld „to" das Ziel eintippen und die Taste des Ziel-Playbacks drücken.

Beispiel aus dem Handbuch: `7`, Playback 15, dann `25`, Playback 18 kopiert Cue 7 von Playback 15 als Cue 25 auf Playback 18. Mehrere Cues gehen mit **And** und **Thru** im Feld „from".

**Löschen:**

1. **Delete**, dann **Z** drücken.
2. Nummer eintippen, Bereiche mit **Thru**, zum Beispiel `15 Thru 20`.
3. Taste des Playbacks drücken.

Löschen lässt sich **nicht rückgängig machen**. Vorher Showfile sichern.

## Cues abspielen

| Aktion | Bedienung |
| --- | --- |
| erster Cue | Playback-Fader auf voll schieben |
| nächster Cue | **Go** |
| zu einem Cue springen (Go To) | Cue im Playback-Fenster antippen (wird gelb), dann **Go** |
| ohne Zeit springen (Snap) | **Shift** halten und **Go**. Auto-Trigger laufen dabei nicht |
| anhalten | **Shift + Go** oder Pause-Funktion der Taste. Mehrfach drücken geht rückwärts, **Go** läuft wieder vorwärts |
| Playback freigeben | Fader auf 0 oder **Clear** halten und **Go** des Playbacks drücken |
| alle Fader-Playbacks freigeben | **Clear** halten und **Fader Function** drücken (Master Playback bleibt) |
| Master Playback freigeben | **Clear** halten und ► drücken |

Nach dem letzten Cue folgt wieder der erste.

## Playback-Einstellungen

**Setup** halten und die Taste unter dem Fader drücken. Fünf Reiter:

**General**
- **Intensity Mixing:** HTP, LTP, LTP Catch oder Inhibit.
- **Fader Function:** HTP Master (Standard, Fader begrenzt die Helligkeit, Cues laufen per Go), Manual Fader 2-Way (Überblenden mit dem Fader, nächster Cue lädt an jedem Ende), Manual Fader 1-Way (nächster Cue lädt nur unten, nicht für Lauflichter).
- **Button Function:** Flash, Latch, Solo, Go (Fade), Go (Snap), Pause, Tap Tempo; mit **Shift** eine zweite Funktion.
- **Stack Name:** Name des Playbacks.

**Chase**
- „Turn into Chase" macht aus dem Playback ein Lauflicht.
- Richtung: Forward, Backward, Bounce, Random.
- Übergang: Cross Fade, Ramp Up, Ramp Down.
- Tempo in BPM oder Global BPM, Sound-to-Light, Shots (0 = endlos).

**Raise & Lower**
- Trigger on Raise / Release on Lower mit Schwellwert in %.
- Raise Time und Lower Time.

**Move on Dark**
- Geräte bereiten im Dunkeln Farbe, Beam und Position für ihren nächsten Einsatz vor.
- Fade Time, Delay Time, „Move to First Cue".
- Don't Move Colour / Beamshape / Position / Effect. Ab Werk ist nur Effect ausgeschlossen.

**Advanced**
- Renumber, Block, Unblock, Allow Stomping, Page Lock.

> **Renumber nie auf dem Steuer-Playback.** Die Cue-Nummern sind die Adressen der Fernsteuerung (`docs/03`).

Playbacks kopierst du mit **Z → Copy → Playback**, löschst sie mit **Delete** und der Taste unter dem Fader, benennst sie mit **Setup** + Taste.

## Rezept: Lauflicht bauen

1. Leeres Playback wählen, zum Beispiel 20.
2. Schritt 1 einstellen, **Record**, Go-Taste von Playback 20.
3. Schritt 2 einstellen, **Record**, Go-Taste von Playback 20. Weiter für alle Schritte.
4. **Setup** halten, Taste von Playback 20, Reiter **Chase**, „Turn into Chase".
5. Richtung, Übergang und BPM einstellen.
6. Optional: im Steuer-Playback per Cue-Einstellung „Macros" starten und beenden.

## Rezept: Steuer-Playback für ProPresenter und Ableton

1. Playback 10 frei machen und benennen, zum Beispiel „Remote".
2. Pro Stimmung: einstellen, Zeiten setzen, **Record**, Go-Taste von Playback 10.
3. Cues ganzzahlig und in der Reihenfolge der Tabelle in `docs/03` anlegen.
4. Cue-Namen vergeben, damit der Event Monitor lesbar bleibt.
5. Lauflichter oder Effekte über „Macros" in den Cues verknüpfen.
6. Showfile speichern (siehe unten) und unter `shows/<ort-oder-anlass>/` ins Repo legen.
7. Jeden Cue einmal per `flxctl` auslösen und im Event Monitor kontrollieren (Teststufe 2 in `docs/06`).

## Master-Funktionen im Z-Menü

| Funktion | Wirkung |
| --- | --- |
| **Speed Override** | 50 % = programmierte Zeiten, 100 % = ohne Zeit, 0 % = angehalten |
| **Global BPM** | gemeinsames Tempo für Lauflichter |
| **Programmer Time** | Überblendzeit für Änderungen im Programmer, 0.0 bis 11:30.0 |
| **Lock Console** | Pult sperren, PIN ab Werk `0000` |

Auf einem leeren Playback kannst du über **Setup** + Taste den Fader auch als Grand Master, Global BPM, Programmer Time oder Speed Override belegen.

## Patch

1. **Setup** drücken, links **Add Fixtures**.
2. Hersteller, Gerät und Mode wählen. Generische Geräte stehen oben.
3. **Next:** Anzahl, Gerätenummer und Startadresse. „Next Address" nimmt die nächste freie Adresse.
4. **Finish**.

| Aufgabe | Bedienung |
| --- | --- |
| Adresse ändern | Adresszelle im Fixture Schedule antippen, Universe und Adresse, **OK** |
| Pan/Tilt invertieren oder tauschen | Alignment-Spalten im Fixture Schedule |
| Gerät doppelt adressieren | „Add as additional address" |
| Gerät löschen | Geräte wählen, **Delete**, **OK**. Entfernt es auch aus Cues, Gruppen und Paletten |

## Showfile speichern, laden, Pult leeren

**Speichern**
- Schnell: **Z → Save Show**. Hat die Show schon einen Namen, legt ZerOS eine neue Kopie mit fortlaufender Nummer an.
- Ausführlich: **Setup → Save Show**, USB-Stick wählen (bei Bedarf **Refresh**), Namen eingeben, **OK**.
- USB-Stick in **FAT32**, nicht exFAT. exFAT erkennt ZerOS nicht.
- Das Pult speichert zusätzlich regelmäßig intern. Das ersetzt keine Sicherung auf USB.

**Laden**
1. **Setup → Load File**, Stick wählen, Showfile wählen, **OK**.
2. Auswahl: **Load Complete Show** (Patch, Cues, Paletten, Gruppen, Einstellungen, Netzwerk), **Load Setup Only** oder **Load Setup & Palettes**.

Laden überschreibt alles am Pult. Vorher die aktuelle Show sichern. **Load Complete Show** übernimmt auch die Netzwerkeinstellungen, also prüfen, ob IP-Adresse und OSC danach noch zum Adressplan in `docs/03` passen.

**Leeren:** **Setup → Clear Options**. Einzeln (Paletten je Art, Gruppen, Playbacks), „Clear All", „Reset Desk" oder „Factory Reset". Nichts davon lässt sich rückgängig machen.

**Software-Update:** Datei auf einen USB-Stick (nicht in einen Ordner), **Setup → Load**, Datei wählen, neu starten. **Das Update löscht alle Daten am Pult, auch Showfiles.** Vorher sichern, danach Show neu laden und OSC-Einstellungen prüfen. Stabile Stromversorgung während des Updates.

## Kurzreferenz

| Ich will … | Tasten |
| --- | --- |
| Programmer leeren | **Clear Clear** |
| Cue aufnehmen | **Record**, Zeiten, Go-Taste |
| Cue ändern | Cue abspielen, ändern, **Update**, Go-Taste |
| Snapshot-Cue | **Shift + Record**, Go-Taste |
| zu Cue springen | Cue antippen, **Go** |
| ohne Zeit springen | **Shift + Go** |
| Playback freigeben | **Clear** + **Go** |
| alle Fader freigeben | **Clear** + **Fader Function** |
| Playback einrichten | **Setup** + Taste unter dem Fader |
| Cue kopieren | **Z → Copy** |
| Cue löschen | **Delete Z**, Nummer, Playback-Taste |
| Show speichern | **Z → Save Show** |
| Faderseite wechseln | **Page** |
| Cues ↔ Faders-Fenster | **View** |

## Häufige Fehler

- **Neuer Cue enthält Reste.** Vor dem Einstellen **Clear Clear** vergessen.
- **Update landet im falschen Cue.** Der Cue war nicht grün im angezeigten Playback.
- **Änderung taucht in späteren Cues auf.** Tracking. Mit **Cue Only** im Record-Fenster aufnehmen.
- **Fader bewegt nichts.** **Fader Function** steht auf Kanälen statt Playbacks, oder falsche **Page**.
- **Lauflicht läuft nach dem Cue weiter.** Im Folge-Cue per „Macros" freigeben, ein „Release all" gibt es per OSC nicht (`docs/02`).
- **Show lädt nicht vom Stick.** Stick ist exFAT formatiert.

## Quellen

- [FLX S24 & FLX S48 User Manual (englisch, ZerOS 7.9.3)](https://www.jpleisure.co.uk/Data/zero88_flx-series_manual.pdf)
- [FLX S Bedienungsanleitung (deutsch, ZerOS 7.9.3)](https://images.static-thomann.de/pics/atg/atgdata/document/manual/zero88_flx_s_de.pdf)
- [ZerOS 8.0.1 Release Notes](https://vari-lite.s3.eu-west-1.amazonaws.com/graphics/technical/documents/ZerOS-8.0.1-release-notes.pdf)
- [ZerOS-Handbuch: Macros](https://www.zero88.com/manuals/zeros/macros)

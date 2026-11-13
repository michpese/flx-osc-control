# Prompt 7: Max-for-Live-Device (optional)

**Effort:** `high`

Voraussetzung: Live Suite oder Standard mit Max for Live.

```text
Ich möchte ein Max-for-Live-MIDI-Effekt-Device "LX Cue Send", das bei
jeder eingehenden Note eine OSC-Adresse per UDP an ein Lichtpult sendet.
Lies CLAUDE.md, docs/02-flx-osc-referenz.md und
shows/mapping.example.yaml.

Liefere keine .amxd-Datei, sondern:
1. eine Schritt-für-Schritt-Bauanleitung für den Max-Editor mit jedem
   Objekt und jeder Verbindung
2. den JavaScript-Teil für das Nachschlagen Note → Adresse als Datei
3. die Bedienelemente: IP, Port, Testknopf, Anzeige der letzten Adresse
4. einen Prüfplan mit der mock-console

Erkläre jeden Schritt so, dass ihn jemand ohne Max-Erfahrung nachbauen
kann. Lege alles unter integrations/ableton/lx-cue-send/ ab.
```

# Prompt 4: midi-bridge

**Effort:** `high`

```text
Baue das Paket midi-bridge: ein Dauerläufer, der MIDI-Noten in
OSC-Befehle übersetzt. Lies CLAUDE.md, docs/01-konzept.md,
packages/midi-bridge/README.md und shows/mapping.example.yaml.

Ablauf: mapping.yaml laden und prüfen, MIDI-Eingang öffnen, bei Note On
Kanal und Note nachschlagen, Adresse über zeros-osc senden.

Anforderungen
1. Nur Note On mit Velocity größer 0 löst aus. Alles andere wird
   ignoriert.
2. Entprellen: dieselbe Note auf demselben Kanal löst innerhalb von
   debounce_ms nur einmal aus.
3. Verschwindet der MIDI-Port, versucht die Bridge alle zwei Sekunden,
   ihn neu zu öffnen, ohne abzustürzen.
4. Änderungen an mapping.yaml werden ohne Neustart übernommen. Ist die
   neue Datei fehlerhaft, bleibt die alte aktiv und das Log sagt warum.
5. --dry-run sendet nichts und zeigt, was gesendet würde.
   --list-ports zeigt alle MIDI-Eingänge.
6. Log je Ereignis: Empfangszeit, Quelle, Kanal, Note, Name, Adresse,
   Dauer zwischen Empfang und Versand in Millisekunden.
7. Beim Start und nach jedem Neuladen zeigt die Bridge die Hinweise
   aus der Mapping-Prüfung an, insbesondere Einträge mit Status
   "vermutet" oder "Forum".
8. Sauberes Beenden mit Strg+C.

Grenzen: keine grafische Oberfläche, kein eigenes Senden an zeros-osc
vorbei, keine Annahmen über Portnamen außerhalb der Konfiguration. Die
Prüfung der mapping.yaml kommt aus zeros-osc, nicht aus einer zweiten
Kopie.

Nenne mir vor dem Schreiben kurz deinen Aufbau für Threads und
Warteschlange und warum er keine Note verliert.

Fertig, wenn: tests/e2e mit einem virtuellen MIDI-Port und der
mock-console zeigt, dass eine Note genau eine Nachricht erzeugt, dass
Entprellen greift und dass ein Port-Verlust überstanden wird; und das
README des Pakets die Einrichtung auf macOS und Windows Schritt für
Schritt beschreibt; und die CI des Pull Requests grün ist. Braucht ein
Test einen virtuellen MIDI-Port, den die CI nicht hat, markiere ihn so,
dass er dort übersprungen wird, und decke dieselbe Logik zusätzlich mit
einem Test ohne echten Port ab. Sage mir ausdrücklich, welche Tests wo
nicht laufen, und warum.
```

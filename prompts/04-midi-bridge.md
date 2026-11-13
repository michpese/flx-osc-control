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
7. Sauberes Beenden mit Strg+C.

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
Schritt beschreibt. Sage mir ausdrücklich, falls ein Test auf einem der
beiden Betriebssysteme nicht laufen kann, und warum.
```

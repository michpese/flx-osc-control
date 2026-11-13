# shows

Hier liegen die Show-Daten: Mapping-Dateien und ZerOS-Showfiles. Kein Code.

## Aufbau

```text
shows/
├─ mapping.example.yaml     Vorlage
└─ <ort-oder-anlass>/
   ├─ mapping.yaml          Zuordnung Note → OSC für diese Show
   ├─ <showfile>            ZerOS-Showfile, so wie das Pult es auf USB speichert
   └─ NOTIZEN.md            Besonderheiten dieser Show
```

## Neue Show anlegen

1. Ordner `shows/<ort-oder-anlass>/` anlegen.
2. `mapping.example.yaml` dorthin als `mapping.yaml` kopieren.
3. IP-Adresse des Pults und die Cues eintragen.
4. Mit `flxctl map check shows/<ort-oder-anlass>/mapping.yaml` prüfen.
5. Das Showfile vom Pult auf USB speichern und in den Ordner legen.

## Regeln

- Notennummern und Cue-Nummern werden nie neu vergeben.
- Jede Änderung am Mapping wird eingecheckt, bevor sie live geht.
- Showfile und Mapping gehören zusammen: Ändert sich eines, prüfe das andere.

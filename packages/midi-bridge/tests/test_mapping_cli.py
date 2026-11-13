"""Loading the mapping and the command line."""

from __future__ import annotations

from pathlib import Path

import pytest

from midi_bridge import load_mapping
from midi_bridge.cli import main

EXAMPLE = Path(__file__).resolve().parents[3] / "shows" / "mapping.example.yaml"


def test_example_mapping_loads():
    result = load_mapping(EXAMPLE)
    assert result.errors == ()
    m = result.mapping
    assert m.midi_ports == ("LX Bridge",)  # shared by both sources
    assert {s.name: s.channel for s in m.sources} == {"propresenter": 15, "ableton": 16}
    assert m.debounce_ms == 250
    assert m.cues[2].osc == "/zeros/cue/go/10/2"
    assert m.source_for("LX Bridge 1", 15).name == "propresenter"
    assert m.source_for("LX Bridge 1", 1) is None


def test_debounce_default(tmp_path, h):
    text = h.mapping_text(8830).replace("debounce_ms: 250\n", "")
    path = tmp_path / "m.yaml"
    path.write_text(text, encoding="utf-8")
    assert load_mapping(path).mapping.debounce_ms == 250


def test_longest_configured_port_wins(tmp_path, h):
    text = h.mapping_text(8830).replace(
        '  ableton:\n    midi_port: "LX Bridge"\n    channel: 16',
        '  ableton:\n    midi_port: "LX Bridge Mac"\n    channel: 15',
    )
    path = tmp_path / "m.yaml"
    path.write_text(text, encoding="utf-8")
    m = load_mapping(path).mapping
    assert m.source_for("LX Bridge Mac 1", 15).name == "ableton"
    assert m.source_for("LX Bridge 1", 15).name == "propresenter"


def test_list_ports(capsys, h):
    assert main(["--list-ports"], backend=h.FakeBackend(["LX Bridge 1", "Mikro"])) == 0
    out = capsys.readouterr().out
    assert "  LX Bridge 1\n" in out and "  Mikro\n" in out


def test_list_ports_empty_and_failing(capsys, h):
    assert main(["--list-ports"], backend=h.FakeBackend([])) == 0
    assert "Keine MIDI-Eingänge" in capsys.readouterr().out
    failing = h.FakeBackend()
    failing.fail_listing = True
    assert main(["--list-ports"], backend=failing) == 1
    assert "nicht abfragbar" in capsys.readouterr().err


def test_mapping_required(capsys):
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_broken_mapping_does_not_start(tmp_path, capsys, h):
    path = tmp_path / "m.yaml"
    path.write_text(h.mapping_text(8830).replace("channel: 16", "channel: 17"), encoding="utf-8")
    assert main(["--mapping", str(path)], backend=h.FakeBackend()) == 1
    err = capsys.readouterr().err
    assert "sources.ableton.channel muss 1 bis 16 sein" in err
    assert "Bridge startet nicht" in err


def test_ctrl_c_ends_cleanly(tmp_path, monkeypatch, capsys, h):
    from midi_bridge import bridge as bridge_module

    path = tmp_path / "m.yaml"
    path.write_text(h.mapping_text(8830), encoding="utf-8")

    def interrupted(self):
        self.start()
        raise KeyboardInterrupt

    monkeypatch.setattr(bridge_module.Bridge, "run", interrupted)
    assert main(["--mapping", str(path), "--dry-run"], backend=h.FakeBackend()) == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out and "beendet" in out
    # main() removes its handler, so later log lines do not hit a closed stream
    import logging

    assert not [
        x
        for x in logging.getLogger("midi_bridge").handlers
        if isinstance(x, logging.StreamHandler) and not type(x).__name__.startswith("LogCapture")
    ]

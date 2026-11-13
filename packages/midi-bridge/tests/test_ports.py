"""Port handling with a fake backend: name matching, shared ports, port loss."""

from __future__ import annotations

import logging
import threading
import time

import mido

from midi_bridge import Bridge, load_mapping, port_matches, resolve_port


def test_port_matches_start_of_name():
    assert port_matches("LX Bridge", "LX Bridge")
    assert port_matches("LX Bridge", "LX Bridge 1")
    assert not port_matches("LX Bridge", "IAC Driver LX Bridge")
    assert not port_matches("LX Bridge", "lx bridge 1")


def test_resolve_port():
    assert resolve_port("LX Bridge", ["LX Bridge 1", "Mikro"]) == ("LX Bridge 1", [])
    assert resolve_port("LX Bridge", ["LX Bridge", "LX Bridge 2"]) == ("LX Bridge", [])
    assert resolve_port("LX Bridge", ["LX Bridge 1", "LX Bridge 2"]) == (
        None,
        ["LX Bridge 1", "LX Bridge 2"],
    )
    assert resolve_port("LX Bridge", ["Mikro"]) == (None, [])


def test_shared_port_is_opened_once(bridge, backend):
    bridge.tick(force=True)
    assert backend.opened == ["LX Bridge 1"]
    assert bridge.ports.resolved == {"LX Bridge": "LX Bridge 1"}
    bridge.tick(force=True)
    assert backend.opened == ["LX Bridge 1"]


def test_both_sources_arrive_through_the_shared_port(bridge, backend, mock_console, caplog, h):
    bridge.tick(force=True)
    callback = backend.callbacks["LX Bridge 1"]
    callback(mido.Message("note_on", channel=14, note=1, velocity=127))
    callback(mido.Message("note_on", channel=15, note=2, velocity=127))
    mock_console.wait_for(2)
    lines = h.wait_lines(caplog, "gesendet", 2)
    assert "quelle=propresenter kanal=15 note=1" in lines[0]
    assert "quelle=ableton kanal=16 note=2" in lines[1]


def test_ambiguous_port_is_not_opened(bridge, backend, caplog, h):
    backend.names = ["LX Bridge 1", "LX Bridge 2"]
    bridge.tick(force=True)
    assert backend.opened == []
    line = h.wait_lines(caplog, "nicht eindeutig")[0]
    assert '"LX Bridge 1"' in line and '"LX Bridge 2"' in line


def test_port_loss_is_survived(bridge, backend, mock_console, caplog, h):
    bridge.tick(force=True)
    first = backend.handles["LX Bridge 1"]

    backend.names = []  # port vanishes
    bridge.tick(force=True)
    assert first.closed
    assert bridge.ports.open_ports == []
    h.wait_lines(caplog, "ist verschwunden, neuer Versuch alle 2 s")

    bridge.tick(force=True)  # still missing: tried again, logged only once
    bridge.tick(force=True)
    assert len(h.wait_lines(caplog, "nicht gefunden")) == 1
    assert backend.opened == ["LX Bridge 1"]

    backend.names = ["LX Bridge 1"]  # port is back
    bridge.tick(force=True)
    assert backend.opened == ["LX Bridge 1", "LX Bridge 1"]
    assert len(h.wait_lines(caplog, "geöffnet", 2)) == 2
    backend.callbacks["LX Bridge 1"](mido.Message("note_on", channel=14, note=2, velocity=90))
    (msg,) = mock_console.wait_for(1)
    assert msg.path == "/zeros/cue/go/10/2"
    assert bridge.worker_alive


def test_port_is_retried_on_the_interval(mapping_file, backend, caplog, h):
    caplog.set_level(logging.INFO, logger="midi_bridge")
    backend.names = []
    b = Bridge(load_mapping(mapping_file).mapping, backend, port_retry_s=0.2)
    runner = threading.Thread(target=b.run)
    runner.start()
    try:
        h.wait_lines(caplog, "nicht gefunden, neuer Versuch alle 0.2 s")
        time.sleep(0.3)
        assert backend.opened == []
        backend.names = ["LX Bridge 1"]
        h.wait_lines(caplog, "geöffnet", timeout=1.0)
        assert backend.opened == ["LX Bridge 1"]
    finally:
        b.request_stop()
        runner.join(3)


def test_listing_failure_does_not_crash(bridge, backend, caplog, h):
    bridge.tick(force=True)
    backend.fail_listing = True
    assert bridge.tick(force=True) is True
    assert bridge.tick(force=True) is True
    assert len(h.wait_lines(caplog, "MIDI-Eingänge nicht abfragbar")) == 1  # logged once
    assert not backend.handles["LX Bridge 1"].closed  # an open input may still work
    backend.fail_listing = False
    bridge.tick(force=True)
    assert backend.opened == ["LX Bridge 1"]


def test_listing_failure_at_start_is_logged_once(bridge, backend, caplog, h):
    backend.fail_listing = True
    for _ in range(3):
        assert bridge.tick(force=True) is True
    assert len(h.wait_lines(caplog, "nicht abfragbar")) == 1
    assert not [r for r in caplog.records if "nicht gefunden" in r.getMessage()]
    backend.fail_listing = False
    bridge.tick(force=True)
    assert backend.opened == ["LX Bridge 1"]


def test_open_failure_does_not_crash(bridge, backend, caplog, h):
    def refuse(name, callback):
        raise OSError("belegt")

    backend.open_input = refuse
    assert bridge.tick(force=True) is True
    h.wait_lines(caplog, "lässt sich nicht öffnen: belegt")


def test_port_change_in_mapping_closes_old_port(bridge, backend, mapping_file, mock_console, h):
    backend.names = ["LX Bridge 1", "Neuer Port"]
    bridge.tick(force=True)
    mapping_file.write_text(
        h.mapping_text(mock_console.port).replace('"LX Bridge"', '"Neuer Port"'), encoding="utf-8"
    )
    bridge.mapping_poll_s = 0.0
    bridge.tick(force=True)
    assert backend.handles["LX Bridge 1"].closed
    assert backend.opened == ["LX Bridge 1", "Neuer Port"]

"""Bridge logic without a real MIDI port: messages go straight into the queue,
OSC goes to the mock-console on 127.0.0.1."""

from __future__ import annotations

import dataclasses
import socket
import threading
import time

import pytest

from midi_bridge import MAX_AGE_S, PORT_RETRY_S, SEND_TIMEOUT_S, Bridge, load_mapping
from midi_bridge.mapping import Console
from zeros_osc import Status, TcpSlipClient

SETTLE = 0.3  # time to make sure no further message follows


def sent_paths(mock_console):
    return [m.path for m in mock_console.messages]


# --- one note, one message ----------------------------------------------------------


def test_one_note_gives_exactly_one_message(bridge, mock_console, caplog, h):
    bridge.queue.put(h.note_on(bridge, 15, 2))
    (msg,) = mock_console.wait_for(1)
    time.sleep(SETTLE)
    assert len(mock_console.messages) == 1
    assert msg.accepted and msg.path == "/zeros/cue/go/10/2" and msg.args == ()
    assert msg.status is Status.BELEGT
    (line,) = h.wait_lines(caplog, "gesendet")
    assert (
        'quelle=propresenter kanal=15 note=2 name="Musik ruhig" '
        "adresse=/zeros/cue/go/10/2 dauer_ms=" in line
    )
    elapsed = float(line.split("dauer_ms=")[1].split()[0])
    assert 0 <= elapsed < 1000
    assert line[:4].isdigit() and line[10] == " "  # receive time first


def test_only_note_on_with_velocity_triggers(bridge, mock_console, caplog, h):
    bridge.queue.put(h.note_on(bridge, 15, 2, kind="note_off"))
    bridge.queue.put(h.note_on(bridge, 15, 2, velocity=0))
    bridge.queue.put(h.note_on(bridge, 15, 2, kind="control_change"))
    bridge.queue.put(h.note_on(bridge, 15, 1))  # the only one that triggers
    mock_console.wait_for(1)
    time.sleep(SETTLE)
    assert sent_paths(mock_console) == ["/zeros/cue/go/10/1"]
    assert len(h.wait_lines(caplog, "kanal=")) == 1  # ignored messages leave no event line


def test_unknown_channel_and_unmapped_note_are_logged_not_sent(bridge, mock_console, caplog, h):
    bridge.queue.put(h.note_on(bridge, 3, 1))
    bridge.queue.put(h.note_on(bridge, 15, 99))
    bridge.queue.put(h.note_on(bridge, 15, 1, port="Anderes Gerät"))
    bridge.queue.put(h.note_on(bridge, 15, 1))
    mock_console.wait_for(1)
    time.sleep(SETTLE)
    assert sent_paths(mock_console) == ["/zeros/cue/go/10/1"]
    assert len(h.wait_lines(caplog, "ignoriert: keine Quelle")) == 2
    (line,) = h.wait_lines(caplog, "ignoriert: Note nicht im Mapping")
    assert "quelle=propresenter kanal=15 note=99" in line


def test_cue_limited_to_one_source(bridge, mock_console, caplog, h):
    bridge.queue.put(h.note_on(bridge, 15, 7))  # propresenter: not allowed
    bridge.queue.put(h.note_on(bridge, 16, 7))  # ableton: allowed
    mock_console.wait_for(1)
    time.sleep(SETTLE)
    assert sent_paths(mock_console) == ["/zeros/cue/go/10/7"]
    (line,) = h.wait_lines(caplog, "gesendet")
    assert "quelle=ableton kanal=16" in line


def test_dry_run_sends_nothing(mapping_file, backend, mock_console, caplog, h):
    import logging

    caplog.set_level(logging.INFO, logger="midi_bridge")
    b = Bridge(load_mapping(mapping_file).mapping, backend, dry_run=True)
    b.start()
    try:
        b.queue.put(h.note_on(b, 15, 2))
        (line,) = h.wait_lines(caplog, "DRY-RUN nicht gesendet")
        assert "adresse=/zeros/cue/go/10/2" in line and "dauer_ms=" in line
        time.sleep(SETTLE)
        assert mock_console.messages == []
        assert h.wait_lines(caplog, "DRY-RUN: es wird nichts gesendet")
    finally:
        b.stop()


# --- 5: debouncing with the receive time stamp ---------------------------------------


def test_debounce_same_note_same_channel(bridge, mock_console, caplog, h):
    t0 = bridge.clock()
    bridge.queue.put(h.note_on(bridge, 15, 2, t=t0))
    bridge.queue.put(h.note_on(bridge, 15, 2, t=t0 + 0.100))  # within 250 ms
    bridge.queue.put(h.note_on(bridge, 15, 2, t=t0 + 0.200))  # within 250 ms of the first
    bridge.queue.put(h.note_on(bridge, 15, 2, t=t0 + 0.300))  # 300 ms after the first
    mock_console.wait_for(2)
    time.sleep(SETTLE)
    assert len(mock_console.messages) == 2
    assert len(h.wait_lines(caplog, "entprellt", 2)) == 2


def test_debounce_is_per_channel_and_note(bridge, mock_console, h):
    t0 = bridge.clock()
    bridge.queue.put(h.note_on(bridge, 15, 2, t=t0))
    bridge.queue.put(h.note_on(bridge, 16, 2, t=t0 + 0.01))  # other channel
    bridge.queue.put(h.note_on(bridge, 15, 1, t=t0 + 0.02))  # other note
    mock_console.wait_for(3)
    time.sleep(SETTLE)
    assert len(mock_console.messages) == 3


def test_debounce_uses_receive_time_not_processing_time(bridge, mock_console, caplog, h):
    t0 = bridge.clock()
    bridge.queue.put(h.note_on(bridge, 15, 2, t=t0))
    mock_console.wait_for(1)
    time.sleep(0.4)  # processed 400 ms later, but received only 100 ms later
    bridge.queue.put(h.note_on(bridge, 15, 2, t=t0 + 0.1))
    h.wait_lines(caplog, "entprellt")
    # Two notes received 300 ms apart but processed back to back: both trigger.
    bridge.queue.put(h.note_on(bridge, 15, 1, t=bridge.clock() - 0.3))
    bridge.queue.put(h.note_on(bridge, 15, 1, t=bridge.clock()))
    mock_console.wait_for(3)
    time.sleep(SETTLE)
    assert len(mock_console.messages) == 3


# --- 2: maximum age ------------------------------------------------------------------


def test_note_older_than_two_seconds_is_discarded(bridge, mock_console, caplog, h):
    assert MAX_AGE_S == 2.0
    bridge.queue.put(h.note_on(bridge, 15, 2, t=bridge.clock() - 2.5))
    (line,) = h.wait_lines(caplog, "verworfen:")
    assert "adresse=/zeros/cue/go/10/2" in line and "nicht nachgesendet" in line
    bridge.queue.put(h.note_on(bridge, 15, 1, t=bridge.clock() - 1.5))  # young enough
    mock_console.wait_for(1)
    time.sleep(SETTLE)
    assert sent_paths(mock_console) == ["/zeros/cue/go/10/1"]


def test_stale_note_does_not_start_debounce(bridge, mock_console, caplog, h):
    bridge.max_age_s = 0.5
    t_first = bridge.clock() - 0.6
    bridge.queue.put(h.note_on(bridge, 15, 2, t=t_first))  # stale, discarded
    h.wait_lines(caplog, "verworfen:")
    bridge.max_age_s = 10.0
    bridge.queue.put(h.note_on(bridge, 15, 2, t=t_first + 0.1))  # within 250 ms of the stale one
    (msg,) = mock_console.wait_for(1)
    assert msg.path == "/zeros/cue/go/10/2"


def test_tcp_client_uses_send_timeout(bridge):
    client = bridge._client_for(Console("127.0.0.1", 9, "tcp-slip"))
    assert isinstance(client, TcpSlipClient)
    assert client.timeout == SEND_TIMEOUT_S


def test_send_failure_is_logged_and_bridge_continues(tmp_path, backend, caplog, h):
    import logging

    caplog.set_level(logging.INFO, logger="midi_bridge")
    closed = socket.socket()
    closed.bind(("127.0.0.1", 0))
    port = closed.getsockname()[1]
    closed.close()  # nothing listens here: TCP connect is refused
    path = tmp_path / "mapping.yaml"
    path.write_text(h.mapping_text(port, transport="tcp-slip"), encoding="utf-8")
    b = Bridge(load_mapping(path).mapping, backend)
    b.start()
    try:
        b.queue.put(h.note_on(b, 15, 2))
        b.queue.put(h.note_on(b, 15, 1))
        lines = h.wait_lines(caplog, "FEHLER beim Senden", 2)
        assert "adresse=/zeros/cue/go/10/2" in lines[0]
        assert b.worker_alive
    finally:
        b.stop()


# --- 1: try/except per message, dead worker is reported ---------------------------------


def test_exception_in_one_message_is_logged_and_next_is_sent(
    bridge, mock_console, caplog, h, monkeypatch
):
    real = bridge._client_for
    calls = []

    def flaky(console):
        calls.append(console)
        if len(calls) == 1:
            raise RuntimeError("kaputt")
        return real(console)

    monkeypatch.setattr(bridge, "_client_for", flaky)
    bridge.queue.put(h.note_on(bridge, 15, 2))
    bridge.queue.put(h.note_on(bridge, 15, 1))
    (line,) = h.wait_lines(caplog, "FEHLER bei der Verarbeitung")
    assert "kanal=15 note=2" in line and "kaputt" in line
    mock_console.wait_for(1)
    assert sent_paths(mock_console) == ["/zeros/cue/go/10/1"]
    assert bridge.worker_alive


def test_garbage_in_queue_does_not_kill_worker(bridge, mock_console, caplog, h):
    bridge.queue.put("kein MIDI")
    bridge.queue.put(h.note_on(bridge, 15, 1))
    h.wait_lines(caplog, "FEHLER bei der Verarbeitung")
    mock_console.wait_for(1)
    assert bridge.worker_alive


class Boom(BaseException):
    pass


def test_dead_worker_is_reported_once_and_run_ends(mapping_file, backend, caplog, h, monkeypatch):
    import logging

    caplog.set_level(logging.INFO, logger="midi_bridge")
    b = Bridge(load_mapping(mapping_file).mapping, backend)

    def explode(item):
        raise Boom("Thread stirbt")

    monkeypatch.setattr(b, "_process", explode)
    b.start()
    b.queue.put(h.note_on(b, 15, 2))
    deadline = time.monotonic() + 2
    while b.worker_alive and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not b.worker_alive
    assert b.check_worker() is False
    assert b.check_worker() is False
    assert b.run() == 1
    lines = h.wait_lines(caplog, "FEHLER: Verarbeitungs-Thread ist beendet")
    assert len(lines) == 1
    assert "Thread stirbt" in lines[0] and "sendet nichts mehr" in lines[0]
    assert all(
        r.levelname == "ERROR" for r in caplog.records if "Verarbeitungs-Thread" in r.message
    )


# --- 3: mapping swap ---------------------------------------------------------------------


def test_mapping_is_immutable(bridge):
    m = bridge.mapping
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.debounce_ms = 0  # type: ignore[misc]
    with pytest.raises(TypeError):
        m.cues[1] = m.cues[2]  # type: ignore[index]
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.cues[1].osc = "/zeros/macro/1"  # type: ignore[misc]


def test_hints_are_shown_at_start(bridge, caplog, h):
    (line,) = h.wait_lines(caplog, "Hinweis:")
    assert "/zeros/blackout/1" in line and "vermutet" in line


def test_reload_takes_new_mapping(bridge, mapping_file, mock_console, caplog, h):
    old = bridge.mapping
    mapping_file.write_text(
        h.mapping_text(mock_console.port, name2="Musik neu", osc2="/zeros/cue/go/10/22"),
        encoding="utf-8",
    )
    assert bridge.reload_mapping_if_changed() is True
    assert bridge.mapping is not old
    assert bridge.reload_mapping_if_changed() is False  # unchanged file: nothing to do
    h.wait_lines(caplog, "neu geladen")
    assert len(h.wait_lines(caplog, "Hinweis:", 2)) == 2  # hints again after reload
    bridge.queue.put(h.note_on(bridge, 15, 2))
    (msg,) = mock_console.wait_for(1)
    assert msg.path == "/zeros/cue/go/10/22"
    assert 'name="Musik neu"' in h.wait_lines(caplog, "gesendet")[0]


def test_broken_mapping_keeps_old_one(bridge, mapping_file, mock_console, caplog, h):
    old = bridge.mapping
    broken = h.mapping_text(mock_console.port) + '  - note: 1\n    name: "Doppelt"\n    osc: "/x"\n'
    mapping_file.write_text(broken, encoding="utf-8")
    assert bridge.reload_mapping_if_changed() is False
    assert bridge.mapping is old
    h.wait_lines(caplog, "fehlerhaft, das bisherige Mapping bleibt aktiv")
    assert h.wait_lines(caplog, "doppelte Note 1")
    assert h.wait_lines(caplog, "/x passt zu keinem Befehl")
    assert bridge.reload_mapping_if_changed() is False  # reported once per change
    assert len(h.wait_lines(caplog, "bleibt aktiv")) == 1
    bridge.queue.put(h.note_on(bridge, 15, 2))
    (msg,) = mock_console.wait_for(1)
    assert msg.path == "/zeros/cue/go/10/2"


def test_unreadable_yaml_keeps_old_one(bridge, mapping_file, caplog, h):
    old = bridge.mapping
    mapping_file.write_text("console: [\n", encoding="utf-8")
    assert bridge.reload_mapping_if_changed() is False
    assert bridge.mapping is old
    assert h.wait_lines(caplog, "YAML-Fehler")


def test_deleted_mapping_keeps_old_one(bridge, mapping_file, caplog, h):
    old = bridge.mapping
    mapping_file.unlink()
    assert bridge.reload_mapping_if_changed() is False
    assert bridge.mapping is old
    assert h.wait_lines(caplog, "Datei nicht lesbar")


def test_worker_reads_mapping_once_per_message(
    bridge, mapping_file, mock_console, caplog, h, monkeypatch
):
    """A swap in the middle of handling a message does not mix old and new."""
    new = load_mapping(mapping_file).mapping
    new = dataclasses.replace(
        new,
        cues=type(new.cues)(
            {**new.cues, 2: dataclasses.replace(new.cues[2], name="Neu", osc="/zeros/cue/go/10/9")}
        ),
    )
    real = bridge._client_for
    swapped = []

    def swap_during_send(console):
        if not swapped:
            bridge._mapping = new  # what reload_mapping_if_changed does
            swapped.append(True)
        return real(console)

    monkeypatch.setattr(bridge, "_client_for", swap_during_send)
    bridge.queue.put(h.note_on(bridge, 15, 2))
    first = mock_console.wait_for(1)[0]
    assert first.path == "/zeros/cue/go/10/2"
    assert 'name="Musik ruhig" adresse=/zeros/cue/go/10/2' in h.wait_lines(caplog, "gesendet")[0]
    bridge.queue.put(h.note_on(bridge, 15, 2, t=bridge.clock() + 1))  # past debounce
    second = mock_console.wait_for(2)[1]
    assert second.path == "/zeros/cue/go/10/9"


def test_reload_through_tick(bridge, mapping_file, mock_console, caplog, h):
    bridge.mapping_poll_s = 0.0
    mapping_file.write_text(
        h.mapping_text(mock_console.port, osc2="/zeros/cue/go/10/3"), encoding="utf-8"
    )
    assert bridge.tick() is True
    assert bridge.mapping.cues[2].osc == "/zeros/cue/go/10/3"


# --- 5: Ctrl+C discards waiting notes -------------------------------------------------------


def test_stop_discards_waiting_notes(bridge, mock_console, caplog, h, monkeypatch):
    release = threading.Event()
    entered = threading.Event()
    real = bridge._client_for

    class SlowClient:
        def __init__(self, inner):
            self.inner = inner

        def send(self, address):
            entered.set()
            release.wait(5)
            return self.inner.send(address)

    monkeypatch.setattr(bridge, "_client_for", lambda console: SlowClient(real(console)))
    bridge.queue.put(h.note_on(bridge, 15, 1))  # being sent while Ctrl+C comes
    assert entered.wait(2)
    bridge.queue.put(h.note_on(bridge, 15, 2))  # waiting
    bridge.queue.put(h.note_on(bridge, 16, 2))  # waiting
    stopper = threading.Thread(target=bridge.stop)
    stopper.start()
    deadline = time.monotonic() + 2
    while not bridge._stopping.is_set() and time.monotonic() < deadline:
        time.sleep(0.01)
    release.set()
    stopper.join(5)
    assert not bridge.worker_alive
    assert len(h.wait_lines(caplog, "verworfen: Bridge wird beendet", 2)) == 2
    time.sleep(SETTLE)
    assert sent_paths(mock_console) == ["/zeros/cue/go/10/1"]  # only the one already in flight


def test_keyboard_interrupt_in_run_closes_everything(bridge, backend, monkeypatch):
    bridge.tick(force=True)
    h_port = "LX Bridge 1"
    assert backend.opened == [h_port]
    calls = []

    def interrupted(force=False):
        calls.append(force)
        raise KeyboardInterrupt

    monkeypatch.setattr(bridge, "tick", interrupted)
    with pytest.raises(KeyboardInterrupt):
        bridge.run()
    assert backend.handles[h_port].closed
    assert not bridge.worker_alive


def test_request_stop_from_other_thread_ends_run(bridge, backend):
    result = []
    runner = threading.Thread(target=lambda: result.append(bridge.run()))
    runner.start()
    time.sleep(0.2)
    bridge.request_stop()
    runner.join(3)
    assert result == [0]
    assert backend.handles["LX Bridge 1"].closed


def test_port_retry_interval_is_two_seconds():
    assert PORT_RETRY_S == 2.0

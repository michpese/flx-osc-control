"""End to end: virtual MIDI port -> midi-bridge -> zeros-osc -> mock-console.

Needs a virtual MIDI port. rtmidi creates one on macOS (CoreMIDI) and on
Linux (ALSA, if /dev/snd/seq exists). On Windows rtmidi cannot create
virtual ports, so these tests are skipped there; the same logic is covered
without a real port in packages/midi-bridge/tests.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
import time

import pytest

mido = pytest.importorskip("mido")

from midi_bridge import Bridge, load_mapping  # noqa: E402

RETRY_S = 0.3  # faster than the 2 s default so the test does not wait long
SETTLE = 0.4

MAPPING = """\
console:
  host: 127.0.0.1
  port: {port}
  transport: udp
sources:
  propresenter:
    midi_port: "{midi_port}"
    channel: 15
debounce_ms: 200
cues:
  - note: 2
    name: "Musik ruhig"
    osc: "/zeros/cue/go/10/2"
"""


def _open_virtual(name: str):
    if sys.platform == "win32":
        pytest.skip("rtmidi kann unter Windows keine virtuellen MIDI-Ports anlegen (WinMM)")
    try:
        return mido.open_output(name, virtual=True)
    except Exception as exc:  # e.g. Linux without /dev/snd/seq
        pytest.skip(f"virtueller MIDI-Port nicht verfügbar: {exc}")


def _wait_input(tag: str, present: bool = True, timeout: float = 3.0) -> str | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        names = [n for n in mido.get_input_names() if tag in n]
        if present and names:
            return names[0]
        if not present and not names:
            return None
        time.sleep(0.05)
    raise AssertionError(f"input {tag!r} {'did not appear' if present else 'did not vanish'}")


def _lines(caplog, text: str) -> list[str]:
    records = list(caplog.get_records("setup")) + list(caplog.records)
    return [r.getMessage() for r in records if text in r.getMessage()]


def _wait_log(caplog, text: str, count: int = 1, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while len(_lines(caplog, text)) < count:
        if time.monotonic() > deadline:
            raise AssertionError(f"log line {text!r} x{count} missing")
        time.sleep(0.02)


@pytest.fixture
def setup(tmp_path, mock_console, caplog):
    caplog.set_level(logging.INFO, logger="midi_bridge")
    tag = f"LX E2E {os.getpid()} Test"  # no trailing digits, see midi_port below
    out = _open_virtual(tag)
    state = {"out": out}
    actual = _wait_input(tag)
    # The configured name is the start of the input name; strip a trailing
    # client/port number the system may add (it can change on re-creation).
    midi_port = re.sub(r"\s+\d+(:\d+)?$", "", actual)
    path = tmp_path / "mapping.yaml"
    path.write_text(MAPPING.format(port=mock_console.port, midi_port=midi_port), encoding="utf-8")
    bridge = Bridge(load_mapping(path).mapping, port_retry_s=RETRY_S)
    runner = threading.Thread(target=bridge.run, daemon=True)
    runner.start()
    _wait_log(caplog, "geöffnet")
    yield bridge, state, tag, runner
    bridge.request_stop()
    runner.join(5)
    state["out"].close()


def _note(out, note=2, channel=15):
    out.send(mido.Message("note_on", channel=channel - 1, note=note, velocity=100))


def test_one_note_gives_exactly_one_message(setup, mock_console):
    bridge, state, _, _ = setup
    _note(state["out"])
    (msg,) = mock_console.wait_for(1)
    time.sleep(SETTLE)
    assert len(mock_console.messages) == 1
    assert msg.accepted and msg.path == "/zeros/cue/go/10/2"


def test_debounce(setup, mock_console):
    _, state, _, _ = setup
    for _ in range(3):
        _note(state["out"])
    mock_console.wait_for(1)
    time.sleep(SETTLE)  # longer than debounce_ms
    assert len(mock_console.messages) == 1
    _note(state["out"])
    mock_console.wait_for(2)
    time.sleep(SETTLE)
    assert len(mock_console.messages) == 2


def test_port_loss_is_survived(setup, mock_console, caplog):
    bridge, state, tag, runner = setup
    state["out"].close()
    _wait_input(tag, present=False)
    _wait_log(caplog, "ist verschwunden")
    state["out"] = _open_virtual(tag)
    _wait_input(tag)
    _wait_log(caplog, "geöffnet", count=2)
    assert runner.is_alive() and bridge.worker_alive
    _note(state["out"])
    (msg,) = mock_console.wait_for(1, timeout=3.0)
    assert msg.path == "/zeros/cue/go/10/2"

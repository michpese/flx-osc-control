"""Shared fixtures for midi-bridge tests without a real MIDI port.

Messages are put straight into ``bridge.queue`` (or through the fake
backend's callback); OSC goes to the mock-console on 127.0.0.1.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import mido
import pytest

from midi_bridge import Bridge, Incoming, load_mapping

PORT = "LX Bridge 1"  # how loopMIDI's "LX Bridge" shows up on Windows

MAPPING_TEMPLATE = """\
console:
  host: 127.0.0.1
  port: {port}
  transport: {transport}
sources:
  propresenter:
    midi_port: "LX Bridge"
    channel: 15
  ableton:
    midi_port: "LX Bridge"
    channel: 16
debounce_ms: {debounce}
cues:
  - note: 1
    name: "Einlass"
    osc: "/zeros/cue/go/10/1"
  - note: 2
    name: "{name2}"
    osc: "{osc2}"
  - note: 5
    name: "Blackout"
    osc: "/zeros/blackout/1"
  - note: 7
    name: "Nur Ableton"
    osc: "/zeros/cue/go/10/7"
    sources: [ableton]
"""


def mapping_text(port: int, **kw: object) -> str:
    values = {
        "port": port,
        "transport": "udp",
        "debounce": 250,
        "name2": "Musik ruhig",
        "osc2": "/zeros/cue/go/10/2",
    }
    values.update(kw)
    return MAPPING_TEMPLATE.format(**values)


class FakeHandle:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeBackend:
    """Stands in for mido/rtmidi: a list of input names and the callbacks."""

    def __init__(self, names: list[str] | None = None) -> None:
        self.names = list(names if names is not None else [PORT])
        self.opened: list[str] = []
        self.handles: dict[str, FakeHandle] = {}
        self.callbacks: dict[str, object] = {}
        self.fail_listing = False

    def input_names(self) -> list[str]:
        if self.fail_listing:
            raise OSError("MIDI-Dienst weg")
        return list(self.names)

    def open_input(self, name, callback):
        self.opened.append(name)
        handle = FakeHandle()
        self.handles[name] = handle
        self.callbacks[name] = callback
        return handle


def note_on(
    bridge: Bridge,
    channel: int,
    note: int,
    velocity: int = 100,
    *,
    port: str = PORT,
    t: float | None = None,
    kind: str = "note_on",
) -> Incoming:
    if kind in ("note_on", "note_off"):
        msg = mido.Message(kind, channel=channel - 1, note=note, velocity=velocity)
    else:
        msg = mido.Message("control_change", channel=channel - 1, control=note, value=velocity)
    from datetime import datetime

    return Incoming(msg, port, bridge.clock() if t is None else t, datetime.now())


def wait_lines(caplog, text: str, count: int = 1, timeout: float = 3.0) -> list[str]:
    """Wait until ``count`` log lines contain ``text``; return them."""
    deadline = time.monotonic() + timeout
    while True:
        records = list(caplog.get_records("setup")) + list(caplog.records)
        lines = [r.getMessage() for r in records if text in r.getMessage()]
        if len(lines) >= count:
            return lines
        if time.monotonic() > deadline:
            raise AssertionError(f"{len(lines)} of {count} log lines with {text!r}")
        time.sleep(0.01)


@pytest.fixture
def mapping_file(tmp_path, mock_console) -> Path:
    path = tmp_path / "mapping.yaml"
    path.write_text(mapping_text(mock_console.port), encoding="utf-8")
    return path


@pytest.fixture
def backend() -> FakeBackend:
    return FakeBackend()


@pytest.fixture
def bridge(mapping_file, backend, caplog):
    caplog.set_level(logging.INFO, logger="midi_bridge")
    result = load_mapping(mapping_file)
    assert result.mapping is not None, result.errors
    b = Bridge(result.mapping, backend)
    b.start()
    yield b
    b.stop()


@pytest.fixture
def h():
    """Helpers for test modules (conftest.py cannot be imported with importlib mode)."""
    from types import SimpleNamespace

    return SimpleNamespace(
        PORT=PORT,
        FakeBackend=FakeBackend,
        mapping_text=mapping_text,
        note_on=note_on,
        wait_lines=wait_lines,
    )

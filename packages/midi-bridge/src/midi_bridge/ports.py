"""MIDI input ports: backend access and the port manager.

The port manager runs in the main thread. It opens every configured port
once (sources sharing a port share one input), notices when a port has
disappeared and tries to open it again on every check. Port names come only
from the configuration; a configured name matches the input whose name
starts with it.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Protocol

from .mapping import port_matches

log = logging.getLogger("midi_bridge")

PortCallback = Callable[[Any], None]


class InputHandle(Protocol):
    def close(self) -> None: ...


class MidiBackend(Protocol):
    def input_names(self) -> list[str]: ...

    def open_input(self, name: str, callback: PortCallback) -> InputHandle: ...


class MidoBackend:
    """Real MIDI access through mido with python-rtmidi."""

    def input_names(self) -> list[str]:
        import mido

        # dict.fromkeys: some systems list the same port twice
        return list(dict.fromkeys(mido.get_input_names()))

    def open_input(self, name: str, callback: PortCallback) -> InputHandle:
        import mido

        return mido.open_input(name, callback=callback)


def resolve_port(configured: str, available: list[str]) -> tuple[str | None, list[str]]:
    """Find the input for a configured name.

    An exact match wins. Otherwise exactly one input must start with the
    configured name. Returns (name, []) or (None, candidates).
    """
    if configured in available:
        return configured, []
    candidates = [name for name in available if port_matches(configured, name)]
    if len(candidates) == 1:
        return candidates[0], []
    return None, candidates


class PortManager:
    """Keeps the configured inputs open. Not thread-safe: main thread only."""

    def __init__(
        self,
        backend: MidiBackend,
        make_callback: Callable[[str], PortCallback],
        emit: Callable[[str], None],
        retry_s: float = 2.0,
    ) -> None:
        self.backend = backend
        self.retry_s = retry_s
        self.make_callback = make_callback  # actual port name -> callback
        self.emit = emit  # writes one status line to the log
        self._open: dict[str, InputHandle] = {}  # actual name -> handle
        self._resolved: dict[str, str] = {}  # configured name -> actual name
        self._last_problem: dict[str, str] = {}  # configured name -> last logged problem

    @property
    def open_ports(self) -> list[str]:
        return list(self._open)

    @property
    def resolved(self) -> dict[str, str]:
        return dict(self._resolved)

    def check(self, wanted: tuple[str, ...]) -> None:
        """Close vanished or unneeded inputs and try to open missing ones."""
        try:
            available = self.backend.input_names()
        except Exception as exc:  # backend trouble must not stop the bridge
            # Keep open inputs (they may still work) and open nothing new.
            self._problem_all(wanted, f"MIDI-Eingänge nicht abfragbar: {exc}")
            return

        # 1. close inputs that vanished
        for actual in list(self._open):
            if actual not in available:
                self._close(actual)
                self.emit(f'MIDI-Port "{actual}" ist verschwunden{self._retry_text}')

        # 2. forget resolutions that are no longer wanted or no longer open
        for configured in list(self._resolved):
            if configured not in wanted or self._resolved[configured] not in self._open:
                del self._resolved[configured]

        # 3. open what is missing
        for configured in wanted:
            if configured in self._resolved:
                continue
            actual, candidates = resolve_port(configured, available)
            if actual is None:
                if candidates:
                    self._problem(
                        configured,
                        f'MIDI-Port "{configured}" ist nicht eindeutig: '
                        + ", ".join(f'"{c}"' for c in candidates),
                    )
                else:
                    self._problem(configured, f'MIDI-Port "{configured}" nicht gefunden')
                continue
            if actual not in self._open:
                try:
                    self._open[actual] = self.backend.open_input(actual, self.make_callback(actual))
                except Exception as exc:
                    self._problem(
                        configured, f'MIDI-Port "{actual}" lässt sich nicht öffnen: {exc}'
                    )
                    continue
                self.emit(f'MIDI-Port "{actual}" geöffnet')
            self._resolved[configured] = actual
            self._last_problem.pop(configured, None)

        # 4. close inputs nobody needs any more (e.g. after a mapping change)
        needed = set(self._resolved.values())
        for actual in list(self._open):
            if actual not in needed:
                self._close(actual)
                self.emit(f'MIDI-Port "{actual}" geschlossen, nicht mehr im Mapping')

    @property
    def _retry_text(self) -> str:
        return f", neuer Versuch alle {self.retry_s:g} s"

    def close_all(self) -> None:
        for actual in list(self._open):
            self._close(actual)
        self._resolved.clear()

    def _close(self, actual: str) -> None:
        handle = self._open.pop(actual)
        try:
            handle.close()
        except Exception as exc:
            log.debug("closing %s failed: %s", actual, exc)

    def _problem(self, configured: str, text: str) -> None:
        # Log a problem once; retries continue silently until it changes.
        if self._last_problem.get(configured) != text:
            self._last_problem[configured] = text
            self.emit(f"{text}{self._retry_text}")

    def _problem_all(self, wanted: tuple[str, ...], text: str) -> None:
        for configured in wanted:
            self._problem(configured, text)

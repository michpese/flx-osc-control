"""UDP listener that records and judges every OSC message, like an FLX S24 would.

The mock never answers, just like the real console.
"""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import IO

from zeros_osc import DEFAULT_PORT, Status

from .evaluate import ParsedMessage, Reason, evaluate_packet

log = logging.getLogger("mock_console")

MAX_DATAGRAM = 65535
POLL_INTERVAL = 0.1  # seconds; how quickly stop() is noticed


@dataclass(frozen=True)
class Received:
    """One received OSC message with its verdict."""

    time: datetime  # local time, timezone-aware
    sender: str  # "ip:port"
    address: str
    args: tuple[object, ...]
    accepted: bool
    reason: Reason | None
    detail: str
    command_id: str | None
    status: Status | None
    path: str | None  # normalised path form, e.g. /zeros/cue/go/1/5
    values: tuple[str, ...]
    notes: tuple[str, ...]
    bundle_timetag: int | None

    @classmethod
    def from_parsed(cls, parsed: ParsedMessage, sender: str, when: datetime) -> Received:
        v = parsed.verdict
        return cls(
            time=when,
            sender=sender,
            address=parsed.address,
            args=parsed.args,
            accepted=v.accepted,
            reason=v.reason,
            detail=v.detail,
            command_id=v.command_id,
            status=v.status,
            path=v.path,
            values=v.values,
            notes=v.notes,
            bundle_timetag=parsed.bundle_timetag,
        )

    @property
    def ignored(self) -> bool:
        return not self.accepted

    def to_dict(self) -> dict[str, object]:
        return {
            "time": self.time.isoformat(timespec="milliseconds"),
            "sender": self.sender,
            "address": self.address,
            "args": [_jsonable(a) for a in self.args],
            "result": "accepted" if self.accepted else "ignored",
            "reason": self.reason.value if self.reason else None,
            "detail": self.detail,
            "command": self.command_id,
            "status": self.status.value if self.status else None,
            "path": self.path,
            "values": list(self.values),
            "notes": list(self.notes),
            "bundle_timetag": self.bundle_timetag,
        }

    def log_line(self) -> str:
        # One line per event: timestamp, source, channel, note, name, address (CLAUDE.md).
        # Channel, note and name belong to the MIDI side and are unknown here.
        ts = self.time.strftime("%Y-%m-%d %H:%M:%S.") + f"{self.time.microsecond // 1000:03d}"
        args = json.dumps([_jsonable(a) for a in self.args], ensure_ascii=False)
        line = (
            f"{ts} quelle={self.sender} kanal=- note=- name=- "
            f"adresse={self.address or '-'} argumente={args}"
        )
        if self.bundle_timetag is not None:
            line += f" bundle=0x{self.bundle_timetag:016x}"
        if self.accepted:
            assert self.status is not None
            line += (
                f" akzeptiert befehl={self.command_id} pfad={self.path} status={self.status.value}"
            )
        else:
            assert self.reason is not None
            line += f" ignoriert grund={self.reason.value} ({self.detail})"
        for note in self.notes:
            line += f" HINWEIS: {note}"
        return line


def _jsonable(value: object) -> object:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return repr(value)


class MockConsole:
    """Stand-in for the FLX S24: listens on UDP, logs and judges every message.

    Use as a context manager or call ``start()`` / ``stop()``. ``port=0`` picks
    a free port; the actual port is in ``.port`` after ``start()``.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = DEFAULT_PORT,
        jsonl: str | Path | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.jsonl = Path(jsonl) if jsonl is not None else None
        self._messages: list[Received] = []
        self._cond = threading.Condition()
        self._stop = threading.Event()
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._jsonl_file: IO[str] | None = None

    # --- lifecycle ---------------------------------------------------------------

    def start(self) -> MockConsole:
        if self._thread is not None:
            raise RuntimeError("mock console already running")
        family = socket.AF_INET6 if ":" in self.host else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_DGRAM)
        try:
            sock.bind((self.host, self.port))
        except OSError:
            sock.close()
            raise
        sock.settimeout(POLL_INTERVAL)
        self._sock = sock
        self.port = sock.getsockname()[1]
        if self.jsonl is not None:
            self._jsonl_file = self.jsonl.open("a", encoding="utf-8")
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="mock-console", daemon=True)
        self._thread.start()
        log.info("mock-console lauscht auf %s:%d/udp", self.host, self.port)
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5 * POLL_INTERVAL + 1.0)
            self._thread = None
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        if self._jsonl_file is not None:
            self._jsonl_file.close()
            self._jsonl_file = None

    def __enter__(self) -> MockConsole:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def serve_forever(self) -> None:
        """Block until KeyboardInterrupt (used by the CLI)."""
        if self._thread is None:
            self.start()
        try:
            while not self._stop.wait(0.5):
                pass
        finally:
            self.stop()

    # --- results -----------------------------------------------------------------

    @property
    def messages(self) -> list[Received]:
        """Copy of all messages received so far, in order of arrival."""
        with self._cond:
            return list(self._messages)

    @property
    def accepted(self) -> list[Received]:
        return [m for m in self.messages if m.accepted]

    @property
    def ignored(self) -> list[Received]:
        return [m for m in self.messages if m.ignored]

    def clear(self) -> None:
        with self._cond:
            self._messages.clear()

    def wait_for(self, count: int = 1, timeout: float = 2.0) -> list[Received]:
        """Wait until at least ``count`` messages arrived; return all of them.

        Raises ``TimeoutError`` if they do not arrive in time.
        """
        deadline = time.monotonic() + timeout
        with self._cond:
            while len(self._messages) < count:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        f"mock-console: {len(self._messages)} von {count} Nachrichten "
                        f"nach {timeout} s empfangen"
                    )
                self._cond.wait(remaining)
            return list(self._messages)

    # --- receive loop ------------------------------------------------------------

    def _run(self) -> None:
        assert self._sock is not None
        sock = self._sock
        while not self._stop.is_set():
            try:
                data, addr = sock.recvfrom(MAX_DATAGRAM)
            except TimeoutError:
                continue
            except ConnectionResetError:
                # Windows reports ICMP "port unreachable" of earlier packets here.
                continue
            except OSError:
                if self._stop.is_set():
                    break
                raise
            try:
                self.handle_datagram(data, f"{addr[0]}:{addr[1]}")
            except Exception:  # keep receiving whatever one datagram does
                log.exception(
                    "mock-console: FEHLER bei einem Paket von %s, Empfang läuft weiter", addr[0]
                )

    def handle_datagram(self, data: bytes, sender: str) -> list[Received]:
        """Judge, log and store one datagram. Public so tests can feed bytes directly."""
        when = datetime.now().astimezone()
        records = [Received.from_parsed(p, sender, when) for p in evaluate_packet(data)]
        for record in records:
            log.info("%s", record.log_line())
            if self._jsonl_file is not None:
                self._jsonl_file.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
                self._jsonl_file.flush()
        with self._cond:
            self._messages.extend(records)
            self._cond.notify_all()
        return records

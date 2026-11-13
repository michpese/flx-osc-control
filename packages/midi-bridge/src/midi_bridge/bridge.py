"""The bridge: MIDI note in, ZerOS OSC address out (sent through zeros-osc).

Threads:

* MIDI callback threads (one per open input, owned by rtmidi): stamp the
  receive time and put the message into ``queue``. Nothing else.
* Worker thread (exactly one): takes messages in order, filters, looks up
  source and cue, discards stale notes, debounces, sends, logs. Each message
  is handled inside its own try/except.
* Main thread (``run``): every ``mapping_poll_s`` checks mapping.yaml for
  changes, every ``port_retry_s`` checks the MIDI inputs, and on every tick
  checks that the worker is still alive.

The mapping is an immutable object. A reload checks the new file completely
and then replaces the reference with one assignment; the worker reads the
reference once per message.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from zeros_osc import TcpSlipClient, UdpClient, ZerosValueError

from .mapping import Console, Mapping, file_signature, load_mapping
from .ports import MidiBackend, MidoBackend, PortManager

log = logging.getLogger("midi_bridge")

PORT_RETRY_S = 2.0  # requirement: reopen a vanished port every two seconds
MAPPING_POLL_S = 1.0
MAX_AGE_S = 2.0  # notes older than this when processed are discarded, never sent late
SEND_TIMEOUT_S = 1.0  # TCP connect/send timeout; UDP does not block
TICK_S = 0.1
STOP_JOIN_S = 5.0


@dataclass(frozen=True)
class Incoming:
    """One MIDI message as put into the queue by the port callback."""

    message: Any  # mido.Message
    port: str  # actual input name
    t_recv: float  # bridge clock (time.perf_counter) at reception
    received_at: datetime  # wall clock at reception, for the log


_STOP = object()


def _ts(when: datetime) -> str:
    return when.strftime("%Y-%m-%d %H:%M:%S.") + f"{when.microsecond // 1000:03d}"


class Bridge:
    def __init__(
        self,
        mapping: Mapping,
        backend: MidiBackend | None = None,
        *,
        dry_run: bool = False,
        port_retry_s: float = PORT_RETRY_S,
        mapping_poll_s: float = MAPPING_POLL_S,
        max_age_s: float = MAX_AGE_S,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._mapping = mapping
        self.dry_run = dry_run
        self.port_retry_s = port_retry_s
        self.mapping_poll_s = mapping_poll_s
        self.max_age_s = max_age_s
        self.clock = clock
        self.queue: queue.SimpleQueue[Any] = queue.SimpleQueue()
        self.ports = PortManager(
            backend if backend is not None else MidoBackend(),
            self._make_callback,
            self._status,
            retry_s=port_retry_s,
        )
        self._mapping_signature = file_signature(mapping.path)
        self._last_trigger: dict[tuple[int, int], float] = {}  # worker only
        self._client: UdpClient | TcpSlipClient | None = None  # worker only
        self._client_target: Console | None = None  # worker only
        self._stopping = threading.Event()
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._worker_error: BaseException | None = None
        self._worker_reported = False
        self._next_mapping_check = 0.0
        self._next_port_check = 0.0

    # --- public state ------------------------------------------------------------

    @property
    def mapping(self) -> Mapping:
        return self._mapping

    @property
    def worker_alive(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    # --- lifecycle ---------------------------------------------------------------

    def start(self) -> None:
        """Start the worker thread and log the start-up information."""
        if self._worker is not None:
            return
        m = self._mapping
        target = f"{m.console.host}:{m.console.port}/{m.console.transport}"
        self._status(
            f"läuft, Mapping {m.path}, Ziel {target}, debounce_ms={m.debounce_ms:g}"
            + (", DRY-RUN: es wird nichts gesendet" if self.dry_run else "")
        )
        self._show_hints(m)
        self._worker = threading.Thread(target=self._worker_main, name="bridge-worker", daemon=True)
        self._worker.start()

    def run(self) -> int:
        """Run until ``request_stop()`` or Ctrl+C. Returns 0, or 1 if the worker died.

        Ports are opened, checked and closed only in the thread that calls ``run``.
        """
        self.start()
        try:
            if not self.tick(force=True):
                return 1
            while not self._stop_event.wait(TICK_S):
                if not self.tick():
                    return 1
            return 0
        finally:
            self.stop()

    def request_stop(self) -> None:
        """Ask ``run`` to end; safe to call from any thread."""
        self._stop_event.set()

    def stop(self) -> None:
        """Close the inputs, discard waiting notes, end the worker. Idempotent.

        Call it from the thread that runs ``run`` (``run`` does so itself on exit).
        """
        if self._stopping.is_set():
            return
        self._stopping.set()
        self._stop_event.set()
        self.ports.close_all()
        self.queue.put(_STOP)
        if self._worker is not None:
            self._worker.join(STOP_JOIN_S)
        self._status("beendet")

    # --- main thread ---------------------------------------------------------------

    def tick(self, force: bool = False) -> bool:
        """One round of the main loop. Returns False if the worker is dead."""
        if not self.check_worker():
            return False
        now = time.monotonic()
        if force or now >= self._next_mapping_check:
            self._next_mapping_check = now + self.mapping_poll_s
            self.reload_mapping_if_changed()
        if force or now >= self._next_port_check:
            self._next_port_check = now + self.port_retry_s
            self.ports.check(self._mapping.midi_ports)
        return True

    def check_worker(self) -> bool:
        """True while the worker runs. Reports a dead worker once, loudly."""
        if self._worker is None or self._worker.is_alive() or self._stopping.is_set():
            return True
        if not self._worker_reported:
            self._worker_reported = True
            cause = repr(self._worker_error) if self._worker_error else "ohne Fehlermeldung"
            log.error(
                "%s midi-bridge: FEHLER: Verarbeitungs-Thread ist beendet (%s). "
                "Die Bridge sendet nichts mehr und beendet sich. Licht von Hand fahren.",
                _ts(datetime.now()),
                cause,
            )
        return False

    def reload_mapping_if_changed(self) -> bool:
        """Load mapping.yaml again if it changed. Returns True if a new mapping is active."""
        path = self._mapping.path
        signature = file_signature(path)
        if signature == self._mapping_signature:
            return False
        self._mapping_signature = signature
        result = load_mapping(path)
        if result.mapping is None:
            self._status(
                f"mapping.yaml fehlerhaft, das bisherige Mapping bleibt aktiv "
                f"({len(result.errors)} Fehler)"
            )
            for error in result.errors:
                self._status(f"Fehler: {error}")
            return False
        self._mapping = result.mapping  # the single assignment that swaps the mapping
        self._status(f"mapping.yaml neu geladen, {len(result.mapping.cues)} Einträge")
        self._show_hints(result.mapping)
        return True

    # --- MIDI callback (rtmidi thread) ---------------------------------------------

    def _make_callback(self, port: str) -> Callable[[Any], None]:
        put = self.queue.put
        clock = self.clock

        def callback(message: Any) -> None:
            put(Incoming(message, port, clock(), datetime.now()))

        return callback

    # --- worker thread ---------------------------------------------------------------

    def _worker_main(self) -> None:
        try:
            self._worker_loop()
        except BaseException as exc:  # reported by check_worker() in the main thread
            self._worker_error = exc
        finally:
            self._close_client()

    def _worker_loop(self) -> None:
        while True:
            item = self.queue.get()
            if item is _STOP:
                return
            if self._stopping.is_set():
                self._discard_on_stop(item)
                continue
            try:
                self._process(item)
            except Exception as exc:
                self._error_line(item, exc)

    def _process(self, item: Incoming) -> None:
        mapping = self._mapping  # read the reference exactly once per message
        msg = item.message
        if msg.type != "note_on" or msg.velocity <= 0:
            return  # Note Off, velocity 0 and everything else are ignored
        channel = msg.channel + 1
        note = msg.note

        source = mapping.source_for(item.port, channel)
        if source is None:
            self._event(item, channel, note, outcome=f'ignoriert: keine Quelle für "{item.port}"')
            return
        cue = mapping.cues.get(note)
        if cue is None or not cue.allows(source.name):
            self._event(
                item, channel, note, source.name, outcome="ignoriert: Note nicht im Mapping"
            )
            return

        args = (item, channel, note, source.name, cue.name, cue.osc)
        age = self.clock() - item.t_recv
        if age > self.max_age_s:
            self._event(*args, outcome=f"verworfen: {age:.1f} s alt, nicht nachgesendet")
            return

        key = (channel, note)
        last = self._last_trigger.get(key)
        if last is not None and item.t_recv - last < mapping.debounce_ms / 1000:
            self._event(*args, outcome="entprellt")
            return
        self._last_trigger[key] = item.t_recv

        if self.dry_run:
            self._event(*args, elapsed=self._elapsed(item), outcome="DRY-RUN nicht gesendet")
            return
        try:
            self._client_for(mapping.console).send(cue.osc)
        except (OSError, ZerosValueError) as exc:
            self._close_client()  # a broken connection is rebuilt on the next note
            self._event(*args, elapsed=self._elapsed(item), outcome=f"FEHLER beim Senden: {exc}")
            return
        self._event(*args, elapsed=self._elapsed(item), outcome="gesendet")

    def _elapsed(self, item: Incoming) -> float:
        return (self.clock() - item.t_recv) * 1000

    def _client_for(self, console: Console) -> UdpClient | TcpSlipClient:
        if self._client is None or self._client_target != console:
            self._close_client()
            if console.transport == "tcp-slip":
                self._client = TcpSlipClient(console.host, console.port, timeout=SEND_TIMEOUT_S)
            else:
                self._client = UdpClient(console.host, console.port)
            self._client_target = console
        return self._client

    def _close_client(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except OSError:
                pass
        self._client = None
        self._client_target = None

    def _discard_on_stop(self, item: Any) -> None:
        msg = getattr(item, "message", None)
        if getattr(msg, "type", None) == "note_on" and msg.velocity > 0:
            self._event(item, msg.channel + 1, msg.note, outcome="verworfen: Bridge wird beendet")

    def _error_line(self, item: Any, exc: Exception) -> None:
        try:
            msg = item.message
            self._event(
                item,
                getattr(msg, "channel", -1) + 1,
                getattr(msg, "note", "-"),
                outcome=f"FEHLER bei der Verarbeitung: {exc!r}",
            )
        except Exception:
            log.error("%s midi-bridge: FEHLER bei der Verarbeitung: %r", _ts(datetime.now()), exc)

    # --- log lines -------------------------------------------------------------------

    def _event(
        self,
        item: Incoming,
        channel: object,
        note: object,
        source: str = "-",
        name: str | None = None,
        address: str = "-",
        *,
        elapsed: float | None = None,
        outcome: str,
    ) -> None:
        # One line per event: receive time, source, channel, note, name, address,
        # time from reception to sending in ms (CLAUDE.md, requirement 6).
        name_text = f'"{name}"' if name is not None else "-"
        elapsed_text = f"{elapsed:.1f}" if elapsed is not None else "-"
        log.info(
            "%s quelle=%s kanal=%s note=%s name=%s adresse=%s dauer_ms=%s %s",
            _ts(item.received_at),
            source,
            channel,
            note,
            name_text,
            address,
            elapsed_text,
            outcome,
        )

    def _status(self, text: str) -> None:
        log.info("%s midi-bridge: %s", _ts(datetime.now()), text)

    def _show_hints(self, mapping: Mapping) -> None:
        for hint in mapping.warnings:
            self._status(f"Hinweis: {hint}")

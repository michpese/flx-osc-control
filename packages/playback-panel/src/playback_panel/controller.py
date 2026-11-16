"""Headless playback controller that sends ZerOS OSC commands via ``zeros_osc``.

Separates business logic, file change tracking and structured logging from the
Tkinter view so everything can be tested deterministically against ``mock-console``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, TextIO

from zeros_osc import ZerosValueError, address_warnings, make_client, match_address
from zeros_osc.client import Client

from .config import ButtonConfig, CheckResult, PanelConfig, load_config, save_config
from .state import append_event_log

ButtonSide = Literal["on", "off"]


@dataclass(frozen=True)
class LogEntry:
    """A single structured log event."""

    timestamp: str
    button_name: str
    side: ButtonSide
    address: str
    target: str
    outcome: str
    ok: bool
    line: str
    warnings: tuple[str, ...] = ()


def format_log_line(name: str, address: str, target: str, outcome: str) -> str:
    """Format one event line per CLAUDE.md (timestamp, source, channel, note, name, address)."""
    ts = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    safe_name = name.replace('"', "'")
    return (
        f'{ts} quelle=flx-panel kanal=- note=- name="{safe_name}" '
        f"adresse={address} ziel={target} {outcome}"
    )


def _file_sha256(path: Path) -> bytes | None:
    try:
        return hashlib.sha256(path.read_bytes()).digest()
    except OSError:
        return None


class PanelController:
    """Manage a ``PanelConfig``, ``zeros_osc`` transport client, and button state."""

    def __init__(
        self,
        config: PanelConfig | None = None,
        *,
        config_path: str | Path | None = None,
        dry_run: bool = False,
        out: TextIO | None = None,
        app_data_dir: Path | None = None,
        on_log: Callable[[LogEntry], None] | None = None,
    ) -> None:
        self.config: PanelConfig = config or PanelConfig()
        self.config_path: Path | None = Path(config_path) if config_path else None
        self.dry_run = dry_run
        self._out = out
        self._app_data_dir = app_data_dir
        self._on_log = on_log

        self._client: Client | None = None
        self._client_key: tuple[str, int, str] | None = None
        self._file_digest: bytes | None = (
            _file_sha256(self.config_path) if self.config_path else None
        )
        # Local last-sent state per active button index: "on", "off", or None.
        self.button_states: dict[int, ButtonSide | None] = {}
        self.history: list[LogEntry] = []

    @property
    def target_label(self) -> str:
        c = self.config.console
        return f"{c.host}:{c.port}/{c.transport}"

    def _get_client(self) -> Client:
        c = self.config.console
        key = (c.host, c.port, c.transport)
        if self._client is None or self._client_key != key:
            self.close()
            self._client = make_client(c.host, c.port, c.transport)
            self._client_key = key
        return self._client

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None
                self._client_key = None

    def __enter__(self) -> PanelController:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- Config lifecycle -----------------------------------------------------

    def set_config(self, config: PanelConfig, path: str | Path | None = None) -> None:
        """Apply a new ``PanelConfig`` and reset button states if button count changed."""
        old_count = len(self.config.active_buttons)
        self.config = config
        if path is not None:
            self.config_path = Path(path)
        if self.config_path is not None:
            self._file_digest = _file_sha256(self.config_path)
        if len(config.active_buttons) != old_count:
            self.button_states.clear()
        # Re-open transport socket lazily on next send if console target changed.
        c = config.console
        if self._client_key is not None and self._client_key != (c.host, c.port, c.transport):
            self.close()

    def load_from_file(self, path: str | Path) -> CheckResult:
        target = Path(path)
        config, result = load_config(target)
        self.set_config(config, target)
        return result

    def save_to_file(
        self, config: PanelConfig | None = None, path: str | Path | None = None
    ) -> Path:
        cfg = config or self.config
        target = Path(path) if path is not None else self.config_path
        if target is None:
            raise ZerosValueError("Kein Dateipfad zum Speichern angegeben")
        save_config(cfg, target)
        self.set_config(cfg, target)
        return target

    def reload_if_changed(self) -> tuple[bool, str | None]:
        """Reload ``config_path`` if its content hash changed on disk.

        Returns ``(reloaded, error_message)``. On invalid edits on disk, keeps the
        current active configuration running (same resilience principle as midi-bridge).
        """
        if self.config_path is None or not self.config_path.exists():
            return False, None
        digest = _file_sha256(self.config_path)
        if digest is None or digest == self._file_digest:
            return False, None
        self._file_digest = digest
        try:
            config, _ = load_config(self.config_path)
        except ZerosValueError as exc:
            return False, str(exc)
        self.set_config(config, self.config_path)
        return True, None

    # --- Sending OSC commands -------------------------------------------------

    def trigger_active_button(self, active_index: int, side: ButtonSide) -> list[LogEntry]:
        """Trigger ON or OFF for the ``active_index``-th active button."""
        active = self.config.active_buttons
        if not 0 <= active_index < len(active):
            raise IndexError(f"Ungültiger Button-Index {active_index}")
        button = active[active_index]
        entries = self.trigger_button_config(button, side)
        if entries and all(e.ok for e in entries):
            self.button_states[active_index] = side
        return entries

    def trigger_button_config(self, button: ButtonConfig, side: ButtonSide) -> list[LogEntry]:
        """Send all resolved ON or OFF commands for ``button``."""
        addresses = button.resolve_on_commands() if side == "on" else button.resolve_off_commands()
        side_label = button.on_label if side == "on" else button.off_label
        display_name = f"{button.name} ({side_label})"
        entries: list[LogEntry] = []

        for address in addresses:
            notes = tuple(address_warnings(match_address(address)))
            target = self.target_label
            if self.dry_run:
                outcome = "DRY-RUN nicht gesendet"
                ok = True
            else:
                try:
                    self._get_client().send(address)
                except OSError as exc:
                    outcome = f"FEHLER {exc}"
                    ok = False
                else:
                    outcome = "gesendet"
                    ok = True

            line = format_log_line(display_name, address, target, outcome)
            ts = line.split(" ", 2)[0] + " " + line.split(" ", 2)[1]
            entry = LogEntry(
                timestamp=ts,
                button_name=button.name,
                side=side,
                address=address,
                target=target,
                outcome=outcome,
                ok=ok,
                line=line,
                warnings=notes,
            )
            self._record(entry)
            entries.append(entry)
        return entries

    def trigger_all_off(self) -> list[LogEntry]:
        """Send the OFF action for every active button in order."""
        all_entries: list[LogEntry] = []
        for idx in range(len(self.config.active_buttons)):
            all_entries.extend(self.trigger_active_button(idx, "off"))
        return all_entries

    def trigger_startup_actions(self) -> list[LogEntry]:
        """Trigger ON for every active button marked with ``auto_on_at_startup``."""
        sent: list[LogEntry] = []
        for idx, button in enumerate(self.config.active_buttons):
            if button.auto_on_at_startup:
                sent.extend(self.trigger_active_button(idx, "on"))
        return sent

    def _record(self, entry: LogEntry) -> None:
        self.history.append(entry)
        if len(self.history) > 500:
            del self.history[: len(self.history) - 500]
        if self._out is not None:
            print(entry.line, file=self._out, flush=True)
        append_event_log(entry.line, directory=self._app_data_dir)
        if self._on_log is not None:
            self._on_log(entry)

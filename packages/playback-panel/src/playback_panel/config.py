"""Configuration schema, validation and YAML persistence for playback-panel.

All OSC addresses are built and validated exclusively via ``zeros_osc``
(see ``docs/02-flx-osc-referenz.md``). User-facing error and warning messages
are German because operators read them.
"""

from __future__ import annotations

import math
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from zeros_osc import (
    DEFAULT_PORT,
    ZerosValueError,
    address_warnings,
    cue_go,
    match_address,
    playback_go,
    playback_level,
    playback_pause,
    playback_release,
)
from zeros_osc.client import TRANSPORTS
from zeros_osc.commands import norm_cue, norm_fade, norm_level, norm_playback

MAX_BUTTONS = 12

ACCENT_COLORS = ("amber", "emerald", "blue", "violet", "rose", "cyan", "slate")
WINDOW_MODES = ("normal", "maximized", "fullscreen")
BUTTON_MODES = ("playback_level", "playback_go_release", "cue_pair", "custom")
RELEASE_ACTIONS = ("release", "pause")


@dataclass
class CheckResult:
    """Validation errors and reference caveats for a panel configuration."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class ConsoleConfig:
    """Target FLX S48 console network parameters."""

    host: str = "192.168.1.10"
    port: int = DEFAULT_PORT
    transport: str = "udp"

    def to_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "transport": self.transport,
        }


@dataclass
class UiConfig:
    """Window and event-operation preferences."""

    start_locked: bool = False
    always_on_top: bool = False
    window_mode: str = "normal"
    show_all_off: bool = True
    startup_delay_s: float = 2.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_locked": self.start_locked,
            "always_on_top": self.always_on_top,
            "window_mode": self.window_mode,
            "show_all_off": self.show_all_off,
            "startup_delay_s": self.startup_delay_s,
        }


@dataclass
class ButtonConfig:
    """A configurable playback button card with ON and OFF actions.

    Supported modes:
    * ``playback_level``: ON sets ``playback`` to ``on_level`` (default 100),
      OFF sets the **same** ``playback`` to ``off_level`` (default 0).
    * ``playback_go_release``: ON triggers ``playback_go``, OFF triggers
      ``playback_release`` or ``playback_pause`` on the same ``playback``.
    * ``cue_pair``: ON triggers ``cue_go(playback, on_cue)``, OFF triggers
      ``cue_go(playback, off_cue)`` (both confirmed ``belegt`` in ZerOS).
    * ``custom``: ``on_commands`` and ``off_commands`` each hold one or more
      validated ZerOS OSC addresses from ``docs/02-flx-osc-referenz.md``.
    """

    name: str
    id: str = ""
    description: str = ""
    enabled: bool = True
    color: str = "amber"
    mode: str = "playback_level"
    on_label: str = "EIN"
    off_label: str = "AUS"
    auto_on_at_startup: bool = False

    # Mode parameters
    playback: int = 1
    on_level: int = 100
    off_level: int = 0
    on_fade: str | None = None
    off_fade: str | None = None
    off_action: str = "release"
    on_cue: str = "1"
    off_cue: str = "2"
    on_commands: tuple[str, ...] = ()
    off_commands: tuple[str, ...] = ()

    def resolve_on_commands(self) -> list[str]:
        """Build and validate all OSC addresses sent when pressing ON."""
        if self.mode == "playback_level":
            return [playback_level(self.playback, self.on_level, self.on_fade)]
        if self.mode == "playback_go_release":
            return [playback_go(self.playback)]
        if self.mode == "cue_pair":
            return [cue_go(self.playback, self.on_cue)]
        if self.mode == "custom":
            if not self.on_commands:
                raise ZerosValueError("on_commands darf im Modus custom nicht leer sein")
            for addr in self.on_commands:
                match_address(addr)
            return list(self.on_commands)
        raise ZerosValueError(f"Unbekannter Modus {self.mode!r}")

    def resolve_off_commands(self) -> list[str]:
        """Build and validate all OSC addresses sent when pressing OFF."""
        if self.mode == "playback_level":
            return [playback_level(self.playback, self.off_level, self.off_fade)]
        if self.mode == "playback_go_release":
            if self.off_action == "release":
                return [playback_release(self.playback)]
            if self.off_action == "pause":
                return [playback_pause(self.playback)]
            raise ZerosValueError(
                f"off_action muss release oder pause sein, ist {self.off_action!r}"
            )
        if self.mode == "cue_pair":
            return [cue_go(self.playback, self.off_cue)]
        if self.mode == "custom":
            if not self.off_commands:
                raise ZerosValueError("off_commands darf im Modus custom nicht leer sein")
            for addr in self.off_commands:
                match_address(addr)
            return list(self.off_commands)
        raise ZerosValueError(f"Unbekannter Modus {self.mode!r}")

    def badge_text(self) -> str:
        """Compact technical summary shown on the button card."""
        if self.mode == "playback_level":
            fade_part = ""
            if self.on_fade is not None and self.on_fade == self.off_fade:
                fade_part = f" · {self.on_fade}s"
            elif self.on_fade is not None or self.off_fade is not None:
                fade_part = f" · {self.on_fade or '-'}s/{self.off_fade or '-'}s"
            return f"PB {self.playback} · {self.on_level}% / {self.off_level}%{fade_part}"
        if self.mode == "playback_go_release":
            action = "Release" if self.off_action == "release" else "Pause"
            return f"PB {self.playback} · Go / {action}"
        if self.mode == "cue_pair":
            return f"PB {self.playback} · Cue {self.on_cue} / {self.off_cue}"
        total_on = len(self.on_commands)
        total_off = len(self.off_commands)
        if total_on == 1 and total_off == 1:
            return "Frei · 1 / 1 Befehl"
        return f"Frei · {total_on} / {total_off} Befehle"

    def status_tags(self) -> list[str]:
        """Collect unique non-confirmed status tags (e.g. 'vermutet', 'ungetestet')."""
        tags: list[str] = []
        for addr in (*self.resolve_on_commands(), *self.resolve_off_commands()):
            match = match_address(addr)
            if match.command.status.unconfirmed and "vermutet" not in tags:
                tags.append("vermutet")
            elif match.command.status.untested and not match.command.status.unconfirmed:
                if "ungetestet" not in tags:
                    tags.append("ungetestet")
        return tags

    def warnings(self) -> list[str]:
        """Return unique German reference warnings for all addresses of this button."""
        seen: list[str] = []
        for addr in (*self.resolve_on_commands(), *self.resolve_off_commands()):
            match = match_address(addr)
            for note in address_warnings(match):
                msg = f"{addr}: {note}"
                if msg not in seen:
                    seen.append(msg)
        return seen

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a clean, minimal YAML-friendly dictionary."""
        out: dict[str, Any] = {}
        if self.id:
            out["id"] = self.id
        out["name"] = self.name
        if self.description:
            out["description"] = self.description
        if not self.enabled:
            out["enabled"] = False
        out["color"] = self.color
        out["mode"] = self.mode
        if self.on_label != "EIN":
            out["on_label"] = self.on_label
        if self.off_label != "AUS":
            out["off_label"] = self.off_label
        if self.auto_on_at_startup:
            out["auto_on_at_startup"] = True

        if self.mode == "playback_level":
            out["playback"] = self.playback
            out["on_level"] = self.on_level
            out["off_level"] = self.off_level
            if self.on_fade is not None and self.on_fade == self.off_fade:
                out["fade"] = _maybe_number(self.on_fade)
            else:
                if self.on_fade is not None:
                    out["on_fade"] = _maybe_number(self.on_fade)
                if self.off_fade is not None:
                    out["off_fade"] = _maybe_number(self.off_fade)
        elif self.mode == "playback_go_release":
            out["playback"] = self.playback
            out["off_action"] = self.off_action
        elif self.mode == "cue_pair":
            out["playback"] = self.playback
            out["on_cue"] = _maybe_number(self.on_cue)
            out["off_cue"] = _maybe_number(self.off_cue)
        elif self.mode == "custom":
            out["on_commands"] = list(self.on_commands)
            out["off_commands"] = list(self.off_commands)
        return out


@dataclass
class PanelConfig:
    """Complete configuration of a playback-panel show."""

    title: str = "FLX Playback-Panel"
    console: ConsoleConfig = field(default_factory=ConsoleConfig)
    ui: UiConfig = field(default_factory=UiConfig)
    buttons: list[ButtonConfig] = field(default_factory=list)

    @property
    def active_buttons(self) -> list[ButtonConfig]:
        """Buttons currently enabled for display in the operator view."""
        return [b for b in self.buttons if b.enabled]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "console": self.console.to_dict(),
            "ui": self.ui.to_dict(),
            "buttons": [b.to_dict() for b in self.buttons],
        }


# --- Helpers & parsing --------------------------------------------------------


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def _maybe_number(text: str) -> int | float | str:
    """Keep clean YAML scalars (e.g. 2 instead of '2', 1.5 instead of '1.5')."""
    if text.isdigit():
        return int(text)
    try:
        val = float(text)
    except ValueError:
        return text
    if math.isfinite(val) and str(val) == text:
        return val
    return text


def load_raw(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _parse_command_list(raw: Any, field_name: str) -> tuple[list[str], list[str]]:
    """Accept either a single address string or a non-empty list of address strings."""
    errors: list[str] = []
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, list):
        items = raw
    else:
        return [], [f"{field_name} muss eine OSC-Adresse oder eine Liste von OSC-Adressen sein"]

    if not items:
        return [], [f"{field_name} darf nicht leer sein"]

    validated: list[str] = []
    for idx, item in enumerate(items):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{field_name}[{idx}] muss eine nicht leere OSC-Adresse sein")
            continue
        addr = item.strip()
        if addr != item:
            errors.append(f"{field_name}[{idx}] hat Leerzeichen am Anfang oder Ende: {item!r}")
            continue
        try:
            match_address(addr)
        except ZerosValueError as exc:
            errors.append(f"{field_name}[{idx}]: {exc}")
        else:
            validated.append(addr)
    return validated, errors


def _parse_optional_fade(entry: dict[str, Any], key: str, fallback: Any) -> str | None:
    raw = entry.get(key, fallback)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    return norm_fade(raw)


def parse_config(data: Any) -> tuple[PanelConfig | None, CheckResult]:
    """Parse and validate a raw YAML dictionary into a ``PanelConfig``."""
    result = CheckResult()
    err = result.errors.append

    if not isinstance(data, dict):
        err("Datei enthält kein YAML-Objekt auf oberster Ebene")
        return None, result

    # title
    raw_title = data.get("title", "FLX Playback-Panel")
    if not isinstance(raw_title, str) or not raw_title.strip():
        err("title muss ein nicht leerer Text sein")
        title = "FLX Playback-Panel"
    else:
        title = raw_title.strip()

    # console
    console_raw = data.get("console")
    host = "192.168.1.10"
    port = DEFAULT_PORT
    transport = "udp"
    if not isinstance(console_raw, dict):
        err("console fehlt")
    else:
        raw_host = console_raw.get("host")
        if not isinstance(raw_host, str) or not raw_host.strip():
            err("console.host fehlt")
        elif raw_host != raw_host.strip():
            err(f"console.host hat Leerzeichen am Anfang oder Ende: {raw_host!r}")
        else:
            host = raw_host
        raw_port = console_raw.get("port", DEFAULT_PORT)
        if not _is_int(raw_port) or not 1 <= raw_port <= 65535:
            err(f"console.port muss eine Zahl von 1 bis 65535 sein, ist {raw_port!r}")
        else:
            port = raw_port
        raw_transport = console_raw.get("transport", "udp")
        if raw_transport not in TRANSPORTS:
            err(f"console.transport muss udp oder tcp-slip sein, ist {raw_transport!r}")
        else:
            transport = raw_transport

    # ui (optional)
    ui_raw = data.get("ui", {})
    ui_cfg = UiConfig()
    if ui_raw is None:
        ui_raw = {}
    if not isinstance(ui_raw, dict):
        err("ui muss ein YAML-Objekt sein")
    else:
        for bool_key in ("start_locked", "always_on_top", "show_all_off"):
            if bool_key in ui_raw:
                val = ui_raw[bool_key]
                if not isinstance(val, bool):
                    err(f"ui.{bool_key} muss true oder false sein, ist {val!r}")
                else:
                    setattr(ui_cfg, bool_key, val)
        if "window_mode" in ui_raw:
            wm = ui_raw["window_mode"]
            if wm not in WINDOW_MODES:
                err(f"ui.window_mode muss einer von {', '.join(WINDOW_MODES)} sein, ist {wm!r}")
            else:
                ui_cfg.window_mode = wm
        if "startup_delay_s" in ui_raw:
            delay = ui_raw["startup_delay_s"]
            if not _is_number(delay) or delay < 0 or delay > 300:
                err(f"ui.startup_delay_s muss eine Zahl von 0 bis 300 sein, ist {delay!r}")
            else:
                ui_cfg.startup_delay_s = float(delay)

    # buttons
    buttons_raw = data.get("buttons")
    parsed_buttons: list[ButtonConfig] = []
    if buttons_raw is None:
        err("buttons fehlt")
    elif not isinstance(buttons_raw, list):
        err("buttons muss eine Liste sein")
    else:
        if len(buttons_raw) > MAX_BUTTONS:
            err(
                f"buttons enthält {len(buttons_raw)} Einträge; "
                f"maximal {MAX_BUTTONS} Playbacks/Buttons sind erlaubt"
            )
        seen_ids: dict[str, int] = {}
        for index, entry in enumerate(buttons_raw):
            label = f"buttons[{index}]"
            if not isinstance(entry, dict):
                err(f"{label}: Eintrag muss ein YAML-Objekt sein")
                continue

            raw_name = entry.get("name")
            if not isinstance(raw_name, str) or not raw_name.strip():
                err(f"{label}: name fehlt")
                btn_name = f"Button {index + 1}"
            else:
                btn_name = raw_name.strip()
                label = f"buttons[{index}] ({btn_name!r})"

            raw_id = entry.get("id", "")
            if raw_id is None:
                raw_id = ""
            if not isinstance(raw_id, str):
                err(f"{label}: id muss Text sein, ist {raw_id!r}")
                btn_id = ""
            else:
                btn_id = raw_id.strip()
                if btn_id:
                    if btn_id in seen_ids:
                        err(
                            f"{label}: doppelte id {btn_id!r}, "
                            f"schon vergeben in buttons[{seen_ids[btn_id]}]"
                        )
                    else:
                        seen_ids[btn_id] = index

            raw_desc = entry.get("description", "")
            if raw_desc is None:
                raw_desc = ""
            if not isinstance(raw_desc, str):
                err(f"{label}: description muss Text sein")
                desc = ""
            else:
                desc = raw_desc.strip()

            enabled = entry.get("enabled", True)
            if not isinstance(enabled, bool):
                err(f"{label}: enabled muss true oder false sein, ist {enabled!r}")
                enabled = True

            color = entry.get("color", "amber")
            if color not in ACCENT_COLORS:
                err(f"{label}: color muss einer von {', '.join(ACCENT_COLORS)} sein, ist {color!r}")
                color = "amber"

            on_label = entry.get("on_label", "EIN")
            if not isinstance(on_label, str) or not on_label.strip():
                err(f"{label}: on_label darf nicht leer sein")
                on_label = "EIN"
            else:
                on_label = on_label.strip()

            off_label = entry.get("off_label", "AUS")
            if not isinstance(off_label, str) or not off_label.strip():
                err(f"{label}: off_label darf nicht leer sein")
                off_label = "AUS"
            else:
                off_label = off_label.strip()

            auto_on = entry.get("auto_on_at_startup", False)
            if not isinstance(auto_on, bool):
                err(f"{label}: auto_on_at_startup muss true oder false sein, ist {auto_on!r}")
                auto_on = False

            # Infer mode when omitted: custom if on_commands/off_commands given, else playback_level
            if "mode" in entry:
                mode = entry["mode"]
            elif "on_commands" in entry or "off_commands" in entry:
                mode = "custom"
            elif "on_cue" in entry or "off_cue" in entry:
                mode = "cue_pair"
            else:
                mode = "playback_level"

            if mode not in BUTTON_MODES:
                err(f"{label}: mode muss einer von {', '.join(BUTTON_MODES)} sein, ist {mode!r}")
                continue

            btn = ButtonConfig(
                id=btn_id,
                name=btn_name,
                description=desc,
                enabled=enabled,
                color=color,
                mode=mode,
                on_label=on_label,
                off_label=off_label,
                auto_on_at_startup=auto_on,
            )

            entry_ok = True
            if mode == "playback_level":
                if "playback" not in entry:
                    err(f"{label}: playback fehlt")
                    entry_ok = False
                else:
                    try:
                        btn.playback = int(norm_playback(entry["playback"]))
                    except ZerosValueError as exc:
                        err(f"{label}: {exc}")
                        entry_ok = False
                try:
                    btn.on_level = int(norm_level(entry.get("on_level", 100)))
                except ZerosValueError as exc:
                    err(f"{label}: on_level: {exc}")
                    entry_ok = False
                try:
                    btn.off_level = int(norm_level(entry.get("off_level", 0)))
                except ZerosValueError as exc:
                    err(f"{label}: off_level: {exc}")
                    entry_ok = False
                shared_fade = entry.get("fade")
                try:
                    btn.on_fade = _parse_optional_fade(entry, "on_fade", shared_fade)
                except ZerosValueError as exc:
                    err(f"{label}: on_fade: {exc}")
                    entry_ok = False
                try:
                    btn.off_fade = _parse_optional_fade(entry, "off_fade", shared_fade)
                except ZerosValueError as exc:
                    err(f"{label}: off_fade: {exc}")
                    entry_ok = False

            elif mode == "playback_go_release":
                if "playback" not in entry:
                    err(f"{label}: playback fehlt")
                    entry_ok = False
                else:
                    try:
                        btn.playback = int(norm_playback(entry["playback"]))
                    except ZerosValueError as exc:
                        err(f"{label}: {exc}")
                        entry_ok = False
                off_action = entry.get("off_action", "release")
                if off_action not in RELEASE_ACTIONS:
                    err(f"{label}: off_action muss release oder pause sein, ist {off_action!r}")
                    entry_ok = False
                else:
                    btn.off_action = off_action

            elif mode == "cue_pair":
                if "playback" not in entry:
                    err(f"{label}: playback fehlt")
                    entry_ok = False
                else:
                    try:
                        btn.playback = int(norm_playback(entry["playback"]))
                    except ZerosValueError as exc:
                        err(f"{label}: {exc}")
                        entry_ok = False
                for cue_key, attr in (("on_cue", "on_cue"), ("off_cue", "off_cue")):
                    if cue_key not in entry:
                        err(f"{label}: {cue_key} fehlt")
                        entry_ok = False
                    else:
                        try:
                            setattr(btn, attr, norm_cue(entry[cue_key]))
                        except ZerosValueError as exc:
                            err(f"{label}: {cue_key}: {exc}")
                            entry_ok = False

            elif mode == "custom":
                on_cmds, on_errs = _parse_command_list(entry.get("on_commands"), "on_commands")
                off_cmds, off_errs = _parse_command_list(entry.get("off_commands"), "off_commands")
                for e in (*on_errs, *off_errs):
                    err(f"{label}: {e}")
                    entry_ok = False
                btn.on_commands = tuple(on_cmds)
                btn.off_commands = tuple(off_cmds)

            if entry_ok:
                for warning_text in btn.warnings():
                    result.warnings.append(f"{label}: {warning_text}")
                parsed_buttons.append(btn)

    if buttons_raw == [] or (parsed_buttons and not any(b.enabled for b in parsed_buttons)):
        result.warnings.append(
            "Keine aktiven Buttons konfiguriert – das Bedienfenster zeigt noch keine Schalter."
        )

    if not result.ok:
        return None, result

    config = PanelConfig(
        title=title,
        console=ConsoleConfig(host=host, port=port, transport=transport),
        ui=ui_cfg,
        buttons=parsed_buttons,
    )
    return config, result


def check(data: Any) -> CheckResult:
    """Validate parsed YAML data and return errors and reference warnings."""
    _, result = parse_config(data)
    return result


def check_file(path: str | Path) -> CheckResult:
    """Validate a YAML configuration file on disk."""
    try:
        data = load_raw(path)
    except OSError as exc:
        return CheckResult(errors=[f"Datei nicht lesbar: {exc}"])
    except UnicodeDecodeError as exc:
        return CheckResult(errors=[f"Datei ist nicht als UTF-8 gespeichert: {exc}"])
    except yaml.YAMLError as exc:
        return CheckResult(errors=[f"YAML-Fehler: {exc}"])
    return check(data)


def load_config(path: str | Path) -> tuple[PanelConfig, CheckResult]:
    """Load and validate a ``PanelConfig`` from ``path`` or raise ``ZerosValueError``."""
    try:
        data = load_raw(path)
    except UnicodeDecodeError as exc:
        raise ZerosValueError(f"Datei ist nicht als UTF-8 gespeichert: {exc}") from None
    except OSError as exc:
        raise ZerosValueError(f"Datei nicht lesbar: {exc}") from None
    except yaml.YAMLError as exc:
        raise ZerosValueError(f"YAML-Fehler: {exc}") from None

    config, result = parse_config(data)
    if config is None or not result.ok:
        raise ZerosValueError("\n".join(result.errors))
    return config, result


def render_yaml(config: PanelConfig) -> str:
    """Render ``PanelConfig`` to human-readable UTF-8 YAML with header comments."""
    result = check(config.to_dict())
    if not result.ok:
        raise ZerosValueError("\n".join(result.errors))
    header = (
        "# Konfiguration für das FLX Playback-Panel\n"
        "# Bis zu 12 Playbacks/Buttons; nur aktive Einträge werden im Bedienfenster angezeigt.\n"
        "# Erlaubte OSC-Adressen: docs/02-flx-osc-referenz.md\n\n"
    )
    body = yaml.safe_dump(
        config.to_dict(),
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    return header + body


def save_config(config: PanelConfig, path: str | Path) -> None:
    """Validate and atomically write ``config`` as UTF-8 YAML to ``path``."""
    target = Path(path)
    text = render_yaml(config)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp_path, target)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def default_starter_config(host: str = "192.168.1.10") -> PanelConfig:
    """Create a 4-button starter configuration for new shows or demo mode."""
    return PanelConfig(
        title="Kleines Event - Lichtsteuerung",
        console=ConsoleConfig(host=host, port=DEFAULT_PORT, transport="udp"),
        ui=UiConfig(
            start_locked=False,
            always_on_top=False,
            window_mode="normal",
            show_all_off=True,
            startup_delay_s=2.0,
        ),
        buttons=[
            ButtonConfig(
                id="pb_front",
                name="Bühne Grundlicht",
                description="Warmweißes Frontlicht für Moderation und Redner",
                color="amber",
                mode="playback_level",
                playback=1,
                on_level=100,
                off_level=0,
                on_fade="1.5",
                off_fade="1.5",
            ),
            ButtonConfig(
                id="pb_atmo",
                name="Hintergrund Ambiente",
                description="Farbiges Rückwandlicht gedimmt auf 70 %",
                color="blue",
                mode="playback_level",
                playback=2,
                on_level=70,
                off_level=0,
                on_fade="2",
                off_fade="2",
            ),
            ButtonConfig(
                id="pb_hall",
                name="Saallicht",
                description="Publikumsbeleuchtung für Einlass und Pause",
                color="emerald",
                mode="playback_level",
                playback=3,
                on_level=100,
                off_level=0,
                on_fade="3",
                off_fade="3",
            ),
            ButtonConfig(
                id="cue_band",
                name="Musik-Szene",
                description="Startet Cue 1 (Ein) bzw. Cue 2 (Aus) auf Playback 10",
                color="violet",
                mode="cue_pair",
                playback=10,
                on_cue="1",
                off_cue="2",
            ),
        ],
    )

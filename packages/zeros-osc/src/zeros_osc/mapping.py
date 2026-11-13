"""Check a mapping.yaml and render it as an operator cheat sheet.

Schema: docs/01-konzept.md, section "Schema der Mapping-Datei".
Messages are German because operators read them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .client import TRANSPORTS
from .commands import ZerosValueError, address_warnings, match_address


@dataclass
class CheckResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def load(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _label(index: int, entry: Any) -> str:
    note = entry.get("note") if isinstance(entry, dict) else None
    return f"cues[{index}]" + (f" (Note {note})" if note is not None else "")


def check(data: Any) -> CheckResult:
    """Validate parsed mapping data."""
    result = CheckResult()
    err = result.errors.append

    if not isinstance(data, dict):
        err("Datei enthält kein YAML-Objekt auf oberster Ebene")
        return result

    # console
    console = data.get("console")
    if not isinstance(console, dict):
        err("console fehlt")
    else:
        host = console.get("host")
        if not isinstance(host, str) or not host.strip():
            err("console.host fehlt")
        port = console.get("port")
        if not _is_int(port) or not 1 <= port <= 65535:
            err(f"console.port muss eine Zahl von 1 bis 65535 sein, ist {port!r}")
        transport = console.get("transport")
        if transport not in TRANSPORTS:
            err(f"console.transport muss udp oder tcp-slip sein, ist {transport!r}")

    # sources
    sources = data.get("sources")
    source_names: set[str] = set()
    if not isinstance(sources, dict) or not sources:
        err("sources fehlt oder ist leer")
    else:
        for name, src in sources.items():
            source_names.add(str(name))
            if not isinstance(src, dict):
                err(f"sources.{name} muss midi_port und channel enthalten")
                continue
            port = src.get("midi_port")
            if not isinstance(port, str) or not port.strip():
                err(f"sources.{name}.midi_port fehlt")
            channel = src.get("channel")
            if not _is_int(channel) or not 1 <= channel <= 16:
                err(f"sources.{name}.channel muss 1 bis 16 sein, ist {channel!r}")

    # debounce_ms (optional)
    if "debounce_ms" in data:
        debounce = data["debounce_ms"]
        if not _is_number(debounce) or debounce < 0:
            err(f"debounce_ms muss eine Zahl ab 0 sein, ist {debounce!r}")

    # cues
    cues = data.get("cues")
    if not isinstance(cues, list) or not cues:
        err("cues fehlt oder ist leer")
        return result

    seen_notes: dict[int, int] = {}
    for index, entry in enumerate(cues):
        label = _label(index, entry)
        if not isinstance(entry, dict):
            err(f"{label}: Eintrag muss note, name und osc enthalten")
            continue

        note = entry.get("note")
        if note is None:
            err(f"{label}: note fehlt")
        elif not _is_int(note) or not 0 <= note <= 127:
            err(f"{label}: note muss eine ganze Zahl von 0 bis 127 sein, ist {note!r}")
        elif note in seen_notes:
            err(f"{label}: doppelte Note {note}, schon in cues[{seen_notes[note]}]")
        else:
            seen_notes[note] = index

        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            err(f"{label}: name fehlt")

        osc = entry.get("osc")
        if not isinstance(osc, str) or not osc.strip():
            err(f"{label}: osc fehlt")
        else:
            try:
                match = match_address(osc)
            except ZerosValueError as exc:
                err(f"{label}: {exc}")
            else:
                for note_text in address_warnings(match):
                    result.warnings.append(f"{label}: {osc}: {note_text}")

        if "sources" in entry:
            limited = entry["sources"]
            if not isinstance(limited, list) or not limited:
                err(f"{label}: sources muss eine nicht leere Liste sein")
            else:
                for src_name in limited:
                    if str(src_name) not in source_names:
                        err(f"{label}: Quelle {src_name!r} steht nicht unter sources")

    return result


def check_file(path: str | Path) -> CheckResult:
    try:
        data = load(path)
    except OSError as exc:
        return CheckResult(errors=[f"Datei nicht lesbar: {exc}"])
    except yaml.YAMLError as exc:
        return CheckResult(errors=[f"YAML-Fehler: {exc}"])
    return check(data)


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def render_doc(data: dict[str, Any], title: str = "mapping.yaml") -> str:
    """Markdown cheat sheet for operators. Expects data that passed ``check``."""
    console = data["console"]
    sources = data["sources"]
    lines = [
        f"# Spickzettel: {_cell(title)}",
        "",
        f"Pult: {_cell(console['host'])}:{console['port']} ({console['transport']})",
        "",
        "| Quelle | MIDI-Port | Kanal |",
        "| --- | --- | --- |",
    ]
    for name, src in sources.items():
        lines.append(f"| {_cell(name)} | {_cell(src['midi_port'])} | {src['channel']} |")
    lines += [
        "",
        "| Note | Name | Befehl | OSC-Adresse | Quellen | Hinweis |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for entry in sorted(data["cues"], key=lambda e: e["note"]):
        match = match_address(entry["osc"])
        limited = entry.get("sources")
        where = ", ".join(_cell(s) for s in limited) if limited else "alle"
        hint = "; ".join(address_warnings(match))
        lines.append(
            f"| {entry['note']} | {_cell(entry['name'])} | {match.command.summary} "
            f"| `{entry['osc']}` | {where} | {_cell(hint)} |"
        )
    lines += [
        "",
        "Noten sind MIDI-Notennummern 0–127, nicht Notennamen. "
        "Programme zählen Oktaven verschieden.",
        "",
    ]
    return "\n".join(lines)

"""Immutable, fully checked view of a mapping.yaml.

The check itself comes from ``zeros_osc.mapping``; this module only turns
data that passed the check into frozen objects. A ``Mapping`` is never
changed after creation: a reload builds a new one and the bridge swaps the
reference with a single assignment.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

from zeros_osc import mapping as zmapping

DEFAULT_DEBOUNCE_MS = 250


@dataclass(frozen=True)
class Console:
    host: str
    port: int
    transport: str


@dataclass(frozen=True)
class Source:
    name: str
    midi_port: str  # start of the MIDI input name, as written in the config
    channel: int  # 1..16


@dataclass(frozen=True)
class Cue:
    note: int
    name: str
    osc: str
    sources: frozenset[str] | None  # None: valid for all sources

    def allows(self, source: str) -> bool:
        return self.sources is None or source in self.sources


@dataclass(frozen=True, eq=False)
class Mapping:
    path: str
    console: Console
    sources: tuple[Source, ...]
    debounce_ms: float
    cues: MappingProxyType[int, Cue]  # read-only view, keyed by note
    warnings: tuple[str, ...]  # hints from the zeros-osc check (Forum, vermutet, ...)

    @property
    def midi_ports(self) -> tuple[str, ...]:
        """Distinct configured port names, in order of first appearance."""
        return tuple(dict.fromkeys(s.midi_port for s in self.sources))

    def source_for(self, port: str, channel: int) -> Source | None:
        """Source for a message from input ``port`` on ``channel`` (1..16).

        If several configured port names match, the longest one wins.
        """
        best: Source | None = None
        for source in self.sources:
            if source.channel == channel and port_matches(source.midi_port, port):
                if best is None or len(source.midi_port) > len(best.midi_port):
                    best = source
        return best


def port_matches(configured: str, actual: str) -> bool:
    """A configured name matches an input whose name starts with it.

    Windows (loopMIDI via WinMM) appends a number, e.g. "LX Bridge 1".
    """
    return actual.startswith(configured)


@dataclass(frozen=True)
class LoadResult:
    mapping: Mapping | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    signature: str | None = None  # content hash of the bytes that were checked


def content_signature(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_signature(path: str | Path) -> str | None:
    """Hash of the file content, or None if it cannot be read.

    The content is compared instead of mtime and size: a same-size edit can
    keep the same mtime (coarse timestamps on Windows, FAT/exFAT sticks).
    """
    try:
        with open(path, "rb") as fh:
            return content_signature(fh.read())
    except OSError:
        return None


def _build(path: str, data: dict[str, Any], warnings: tuple[str, ...]) -> Mapping:
    console = data["console"]
    sources = tuple(
        Source(str(name), src["midi_port"], src["channel"]) for name, src in data["sources"].items()
    )
    cues = {
        entry["note"]: Cue(
            note=entry["note"],
            name=entry["name"],
            osc=entry["osc"],
            sources=frozenset(str(s) for s in entry["sources"]) if "sources" in entry else None,
        )
        for entry in data["cues"]
    }
    return Mapping(
        path=path,
        console=Console(console["host"], console["port"], console["transport"]),
        sources=sources,
        debounce_ms=float(data.get("debounce_ms", DEFAULT_DEBOUNCE_MS)),
        cues=MappingProxyType(cues),
        warnings=warnings,
    )


def load_mapping(path: str | Path) -> LoadResult:
    """Read, check completely and, only if there are no errors, build a Mapping.

    The file is read once; hash, check and build work on the same bytes.
    """
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        return LoadResult(None, (f"Datei nicht lesbar: {exc}",), ())
    signature = content_signature(raw)
    try:
        data = yaml.safe_load(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        error = f"Datei ist nicht als UTF-8 gespeichert: {exc}"
        return LoadResult(None, (error,), (), signature)
    except yaml.YAMLError as exc:
        return LoadResult(None, (f"YAML-Fehler: {exc}",), (), signature)
    result = zmapping.check(data)
    warnings = tuple(result.warnings)
    if not result.ok:
        return LoadResult(None, tuple(result.errors), warnings, signature)
    return LoadResult(_build(str(path), data, warnings), (), warnings, signature)

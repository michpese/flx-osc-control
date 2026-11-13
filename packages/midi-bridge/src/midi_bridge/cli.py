"""Command line: ``midi-bridge --mapping FILE [--dry-run]`` and ``midi-bridge --list-ports``."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from .bridge import Bridge
from .mapping import load_mapping
from .ports import MidiBackend, MidoBackend


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="midi-bridge",
        description=(
            "Übersetzt MIDI-Noten (Note On) in OSC-Befehle für das FLX S24 und sendet sie "
            "über zeros-osc an console.host aus der mapping.yaml. Beenden mit Strg+C."
        ),
    )
    parser.add_argument("--mapping", metavar="DATEI", help="Pfad zur mapping.yaml")
    parser.add_argument(
        "--dry-run", action="store_true", help="nichts senden, nur zeigen, was gesendet würde"
    )
    parser.add_argument("--list-ports", action="store_true", help="alle MIDI-Eingänge anzeigen")
    return parser


def _setup_logging() -> None:
    logger = logging.getLogger("midi_bridge")
    if not any(getattr(h, "_midi_bridge", False) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler._midi_bridge = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _list_ports(backend: MidiBackend) -> int:
    try:
        names = backend.input_names()
    except Exception as exc:
        print(f"Fehler: MIDI-Eingänge nicht abfragbar: {exc}", file=sys.stderr)
        return 1
    if not names:
        print("Keine MIDI-Eingänge gefunden.")
        return 0
    print("MIDI-Eingänge (midi_port in der mapping.yaml muss der Anfang eines Namens sein):")
    for name in names:
        print(f"  {name}")
    return 0


def main(argv: Sequence[str] | None = None, backend: MidiBackend | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    backend = backend if backend is not None else MidoBackend()

    if args.list_ports:
        return _list_ports(backend)
    if not args.mapping:
        parser.error("--mapping DATEI fehlt (oder --list-ports verwenden)")

    result = load_mapping(args.mapping)
    if result.mapping is None:
        for error in result.errors:
            print(f"Fehler: {error}", file=sys.stderr)
        print(
            f"{len(result.errors)} Fehler in {args.mapping}, Bridge startet nicht", file=sys.stderr
        )
        return 1

    _setup_logging()
    bridge = Bridge(result.mapping, backend, dry_run=args.dry_run)
    try:
        return bridge.run()
    except KeyboardInterrupt:
        bridge.stop()  # already done by run(); stop() is idempotent
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

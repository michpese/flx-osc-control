"""Command line: ``mock-console [--host H] [--port P] [--jsonl FILE]``."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from zeros_osc import DEFAULT_PORT

from .server import MockConsole


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mock-console",
        description=(
            "Attrappe des FLX S24: lauscht per UDP, schreibt jede OSC-Nachricht ins Log "
            "und bewertet sie nach docs/02-flx-osc-referenz.md. Simuliert kein Licht "
            "und keine Cue-Zustände und antwortet nie."
        ),
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Adresse, auf der gelauscht wird (Standard 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help=f"UDP-Port (Standard {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--jsonl", metavar="DATEI", help="jede Nachricht zusätzlich als JSON-Zeile anhängen"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("mock_console")
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        console = MockConsole(host=args.host, port=args.port, jsonl=args.jsonl)
        try:
            console.start()
        except OSError as exc:
            print(
                f"Fehler: Port {args.port} auf {args.host} nicht verfügbar: {exc}", file=sys.stderr
            )
            return 1
        try:
            console.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0
    finally:
        # Leave the logger as it was: main() is also called from tests.
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


if __name__ == "__main__":
    raise SystemExit(main())

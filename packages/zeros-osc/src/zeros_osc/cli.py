"""flxctl - send ZerOS OSC commands and check mapping files.

User-facing text is German (operators read it); code is English.
Exit codes: 0 ok, 1 send failed or mapping has errors, 2 invalid input.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import TextIO

import yaml

from . import __version__, mapping
from .client import DEFAULT_PORT, TRANSPORTS, make_client
from .commands import COMMANDS, Command, Status, ZerosValueError, address_warnings, match_address

EPILOG = (
    "Adressen stammen aus docs/02-flx-osc-referenz.md. Befehle mit dem Vermerk "
    "[ungetestet] stehen dort mit Status „Forum“: im Herstellerforum genannt, "
    "nicht im Handbuch belegt und noch nicht am Pult getestet. Das Pult meldet "
    "nichts zurück; ob ein Befehl ankam, zeigt nur der Event Monitor am Pult."
)


def _status_tag(command: Command) -> str:
    if command.status is Status.FORUM:
        return "[ungetestet]"
    return "[belegt]"


def _command_help(command: Command) -> str:
    return f"{command.summary} {_status_tag(command)}"


def _command_description(command: Command) -> str:
    text = f"{command.summary}.\nAdresse: {command.pattern}\nBeispiel: {command.example}\n"
    if command.status is Status.FORUM:
        text += (
            "Status: Forum – UNGETESTET. Nur im Herstellerforum genannt, "
            "nicht im ZerOS-Handbuch belegt.\n"
        )
    else:
        text += "Status: belegt (ZerOS-Handbuch).\n"
    if command.id == "cue_go":
        text += (
            "Hinweis: Playback 0 (Master) wurde laut Forum auf einem FLX S48 "
            "ignoriert; in Teststufe 2 prüfen.\n"
        )
    if command.id == "macro":
        text += (
            "Hinweis: FLX-S-Pulte haben keine User-Makros, nur Fixture-Makros. "
            "Die Steuerung baut auf Cues auf.\n"
        )
    return text


def _target_options() -> argparse.ArgumentParser:
    # SUPPRESS lets these options appear both before and after the subcommand
    # without the subparser overwriting values given earlier.
    common = argparse.ArgumentParser(add_help=False)
    group = common.add_argument_group("Ziel")
    group.add_argument("--host", default=argparse.SUPPRESS, help="IP-Adresse des Pults")
    group.add_argument(
        "--port",
        type=int,
        default=argparse.SUPPRESS,
        help=f"OSC-Port des Pults (Standard {DEFAULT_PORT})",
    )
    group.add_argument(
        "--transport",
        choices=TRANSPORTS,
        default=argparse.SUPPRESS,
        help="udp (Standard) oder tcp-slip; muss zur Einstellung am Pult passen",
    )
    group.add_argument(
        "--config",
        metavar="MAPPING",
        default=argparse.SUPPRESS,
        help="console.host, .port und .transport aus dieser mapping.yaml lesen",
    )
    group.add_argument(
        "--dry-run",
        action="store_true",
        default=argparse.SUPPRESS,
        help="nur anzeigen, was gesendet würde; nichts senden",
    )
    return common


def build_parser() -> argparse.ArgumentParser:
    common = _target_options()
    parser = argparse.ArgumentParser(
        prog="flxctl",
        description="ZerOS-OSC-Befehle an ein Zero 88 FLX S24 senden und Mappings prüfen.",
        epilog=EPILOG,
        parents=[common],
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    top = parser.add_subparsers(dest="group", metavar="BEFEHL", required=True)

    groups: dict[str, argparse._SubParsersAction] = {}
    group_help = {"cue": "Cues", "playback": "Playbacks"}
    for command in COMMANDS.values():
        if len(command.cli) == 1:
            leaf = top.add_parser(
                command.cli[0],
                help=_command_help(command),
                description=_command_description(command),
                epilog=EPILOG,
                parents=[common],
                formatter_class=argparse.RawDescriptionHelpFormatter,
            )
        else:
            group_name, action = command.cli
            if group_name not in groups:
                gp = top.add_parser(group_name, help=group_help.get(group_name, group_name))
                groups[group_name] = gp.add_subparsers(
                    dest="action", metavar="AKTION", required=True
                )
            leaf = groups[group_name].add_parser(
                action,
                help=_command_help(command),
                description=_command_description(command),
                epilog=EPILOG,
                parents=[common],
                formatter_class=argparse.RawDescriptionHelpFormatter,
            )
        for param in command.params:
            leaf.add_argument(param.name, help=param.help)
        for param in command.optional:
            leaf.add_argument(f"--{param.name}", default=None, help=f"optional: {param.help}")
        leaf.set_defaults(command=command)

    map_parser = top.add_parser("map", help="mapping.yaml prüfen oder als Spickzettel ausgeben")
    map_sub = map_parser.add_subparsers(dest="action", metavar="AKTION", required=True)
    check_p = map_sub.add_parser(
        "check",
        help="doppelte Noten, fehlende Namen und falsche Adressen melden",
        description="Prüft eine mapping.yaml nach dem Schema in docs/01-konzept.md.",
    )
    check_p.add_argument("file", help="Pfad zur mapping.yaml")
    check_p.set_defaults(handler=_cmd_map_check)
    doc_p = map_sub.add_parser(
        "doc",
        help="Markdown-Tabelle für Bediener schreiben",
        description="Schreibt eine Markdown-Tabelle aller Einträge, sortiert nach Note.",
    )
    doc_p.add_argument("file", help="Pfad zur mapping.yaml")
    doc_p.add_argument("-o", "--output", help="in diese Datei schreiben statt auf die Konsole")
    doc_p.set_defaults(handler=_cmd_map_doc)
    return parser


# --- handlers --------------------------------------------------------------------


def _log_line(address: str, target: str, outcome: str) -> str:
    # One line per event: timestamp, source, channel, note, name, address (CLAUDE.md).
    ts = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    return f"{ts} quelle=flxctl kanal=- note=- name=- adresse={address} ziel={target} {outcome}"


def _resolve_target(args: argparse.Namespace) -> tuple[str | None, int, str]:
    host: str | None = None
    port = DEFAULT_PORT
    transport = "udp"
    config = getattr(args, "config", None)
    if config:
        data = mapping.load(config)
        console = data.get("console") if isinstance(data, dict) else None
        if not isinstance(console, dict):
            raise ZerosValueError(f"{config}: console fehlt")
        host = console.get("host", host)
        port = console.get("port", port)
        transport = console.get("transport", transport)
    host = getattr(args, "host", host)
    port = getattr(args, "port", port)
    transport = getattr(args, "transport", transport)
    if transport not in TRANSPORTS:
        raise ZerosValueError(f"Transport {transport!r} unbekannt, erlaubt: udp, tcp-slip")
    return host, port, transport


def _cmd_send(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    command: Command = args.command
    values = [getattr(args, p.name) for p in command.params]
    values += [getattr(args, p.name) for p in command.optional]
    try:
        address = command.build(*values)
        host, port, transport = _resolve_target(args)
    except (ZerosValueError, OSError, yaml.YAMLError) as exc:
        print(f"Fehler: {exc}", file=err)
        return 2

    for note in address_warnings(match_address(address)):
        print(f"Hinweis: {note}", file=err)

    dry_run = getattr(args, "dry_run", False)
    target = f"{host}:{port}/{transport}" if host else "-"
    if dry_run:
        print(_log_line(address, target, "DRY-RUN nicht gesendet"), file=out)
        return 0
    if not host:
        print("Fehler: kein Ziel – --host oder --config angeben", file=err)
        return 2

    client = make_client(host, port, transport)
    try:
        client.send(address)
    except OSError as exc:
        print(_log_line(address, target, f"FEHLER {exc}"), file=out)
        return 1
    finally:
        client.close()
    print(_log_line(address, target, "gesendet"), file=out)
    return 0


def _cmd_map_check(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    result = mapping.check_file(args.file)
    for line in result.errors:
        print(f"Fehler: {line}", file=out)
    for line in result.warnings:
        print(f"Hinweis: {line}", file=out)
    if result.ok:
        print(f"OK: {args.file} ({len(result.warnings)} Hinweise)", file=out)
        return 0
    print(f"{len(result.errors)} Fehler in {args.file}", file=out)
    return 1


def _cmd_map_doc(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    result = mapping.check_file(args.file)
    if not result.ok:
        for line in result.errors:
            print(f"Fehler: {line}", file=err)
        print("Kein Spickzettel: erst die Fehler beheben (flxctl map check).", file=err)
        return 1
    text = mapping.render_doc(mapping.load(args.file), title=Path(args.file).name)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"geschrieben: {args.output}", file=err)
    else:
        out.write(text)
    return 0


def main(
    argv: Sequence[str] | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    args = build_parser().parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is not None:
        return handler(args, out, err)
    return _cmd_send(args, out, err)


if __name__ == "__main__":
    raise SystemExit(main())

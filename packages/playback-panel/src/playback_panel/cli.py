"""CLI and GUI entry point for ``flx-panel``.

Handles headless validation (``--check``), Windows Autostart management
(``--autostart``), and launching the Tkinter GUI safely even in ``--windowed``
PyInstaller ``.exe`` builds where ``sys.stdout`` / ``sys.stderr`` are ``None``.
"""

from __future__ import annotations

import argparse
import io
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from zeros_osc import ZerosValueError

from . import __version__
from .autostart import AutostartManager, AutostartNotSupportedError
from .config import PanelConfig, check_file, load_config
from .controller import PanelController
from .state import AppSettings

EPILOG = (
    "Alle OSC-Befehle werden über zeros-osc gegen docs/02-flx-osc-referenz.md "
    "geprüft. Befehle mit Status [vermutet] haben keine bestätigte Quelle im "
    "ZerOS-Handbuch und sollten vor dem Einsatz am Pult getestet werden."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flx-panel",
        description="Grafische Playback-Steuerung (bis zu 12 Playbacks mit EIN/AUS) für FLX S48.",
        epilog=EPILOG,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--config",
        metavar="DATEI",
        help="Pfad zur YAML-Konfigurationsdatei (wird für zukünftige Starts gemerkt)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Testmodus: Befehle protokollieren, aber keine Netzwerkpakete senden",
    )
    parser.add_argument(
        "--locked",
        action="store_true",
        help="direkt im gesperrten Bedienmodus starten",
    )
    parser.add_argument(
        "--edit",
        action="store_true",
        help="Konfigurationsdialog direkt beim Start öffnen",
    )
    parser.add_argument(
        "--check",
        metavar="DATEI",
        help="Konfigurationsdatei ohne Oberfläche prüfen und beenden",
    )
    parser.add_argument(
        "--autostart",
        choices=("status", "enable", "disable"),
        help="Windows-Autostart abfragen, aktivieren oder deaktivieren und beenden",
    )
    return parser


def _safe_stream(stream: TextIO | None) -> TextIO:
    """Provide a writable stream even in --windowed .exe builds where stdout/stderr is None."""
    return stream if stream is not None else io.StringIO()


def _handle_check(path_str: str, out: TextIO) -> int:
    result = check_file(path_str)
    for line in result.errors:
        print(f"Fehler: {line}", file=out)
    for line in result.warnings:
        print(f"Hinweis: {line}", file=out)
    if result.ok:
        print(f"OK: {path_str} ({len(result.warnings)} Hinweise)", file=out)
        return 0
    print(f"{len(result.errors)} Fehler in {path_str}", file=out)
    return 1


def _handle_autostart(
    action: str,
    config_arg: str | None,
    autostart: AutostartManager,
    out: TextIO,
    err: TextIO,
) -> int:
    if action == "status":
        if not autostart.supported:
            print("Autostart: nicht unterstützt (nur unter Windows verfügbar)", file=out)
            return 0
        cmd = autostart.current_command()
        if cmd:
            print(f"Autostart: aktiv ({cmd})", file=out)
        else:
            print("Autostart: inaktiv", file=out)
        return 0

    try:
        if action == "enable":
            cfg_path = Path(config_arg).resolve() if config_arg else None
            cmd = autostart.enable(config_path=cfg_path)
            print(f"Autostart aktiviert: {cmd}", file=out)
            return 0
        if action == "disable":
            autostart.disable()
            print("Autostart deaktiviert.", file=out)
            return 0
    except (AutostartNotSupportedError, OSError) as exc:
        print(f"Fehler: {exc}", file=err)
        return 1
    return 2


def main(
    argv: Sequence[str] | None = None,
    *,
    out: TextIO | None = None,
    err: TextIO | None = None,
    autostart: AutostartManager | None = None,
    app_data_dir: Path | None = None,
) -> int:
    has_console_out = out is not None or sys.stdout is not None
    out_stream = _safe_stream(out if out is not None else sys.stdout)
    err_stream = _safe_stream(err if err is not None else sys.stderr)

    args = build_parser().parse_args(argv)
    autostart_mgr = autostart or AutostartManager()

    if args.check:
        return _handle_check(args.check, out_stream)

    if args.autostart:
        return _handle_autostart(args.autostart, args.config, autostart_mgr, out_stream, err_stream)

    settings = AppSettings.load(app_data_dir)
    chosen_path: Path | None = None
    startup_error: str | None = None

    if args.config:
        chosen_path = Path(args.config)
    elif settings.last_config_path:
        candidate = Path(settings.last_config_path)
        if candidate.exists():
            chosen_path = candidate

    config = PanelConfig()
    if chosen_path is not None:
        try:
            config, check_res = load_config(chosen_path)
            for warning in check_res.warnings:
                print(f"Hinweis: {warning}", file=err_stream)
            settings.last_config_path = str(chosen_path.resolve())
            settings.save(app_data_dir)
        except ZerosValueError as exc:
            startup_error = f"{chosen_path}: {exc}"
            print(f"Fehler: {startup_error}", file=err_stream)
            if args.config and has_console_out and not getattr(sys, "frozen", False):
                return 2
            chosen_path = None

    dry_run = bool(args.dry_run or settings.dry_run)
    controller = PanelController(
        config=config,
        config_path=chosen_path,
        dry_run=dry_run,
        out=out_stream if has_console_out else None,
        app_data_dir=app_data_dir,
    )

    from .ui.app import run_gui

    if startup_error is not None:
        # Surface startup error in windowed mode once Tk initializes
        import tkinter as tk
        from tkinter import messagebox

        from .ui.app import PlaybackPanelApp
        from .ui.theme import enable_windows_high_dpi

        enable_windows_high_dpi()
        root = tk.Tk()
        PlaybackPanelApp(
            root,
            controller,
            settings=settings,
            autostart=autostart_mgr,
            app_data_dir=app_data_dir,
            force_locked=args.locked,
            open_editor_on_start=args.edit,
        )
        root.after(
            100,
            lambda: messagebox.showerror(
                "Konfiguration konnte nicht geladen werden",
                startup_error or "",
                parent=root,
            ),
        )
        root.mainloop()
        return 0

    return run_gui(
        controller,
        settings=settings,
        autostart=autostart_mgr,
        app_data_dir=app_data_dir,
        force_locked=args.locked,
        open_editor_on_start=args.edit,
    )

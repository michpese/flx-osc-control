"""Build a standalone single-file executable (``flx-panel.exe`` on Windows) via PyInstaller.

Usage on Windows (from the repository root):
    uv run --package playback-panel --extra build flx-panel-build
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path


def build_pyinstaller_args(
    *,
    entry_script: Path,
    dist_dir: Path,
    work_dir: Path,
    name: str = "flx-panel",
    console: bool = False,
) -> list[str]:
    """Construct deterministic PyInstaller CLI arguments for bundling playback-panel."""
    args = [
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console" if console else "--windowed",
        "--name",
        name,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(work_dir),
        "--collect-submodules",
        "zeros_osc",
        "--collect-submodules",
        "playback_panel",
        "--hidden-import",
        "yaml",
        "--hidden-import",
        "pythonosc",
        "--hidden-import",
        "pythonosc.osc_message_builder",
        str(entry_script),
    ]
    return args


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="flx-panel-build",
        description="Baut eine eigenständige Programmdatei (unter Windows: flx-panel.exe).",
    )
    parser.add_argument(
        "--dist-dir",
        default="dist",
        help="Zielordner für die erzeugte Programmdatei (Standard: dist)",
    )
    parser.add_argument(
        "--work-dir",
        default="build/pyinstaller",
        help="Arbeitsordner für temporäre Build-Dateien (Standard: build/pyinstaller)",
    )
    parser.add_argument(
        "--name",
        default="flx-panel",
        help="Dateiname ohne Endung (Standard: flx-panel -> flx-panel.exe)",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Konsolenfenster beibehalten (für Fehlersuche; Standard: reines GUI-Fenster)",
    )
    args = parser.parse_args(argv)

    try:
        import PyInstaller.__main__ as pyi_main
    except ImportError:
        print(
            "Fehler: PyInstaller ist nicht installiert.\n"
            "Starte den Build mit:\n"
            "  uv run --package playback-panel --extra build flx-panel-build",
            file=sys.stderr,
        )
        return 1

    entry_script = Path(__file__).resolve().with_name("__main__.py")
    dist_dir = Path(args.dist_dir).resolve()
    work_dir = Path(args.work_dir).resolve()

    pyi_args = build_pyinstaller_args(
        entry_script=entry_script,
        dist_dir=dist_dir,
        work_dir=work_dir,
        name=args.name,
        console=args.console,
    )
    pyi_main.run(pyi_args)

    suffix = ".exe" if sys.platform == "win32" else ""
    output_bin = dist_dir / f"{args.name}{suffix}"
    print(f"Erfolgreich gebaut: {output_bin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Tests for Windows Autostart management, AppSettings, CLI flags and .exe builder args."""

from __future__ import annotations

import io
from pathlib import Path

from playback_panel.autostart import (
    AutostartManager,
    InMemoryRegistryBackend,
    UnsupportedRegistryBackend,
    build_autostart_command,
)
from playback_panel.build_exe import build_pyinstaller_args
from playback_panel.cli import main
from playback_panel.state import MAX_LOG_BYTES, AppSettings, append_event_log

EXAMPLE_CONFIG = Path(__file__).resolve().parents[3] / "shows" / "playbacks.example.yaml"


def test_build_autostart_command_for_frozen_exe_quotes_paths(tmp_path: Path) -> None:
    exe = tmp_path / "Program Files" / "FLX Panel" / "flx-panel.exe"
    cfg = tmp_path / "Meine Shows" / "kleines event.yaml"
    cmd = build_autostart_command(cfg, executable=exe, frozen=True)
    assert "flx-panel.exe" in cmd
    assert "--config" in cmd
    assert "kleines event.yaml" in cmd
    assert "-m playback_panel" not in cmd


def test_build_autostart_command_for_python_script_prefers_pythonw(tmp_path: Path) -> None:
    py = tmp_path / "python.exe"
    pyw = tmp_path / "pythonw.exe"
    py.write_text("", encoding="utf-8")
    pyw.write_text("", encoding="utf-8")
    cmd = build_autostart_command(EXAMPLE_CONFIG, executable=py, frozen=False)
    assert "pythonw.exe" in cmd
    assert "-m playback_panel" in cmd
    assert "--config" in cmd


def test_autostart_manager_enable_status_disable(tmp_path: Path) -> None:
    backend = InMemoryRegistryBackend()
    mgr = AutostartManager(backend=backend)
    assert mgr.supported
    assert not mgr.is_enabled()

    written = mgr.enable(
        config_path=EXAMPLE_CONFIG, executable=tmp_path / "flx-panel.exe", frozen=True
    )
    assert mgr.is_enabled()
    assert mgr.current_command() == written

    mgr.disable()
    assert not mgr.is_enabled()
    assert mgr.current_command() is None


def test_cli_check_and_autostart_commands(tmp_path: Path) -> None:
    out = io.StringIO()
    err = io.StringIO()
    rc = main(["--check", str(EXAMPLE_CONFIG)], out=out, err=err)
    assert rc == 0
    assert "OK:" in out.getvalue()

    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("buttons: 123\n", encoding="utf-8")
    out_bad = io.StringIO()
    rc_bad = main(["--check", str(bad_file)], out=out_bad, err=err)
    assert rc_bad == 1
    assert "Fehler:" in out_bad.getvalue()

    # CLI autostart lifecycle with injected backend
    mgr = AutostartManager(backend=InMemoryRegistryBackend())
    out_auto = io.StringIO()
    assert (
        main(
            ["--autostart", "enable", "--config", str(EXAMPLE_CONFIG)],
            out=out_auto,
            err=err,
            autostart=mgr,
        )
        == 0
    )
    assert mgr.is_enabled()

    out_status = io.StringIO()
    assert main(["--autostart", "status"], out=out_status, err=err, autostart=mgr) == 0
    assert "aktiv" in out_status.getvalue()

    assert main(["--autostart", "disable"], out=out_auto, err=err, autostart=mgr) == 0
    assert not mgr.is_enabled()

    # Unsupported OS returns error code 1 on enable, 0 on status
    unsupported = AutostartManager(backend=UnsupportedRegistryBackend())
    assert main(["--autostart", "status"], out=io.StringIO(), err=err, autostart=unsupported) == 0
    assert main(["--autostart", "enable"], out=io.StringIO(), err=err, autostart=unsupported) == 1


def test_cli_handles_none_stdout_like_windowed_exe(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdout", None)
    monkeypatch.setattr("sys.stderr", None)
    rc = main(["--check", str(EXAMPLE_CONFIG)])
    assert rc == 0


def test_app_settings_and_log_rotation(tmp_path: Path) -> None:
    s = AppSettings(last_config_path="/shows/a.yaml", dry_run=True)
    s.save(tmp_path)
    loaded = AppSettings.load(tmp_path)
    assert loaded.last_config_path == "/shows/a.yaml"
    assert loaded.dry_run is True

    log_file = tmp_path / "events.log"
    log_file.write_bytes(b"x" * (MAX_LOG_BYTES + 10))
    append_event_log("neue zeile", directory=tmp_path)
    assert (tmp_path / "events.prev.log").exists()
    assert log_file.read_text(encoding="utf-8") == "neue zeile\n"


def test_pyinstaller_args_include_windowed_and_zeros_osc(tmp_path: Path) -> None:
    args = build_pyinstaller_args(
        entry_script=tmp_path / "__main__.py",
        dist_dir=tmp_path / "dist",
        work_dir=tmp_path / "build",
        name="flx-panel",
        console=False,
    )
    assert "--onefile" in args
    assert "--windowed" in args
    assert "zeros_osc" in args
    assert "playback_panel" in args

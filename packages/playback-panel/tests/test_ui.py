"""GUI widget and interaction tests for PlaybackPanelApp and ConfigEditorWindow."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import pytest

from mock_console.server import MockConsole
from playback_panel.autostart import AutostartManager, InMemoryRegistryBackend
from playback_panel.config import (
    ButtonConfig,
    ConsoleConfig,
    PanelConfig,
    default_starter_config,
    load_config,
)
from playback_panel.controller import PanelController
from playback_panel.state import AppSettings
from playback_panel.ui.app import PlaybackPanelApp, optimal_grid_columns


@pytest.fixture
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tkinter display not available in this environment: {exc}")
    root.withdraw()
    yield root
    if root.winfo_exists():
        root.destroy()


def test_optimal_grid_columns_scales_from_1_to_12() -> None:
    assert optimal_grid_columns(1) == 1
    assert optimal_grid_columns(2) == 2
    assert optimal_grid_columns(4) == 2
    assert optimal_grid_columns(6) == 3
    assert optimal_grid_columns(9) == 3
    assert optimal_grid_columns(12) == 4


def test_operator_window_renders_only_configured_buttons_and_sends_osc(
    tk_root: tk.Tk, mock_console: MockConsole, tmp_path: Path
) -> None:
    cfg = default_starter_config(host="127.0.0.1")
    cfg.console.port = mock_console.port
    assert len(cfg.active_buttons) == 4

    with PanelController(cfg, app_data_dir=tmp_path) as ctrl:
        app = PlaybackPanelApp(
            tk_root,
            ctrl,
            settings=AppSettings(),
            autostart=AutostartManager(backend=InMemoryRegistryBackend()),
            app_data_dir=tmp_path,
            enable_timers=False,
        )
        tk_root.update_idletasks()

        # 4 configured buttons -> exactly 4 cards rendered (not 12!)
        assert len(app.cards) == 4

        # Clicking card 0 ON sends /zeros/playback/level/1/100/1.5, OFF sends .../1/0/1.5
        app.cards[0].btn_on.invoke()
        assert "EIN" in app.cards[0].state_lbl.cget("text")

        app.cards[0].btn_off.invoke()
        assert "AUS" in app.cards[0].state_lbl.cget("text")

        received = mock_console.wait_for(2, timeout=2.0)
        assert [m.address for m in received] == [
            "/zeros/playback/level/1/100/1.5",
            "/zeros/playback/level/1/0/1.5",
        ]

        # Lock mode disables configuration/dry-run buttons while keeping playback buttons active
        app.toggle_lock()
        assert app.locked is True
        app.open_editor()
        assert app._editor_win is None
        app.cards[3].btn_on.invoke()
        received_after_lock = mock_console.wait_for(3, timeout=2.0)
        assert received_after_lock[2].address == "/zeros/cue/go/10/1"


def test_12_buttons_with_disabled_slots_and_editor_save_workflow(
    tk_root: tk.Tk, tmp_path: Path
) -> None:
    cfg_file = tmp_path / "twelve.yaml"
    buttons = [
        ButtonConfig(
            name=f"Licht {i}",
            description=f"Beschreibung {i}",
            playback=i,
            enabled=(i <= 6),
        )
        for i in range(1, 13)
    ]
    cfg = PanelConfig(console=ConsoleConfig(host="127.0.0.1"), buttons=buttons)

    reg = InMemoryRegistryBackend()
    autostart = AutostartManager(backend=reg)

    with PanelController(cfg, config_path=cfg_file, dry_run=True, app_data_dir=tmp_path) as ctrl:
        ctrl.save_to_file(cfg, cfg_file)
        app = PlaybackPanelApp(
            tk_root,
            ctrl,
            settings=AppSettings(),
            autostart=autostart,
            app_data_dir=tmp_path,
            enable_timers=False,
        )
        tk_root.update_idletasks()
        # 12 slots programmed, 6 enabled -> 6 cards shown
        assert len(app.cards) == 6

        # Open editor, clear slot 12 (index 11), enable slot 7 (index 6), enable autostart, save
        app.open_editor()
        editor = app._editor_win
        assert editor is not None
        editor._select_slot(6)
        editor.var_btn_enabled.set(True)
        editor.var_btn_desc.set("Neu aktiviert im Dialog")
        editor._on_form_changed()

        editor._select_slot(11)
        editor._clear_current_slot()

        editor.var_autostart.set(True)
        editor._on_save()
        tk_root.update_idletasks()

        # Now 7 active cards in main window, 11 total buttons saved on disk, autostart enabled!
        assert len(app.cards) == 7
        assert autostart.is_enabled()
        reloaded, _ = load_config(cfg_file)
        assert len(reloaded.buttons) == 11
        assert len(reloaded.active_buttons) == 7
        assert reloaded.buttons[6].description == "Neu aktiviert im Dialog"

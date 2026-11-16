"""Integration tests sending OSC from PanelController to mock-console on 127.0.0.1."""

from __future__ import annotations

import io
from pathlib import Path

from mock_console.server import MockConsole
from playback_panel.config import (
    ButtonConfig,
    ConsoleConfig,
    PanelConfig,
    UiConfig,
    save_config,
)
from playback_panel.controller import PanelController


def _make_test_config(port: int) -> PanelConfig:
    return PanelConfig(
        title="Test Event",
        console=ConsoleConfig(host="127.0.0.1", port=port, transport="udp"),
        ui=UiConfig(show_all_off=True, startup_delay_s=0.1),
        buttons=[
            ButtonConfig(
                name="Bühne Hell",
                description="Hauptlicht",
                mode="playback_level",
                playback=1,
                on_level=100,
                off_level=0,
                auto_on_at_startup=True,
            ),
            ButtonConfig(
                name="Ambiente",
                mode="playback_level",
                playback=2,
                on_level=65,
                off_level=0,
                on_fade="2",
                off_fade="3",
            ),
            ButtonConfig(
                name="Reserve versteckt",
                enabled=False,
                mode="playback_level",
                playback=9,
                on_level=100,
                off_level=0,
            ),
            ButtonConfig(
                name="Kombi-Szene",
                mode="custom",
                on_commands=("/zeros/cue/go/10/1", "/zeros/playback/go/4"),
                off_commands=("/zeros/cue/go/10/2", "/zeros/playback/release/4"),
            ),
        ],
    )


def test_trigger_on_and_off_sends_expected_osc_to_mock_console(
    mock_console: MockConsole, tmp_path: Path
) -> None:
    log_buf = io.StringIO()
    cfg = _make_test_config(mock_console.port)
    # 4 buttons total, 3 active (1 disabled)
    assert len(cfg.active_buttons) == 3

    with PanelController(cfg, out=log_buf, app_data_dir=tmp_path / "appdata") as ctrl:
        ctrl.trigger_active_button(0, "on")
        assert ctrl.button_states[0] == "on"

        ctrl.trigger_active_button(0, "off")
        assert ctrl.button_states[0] == "off"

        ctrl.trigger_active_button(1, "on")
        ctrl.trigger_active_button(2, "on")

        received = mock_console.wait_for(5, timeout=2.0)
        assert [m.address for m in received] == [
            "/zeros/playback/level/1/100",
            "/zeros/playback/level/1/0",
            "/zeros/playback/level/2/65/2",
            "/zeros/cue/go/10/1",
            "/zeros/playback/go/4",
        ]
        assert all(m.accepted for m in received)

    lines = log_buf.getvalue().strip().splitlines()
    assert len(lines) == 5
    assert 'quelle=flx-panel kanal=- note=- name="Bühne Hell (EIN)"' in lines[0]
    assert "adresse=/zeros/playback/level/1/100" in lines[0]
    assert lines[0].endswith("gesendet")
    assert (tmp_path / "appdata" / "events.log").exists()


def test_all_off_and_startup_actions(mock_console: MockConsole, tmp_path: Path) -> None:
    cfg = _make_test_config(mock_console.port)
    with PanelController(cfg, app_data_dir=tmp_path / "appdata") as ctrl:
        startup_sent = ctrl.trigger_startup_actions()
        assert len(startup_sent) == 1
        assert ctrl.button_states[0] == "on"

        all_off_sent = ctrl.trigger_all_off()
        # 3 active buttons: button 0 (1 cmd), button 1 (1 cmd), button 2 (2 cmds) -> 4 packets
        assert len(all_off_sent) == 4

        received = mock_console.wait_for(5, timeout=2.0)
        assert [m.address for m in received] == [
            "/zeros/playback/level/1/100",
            "/zeros/playback/level/1/0",
            "/zeros/playback/level/2/0/3",
            "/zeros/cue/go/10/2",
            "/zeros/playback/release/4",
        ]
        assert all(ctrl.button_states[i] == "off" for i in range(3))


def test_dry_run_sends_no_network_packets(mock_console: MockConsole, tmp_path: Path) -> None:
    cfg = _make_test_config(mock_console.port)
    with PanelController(cfg, dry_run=True, app_data_dir=tmp_path / "appdata") as ctrl:
        entries = ctrl.trigger_active_button(0, "on")
        assert len(entries) == 1
        assert entries[0].outcome == "DRY-RUN nicht gesendet"
        assert mock_console.messages == []


def test_live_file_reload_by_content_hash_keeps_old_config_on_error(
    mock_console: MockConsole, tmp_path: Path
) -> None:
    cfg_path = tmp_path / "show.yaml"
    cfg = _make_test_config(mock_console.port)
    save_config(cfg, cfg_path)

    with PanelController(app_data_dir=tmp_path / "appdata") as ctrl:
        ctrl.load_from_file(cfg_path)
        assert len(ctrl.config.active_buttons) == 3

        reloaded, err = ctrl.reload_if_changed()
        assert not reloaded and err is None

        # Valid change on disk -> reloaded
        cfg.buttons[0].on_level = 85
        save_config(cfg, cfg_path)
        reloaded, err = ctrl.reload_if_changed()
        assert reloaded and err is None
        assert ctrl.config.active_buttons[0].on_level == 85

        # Invalid edit on disk -> rejected, previous config stays active!
        cfg_path.write_text("console:\n  host: 127.0.0.1\nbuttons: 'kaputt'\n", encoding="utf-8")
        reloaded, err = ctrl.reload_if_changed()
        assert not reloaded and err is not None
        assert ctrl.config.active_buttons[0].on_level == 85

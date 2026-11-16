"""Tests for playback-panel configuration schema, validation and YAML roundtrip."""

from __future__ import annotations

from pathlib import Path

import pytest

from playback_panel.config import (
    MAX_BUTTONS,
    ButtonConfig,
    ConsoleConfig,
    PanelConfig,
    check,
    check_file,
    default_starter_config,
    load_config,
    save_config,
)
from zeros_osc import ZerosValueError

EXAMPLE_CONFIG = Path(__file__).resolve().parents[3] / "shows" / "playbacks.example.yaml"


def test_example_config_is_valid() -> None:
    assert EXAMPLE_CONFIG.exists()
    res = check_file(EXAMPLE_CONFIG)
    assert res.ok, res.errors
    cfg, _ = load_config(EXAMPLE_CONFIG)
    # Example has 4 configured buttons -> exactly 4 active buttons
    assert len(cfg.buttons) == 4
    assert len(cfg.active_buttons) == 4
    # First 3 buttons use playback_level (status vermutet -> surfaced as warnings)
    assert any("vermutet" in w for w in res.warnings)


def test_minimal_playback_button_defaults_to_100_on_and_0_off_same_playback() -> None:
    raw = {
        "console": {"host": "127.0.0.1", "port": 8830, "transport": "udp"},
        "buttons": [
            {"name": "Frontlicht", "playback": 7},
        ],
    }
    res = check(raw)
    assert res.ok, res.errors

    # Save & reload via temp dict check
    from playback_panel.config import parse_config

    cfg, _ = parse_config(raw)
    assert cfg is not None
    btn = cfg.buttons[0]
    assert btn.mode == "playback_level"
    assert btn.playback == 7
    assert btn.on_level == 100
    assert btn.off_level == 0
    assert btn.resolve_on_commands() == ["/zeros/playback/level/7/100"]
    assert btn.resolve_off_commands() == ["/zeros/playback/level/7/0"]


def test_fade_shorthand_and_separate_on_off_fades() -> None:
    from playback_panel.config import parse_config

    raw = {
        "console": {"host": "127.0.0.1"},
        "buttons": [
            {"name": "Sanft", "playback": 2, "on_level": 80, "fade": 2.5},
            {
                "name": "Getrennt",
                "playback": 3,
                "on_level": 100,
                "off_level": 10,
                "on_fade": 1,
                "off_fade": 4.5,
            },
        ],
    }
    cfg, res = parse_config(raw)
    assert res.ok, res.errors
    assert cfg is not None
    assert cfg.buttons[0].resolve_on_commands() == ["/zeros/playback/level/2/80/2.5"]
    assert cfg.buttons[0].resolve_off_commands() == ["/zeros/playback/level/2/0/2.5"]
    assert cfg.buttons[1].resolve_on_commands() == ["/zeros/playback/level/3/100/1"]
    assert cfg.buttons[1].resolve_off_commands() == ["/zeros/playback/level/3/10/4.5"]


def test_all_four_button_modes_resolve_valid_zeros_addresses() -> None:
    from playback_panel.config import parse_config

    raw = {
        "console": {"host": "127.0.0.1"},
        "buttons": [
            {"name": "Level", "mode": "playback_level", "playback": 1, "on_level": 90},
            {
                "name": "GoRelease",
                "mode": "playback_go_release",
                "playback": 4,
                "off_action": "release",
            },
            {
                "name": "GoPause",
                "mode": "playback_go_release",
                "playback": 5,
                "off_action": "pause",
            },
            {
                "name": "CuePair",
                "mode": "cue_pair",
                "playback": 10,
                "on_cue": 1,
                "off_cue": 2.5,
            },
            {
                "name": "CustomMulti",
                "mode": "custom",
                "on_commands": ["/zeros/cue/go/1/1", "/zeros/playback/level/2/100"],
                "off_commands": ["/zeros/playback/release/1", "/zeros/playback/level/2/0"],
            },
        ],
    }
    cfg, res = parse_config(raw)
    assert res.ok, res.errors
    assert cfg is not None

    b0, b1, b2, b3, b4 = cfg.buttons
    assert b0.resolve_on_commands() == ["/zeros/playback/level/1/90"]
    assert b0.resolve_off_commands() == ["/zeros/playback/level/1/0"]
    assert b1.resolve_on_commands() == ["/zeros/playback/go/4"]
    assert b1.resolve_off_commands() == ["/zeros/playback/release/4"]
    assert b2.resolve_off_commands() == ["/zeros/playback/pause/5"]
    assert b3.resolve_on_commands() == ["/zeros/cue/go/10/1"]
    assert b3.resolve_off_commands() == ["/zeros/cue/go/10/2.5"]
    assert b3.warnings() == []  # cue_go has status belegt!
    assert len(b4.resolve_on_commands()) == 2
    assert len(b4.resolve_off_commands()) == 2


def test_max_12_buttons_enforced_and_disabled_buttons_filtered() -> None:
    from playback_panel.config import parse_config

    twelve = [{"name": f"PB {i}", "playback": i, "enabled": i <= 4} for i in range(1, 13)]
    cfg, res = parse_config({"console": {"host": "127.0.0.1"}, "buttons": twelve})
    assert res.ok, res.errors
    assert cfg is not None
    assert len(cfg.buttons) == MAX_BUTTONS == 12
    assert len(cfg.active_buttons) == 4

    thirteen = [{"name": f"PB {i}", "playback": i} for i in range(1, 14)]
    _, res_too_many = parse_config({"console": {"host": "127.0.0.1"}, "buttons": thirteen})
    assert not res_too_many.ok
    assert any("maximal 12" in e for e in res_too_many.errors)


@pytest.mark.parametrize(
    "bad_data",
    [
        "not-a-dict",
        {"buttons": []},
        {"console": {"host": "127.0.0.1", "port": True}, "buttons": []},
        {"console": {"host": " 127.0.0.1 "}, "buttons": []},
        {"console": {"host": "127.0.0.1", "transport": "http"}, "buttons": []},
        {
            "console": {"host": "127.0.0.1"},
            "buttons": [{"name": "BadPB", "playback": 97}],
        },
        {
            "console": {"host": "127.0.0.1"},
            "buttons": [{"name": "BadLvl", "playback": 1, "on_level": 105}],
        },
        {
            "console": {"host": "127.0.0.1"},
            "buttons": [
                {
                    "name": "Invented",
                    "mode": "custom",
                    "on_commands": ["/zeros/invented/1"],
                    "off_commands": ["/zeros/blackout/0"],
                }
            ],
        },
        {
            "console": {"host": "127.0.0.1"},
            "buttons": [
                {"id": "dup", "name": "A", "playback": 1},
                {"id": "dup", "name": "B", "playback": 2},
            ],
        },
    ],
)
def test_invalid_configs_are_rejected(bad_data: object) -> None:
    res = check(bad_data)
    assert not res.ok


def test_save_and_load_roundtrip_and_utf8_check(tmp_path: Path) -> None:
    cfg = default_starter_config(host="127.0.0.1")
    cfg.buttons[0].description = "Wärmeres Licht für Begrüßung & Übergänge"
    target = tmp_path / "event.yaml"
    save_config(cfg, target)

    loaded, res = load_config(target)
    assert res.ok
    assert loaded.title == cfg.title
    assert loaded.console == ConsoleConfig(host="127.0.0.1", port=8830, transport="udp")
    assert loaded.buttons[0].description == "Wärmeres Licht für Begrüßung & Übergänge"
    assert len(loaded.active_buttons) == 4

    # Non-UTF-8 file must be rejected cleanly with German error message
    bad_encoding = tmp_path / "latin1.yaml"
    bad_encoding.write_bytes(
        "title: 'Bühne'\nconsole:\n  host: 127.0.0.1\nbuttons: []\n".encode("latin-1")
    )
    res_enc = check_file(bad_encoding)
    assert not res_enc.ok
    assert any("UTF-8" in e for e in res_enc.errors)
    with pytest.raises(ZerosValueError, match="UTF-8"):
        load_config(bad_encoding)


def test_save_refuses_invalid_panel_config(tmp_path: Path) -> None:
    bad = PanelConfig(
        console=ConsoleConfig(host="127.0.0.1"),
        buttons=[ButtonConfig(name="Invalid", playback=999)],
    )
    with pytest.raises(ZerosValueError):
        save_config(bad, tmp_path / "out.yaml")

"""Graphical playback control panel for the Zero 88 FLX S48.

Builds on ``zeros_osc`` for all OSC command construction, validation and network
transport. Only commands from ``docs/02-flx-osc-referenz.md`` are allowed.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .autostart import AutostartManager, build_autostart_command
from .config import (
    ACCENT_COLORS,
    BUTTON_MODES,
    MAX_BUTTONS,
    RELEASE_ACTIONS,
    WINDOW_MODES,
    ButtonConfig,
    CheckResult,
    ConsoleConfig,
    PanelConfig,
    UiConfig,
    check,
    check_file,
    default_starter_config,
    load_config,
    save_config,
)
from .controller import LogEntry, PanelController

__all__ = [
    "ACCENT_COLORS",
    "BUTTON_MODES",
    "MAX_BUTTONS",
    "RELEASE_ACTIONS",
    "WINDOW_MODES",
    "AutostartManager",
    "ButtonConfig",
    "CheckResult",
    "ConsoleConfig",
    "LogEntry",
    "PanelConfig",
    "PanelController",
    "UiConfig",
    "__version__",
    "build_autostart_command",
    "check",
    "check_file",
    "default_starter_config",
    "load_config",
    "save_config",
]

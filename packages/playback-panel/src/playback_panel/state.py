"""Per-user state persistence (last opened configuration and rotating event log)."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

APP_DIR_NAME = "flx-playback-panel"
MAX_LOG_BYTES = 512 * 1024  # 512 KiB cap per log file


def default_app_data_dir() -> Path:
    """Return OS-standard per-user application data directory."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / APP_DIR_NAME
        return Path.home() / "AppData" / "Roaming" / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / APP_DIR_NAME
    return Path.home() / ".config" / APP_DIR_NAME


@dataclass
class AppSettings:
    """User-level settings persisted across launches."""

    last_config_path: str | None = None
    dry_run: bool = False
    language: str = "de"

    @classmethod
    def load(cls, directory: Path | None = None) -> AppSettings:
        base = directory or default_app_data_dir()
        settings_file = base / "settings.json"
        try:
            raw = json.loads(settings_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        last_cfg = raw.get("last_config_path")
        dry_run = raw.get("dry_run", False)
        lang_raw = raw.get("language", "de")
        lang = lang_raw if isinstance(lang_raw, str) and lang_raw in ("de", "en", "ro") else "de"
        return cls(
            last_config_path=last_cfg if isinstance(last_cfg, str) and last_cfg else None,
            dry_run=bool(dry_run) if isinstance(dry_run, bool) else False,
            language=lang,
        )

    def save(self, directory: Path | None = None) -> None:
        base = directory or default_app_data_dir()
        lang = self.language if self.language in ("de", "en", "ro") else "de"
        try:
            base.mkdir(parents=True, exist_ok=True)
            settings_file = base / "settings.json"
            payload = {
                "last_config_path": self.last_config_path,
                "dry_run": self.dry_run,
                "language": lang,
            }
            settings_file.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError:
            # Non-fatal if user profile directory is read-only.
            pass


def append_event_log(line: str, directory: Path | None = None) -> None:
    """Append a structured log line to ``events.log`` with simple size rotation."""
    base = directory or default_app_data_dir()
    try:
        base.mkdir(parents=True, exist_ok=True)
        log_path = base / "events.log"
        if log_path.exists() and log_path.stat().st_size >= MAX_LOG_BYTES:
            backup = base / "events.prev.log"
            log_path.replace(backup)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass

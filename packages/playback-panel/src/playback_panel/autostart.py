"""Cross-platform Autostart integration for Windows and Linux.

* **Windows**: ``HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run`` via standard-library
  ``winreg`` (no administrator rights needed).
* **Linux**: Freedesktop XDG Autostart ``~/.config/autostart/<name>.desktop``
  (respecting ``$XDG_CONFIG_HOME``, no root rights needed; supported by GNOME, KDE Plasma,
  XFCE, Cinnamon, MATE, LXQt, Raspberry Pi OS, etc.).
* **Tests / Unsupported OS**: ``InMemoryRegistryBackend`` or ``UnsupportedRegistryBackend``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Protocol

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
DEFAULT_ENTRY_NAME = "FLXPlaybackPanel"
_XDG_RESERVED_CHARS = frozenset(" \t\n\"'\\><~|&;$*?#()`")


class AutostartNotSupportedError(OSError):
    """Raised when autostart is requested on an unsupported operating system."""


class RegistryBackend(Protocol):
    """Minimal key-value interface for per-user autostart storage."""

    @property
    def supported(self) -> bool: ...

    def get_value(self, name: str) -> str | None: ...

    def set_value(self, name: str, command: str) -> None: ...

    def delete_value(self, name: str) -> None: ...


class InMemoryRegistryBackend:
    """In-memory backend for unit tests on any operating system."""

    supported = True

    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self._values: dict[str, str] = dict(initial or {})

    def get_value(self, name: str) -> str | None:
        return self._values.get(name)

    def set_value(self, name: str, command: str) -> None:
        self._values[name] = command

    def delete_value(self, name: str) -> None:
        self._values.pop(name, None)


class UnsupportedRegistryBackend:
    """Fallback backend on operating systems without configured autostart support."""

    supported = False

    def get_value(self, name: str) -> str | None:
        return None

    def set_value(self, name: str, command: str) -> None:
        raise AutostartNotSupportedError(
            "System-Autostart ist nur unter Windows und Linux verfügbar."
        )

    def delete_value(self, name: str) -> None:
        raise AutostartNotSupportedError(
            "System-Autostart ist nur unter Windows und Linux verfügbar."
        )


class WindowsRegistryBackend:
    """Real Windows HKCU Run key backend using ``winreg``."""

    supported = True

    def get_value(self, name: str) -> str | None:
        import winreg  # type: ignore[import-not-found]

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
                value, reg_type = winreg.QueryValueEx(key, name)
                if reg_type == winreg.REG_SZ and isinstance(value, str):
                    return value
                return None
        except FileNotFoundError:
            return None

    def set_value(self, name: str, command: str) -> None:
        import winreg  # type: ignore[import-not-found]

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, command)

    def delete_value(self, name: str) -> None:
        import winreg  # type: ignore[import-not-found]

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.DeleteValue(key, name)
        except FileNotFoundError:
            pass


def default_xdg_autostart_dir() -> Path:
    """Return ``$XDG_CONFIG_HOME/autostart`` or ``~/.config/autostart``."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else (Path.home() / ".config")
    return base / "autostart"


def format_desktop_exec(argv: list[str]) -> str:
    """Format ``argv`` according to the Freedesktop Desktop Entry ``Exec=`` specification."""
    parts: list[str] = []
    for raw in argv:
        arg = raw.replace("%", "%%")
        if not arg or any(ch in _XDG_RESERVED_CHARS for ch in arg):
            escaped = (
                arg.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("`", "\\`")
                .replace("$", "\\$")
            )
            parts.append(f'"{escaped}"')
        else:
            parts.append(arg)
    return " ".join(parts)


class XdgAutostartBackend:
    """Linux Freedesktop XDG Autostart backend (``~/.config/autostart/*.desktop``)."""

    supported = True

    def __init__(self, autostart_dir: Path | None = None) -> None:
        self._dir = autostart_dir

    def _target_dir(self) -> Path:
        return self._dir if self._dir is not None else default_xdg_autostart_dir()

    def desktop_file_path(self, name: str) -> Path:
        slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
        if not slug:
            slug = "flx-playback-panel"
        return self._target_dir() / f"{slug}.desktop"

    def get_value(self, name: str) -> str | None:
        path = self.desktop_file_path(name)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            return None

        exec_cmd: str | None = None
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            low = line.lower()
            if low == "hidden=true" or low == "x-gnome-autostart-enabled=false":
                return None
            if line.startswith("Exec="):
                val = line[len("Exec=") :].strip()
                if val:
                    exec_cmd = val.replace("%%", "%")
        return exec_cmd

    def set_value(self, name: str, command: str) -> None:
        path = self.desktop_file_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        exec_line = command.replace("%", "%%")
        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Version=1.0\n"
            "Name=FLX Playback-Panel\n"
            "Comment=Zero 88 FLX S48 OSC Playback Control\n"
            f"Exec={exec_line}\n"
            "Terminal=false\n"
            "Categories=AudioVideo;Lighting;\n"
            "X-GNOME-Autostart-enabled=true\n"
        )
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
            os.replace(tmp_path, path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

    def delete_value(self, name: str) -> None:
        self.desktop_file_path(name).unlink(missing_ok=True)


def default_registry_backend() -> RegistryBackend:
    if sys.platform == "win32":
        return WindowsRegistryBackend()
    if sys.platform.startswith("linux"):
        return XdgAutostartBackend()
    return UnsupportedRegistryBackend()


def build_autostart_command(
    config_path: str | Path | None = None,
    *,
    executable: str | Path | None = None,
    frozen: bool | None = None,
    extra_args: list[str] | None = None,
    platform: str | None = None,
) -> str:
    """Build a properly quoted command line for Windows Registry or Linux XDG Autostart."""
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    exe = Path(executable) if executable is not None else Path(sys.executable)
    target_platform = platform if platform is not None else sys.platform
    is_windows_cmd = target_platform == "win32" or exe.suffix.lower() == ".exe"

    if is_frozen:
        argv = [str(exe.resolve())]
    else:
        if is_windows_cmd:
            pythonw = exe.with_name("pythonw.exe")
            runner = pythonw if exe.name.lower() == "python.exe" and pythonw.exists() else exe
        else:
            runner = exe
        argv = [str(runner), "-m", "playback_panel"]

    if config_path is not None:
        argv += ["--config", str(Path(config_path).resolve())]
    if extra_args:
        argv += list(extra_args)

    if is_windows_cmd:
        return subprocess.list2cmdline(argv)
    return format_desktop_exec(argv).replace("%%", "%")


class AutostartManager:
    """Read, enable or disable per-user Autostart (Windows Registry / Linux XDG)."""

    def __init__(
        self,
        backend: RegistryBackend | None = None,
        entry_name: str = DEFAULT_ENTRY_NAME,
    ) -> None:
        self.backend = backend or default_registry_backend()
        self.entry_name = entry_name

    @property
    def supported(self) -> bool:
        return self.backend.supported

    def current_command(self) -> str | None:
        if not self.backend.supported:
            return None
        return self.backend.get_value(self.entry_name)

    def is_enabled(self) -> bool:
        return self.current_command() is not None

    def enable(
        self,
        config_path: str | Path | None = None,
        *,
        executable: str | Path | None = None,
        frozen: bool | None = None,
        extra_args: list[str] | None = None,
    ) -> str:
        command = build_autostart_command(
            config_path=config_path,
            executable=executable,
            frozen=frozen,
            extra_args=extra_args,
        )
        self.backend.set_value(self.entry_name, command)
        return command

    def disable(self) -> None:
        if not self.backend.supported:
            return
        self.backend.delete_value(self.entry_name)

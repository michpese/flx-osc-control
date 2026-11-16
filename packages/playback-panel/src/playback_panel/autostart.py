"""Windows Autostart integration (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run).

Uses only standard-library ``winreg`` on Windows (no administrator rights needed).
On non-Windows platforms or in unit tests, a custom ``RegistryBackend`` can be injected.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Protocol

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
DEFAULT_ENTRY_NAME = "FLXPlaybackPanel"


class AutostartNotSupportedError(OSError):
    """Raised when Windows Registry autostart is requested on a non-Windows OS."""


class RegistryBackend(Protocol):
    """Minimal key-value interface for the Windows Run registry key."""

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
    """Fallback backend on macOS and Linux."""

    supported = False

    def get_value(self, name: str) -> str | None:
        return None

    def set_value(self, name: str, command: str) -> None:
        raise AutostartNotSupportedError(
            "Windows-Autostart (Registry) ist nur unter Windows verfügbar."
        )

    def delete_value(self, name: str) -> None:
        raise AutostartNotSupportedError(
            "Windows-Autostart (Registry) ist nur unter Windows verfügbar."
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


def default_registry_backend() -> RegistryBackend:
    if sys.platform == "win32":
        return WindowsRegistryBackend()
    return UnsupportedRegistryBackend()


def build_autostart_command(
    config_path: str | Path | None = None,
    *,
    executable: str | Path | None = None,
    frozen: bool | None = None,
    extra_args: list[str] | None = None,
) -> str:
    """Build a properly quoted Windows command line for autostart.

    When running as a PyInstaller ``.exe`` (``sys.frozen`` is truthy), launches the
    executable directly. When running from Python, invokes ``pythonw.exe -m playback_panel``
    if ``pythonw.exe`` sits next to ``python.exe``, otherwise ``sys.executable -m playback_panel``.
    """
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    exe = Path(executable) if executable is not None else Path(sys.executable)

    if is_frozen:
        argv = [str(exe.resolve())]
    else:
        pythonw = exe.with_name("pythonw.exe")
        runner = pythonw if exe.name.lower() == "python.exe" and pythonw.exists() else exe
        argv = [str(runner), "-m", "playback_panel"]

    if config_path is not None:
        argv += ["--config", str(Path(config_path).resolve())]
    if extra_args:
        argv += list(extra_args)

    return subprocess.list2cmdline(argv)


class AutostartManager:
    """Read, enable or disable per-user Windows Autostart for ``flx-panel``."""

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

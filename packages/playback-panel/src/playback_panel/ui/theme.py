"""Visual theme, High-DPI helpers and custom tactile widgets for Tkinter.

Designed for dim event environments: high-contrast dark slate surfaces, clear
typography, rounded tactile buttons that render identically on Windows, macOS
and Linux without OS button-chrome overrides.
"""

from __future__ import annotations

import sys
import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable

# Stage-friendly dark slate color system
BG_ROOT = "#0B1120"
BG_HEADER = "#111827"
BG_SURFACE = "#151F32"
BG_ELEVATED = "#1E293B"
BG_INPUT = "#0F172A"

BORDER_SUBTLE = "#1F2937"
BORDER_CARD = "#29384E"
BORDER_FOCUS = "#3B82F6"

TEXT_PRIMARY = "#F8FAFC"
TEXT_SECONDARY = "#94A3B8"
TEXT_MUTED = "#64748B"

# Semantic button colors
BTN_ON_BG = "#059669"
BTN_ON_HOVER = "#10B981"
BTN_ON_ACTIVE = "#047857"

BTN_OFF_BG = "#334155"
BTN_OFF_ARMED_BG = "#991B1B"
BTN_OFF_HOVER = "#DC2626"
BTN_OFF_ACTIVE = "#7F1D1D"

BTN_PRIMARY_BG = "#2563EB"
BTN_PRIMARY_HOVER = "#3B82F6"
BTN_PRIMARY_ACTIVE = "#1D4ED8"

BTN_SECONDARY_BG = "#1E293B"
BTN_SECONDARY_HOVER = "#334155"
BTN_SECONDARY_ACTIVE = "#0F172A"

BTN_DANGER_BG = "#991B1B"
BTN_DANGER_HOVER = "#DC2626"
BTN_DANGER_ACTIVE = "#7F1D1D"

BTN_DISABLED_BG = "#1E293B"
BTN_DISABLED_FG = "#475569"

STATUS_ON_BG = "#064E3B"
STATUS_ON_FG = "#34D399"
STATUS_OFF_BG = "#1E293B"
STATUS_OFF_FG = "#94A3B8"
STATUS_WARN_BG = "#451A03"
STATUS_WARN_FG = "#FBBF24"
STATUS_ERR_BG = "#450A0A"
STATUS_ERR_FG = "#F87171"

# Accent palette matching config.ACCENT_COLORS
ACCENT_HEX: dict[str, str] = {
    "amber": "#F59E0B",
    "emerald": "#10B981",
    "blue": "#3B82F6",
    "violet": "#8B5CF6",
    "rose": "#F43F5E",
    "cyan": "#06B6D4",
    "slate": "#64748B",
}

ACCENT_LABELS_DE: dict[str, str] = {
    "amber": "Bernstein",
    "emerald": "Grün",
    "blue": "Blau",
    "violet": "Violett",
    "rose": "Rot",
    "cyan": "Türkis",
    "slate": "Neutral",
}


def enable_windows_high_dpi() -> None:
    """Enable crisp High-DPI font/canvas rendering on Windows 10/11."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def pick_font_family(root: tk.Misc) -> str:
    """Choose a clean sans-serif UI font available on the current OS."""
    try:
        available = {f.lower(): f for f in tkfont.families(root)}
    except tk.TclError:
        return "TkDefaultFont"
    for candidate in (
        "Segoe UI",
        "SF Pro Text",
        "Helvetica Neue",
        "Inter",
        "DejaVu Sans",
        "Nimbus Sans L",
        "Helvetica",
    ):
        found = available.get(candidate.lower())
        if found:
            return found
    return "TkDefaultFont"


def pick_mono_family(root: tk.Misc) -> str:
    """Choose a clean monospace font for OSC addresses and logs."""
    try:
        available = {f.lower(): f for f in tkfont.families(root)}
    except tk.TclError:
        return "TkFixedFont"
    for candidate in (
        "Cascadia Mono",
        "Consolas",
        "SF Mono",
        "Menlo",
        "DejaVu Sans Mono",
        "Nimbus Mono L",
        "Courier",
    ):
        found = available.get(candidate.lower())
        if found:
            return found
    return "TkFixedFont"


def _rounded_rect_points(x1: float, y1: float, x2: float, y2: float, r: float) -> list[float]:
    r = max(0.0, min(r, (x2 - x1) / 2.0, (y2 - y1) / 2.0))
    return [
        x1 + r,
        y1,
        x2 - r,
        y1,
        x2,
        y1,
        x2,
        y1 + r,
        x2,
        y2 - r,
        x2,
        y2,
        x2 - r,
        y2,
        x1 + r,
        y2,
        x1,
        y2,
        x1,
        y2 - r,
        x1,
        y1 + r,
        x1,
        y1,
    ]


class TactileButton(tk.Canvas):
    """Rounded flat tactile button rendered on a ``tk.Canvas``.

    Avoids OS-specific native ``tk.Button`` quirks in dark themes while providing
    smooth hover, press and disabled states for mouse and touch screens.
    """

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None] | None = None,
        *,
        bg_color: str = BTN_SECONDARY_BG,
        hover_color: str = BTN_SECONDARY_HOVER,
        active_color: str = BTN_SECONDARY_ACTIVE,
        fg_color: str = TEXT_PRIMARY,
        border_color: str = "",
        parent_bg: str = BG_SURFACE,
        font: tuple[str, int] | tuple[str, int, str] = ("TkDefaultFont", 10, "bold"),
        height: int = 38,
        width: int = 110,
        radius: int = 8,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            bg=parent_bg,
            highlightthickness=0,
            bd=0,
            cursor="arrow" if disabled else "hand2",
        )
        self._text = text
        self._command = command
        self._bg_color = bg_color
        self._hover_color = hover_color
        self._active_color = active_color
        self._fg_color = fg_color
        self._border_color = border_color
        self._font = font
        self._radius = radius
        self._disabled = disabled
        self._hovered = False
        self._pressed = False

        self.bind("<Configure>", self._redraw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._redraw()

    def configure_style(
        self,
        *,
        text: str | None = None,
        bg_color: str | None = None,
        hover_color: str | None = None,
        active_color: str | None = None,
        fg_color: str | None = None,
        border_color: str | None = None,
        disabled: bool | None = None,
    ) -> None:
        if text is not None:
            self._text = text
        if bg_color is not None:
            self._bg_color = bg_color
        if hover_color is not None:
            self._hover_color = hover_color
        if active_color is not None:
            self._active_color = active_color
        if fg_color is not None:
            self._fg_color = fg_color
        if border_color is not None:
            self._border_color = border_color
        if disabled is not None:
            self._disabled = disabled
            self.configure(cursor="arrow" if disabled else "hand2")
            if disabled:
                self._hovered = False
                self._pressed = False
        self._redraw()

    def invoke(self) -> None:
        """Programmatically trigger the button action (useful for tests & shortcuts)."""
        if not self._disabled and self._command is not None:
            self._command()

    def _current_fill(self) -> str:
        if self._disabled:
            return BTN_DISABLED_BG
        if self._pressed:
            return self._active_color
        if self._hovered:
            return self._hover_color
        return self._bg_color

    def _redraw_impl(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), int(self.cget("width")))
        h = max(self.winfo_height(), int(self.cget("height")))
        if w <= 2 or h <= 2:
            return
        fill = self._current_fill()
        outline = (
            BORDER_SUBTLE
            if self._disabled
            else (self._border_color if self._border_color else fill)
        )
        pts = _rounded_rect_points(1, 1, w - 2, h - 2, self._radius)
        self.create_polygon(pts, smooth=True, splinesteps=16, fill=fill, outline=outline, width=1)
        fg = BTN_DISABLED_FG if self._disabled else self._fg_color
        self.create_text(w / 2, h / 2, text=self._text, fill=fg, font=self._font)

    def _redraw(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._redraw_impl()

    def _on_enter(self, _event: tk.Event[tk.Misc]) -> None:
        if not self._disabled:
            self._hovered = True
            self._redraw_impl()

    def _on_leave(self, _event: tk.Event[tk.Misc]) -> None:
        self._hovered = False
        self._pressed = False
        self._redraw_impl()

    def _on_press(self, _event: tk.Event[tk.Misc]) -> None:
        if not self._disabled:
            self._pressed = True
            self._redraw_impl()

    def _on_release(self, event: tk.Event[tk.Misc]) -> None:
        if self._disabled or not self._pressed:
            return
        self._pressed = False
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self._hovered = inside
        self._redraw_impl()
        if inside and self._command is not None:
            self._command()


class ScrollableFrame(tk.Frame):
    """Vertical scrollable container for configuration forms."""

    def __init__(self, master: tk.Misc, *, bg: str = BG_ROOT) -> None:
        super().__init__(master, bg=bg, highlightthickness=0, bd=0)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg, highlightthickness=0, bd=0)

        self._window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_inner_configure(self, _event: tk.Event[tk.Misc]) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event[tk.Misc]) -> None:
        self.canvas.itemconfigure(self._window_id, width=event.width)

"""Modern dark studio theme, High-DPI auto-sizing, Win11 DWM dark chrome and widgets.

Renders supersampled anti-aliased rounded surfaces via Pillow into native Tcl/Tk 8.6
PNG ``PhotoImage`` buffers (no ``_imagingtk`` C extension required) and measures real
font metrics dynamically so labels and buttons never clip at any DPI or UI language.
"""

from __future__ import annotations

import io
import sys
import tkinter as tk
import tkinter.font as tkfont
from collections import OrderedDict
from collections.abc import Callable, Sequence

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Modern Deep Obsidian / Indigo Studio Palette (no harsh light borders)
# ---------------------------------------------------------------------------
BG_ROOT = "#090B10"
BG_HEADER = "#0D1017"
BG_SURFACE = "#131722"
BG_ELEVATED = "#191F2E"
BG_INPUT = "#0B0E15"

BORDER_SUBTLE = "#161B26"
BORDER_CARD = "#1D2434"
BORDER_INPUT = "#242D42"
BORDER_FOCUS = "#6366F1"

TEXT_PRIMARY = "#F8FAFC"
TEXT_SECONDARY = "#94A3B8"
TEXT_MUTED = "#64748B"

# Semantic button colors (modern Indigo primary, Emerald ON, Slate/Crimson OFF)
BTN_ON_BG = "#059669"
BTN_ON_HOVER = "#10B981"
BTN_ON_ACTIVE = "#047857"

BTN_OFF_BG = "#1B2233"
BTN_OFF_BORDER = "#28324B"
BTN_OFF_ARMED_BG = "#B91C1C"
BTN_OFF_HOVER = "#DC2626"
BTN_OFF_ACTIVE = "#991B1B"

BTN_PRIMARY_BG = "#4F46E5"
BTN_PRIMARY_HOVER = "#6366F1"
BTN_PRIMARY_ACTIVE = "#4338CA"

BTN_SECONDARY_BG = "#181E2C"
BTN_SECONDARY_HOVER = "#232B3E"
BTN_SECONDARY_ACTIVE = "#111622"
BTN_SECONDARY_BORDER = "#252E42"

BTN_DANGER_BG = "#991B1B"
BTN_DANGER_HOVER = "#DC2626"
BTN_DANGER_ACTIVE = "#7F1D1D"

BTN_DISABLED_BG = "#141824"
BTN_DISABLED_FG = "#475569"

STATUS_ON_BG = "#064E3B"
STATUS_ON_FG = "#34D399"
STATUS_OFF_BG = "#191F2E"
STATUS_OFF_FG = "#94A3B8"
STATUS_WARN_BG = "#3B1D06"
STATUS_WARN_FG = "#FBBF24"
STATUS_ERR_BG = "#450A0A"
STATUS_ERR_FG = "#F87171"

ACCENT_HEX: dict[str, str] = {
    "amber": "#F59E0B",
    "emerald": "#10B981",
    "blue": "#3B82F6",
    "violet": "#8B5CF6",
    "rose": "#F43F5E",
    "cyan": "#06B6D4",
    "slate": "#64748B",
}


# ---------------------------------------------------------------------------
# High-DPI Scaling & Windows 10/11 Native Dark Chrome
# ---------------------------------------------------------------------------
def enable_windows_high_dpi() -> None:
    """Enable per-monitor High-DPI rendering on Windows 10/11 before creating Tk."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        # PROCESS_PER_MONITOR_DPI_AWARE (2) or PROCESS_SYSTEM_DPI_AWARE (1)
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def compute_ui_scale(widget: tk.Misc) -> float:
    """Return actual DPI scale factor relative to 96 DPI (e.g. 1.0, 1.25, 1.5, 2.0)."""
    try:
        dpi = float(widget.winfo_fpixels("1i"))
    except Exception:
        return 1.0
    return max(1.0, min(2.5, dpi / 96.0))


def scale_px(widget: tk.Misc, value: float) -> int:
    """Scale a 96-DPI pixel metric proportionally to the display's real DPI."""
    return max(1, round(value * compute_ui_scale(widget)))


def apply_scaled_geometry(
    window: tk.Wm,
    base_w: int,
    base_h: int,
    *,
    min_w: int = 720,
    min_h: int = 480,
    parent: tk.Misc | None = None,
) -> None:
    """Apply DPI-scaled size and minsize clamped safely to the user's screen."""
    assert isinstance(window, tk.Misc)
    scale = compute_ui_scale(window)
    try:
        sw = window.winfo_screenwidth()
        sh = window.winfo_screenheight()
    except tk.TclError:
        sw, sh = 1920, 1080

    max_w = max(640, int(sw * 0.92))
    max_h = max(460, int(sh * 0.88))

    target_w = min(max_w, round(base_w * scale))
    target_h = min(max_h, round(base_h * scale))
    scaled_min_w = min(target_w, round(min_w * scale))
    scaled_min_h = min(target_h, round(min_h * scale))

    window.minsize(scaled_min_w, scaled_min_h)

    if parent is not None:
        try:
            px = parent.winfo_rootx() + max(20, (parent.winfo_width() - target_w) // 2)
            py = parent.winfo_rooty() + max(20, (parent.winfo_height() - target_h) // 2)
            px = max(16, min(px, sw - target_w - 16))
            py = max(16, min(py, sh - target_h - 40))
            window.geometry(f"{target_w}x{target_h}+{px}+{py}")
            return
        except tk.TclError:
            pass

    cx = max(16, (sw - target_w) // 2)
    cy = max(16, (sh - target_h) // 2 - round(16 * scale))
    window.geometry(f"{target_w}x{target_h}+{cx}+{cy}")


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (19, 23, 34)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _hex_to_colorref(hex_color: str) -> int:
    """Convert '#RRGGBB' to Win32 COLORREF (0x00BBGGRR)."""
    r, g, b = _hex_to_rgb(hex_color)
    return (b << 16) | (g << 8) | r


_ICON_CACHE: dict[int, tk.PhotoImage] = {}


def apply_app_icon(window: tk.Wm) -> None:
    """Attach a sleek generated dark-indigo stage icon (replaces white Tk feather)."""
    assert isinstance(window, tk.Misc)
    root = window.winfo_toplevel()
    root_key = id(root.tk)
    icon = _ICON_CACHE.get(root_key)
    if icon is None:
        size = 128
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(
            (4, 4, size - 5, size - 5),
            radius=28,
            fill=(19, 23, 34, 255),
            outline=(79, 70, 229, 255),
            width=6,
        )
        # Three modern fader bars (Emerald, Amber, Indigo)
        bars = [
            (28, 52, 46, 98, (16, 185, 129, 255)),
            (55, 30, 73, 98, (245, 158, 11, 255)),
            (82, 44, 100, 98, (99, 102, 241, 255)),
        ]
        for x1, y1, x2, y2, col in bars:
            draw.rounded_rectangle((x1, 28, x2, 98), radius=8, fill=(30, 38, 56, 255))
            draw.rounded_rectangle((x1, y1, x2, y2), radius=8, fill=col)
        final = img.resize((64, 64), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        final.save(buf, format="PNG")
        try:
            icon = tk.PhotoImage(master=root, data=buf.getvalue())
            _ICON_CACHE[root_key] = icon
        except tk.TclError:
            return
    try:
        window.iconphoto(False, icon)
    except tk.TclError:
        pass


def apply_windows_dark_chrome(window: tk.Wm) -> None:
    """Style native Windows 10/11 title bar & outer border to match our dark header."""
    apply_app_icon(window)
    if sys.platform != "win32":
        return
    assert isinstance(window, tk.Misc)

    def _apply_dwm() -> None:
        try:
            import ctypes

            window.update_idletasks()
            inner_hwnd = window.winfo_id()
            user32 = ctypes.windll.user32
            dwmapi = ctypes.windll.dwmapi

            # GA_ROOT = 2 retrieves the actual top-level OS frame HWND
            hwnd = user32.GetAncestor(inner_hwnd, 2)
            if not hwnd:
                hwnd = user32.GetParent(inner_hwnd) or inner_hwnd

            dark = ctypes.c_int(1)
            # DWMWA_USE_IMMERSIVE_DARK_MODE (20 on Win10 20H1+ / Win11, 19 on older Win10)
            if dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4) != 0:
                dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(dark), 4)

            # Windows 11 (22000+): round corners + seamless header/border colors
            round_pref = ctypes.c_int(2)  # DWMWCP_ROUND
            dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(round_pref), 4)

            border_col = ctypes.c_int(_hex_to_colorref("#191F2E"))
            dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_col), 4)

            caption_col = ctypes.c_int(_hex_to_colorref(BG_HEADER))
            dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_col), 4)

            text_col = ctypes.c_int(_hex_to_colorref("#CBD5E1"))
            dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text_col), 4)
        except Exception:
            pass

    _apply_dwm()
    window.bind("<Map>", lambda _e: _apply_dwm(), add="+")


# ---------------------------------------------------------------------------
# Font Selection
# ---------------------------------------------------------------------------
def pick_font_family(root: tk.Misc) -> str:
    """Choose a clean sans-serif UI font with full Unicode support (DE/EN/RO)."""
    try:
        available = {f.lower(): f for f in tkfont.families(root)}
    except tk.TclError:
        return "TkDefaultFont"
    for candidate in (
        "Segoe UI Variable Text",
        "Segoe UI",
        "SF Pro Text",
        "Helvetica Neue",
        "Inter",
        "Roboto",
        "Ubuntu",
        "Cantarell",
        "Noto Sans",
        "DejaVu Sans",
        "Liberation Sans",
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
        "JetBrains Mono",
        "Consolas",
        "SF Mono",
        "Menlo",
        "DejaVu Sans Mono",
        "Liberation Mono",
        "Nimbus Mono L",
        "Courier",
    ):
        found = available.get(candidate.lower())
        if found:
            return found
    return "TkFixedFont"


def measure_text(widget: tk.Misc, font_spec: tuple[object, ...], text: str) -> tuple[int, int]:
    """Return exact rendered (pixel_width, linespace_height) for ``text`` in ``font_spec``."""
    try:
        f = tkfont.Font(root=widget.winfo_toplevel(), font=font_spec)  # type: ignore[arg-type]
        return f.measure(text), f.metrics("linespace")
    except tk.TclError:
        return len(text) * 8, 18


# ---------------------------------------------------------------------------
# Supersampled Anti-Aliased Rounded Shape Cache (Pillow -> Tk PNG PhotoImage)
# ---------------------------------------------------------------------------
_SHAPE_CACHE: OrderedDict[tuple[object, ...], tk.PhotoImage] = OrderedDict()
_MAX_CACHE_SIZE = 320


def _get_rounded_photo(
    master: tk.Misc,
    *,
    width: int,
    height: int,
    radius: int,
    fill: str,
    border: str = "",
    border_width: int = 1,
    top_accent: str = "",
    top_accent_height: int = 0,
    parent_bg: str = BG_ROOT,
) -> tk.PhotoImage | None:
    if width <= 2 or height <= 2:
        return None
    tk_interp_id = id(master.winfo_toplevel().tk)
    key = (
        tk_interp_id,
        width,
        height,
        radius,
        fill,
        border,
        border_width,
        top_accent,
        top_accent_height,
        parent_bg,
    )
    cached = _SHAPE_CACHE.get(key)
    if cached is not None:
        _SHAPE_CACHE.move_to_end(key)
        return cached

    ss = 2  # 2x supersampling for crisp anti-aliased edges
    sw, sh = width * ss, height * ss
    sr = max(0, min(radius * ss, sw // 2, sh // 2))

    bg_rgb = _hex_to_rgb(parent_bg)
    fill_rgb = _hex_to_rgb(fill)

    base = Image.new("RGBA", (sw, sh), (*bg_rgb, 255))

    # Build rounded mask so optional top accent clips cleanly inside rounded corners
    mask = Image.new("L", (sw, sh), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, sw - 1, sh - 1), radius=sr, fill=255)

    card_layer = Image.new("RGBA", (sw, sh), (*fill_rgb, 255))
    if top_accent and top_accent_height > 0:
        acc_rgb = _hex_to_rgb(top_accent)
        card_draw = ImageDraw.Draw(card_layer)
        card_draw.rectangle((0, 0, sw, top_accent_height * ss), fill=(*acc_rgb, 255))

    base.paste(card_layer, (0, 0), mask)

    if border and border_width > 0:
        b_rgb = _hex_to_rgb(border)
        bw = max(1, border_width * ss)
        overlay = ImageDraw.Draw(base)
        inset = bw // 2
        overlay.rounded_rectangle(
            (inset, inset, sw - 1 - inset, sh - 1 - inset),
            radius=max(1, sr - inset),
            outline=(*b_rgb, 255),
            width=bw,
        )

    final = base.resize((width, height), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    final.save(buf, format="PNG")
    try:
        photo = tk.PhotoImage(master=master.winfo_toplevel(), data=buf.getvalue())
    except tk.TclError:
        return None

    _SHAPE_CACHE[key] = photo
    while len(_SHAPE_CACHE) > _MAX_CACHE_SIZE:
        _SHAPE_CACHE.popitem(last=False)
    return photo


render_rounded_photo = _get_rounded_photo


# ---------------------------------------------------------------------------
# Modern Custom Widgets
# ---------------------------------------------------------------------------
class RoundedCard(tk.Canvas):
    """Anti-aliased rounded container hosting ``self.body`` without boxy Tk borders."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        bg_color: str = BG_SURFACE,
        border_color: str = BORDER_CARD,
        border_width: int = 1,
        accent_color: str = "",
        accent_height: int = 3,
        parent_bg: str = BG_ROOT,
        radius: int = 14,
        pad_x: int = 18,
        pad_y: int = 14,
        auto_height: bool = False,
    ) -> None:
        super().__init__(
            master,
            width=10,
            height=10,
            bg=parent_bg,
            highlightthickness=0,
            bd=0,
        )
        self._bg_color = bg_color
        self._border_color = border_color
        self._border_width = border_width
        self._accent_color = accent_color
        self._accent_height = accent_height
        self._parent_bg = parent_bg
        self._radius = radius
        self._pad_x = scale_px(master, pad_x)
        self._pad_y = scale_px(master, pad_y)
        self._auto_height = auto_height
        self._photo_ref: tk.PhotoImage | None = None

        self.body = tk.Frame(self, bg=bg_color, highlightthickness=0, bd=0)
        self._win_id = self.create_window(
            self._pad_x,
            self._pad_y,
            window=self.body,
            anchor="nw",
        )

        self.bind("<Configure>", self._on_canvas_configure)
        if self._auto_height:
            self.body.bind("<Configure>", self._on_body_configure)

    def set_card_style(
        self,
        *,
        border_color: str | None = None,
        border_width: int | None = None,
        accent_color: str | None = None,
    ) -> None:
        if border_color is not None:
            self._border_color = border_color
        if border_width is not None:
            self._border_width = border_width
        if accent_color is not None:
            self._accent_color = accent_color
        self._redraw_bg(self.winfo_width(), self.winfo_height())

    def sync_height(self) -> None:
        """Recompute card height from ``self.body`` requested height when ``auto_height`` is set."""
        if not self._auto_height or not self.winfo_exists():
            return
        self.body.update_idletasks()
        needed_h = self.body.winfo_reqheight() + 2 * self._pad_y
        cur_h = self.winfo_pixels(self.cget("height"))
        if abs(cur_h - needed_h) > 1:
            self.configure(height=needed_h)
            self._redraw_bg(self.winfo_width(), needed_h)

    def _on_body_configure(self, _event: tk.Event[tk.Misc]) -> None:
        if not self._auto_height:
            return
        needed_h = self.body.winfo_reqheight() + 2 * self._pad_y
        cur_h = self.winfo_pixels(self.cget("height"))
        if abs(cur_h - needed_h) > 1:
            self.configure(height=needed_h)
            self._redraw_bg(self.winfo_width(), needed_h)

    def _on_canvas_configure(self, event: tk.Event[tk.Misc]) -> None:
        w, h = event.width, event.height
        inner_w = max(10, w - 2 * self._pad_x)
        if self._auto_height:
            self.itemconfigure(self._win_id, width=inner_w)
            needed_h = self.body.winfo_reqheight() + 2 * self._pad_y
            cur_h = self.winfo_pixels(self.cget("height"))
            if abs(cur_h - needed_h) > 1:
                self.configure(height=needed_h)
                h = needed_h
            self.after_idle(self.sync_height)
        else:
            inner_h = max(10, h - 2 * self._pad_y)
            self.itemconfigure(self._win_id, width=inner_w, height=inner_h)
        self._redraw_bg(w, h)

    def _redraw_bg(self, w: int, h: int) -> None:
        if w <= 4 or h <= 4:
            return
        r = scale_px(self, self._radius)
        acc_h = scale_px(self, self._accent_height) if self._accent_color else 0
        photo = _get_rounded_photo(
            self,
            width=w,
            height=h,
            radius=r,
            fill=self._bg_color,
            border=self._border_color,
            border_width=self._border_width,
            top_accent=self._accent_color,
            top_accent_height=acc_h,
            parent_bg=self._parent_bg,
        )
        self.delete("card_bg")
        if photo is not None:
            self._photo_ref = photo
            self.create_image(0, 0, image=photo, anchor="nw", tags="card_bg")
            self.tag_lower("card_bg")


class TactileButton(tk.Canvas):
    """Anti-aliased rounded button that auto-sizes to its text and DPI scale."""

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
        border_color: str = BTN_SECONDARY_BORDER,
        parent_bg: str = BG_SURFACE,
        font: tuple[str, int] | tuple[str, int, str] = ("TkDefaultFont", 10, "bold"),
        height: int = 36,
        width: int = 0,
        pad_x: int = 16,
        pad_y: int = 8,
        radius: int = 9,
        disabled: bool = False,
    ) -> None:
        self._text = text
        self._command = command
        self._bg_color = bg_color
        self._hover_color = hover_color
        self._active_color = active_color
        self._fg_color = fg_color
        self._border_color = border_color
        self._parent_bg = parent_bg
        self._font = font
        self._base_min_w = width
        self._base_min_h = height
        self._pad_x = pad_x
        self._pad_y = pad_y
        self._radius = radius
        self._disabled = disabled
        self._hovered = False
        self._pressed = False
        self._photo_ref: tk.PhotoImage | None = None

        super().__init__(
            master,
            width=10,
            height=10,
            bg=parent_bg,
            highlightthickness=0,
            bd=0,
            cursor="arrow" if disabled else "hand2",
        )
        self._sync_natural_size()

        self.bind("<Configure>", self._redraw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._redraw_impl()

    def _sync_natural_size(self) -> None:
        tw, th = measure_text(self, self._font, self._text)
        px_pad_x = scale_px(self, self._pad_x)
        px_pad_y = scale_px(self, self._pad_y)
        min_w = scale_px(self, self._base_min_w) if self._base_min_w > 0 else 0
        min_h = scale_px(self, self._base_min_h)
        req_w = max(min_w, tw + 2 * px_pad_x)
        req_h = max(min_h, th + 2 * px_pad_y)
        super().configure(width=req_w, height=req_h)

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
        size_changed = False
        if text is not None and text != self._text:
            self._text = text
            size_changed = True
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
        if size_changed:
            self._sync_natural_size()
        self._redraw_impl()

    def invoke(self) -> None:
        """Programmatically trigger the button action (used by tests & shortcuts)."""
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
        req_w = int(self.cget("width"))
        req_h = int(self.cget("height"))
        w = self.winfo_width() if self.winfo_width() > 4 else req_w
        h = self.winfo_height() if self.winfo_height() > 4 else req_h
        if w <= 4 or h <= 4:
            return
        fill = self._current_fill()
        border = (
            BORDER_SUBTLE
            if self._disabled
            else (self._border_color if self._border_color and fill == self._bg_color else "")
        )
        photo = _get_rounded_photo(
            self,
            width=w,
            height=h,
            radius=scale_px(self, self._radius),
            fill=fill,
            border=border,
            border_width=1 if border else 0,
            parent_bg=self._parent_bg,
        )
        if photo is not None:
            self._photo_ref = photo
            self.create_image(0, 0, image=photo, anchor="nw")
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


class SegmentedControl(tk.Canvas):
    """Modern pill-shaped segmented control that auto-measures all option labels."""

    def __init__(
        self,
        master: tk.Misc,
        options: Sequence[tuple[str, str]],
        *,
        variable: tk.StringVar | None = None,
        command: Callable[[str], None] | None = None,
        parent_bg: str = BG_HEADER,
        track_bg: str = BG_INPUT,
        active_bg: str = BTN_PRIMARY_BG,
        font: tuple[str, int] | tuple[str, int, str] = ("TkDefaultFont", 9, "bold"),
        pad_x: int = 14,
        pad_y: int = 6,
        height: int = 32,
    ) -> None:
        self._items = list(options)
        self._variable = variable
        self._command = command
        self._parent_bg = parent_bg
        self._track_bg = track_bg
        self._active_bg = active_bg
        self._font = font
        self._pad_x = pad_x
        self._pad_y = pad_y
        self._base_h = height
        self._seg_bounds: list[tuple[str, int, int]] = []
        self._hovered_val: str | None = None
        self._photos: list[tk.PhotoImage] = []

        super().__init__(
            master,
            width=20,
            height=20,
            bg=parent_bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        if self._variable is not None:
            self._variable.trace_add("write", lambda *_a: self._redraw())
        self._recompute_layout()
        self.bind("<Configure>", lambda _e: self._redraw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_click)

    def set_options(self, options: Sequence[tuple[str, str]]) -> None:
        self._items = list(options)
        self._recompute_layout()
        self._redraw()

    def _recompute_layout(self) -> None:
        pad = scale_px(self, 3)
        seg_px = scale_px(self, self._pad_x)
        seg_py = scale_px(self, self._pad_y)
        gap = scale_px(self, 2)

        x = pad
        max_th = 16
        bounds: list[tuple[str, int, int]] = []
        for idx, (val, label) in enumerate(self._items):
            tw, th = measure_text(self, self._font, label)
            max_th = max(max_th, th)
            sw = tw + 2 * seg_px
            bounds.append((val, x, x + sw))
            x += sw + (gap if idx < len(self._items) - 1 else 0)

        total_w = x + pad
        total_h = max(scale_px(self, self._base_h), max_th + 2 * seg_py + 2 * pad)
        self._seg_bounds = bounds
        super().configure(width=total_w, height=total_h)

    def _redraw(self) -> None:
        self.delete("all")
        self._photos.clear()
        w = max(int(self.cget("width")), self.winfo_width())
        h = max(int(self.cget("height")), self.winfo_height())
        if w <= 4 or h <= 4:
            return
        pad = scale_px(self, 3)
        outer = _get_rounded_photo(
            self,
            width=w,
            height=h,
            radius=scale_px(self, 9),
            fill=self._track_bg,
            border=BORDER_CARD,
            border_width=1,
            parent_bg=self._parent_bg,
        )
        if outer is not None:
            self._photos.append(outer)
            self.create_image(0, 0, image=outer, anchor="nw")

        cur = self._variable.get() if self._variable is not None else ""
        label_map = dict(self._items)
        for val, x1, x2 in self._seg_bounds:
            selected = val == cur
            hovered = val == self._hovered_val and not selected
            if selected or hovered:
                pill_fill = self._active_bg if selected else BG_ELEVATED
                pill = _get_rounded_photo(
                    self,
                    width=max(4, x2 - x1),
                    height=max(4, h - 2 * pad),
                    radius=scale_px(self, 7),
                    fill=pill_fill,
                    parent_bg=self._track_bg,
                )
                if pill is not None:
                    self._photos.append(pill)
                    self.create_image(x1, pad, image=pill, anchor="nw")
            fg = TEXT_PRIMARY if (selected or hovered) else TEXT_SECONDARY
            self.create_text(
                (x1 + x2) / 2, h / 2, text=label_map.get(val, val), fill=fg, font=self._font
            )

    def _val_at(self, x: int) -> str | None:
        for val, x1, x2 in self._seg_bounds:
            if x1 <= x <= x2:
                return val
        return None

    def _on_motion(self, event: tk.Event[tk.Misc]) -> None:
        hit = self._val_at(event.x)
        if hit != self._hovered_val:
            self._hovered_val = hit
            self._redraw()

    def _on_leave(self, _event: tk.Event[tk.Misc]) -> None:
        if self._hovered_val is not None:
            self._hovered_val = None
            self._redraw()

    def _on_click(self, event: tk.Event[tk.Misc]) -> None:
        hit = self._val_at(event.x)
        if hit is None:
            return
        if self._variable is not None:
            self._variable.set(hit)
        if self._command is not None:
            self._command(hit)
        self._redraw()


class ToggleSwitch(tk.Frame):
    """Modern pill toggle switch with clickable label (replaces classic Checkbutton)."""

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        variable: tk.BooleanVar,
        *,
        command: Callable[[], None] | None = None,
        bg: str = BG_SURFACE,
        fg: str = TEXT_PRIMARY,
        font: tuple[str, int] | tuple[str, int, str] = ("TkDefaultFont", 10),
        active_color: str = BTN_PRIMARY_BG,
        disabled: bool = False,
    ) -> None:
        super().__init__(master, bg=bg, highlightthickness=0, bd=0)
        self._variable = variable
        self._command = command
        self._bg = bg
        self._active_color = active_color
        self._disabled = disabled
        self._photo_ref: tk.PhotoImage | None = None

        self._sw_w = scale_px(master, 40)
        self._sw_h = scale_px(master, 22)

        self.switch_canvas = tk.Canvas(
            self,
            width=self._sw_w,
            height=self._sw_h,
            bg=bg,
            highlightthickness=0,
            bd=0,
            cursor="arrow" if disabled else "hand2",
        )
        self.switch_canvas.pack(side="left", padx=(0, scale_px(master, 10)))

        self.label = tk.Label(
            self,
            text=text,
            font=font,
            fg=BTN_DISABLED_FG if disabled else fg,
            bg=bg,
            anchor="w",
            justify="left",
            cursor="arrow" if disabled else "hand2",
        )
        self.label.pack(side="left", fill="x", expand=True)

        for w in (self.switch_canvas, self.label):
            w.bind("<ButtonRelease-1>", self._toggle)

        self._variable.trace_add("write", lambda *_a: self._redraw())
        self._redraw()

    def set_text(self, text: str) -> None:
        self.label.configure(text=text)

    def _toggle(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if self._disabled:
            return
        self._variable.set(not bool(self._variable.get()))
        if self._command is not None:
            self._command()

    def _redraw(self) -> None:
        self.switch_canvas.delete("all")
        on = bool(self._variable.get())
        w, h = self._sw_w, self._sw_h

        ss = 2
        sw, sh = w * ss, h * ss
        bg_rgb = _hex_to_rgb(self._bg)
        track_hex = BTN_DISABLED_BG if self._disabled else (self._active_color if on else "#222A3D")
        track_rgb = _hex_to_rgb(track_hex)
        thumb_rgb = (120, 130, 150) if self._disabled else (248, 250, 252)

        img = Image.new("RGBA", (sw, sh), (*bg_rgb, 255))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((1, 1, sw - 2, sh - 2), radius=sh // 2, fill=(*track_rgb, 255))

        pad = 3 * ss
        d = sh - 2 * pad
        tx = sw - pad - d if on else pad
        draw.ellipse((tx, pad, tx + d, pad + d), fill=(*thumb_rgb, 255))

        final = img.resize((w, h), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        final.save(buf, format="PNG")
        try:
            photo = tk.PhotoImage(master=self.winfo_toplevel(), data=buf.getvalue())
            self._photo_ref = photo
            self.switch_canvas.create_image(0, 0, image=photo, anchor="nw")
        except tk.TclError:
            pass


class ModernEntry(tk.Canvas):
    """Rounded dark input field wrapping a borderless ``tk.Entry`` with focus glow."""

    def __init__(
        self,
        master: tk.Misc,
        textvariable: tk.StringVar,
        *,
        width_chars: int = 24,
        font: tuple[str, int] | tuple[str, int, str] = ("TkDefaultFont", 10),
        parent_bg: str = BG_SURFACE,
        justify: str = "left",
    ) -> None:
        self._parent_bg = parent_bg
        self._focused = False
        self._photo_ref: tk.PhotoImage | None = None

        sample = "M" * max(3, width_chars)
        tw, th = measure_text(master, font, sample)
        self._pad_x = scale_px(master, 10)
        self._pad_y = scale_px(master, 7)
        req_w = tw + 2 * self._pad_x
        req_h = max(scale_px(master, 34), th + 2 * self._pad_y)

        super().__init__(
            master,
            width=req_w,
            height=req_h,
            bg=parent_bg,
            highlightthickness=0,
            bd=0,
        )
        self.entry = tk.Entry(
            self,
            textvariable=textvariable,
            width=width_chars,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            selectbackground=BTN_PRIMARY_BG,
            selectforeground=TEXT_PRIMARY,
            font=font,
            justify=justify,  # type: ignore[arg-type]
            relief="flat",
            highlightthickness=0,
            bd=0,
        )
        self._win_id = self.create_window(self._pad_x, req_h / 2, window=self.entry, anchor="w")

        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Configure>", self._on_configure)
        self.bind("<Button-1>", lambda _e: self.entry.focus_set())

    def _on_focus_in(self, _event: tk.Event[tk.Misc]) -> None:
        self._focused = True
        self._redraw()

    def _on_focus_out(self, _event: tk.Event[tk.Misc]) -> None:
        self._focused = False
        self._redraw()

    def _on_configure(self, event: tk.Event[tk.Misc]) -> None:
        w, h = event.width, event.height
        inner_w = max(20, w - 2 * self._pad_x)
        self.coords(self._win_id, self._pad_x, h / 2)
        self.itemconfigure(self._win_id, width=inner_w)
        self._redraw()

    def _redraw(self) -> None:
        w = max(int(self.cget("width")), self.winfo_width())
        h = max(int(self.cget("height")), self.winfo_height())
        if w <= 4 or h <= 4:
            return
        border = BORDER_FOCUS if self._focused else BORDER_INPUT
        photo = _get_rounded_photo(
            self,
            width=w,
            height=h,
            radius=scale_px(self, 8),
            fill=BG_INPUT,
            border=border,
            border_width=2 if self._focused else 1,
            parent_bg=self._parent_bg,
        )
        self.delete("entry_bg")
        if photo is not None:
            self._photo_ref = photo
            self.create_image(0, 0, image=photo, anchor="nw", tags="entry_bg")
            self.tag_lower("entry_bg")


class ModernStepper(tk.Frame):
    """Tactile [-] [value] [+] numeric stepper replacing classic Windows Spinbox."""

    def __init__(
        self,
        master: tk.Misc,
        textvariable: tk.StringVar,
        lo: int,
        hi: int,
        *,
        font: tuple[str, int] | tuple[str, int, str] = ("TkDefaultFont", 10),
        parent_bg: str = BG_SURFACE,
    ) -> None:
        super().__init__(master, bg=parent_bg, highlightthickness=0, bd=0)
        self._var = textvariable
        self._lo = lo
        self._hi = hi

        btn_font = (font[0], font[1], "bold")
        TactileButton(
            self,
            "-",
            command=lambda: self._step(-1),
            parent_bg=parent_bg,
            font=btn_font,
            width=32,
            height=34,
            pad_x=8,
            pad_y=4,
            radius=7,
        ).pack(side="left", padx=(0, scale_px(master, 4)))

        self.field = ModernEntry(
            self,
            textvariable,
            width_chars=5,
            font=font,
            parent_bg=parent_bg,
            justify="center",
        )
        self.field.pack(side="left")

        TactileButton(
            self,
            "+",
            command=lambda: self._step(1),
            parent_bg=parent_bg,
            font=btn_font,
            width=32,
            height=34,
            pad_x=8,
            pad_y=4,
            radius=7,
        ).pack(side="left", padx=(scale_px(master, 4), 0))

    def _step(self, delta: int) -> None:
        try:
            cur = int(self._var.get().strip())
        except ValueError:
            cur = self._lo
        nxt = max(self._lo, min(self._hi, cur + delta))
        self._var.set(str(nxt))


class DarkScrollbar(tk.Canvas):
    """Minimal dark rounded scrollbar that auto-hides when content fits."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        command: Callable[..., object],
        bg: str = BG_ROOT,
    ) -> None:
        self._bar_w = scale_px(master, 8)
        super().__init__(
            master,
            width=self._bar_w,
            bg=bg,
            highlightthickness=0,
            bd=0,
        )
        self._command = command
        self._first = 0.0
        self._last = 1.0
        self._hovered = False
        self._drag_start_y: int | None = None
        self._drag_start_first: float = 0.0

        self.bind("<Configure>", lambda _e: self._redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    def set(self, first: float | str, last: float | str) -> None:
        self._first = max(0.0, min(1.0, float(first)))
        self._last = max(0.0, min(1.0, float(last)))
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        if self._last - self._first >= 0.999:
            return
        h = self.winfo_height()
        w = self.winfo_width()
        if h <= 8 or w <= 2:
            return
        y1 = int(self._first * h) + 2
        y2 = max(y1 + scale_px(self, 24), int(self._last * h) - 2)
        color = "#3E4C6E" if (self._hovered or self._drag_start_y is not None) else "#263047"
        self.create_rectangle(2, y1, w - 2, y2, fill=color, outline="")

    def _on_enter(self, _e: tk.Event[tk.Misc]) -> None:
        self._hovered = True
        self._redraw()

    def _on_leave(self, _e: tk.Event[tk.Misc]) -> None:
        self._hovered = False
        self._redraw()

    def _on_press(self, event: tk.Event[tk.Misc]) -> None:
        if self._last - self._first >= 0.999:
            return
        h = max(1, self.winfo_height())
        y1 = self._first * h
        y2 = self._last * h
        if y1 <= event.y <= y2:
            self._drag_start_y = event.y
            self._drag_start_first = self._first
        else:
            target = max(0.0, min(1.0, (event.y / h) - (self._last - self._first) / 2))
            self._command("moveto", target)

    def _on_drag(self, event: tk.Event[tk.Misc]) -> None:
        if self._drag_start_y is None:
            return
        h = max(1, self.winfo_height())
        delta = (event.y - self._drag_start_y) / h
        self._command("moveto", max(0.0, min(1.0, self._drag_start_first + delta)))

    def _on_release(self, _event: tk.Event[tk.Misc]) -> None:
        self._drag_start_y = None
        self._redraw()


class ScrollableFrame(tk.Frame):
    """Vertical scrollable container with sleek dark scrollbar and mousewheel support."""

    def __init__(self, master: tk.Misc, *, bg: str = BG_ROOT) -> None:
        super().__init__(master, bg=bg, highlightthickness=0, bd=0)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = DarkScrollbar(self, command=self.canvas.yview, bg=bg)
        self.inner = tk.Frame(self.canvas, bg=bg, highlightthickness=0, bd=0)

        self._window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y", padx=(2, 4), pady=4)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_inner_configure(self, _event: tk.Event[tk.Misc]) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event[tk.Misc]) -> None:
        self.canvas.itemconfigure(self._window_id, width=event.width)

    def _bind_wheel(self, _event: tk.Event[tk.Misc]) -> None:
        top = self.winfo_toplevel()
        top.bind_all("<MouseWheel>", self._on_mousewheel)
        top.bind_all("<Button-4>", self._on_wheel_linux_up)
        top.bind_all("<Button-5>", self._on_wheel_linux_down)

    def _unbind_wheel(self, _event: tk.Event[tk.Misc]) -> None:
        top = self.winfo_toplevel()
        top.unbind_all("<MouseWheel>")
        top.unbind_all("<Button-4>")
        top.unbind_all("<Button-5>")

    def _can_scroll(self) -> bool:
        first, last = self.canvas.yview()
        return (last - first) < 0.999

    def _on_mousewheel(self, event: tk.Event[tk.Misc]) -> None:
        if not self._can_scroll():
            return
        steps = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(steps * 2, "units")

    def _on_wheel_linux_up(self, _event: tk.Event[tk.Misc]) -> None:
        if self._can_scroll():
            self.canvas.yview_scroll(-2, "units")

    def _on_wheel_linux_down(self, _event: tk.Event[tk.Misc]) -> None:
        if self._can_scroll():
            self.canvas.yview_scroll(2, "units")

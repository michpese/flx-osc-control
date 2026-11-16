"""Main operator window for the FLX Playback-Panel (modern dark studio UI, DE/EN/RO)."""

from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox

from zeros_osc import ZerosValueError

from ..autostart import AutostartManager
from ..config import ButtonConfig, PanelConfig, default_starter_config
from ..controller import ButtonSide, LogEntry, PanelController
from ..i18n import LanguageCode, normalize_language, tr
from ..state import AppSettings
from .editor import ConfigEditorWindow
from .theme import (
    ACCENT_HEX,
    BG_ELEVATED,
    BG_HEADER,
    BG_INPUT,
    BG_ROOT,
    BG_SURFACE,
    BORDER_CARD,
    BORDER_SUBTLE,
    BTN_DANGER_ACTIVE,
    BTN_DANGER_BG,
    BTN_DANGER_HOVER,
    BTN_OFF_ACTIVE,
    BTN_OFF_ARMED_BG,
    BTN_OFF_BG,
    BTN_OFF_BORDER,
    BTN_OFF_HOVER,
    BTN_ON_ACTIVE,
    BTN_ON_BG,
    BTN_ON_HOVER,
    BTN_PRIMARY_ACTIVE,
    BTN_PRIMARY_BG,
    BTN_PRIMARY_HOVER,
    BTN_SECONDARY_BG,
    BTN_SECONDARY_BORDER,
    BTN_SECONDARY_HOVER,
    STATUS_ERR_FG,
    STATUS_OFF_BG,
    STATUS_OFF_FG,
    STATUS_ON_BG,
    STATUS_ON_FG,
    STATUS_WARN_BG,
    STATUS_WARN_FG,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    DarkScrollbar,
    RoundedCard,
    SegmentedControl,
    TactileButton,
    apply_scaled_geometry,
    apply_windows_dark_chrome,
    enable_windows_high_dpi,
    pick_font_family,
    pick_mono_family,
    scale_px,
)


def optimal_grid_columns(count: int) -> int:
    """Return balanced grid column count for 1..12 active buttons."""
    if count <= 1:
        return 1
    if count in (2, 4):
        return 2
    if count <= 9:
        return 3
    return 4


@dataclass
class _CardWidgets:
    outer: RoundedCard
    state_lbl: tk.Label
    title_lbl: tk.Label
    desc_lbl: tk.Label
    btn_on: TactileButton
    btn_off: TactileButton
    accent_hex: str


class PlaybackPanelApp:
    """Main Tkinter operator interface with High-DPI auto-sizing and DE/EN/RO localization."""

    def __init__(
        self,
        root: tk.Tk,
        controller: PanelController,
        *,
        settings: AppSettings | None = None,
        autostart: AutostartManager | None = None,
        app_data_dir: Path | None = None,
        force_locked: bool = False,
        open_editor_on_start: bool = False,
        enable_timers: bool = True,
    ) -> None:
        self.root = root
        self.controller = controller
        self._app_data_dir = app_data_dir
        self.settings = settings or AppSettings.load(app_data_dir)
        self.autostart = autostart or AutostartManager()
        self._enable_timers = enable_timers

        initial_lang = controller.config.ui.language or self.settings.language
        self.lang: LanguageCode = normalize_language(initial_lang)
        self.var_lang = tk.StringVar(master=root, value=self.lang)

        self.font_ui = pick_font_family(root)
        self.font_mono = pick_mono_family(root)

        self.locked: bool = force_locked or controller.config.ui.start_locked
        self.fullscreen: bool = False
        self.log_expanded: bool = False
        self._has_logged_event: bool = False
        self._last_entry: LogEntry | None = None
        self._editor_win: ConfigEditorWindow | None = None
        self.cards: list[_CardWidgets] = []

        self.controller._on_log = self._on_controller_log

        self.root.configure(bg=BG_ROOT)
        apply_scaled_geometry(self.root, 1140, 740, min_w=820, min_h=540)
        apply_windows_dark_chrome(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self._build_ui()
        self._bind_shortcuts()
        self.refresh_all(apply_window_mode=True)

        if self._enable_timers:
            self._schedule_startup_actions()
            self.root.after(2000, self._poll_file_changes)
        if open_editor_on_start:
            self.root.after(150, self.open_editor)

    def _t(self, key: str, **kwargs: object) -> str:
        return tr(self.lang, key, **kwargs)

    # --- UI construction ------------------------------------------------------

    def _build_ui(self) -> None:
        pad_h = scale_px(self.root, 22)
        pad_v = scale_px(self.root, 13)
        gap = scale_px(self.root, 8)

        # Seamless dark header bar
        self.header = tk.Frame(self.root, bg=BG_HEADER, padx=pad_h, pady=pad_v)
        self.header.pack(side="top", fill="x")
        tk.Frame(self.root, bg=BORDER_SUBTLE, height=1).pack(side="top", fill="x")

        left_hdr = tk.Frame(self.header, bg=BG_HEADER)
        left_hdr.pack(side="left", fill="x", expand=True)

        title_row = tk.Frame(left_hdr, bg=BG_HEADER)
        title_row.pack(fill="x")
        self.lbl_title = tk.Label(
            title_row,
            text=self._t("app_name"),
            font=(self.font_ui, 14, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_HEADER,
            anchor="w",
        )
        self.lbl_title.pack(side="left")

        self.lbl_dry_badge = tk.Label(
            title_row,
            text=f" {self._t('dry_badge')} ",
            font=(self.font_ui, 8, "bold"),
            fg=STATUS_WARN_FG,
            bg=STATUS_WARN_BG,
            padx=scale_px(self.root, 7),
            pady=scale_px(self.root, 2),
        )

        self.lbl_subtitle = tk.Label(
            left_hdr,
            text="",
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_HEADER,
            anchor="w",
        )
        self.lbl_subtitle.pack(fill="x", pady=(scale_px(self.root, 2), 0))

        # Right toolbar with auto-measuring pills + DE/EN/RO switcher
        self.toolbar = tk.Frame(self.header, bg=BG_HEADER)
        self.toolbar.pack(side="right")

        self.lang_switch = SegmentedControl(
            self.toolbar,
            (("de", "DE"), ("en", "EN"), ("ro", "RO")),
            variable=self.var_lang,
            command=self.set_language,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 8, "bold"),
            pad_x=9,
            pad_y=5,
            height=32,
        )
        self.lang_switch.pack(side="left", padx=(0, gap + scale_px(self.root, 2)))

        self.btn_all_off = TactileButton(
            self.toolbar,
            self._t("btn_all_off"),
            command=self._on_all_off,
            bg_color=BTN_DANGER_BG,
            hover_color=BTN_DANGER_HOVER,
            active_color=BTN_DANGER_ACTIVE,
            border_color="",
            parent_bg=BG_HEADER,
            font=(self.font_ui, 9, "bold"),
            height=34,
            pad_x=14,
        )
        self.btn_all_off.pack(side="left", padx=(0, gap))

        self.btn_dry_toggle = TactileButton(
            self.toolbar,
            self._t("btn_dry_off"),
            command=self.toggle_dry_run,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            border_color=BTN_SECONDARY_BORDER,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 9, "bold"),
            height=34,
            pad_x=13,
        )
        self.btn_dry_toggle.pack(side="left", padx=(0, gap))

        self.btn_file_menu = TactileButton(
            self.toolbar,
            self._t("btn_file"),
            command=self._show_file_menu,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            border_color=BTN_SECONDARY_BORDER,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 9, "bold"),
            height=34,
            pad_x=13,
        )
        self.btn_file_menu.pack(side="left", padx=(0, gap))

        self.btn_configure = TactileButton(
            self.toolbar,
            self._t("btn_configure"),
            command=self.open_editor,
            bg_color=BTN_PRIMARY_BG,
            hover_color=BTN_PRIMARY_HOVER,
            active_color=BTN_PRIMARY_ACTIVE,
            border_color="",
            parent_bg=BG_HEADER,
            font=(self.font_ui, 9, "bold"),
            height=34,
            pad_x=16,
        )
        self.btn_configure.pack(side="left", padx=(0, gap))

        self.btn_lock = TactileButton(
            self.toolbar,
            self._t("btn_unlocked"),
            command=self.toggle_lock,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            border_color=BTN_SECONDARY_BORDER,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 9, "bold"),
            height=34,
            pad_x=13,
        )
        self.btn_lock.pack(side="left")

        # File popup menu (rebuilt dynamically per active language)
        self.file_menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=BG_ELEVATED,
            fg=TEXT_PRIMARY,
            activebackground=BTN_PRIMARY_BG,
            activeforeground=TEXT_PRIMARY,
            bd=1,
            relief="flat",
            font=(self.font_ui, 10),
        )
        self._rebuild_file_menu()

        # Bottom status bar & collapsible dark log drawer
        self.bottom_wrap = tk.Frame(self.root, bg=BG_HEADER)
        self.bottom_wrap.pack(side="bottom", fill="x")

        tk.Frame(self.bottom_wrap, bg=BORDER_SUBTLE, height=1).pack(side="top", fill="x")

        status_bar = tk.Frame(
            self.bottom_wrap,
            bg=BG_HEADER,
            padx=pad_h,
            pady=scale_px(self.root, 8),
        )
        status_bar.pack(side="top", fill="x")

        self.lbl_last_event = tk.Label(
            status_bar,
            text=self._t("status_idle"),
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_HEADER,
            anchor="w",
        )
        self.lbl_last_event.pack(side="left", fill="x", expand=True)

        self.lbl_udp_hint = tk.Label(
            status_bar,
            text=self._t("status_udp_hint"),
            font=(self.font_ui, 8),
            fg=TEXT_MUTED,
            bg=BG_HEADER,
        )
        self.lbl_udp_hint.pack(side="left", padx=(scale_px(self.root, 12), scale_px(self.root, 12)))

        self.btn_log_toggle = TactileButton(
            status_bar,
            self._t("btn_log_show"),
            command=self.toggle_log_drawer,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            border_color=BTN_SECONDARY_BORDER,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 8, "bold"),
            height=28,
            pad_x=12,
            pad_y=4,
        )
        self.btn_log_toggle.pack(side="right")

        self.log_drawer = tk.Frame(
            self.bottom_wrap,
            bg=BG_INPUT,
            padx=pad_h,
            pady=scale_px(self.root, 8),
        )
        self.txt_log = tk.Text(
            self.log_drawer,
            height=4,
            bg=BG_INPUT,
            fg=TEXT_SECONDARY,
            font=(self.font_mono, 9),
            relief="flat",
            state="disabled",
            highlightthickness=1,
            highlightbackground=BORDER_CARD,
            padx=scale_px(self.root, 8),
            pady=scale_px(self.root, 6),
        )
        log_scroll = DarkScrollbar(self.log_drawer, command=self.txt_log.yview, bg=BG_INPUT)
        self.txt_log.configure(yscrollcommand=log_scroll.set)
        self.txt_log.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y", padx=(4, 0))

        # Main workspace container (cards grid or empty state)
        self.main_area = tk.Frame(
            self.root,
            bg=BG_ROOT,
            padx=scale_px(self.root, 18),
            pady=scale_px(self.root, 16),
        )
        self.main_area.pack(side="top", fill="both", expand=True)

    def _rebuild_file_menu(self) -> None:
        self.file_menu.delete(0, "end")
        self.file_menu.add_command(label=self._t("menu_new"), command=self.action_new_config)
        self.file_menu.add_command(label=self._t("menu_open"), command=self.action_open_config)
        self.file_menu.add_command(label=self._t("menu_reload"), command=self.action_reload)
        self.file_menu.add_separator()
        self.file_menu.add_command(
            label=self._t("menu_starter"), command=self.action_load_starter_demo
        )

    def _bind_shortcuts(self) -> None:
        self.root.bind("<F11>", lambda _e: self.toggle_fullscreen())
        self.root.bind("<Escape>", lambda _e: self._exit_fullscreen())
        self.root.bind("<F5>", lambda _e: self.action_reload())

    # --- Language Switching ---------------------------------------------------

    def set_language(self, lang: str) -> None:
        normalized = normalize_language(lang)
        if normalized == self.lang and self.var_lang.get() == normalized:
            return
        self.lang = normalized
        if self.var_lang.get() != normalized:
            self.var_lang.set(normalized)
        self.settings.language = normalized
        self.settings.save(self._app_data_dir)
        self._rebuild_file_menu()
        self.refresh_all()
        if self._editor_win is not None and self._editor_win.winfo_exists():
            self._editor_win.set_language(normalized)

    # --- Rendering & Refresh --------------------------------------------------

    def refresh_all(self, *, apply_window_mode: bool = False) -> None:
        cfg = self.controller.config
        app_name = self._t("app_name")
        if cfg.title.strip() == app_name:
            self.root.title(app_name)
        else:
            self.root.title(f"{cfg.title} - {app_name}")
        self.lbl_title.configure(text=cfg.title)

        file_label = (
            self.controller.config_path.name
            if self.controller.config_path is not None
            else self._t("file_unsaved")
        )
        active_n = len(cfg.active_buttons)
        active_text = self._t("active_one") if active_n == 1 else self._t("active_many", n=active_n)
        self.lbl_subtitle.configure(
            text=self._t(
                "subtitle_fmt",
                file=file_label,
                target=self.controller.target_label,
                active=active_text,
            )
        )

        # Toolbar & status labels in active language
        self.lbl_dry_badge.configure(text=f" {self._t('dry_badge')} ")
        self.btn_all_off.configure_style(text=self._t("btn_all_off"))
        self.btn_file_menu.configure_style(text=self._t("btn_file"), disabled=self.locked)
        self.btn_configure.configure_style(text=self._t("btn_configure"), disabled=self.locked)
        self.lbl_udp_hint.configure(text=self._t("status_udp_hint"))
        self.btn_log_toggle.configure_style(
            text=self._t("btn_log_hide" if self.log_expanded else "btn_log_show")
        )
        if not self._has_logged_event:
            self.lbl_last_event.configure(text=self._t("status_idle"), fg=TEXT_SECONDARY)
        elif self._last_entry is not None:
            self._render_last_event_banner(self._last_entry)

        # Dry-run indicator
        gap = scale_px(self.root, 8)
        if self.controller.dry_run:
            self.lbl_dry_badge.pack(side="left", padx=(scale_px(self.root, 10), 0))
            self.btn_dry_toggle.configure_style(
                text=self._t("btn_dry_on"),
                bg_color=STATUS_WARN_BG,
                hover_color="#5C2D0C",
                fg_color=STATUS_WARN_FG,
                border_color="",
                disabled=self.locked,
            )
        else:
            self.lbl_dry_badge.pack_forget()
            self.btn_dry_toggle.configure_style(
                text=self._t("btn_dry_off"),
                bg_color=BTN_SECONDARY_BG,
                hover_color=BTN_SECONDARY_HOVER,
                fg_color=TEXT_PRIMARY,
                border_color=BTN_SECONDARY_BORDER,
                disabled=self.locked,
            )

        # Show/hide Alle Aus
        if cfg.ui.show_all_off and active_n > 0:
            if not self.btn_all_off.winfo_ismapped():
                self.btn_all_off.pack(side="left", padx=(0, gap), before=self.btn_dry_toggle)
        else:
            self.btn_all_off.pack_forget()

        # Lock state
        if self.locked:
            self.btn_lock.configure_style(
                text=self._t("btn_locked"),
                bg_color=STATUS_WARN_BG,
                hover_color="#5C2D0C",
                fg_color=STATUS_WARN_FG,
                border_color="",
            )
        else:
            self.btn_lock.configure_style(
                text=self._t("btn_unlocked"),
                bg_color=BTN_SECONDARY_BG,
                hover_color=BTN_SECONDARY_HOVER,
                fg_color=TEXT_PRIMARY,
                border_color=BTN_SECONDARY_BORDER,
            )

        # Window attributes
        try:
            self.root.attributes("-topmost", bool(cfg.ui.always_on_top))
        except tk.TclError:
            pass

        if apply_window_mode:
            self._apply_window_mode(cfg.ui.window_mode)

        self._rebuild_cards_grid()

    def _apply_window_mode(self, mode: str) -> None:
        try:
            if mode == "fullscreen":
                self.fullscreen = True
                self.root.attributes("-fullscreen", True)
            elif mode == "maximized":
                self.fullscreen = False
                self.root.attributes("-fullscreen", False)
                if sys.platform == "win32":
                    self.root.state("zoomed")
                else:
                    try:
                        self.root.attributes("-zoomed", True)
                    except tk.TclError:
                        self.root.state("normal")
            else:
                self.fullscreen = False
                self.root.attributes("-fullscreen", False)
        except tk.TclError:
            pass

    def _rebuild_cards_grid(self) -> None:
        for child in self.main_area.winfo_children():
            child.destroy()
        self.cards.clear()

        active_buttons = self.controller.config.active_buttons
        if not active_buttons:
            self._build_empty_welcome_state()
            return

        count = len(active_buttons)
        cols = optimal_grid_columns(count)
        rows = (count + cols - 1) // cols

        grid = tk.Frame(self.main_area, bg=BG_ROOT)
        grid.pack(fill="both", expand=True)

        for c in range(cols):
            grid.columnconfigure(c, weight=1, uniform="pb_col")
        for r in range(rows):
            grid.rowconfigure(r, weight=1, uniform="pb_row")

        cell_pad = scale_px(self.root, 8)
        for idx, btn in enumerate(active_buttons):
            r, c = divmod(idx, cols)
            card = self._create_playback_card(grid, idx, btn)
            card.outer.grid(row=r, column=c, sticky="nsew", padx=cell_pad, pady=cell_pad)
            self.cards.append(card)

        self._refresh_card_states()

    def _build_empty_welcome_state(self) -> None:
        holder = tk.Frame(self.main_area, bg=BG_ROOT)
        holder.pack(fill="both", expand=True)

        card = RoundedCard(
            holder,
            bg_color=BG_SURFACE,
            border_color=BORDER_CARD,
            parent_bg=BG_ROOT,
            radius=16,
            pad_x=36,
            pad_y=32,
            auto_height=True,
        )
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.74)

        body = card.body
        tk.Label(
            body,
            text=self._t("welcome_kicker"),
            font=(self.font_ui, 8, "bold"),
            fg="#818CF8",
            bg=BG_SURFACE,
        ).pack(pady=(0, scale_px(self.root, 6)))

        title_lbl = tk.Label(
            body,
            text=self._t("welcome_title"),
            font=(self.font_ui, 16, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            justify="center",
        )
        title_lbl.pack(pady=(0, scale_px(self.root, 10)))

        desc_lbl = tk.Label(
            body,
            text=self._t("welcome_body"),
            font=(self.font_ui, 10),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            justify="center",
        )
        desc_lbl.pack(fill="x", pady=(0, scale_px(self.root, 24)))

        def _sync_wrap(event: tk.Event[tk.Misc]) -> None:
            wrap = max(scale_px(self.root, 260), event.width - scale_px(self.root, 24))
            title_lbl.configure(wraplength=wrap)
            desc_lbl.configure(wraplength=wrap)

        body.bind("<Configure>", _sync_wrap, add="+")

        actions = tk.Frame(body, bg=BG_SURFACE)
        actions.pack()
        btn_gap = scale_px(self.root, 6)

        TactileButton(
            actions,
            self._t("welcome_btn_config"),
            command=self._unlock_and_open_editor,
            bg_color=BTN_PRIMARY_BG,
            hover_color=BTN_PRIMARY_HOVER,
            active_color=BTN_PRIMARY_ACTIVE,
            border_color="",
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 10, "bold"),
            height=40,
            pad_x=20,
        ).pack(side="left", padx=btn_gap)

        TactileButton(
            actions,
            self._t("welcome_btn_open"),
            command=self.action_open_config,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            border_color=BTN_SECONDARY_BORDER,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 10, "bold"),
            height=40,
            pad_x=18,
        ).pack(side="left", padx=btn_gap)

        TactileButton(
            actions,
            self._t("welcome_btn_starter"),
            command=self.action_load_starter_demo,
            bg_color=BTN_ON_BG,
            hover_color=BTN_ON_HOVER,
            active_color=BTN_ON_ACTIVE,
            border_color="",
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 10, "bold"),
            height=40,
            pad_x=18,
        ).pack(side="left", padx=btn_gap)

    def _create_playback_card(
        self, parent: tk.Misc, active_idx: int, button: ButtonConfig
    ) -> _CardWidgets:
        accent_hex = ACCENT_HEX.get(button.color, ACCENT_HEX["amber"])

        outer = RoundedCard(
            parent,
            bg_color=BG_SURFACE,
            border_color=BORDER_CARD,
            accent_color=accent_hex,
            accent_height=3,
            parent_bg=BG_ROOT,
            radius=14,
            pad_x=16,
            pad_y=12,
            auto_height=False,
        )
        inner = outer.body

        # Top badge & status row
        meta_row = tk.Frame(inner, bg=BG_SURFACE)
        meta_row.pack(side="top", fill="x", pady=(scale_px(self.root, 2), 0))

        tk.Label(
            meta_row,
            text=f" {button.badge_text(self.lang)} ",
            font=(self.font_mono, 8, "bold"),
            fg=accent_hex,
            bg=BG_ELEVATED,
            padx=scale_px(self.root, 7),
            pady=scale_px(self.root, 3),
        ).pack(side="left")

        for tag in button.status_tags():
            tag_label = self._t(f"tag_{tag}")
            tk.Label(
                meta_row,
                text=f"[{tag_label}]",
                font=(self.font_ui, 8),
                fg=STATUS_WARN_FG,
                bg=BG_SURFACE,
                padx=scale_px(self.root, 5),
            ).pack(side="left")

        state_lbl = tk.Label(
            meta_row,
            text=f" {self._t('state_ready')} ",
            font=(self.font_ui, 8, "bold"),
            fg=TEXT_MUTED,
            bg=BG_ELEVATED,
            padx=scale_px(self.root, 8),
            pady=scale_px(self.root, 3),
        )
        state_lbl.pack(side="right")

        # Bottom tactile EIN / AUS button bar (always anchored cleanly at bottom)
        btn_row = tk.Frame(inner, bg=BG_SURFACE)
        btn_row.pack(side="bottom", fill="x", pady=(scale_px(self.root, 6), 0))
        btn_row.columnconfigure(0, weight=1, uniform=f"act_{active_idx}")
        btn_row.columnconfigure(1, weight=1, uniform=f"act_{active_idx}")

        half_gap = scale_px(self.root, 6)
        btn_on = TactileButton(
            btn_row,
            button.display_on_label(self.lang),
            command=lambda i=active_idx: self.trigger_button(i, "on"),
            bg_color=BTN_ON_BG,
            hover_color=BTN_ON_HOVER,
            active_color=BTN_ON_ACTIVE,
            border_color="",
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 10, "bold"),
            height=40,
            pad_x=14,
            radius=10,
        )
        btn_on.grid(row=0, column=0, sticky="ew", padx=(0, half_gap))

        btn_off = TactileButton(
            btn_row,
            button.display_off_label(self.lang),
            command=lambda i=active_idx: self.trigger_button(i, "off"),
            bg_color=BTN_OFF_BG,
            hover_color=BTN_OFF_HOVER,
            active_color=BTN_OFF_ACTIVE,
            border_color=BTN_OFF_BORDER,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 10, "bold"),
            height=40,
            pad_x=14,
            radius=10,
        )
        btn_off.grid(row=0, column=1, sticky="ew", padx=(half_gap, 0))

        # Middle text area (title + short description)
        text_box = tk.Frame(inner, bg=BG_SURFACE)
        text_box.pack(
            side="top",
            fill="both",
            expand=True,
            pady=(scale_px(self.root, 6), scale_px(self.root, 2)),
        )

        title_lbl = tk.Label(
            text_box,
            text=button.name,
            font=(self.font_ui, 12, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
        )
        title_lbl.pack(side="top", fill="x")

        desc_text = button.description if button.description else " "
        desc_lbl = tk.Label(
            text_box,
            text=desc_text,
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY if button.description else BG_SURFACE,
            bg=BG_SURFACE,
            anchor="nw",
            justify="left",
        )
        desc_lbl.pack(side="top", fill="both", expand=True, pady=(scale_px(self.root, 2), 0))

        def _update_wrap(event: tk.Event[tk.Misc]) -> None:
            wrap = max(scale_px(self.root, 120), event.width - scale_px(self.root, 8))
            title_lbl.configure(wraplength=wrap)
            desc_lbl.configure(wraplength=wrap)

        text_box.bind("<Configure>", _update_wrap)

        return _CardWidgets(
            outer=outer,
            state_lbl=state_lbl,
            title_lbl=title_lbl,
            desc_lbl=desc_lbl,
            btn_on=btn_on,
            btn_off=btn_off,
            accent_hex=accent_hex,
        )

    def _refresh_card_states(self) -> None:
        for idx, card in enumerate(self.cards):
            state = self.controller.button_states.get(idx)
            if state == "on":
                card.outer.set_card_style(border_color=card.accent_hex, border_width=2)
                card.state_lbl.configure(
                    text=f" {self._t('state_on')} ",
                    fg=STATUS_ON_FG,
                    bg=STATUS_ON_BG,
                )
                card.btn_off.configure_style(
                    bg_color=BTN_OFF_ARMED_BG,
                    hover_color=BTN_OFF_HOVER,
                    border_color="",
                )
            elif state == "off":
                card.outer.set_card_style(border_color=BORDER_CARD, border_width=1)
                card.state_lbl.configure(
                    text=f" {self._t('state_off')} ",
                    fg=STATUS_OFF_FG,
                    bg=STATUS_OFF_BG,
                )
                card.btn_off.configure_style(
                    bg_color=BTN_OFF_BG,
                    hover_color=BTN_OFF_HOVER,
                    border_color=BTN_OFF_BORDER,
                )
            else:
                card.outer.set_card_style(border_color=BORDER_CARD, border_width=1)
                card.state_lbl.configure(
                    text=f" {self._t('state_ready')} ",
                    fg=TEXT_MUTED,
                    bg=BG_ELEVATED,
                )
                card.btn_off.configure_style(
                    bg_color=BTN_OFF_BG,
                    hover_color=BTN_OFF_HOVER,
                    border_color=BTN_OFF_BORDER,
                )

    # --- Actions & Event handlers ---------------------------------------------

    def trigger_button(self, active_idx: int, side: ButtonSide) -> list[LogEntry]:
        entries = self.controller.trigger_active_button(active_idx, side)
        self._refresh_card_states()
        return entries

    def _on_all_off(self) -> None:
        self.controller.trigger_all_off()
        self._refresh_card_states()

    def _render_last_event_banner(self, entry: LogEntry) -> None:
        time_short = entry.timestamp.split(" ")[-1]
        side_lbl = self._t("state_on") if entry.side == "on" else self._t("state_off")
        prefix = self._t("status_ok") if entry.ok else self._t("status_err")
        color = (
            STATUS_WARN_FG
            if self.controller.dry_run and entry.ok
            else (STATUS_ON_FG if entry.ok else STATUS_ERR_FG)
        )
        self.lbl_last_event.configure(
            text=(
                f"[{prefix}] {time_short}  |  {entry.button_name} ({side_lbl})  ->  "
                f"{entry.address}  [{entry.outcome}]"
            ),
            fg=color,
        )

    def _on_controller_log(self, entry: LogEntry) -> None:
        self._has_logged_event = True
        self._last_entry = entry
        self._render_last_event_banner(entry)
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", entry.line + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def toggle_log_drawer(self) -> None:
        self.log_expanded = not self.log_expanded
        if self.log_expanded:
            self.log_drawer.pack(side="bottom", fill="x")
            self.btn_log_toggle.configure_style(text=self._t("btn_log_hide"))
        else:
            self.log_drawer.pack_forget()
            self.btn_log_toggle.configure_style(text=self._t("btn_log_show"))

    def toggle_lock(self) -> None:
        self.locked = not self.locked
        self.refresh_all()

    def toggle_dry_run(self) -> None:
        if self.locked:
            return
        self.controller.dry_run = not self.controller.dry_run
        self.settings.dry_run = self.controller.dry_run
        self.settings.save(self._app_data_dir)
        self.refresh_all()

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        try:
            self.root.attributes("-fullscreen", self.fullscreen)
        except tk.TclError:
            pass

    def _exit_fullscreen(self) -> None:
        if self.fullscreen:
            self.fullscreen = False
            try:
                self.root.attributes("-fullscreen", False)
            except tk.TclError:
                pass

    def _show_file_menu(self) -> None:
        if self.locked:
            return
        x = self.btn_file_menu.winfo_rootx()
        y = self.btn_file_menu.winfo_rooty() + self.btn_file_menu.winfo_height() + 4
        self.file_menu.tk_popup(x, y)

    def _unlock_and_open_editor(self) -> None:
        self.locked = False
        self.refresh_all()
        self.open_editor()

    def open_editor(self) -> None:
        if self.locked:
            return
        if self._editor_win is not None and self._editor_win.winfo_exists():
            self._editor_win.lift()
            return
        self._editor_win = ConfigEditorWindow(
            self.root,
            self.controller,
            self.autostart,
            language=self.lang,
            on_language_changed=self.set_language,
            on_applied=self._on_editor_saved,
        )

    def _on_editor_saved(self, cfg: PanelConfig, saved_path: Path | None) -> None:
        if saved_path is not None:
            self.settings.last_config_path = str(saved_path.resolve())
        if cfg.ui.language:
            self.lang = normalize_language(cfg.ui.language)
            self.var_lang.set(self.lang)
            self.settings.language = self.lang
            self._rebuild_file_menu()
        self.settings.save(self._app_data_dir)
        self.refresh_all()

    def _yaml_filetypes(self) -> list[tuple[str, str]]:
        return [
            (self._t("dlg_yaml_filter"), "*.yaml *.yml"),
            (self._t("dlg_all_filter"), "*.*"),
        ]

    def action_new_config(self) -> None:
        if self.locked:
            return
        chosen = filedialog.asksaveasfilename(
            parent=self.root,
            title=self._t("dlg_new_title"),
            initialfile="playbacks.local.yaml",
            defaultextension=".yaml",
            filetypes=self._yaml_filetypes(),
        )
        if not chosen:
            return
        starter = default_starter_config(lang=self.lang)
        try:
            saved = self.controller.save_to_file(starter, Path(chosen))
        except (OSError, ZerosValueError) as exc:
            messagebox.showerror(self._t("dlg_err_create"), str(exc), parent=self.root)
            return
        self.settings.last_config_path = str(saved.resolve())
        self.settings.save(self._app_data_dir)
        self.refresh_all()
        self.open_editor()

    def action_open_config(self) -> None:
        if self.locked:
            return
        chosen = filedialog.askopenfilename(
            parent=self.root,
            title=self._t("dlg_open_title"),
            filetypes=self._yaml_filetypes(),
        )
        if not chosen:
            return
        try:
            cfg, _ = self.controller.load_from_file(Path(chosen))
        except ZerosValueError as exc:
            messagebox.showerror(self._t("dlg_err_load"), str(exc), parent=self.root)
            return
        self.settings.last_config_path = str(Path(chosen).resolve())
        if cfg.ui.language:
            self.lang = normalize_language(cfg.ui.language)
            self.var_lang.set(self.lang)
            self.settings.language = self.lang
            self._rebuild_file_menu()
        self.settings.save(self._app_data_dir)
        self.locked = self.controller.config.ui.start_locked
        self.refresh_all(apply_window_mode=True)

    def action_reload(self) -> None:
        if self.controller.config_path is None:
            return
        try:
            self.controller.load_from_file(self.controller.config_path)
        except ZerosValueError as exc:
            messagebox.showerror(self._t("dlg_err_reload"), str(exc), parent=self.root)
            return
        self.refresh_all()

    def action_load_starter_demo(self) -> None:
        starter = default_starter_config(host="127.0.0.1", lang=self.lang)
        self.controller.dry_run = True
        self.controller.set_config(starter, path=None)
        self.locked = False
        self.refresh_all()

    # --- Background timers ----------------------------------------------------

    def _schedule_startup_actions(self) -> None:
        if not any(b.auto_on_at_startup for b in self.controller.config.active_buttons):
            return
        delay_ms = max(50, int(self.controller.config.ui.startup_delay_s * 1000))
        self.root.after(delay_ms, self._run_startup_actions)

    def _run_startup_actions(self) -> None:
        self.controller.trigger_startup_actions()
        self._refresh_card_states()

    def _poll_file_changes(self) -> None:
        if not self.root.winfo_exists():
            return
        editor_open = self._editor_win is not None and self._editor_win.winfo_exists()
        if not editor_open:
            reloaded, err = self.controller.reload_if_changed()
            if reloaded:
                self.refresh_all()
            elif err:
                msg = f"[{self._t('status_err')}] {err}"
                self.lbl_last_event.configure(text=msg, fg=STATUS_ERR_FG)
        if self._enable_timers:
            self.root.after(2000, self._poll_file_changes)

    def close(self) -> None:
        self.controller.close()
        self.root.destroy()


def run_gui(
    controller: PanelController,
    *,
    settings: AppSettings | None = None,
    autostart: AutostartManager | None = None,
    app_data_dir: Path | None = None,
    force_locked: bool = False,
    open_editor_on_start: bool = False,
) -> int:
    """Start the Tkinter event loop for ``PlaybackPanelApp``."""
    enable_windows_high_dpi()
    root = tk.Tk()
    PlaybackPanelApp(
        root,
        controller,
        settings=settings,
        autostart=autostart,
        app_data_dir=app_data_dir,
        force_locked=force_locked,
        open_editor_on_start=open_editor_on_start,
    )
    root.mainloop()
    return 0

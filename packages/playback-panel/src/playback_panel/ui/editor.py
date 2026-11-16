"""Modern 12-slot playback button editor and console/autostart settings dialog (DE/EN/RO)."""

from __future__ import annotations

import copy
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox

from zeros_osc import COMMANDS, Command, Status, ZerosValueError

from ..autostart import AutostartManager, AutostartNotSupportedError, build_autostart_command
from ..config import (
    ACCENT_COLORS,
    MAX_BUTTONS,
    ButtonConfig,
    PanelConfig,
    check,
    parse_config,
)
from ..controller import PanelController
from ..i18n import LanguageCode, color_label, normalize_language, tr
from .theme import (
    ACCENT_HEX,
    BG_ELEVATED,
    BG_HEADER,
    BG_INPUT,
    BG_ROOT,
    BG_SURFACE,
    BORDER_CARD,
    BORDER_FOCUS,
    BORDER_INPUT,
    BORDER_SUBTLE,
    BTN_DANGER_ACTIVE,
    BTN_DANGER_BG,
    BTN_DANGER_HOVER,
    BTN_OFF_ACTIVE,
    BTN_OFF_ARMED_BG,
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
    STATUS_ON_FG,
    STATUS_WARN_FG,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    ModernEntry,
    ModernStepper,
    RoundedCard,
    ScrollableFrame,
    SegmentedControl,
    TactileButton,
    ToggleSwitch,
    apply_scaled_geometry,
    apply_windows_dark_chrome,
    measure_text,
    pick_font_family,
    pick_mono_family,
    render_rounded_photo,
    scale_px,
)

MODE_IDS: tuple[tuple[str, str], ...] = (
    ("playback_level", "mode_pb_level"),
    ("playback_go_release", "mode_pb_go"),
    ("cue_pair", "mode_cue_pair"),
    ("custom", "mode_custom"),
)


def _status_badge(lang: str, cmd: Command) -> str:
    if cmd.status is Status.BELEGT:
        return f"[{tr(lang, 'tag_belegt')}]"
    if cmd.status is Status.FORUM:
        return f"[{tr(lang, 'tag_ungetestet')}]"
    return f"[{tr(lang, 'tag_vermutet')}]"


class ConfigEditorWindow(tk.Toplevel):
    """Modal configuration window for up to 12 buttons, console target, language & autostart."""

    def __init__(
        self,
        parent: tk.Misc,
        controller: PanelController,
        autostart: AutostartManager,
        on_applied: Callable[[PanelConfig, Path | None], None],
        *,
        language: str = "de",
        on_language_changed: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.autostart = autostart
        self._on_applied = on_applied
        self._on_language_changed = on_language_changed

        self.lang: LanguageCode = normalize_language(language)
        self._updating_lang = False
        self.var_lang = tk.StringVar(master=self, value=self.lang)
        self.var_active_tab = tk.StringVar(master=self, value="buttons")

        self.font_ui = pick_font_family(self)
        self.font_mono = pick_mono_family(self)

        self.title(self._t("editor_win_title"))
        self.configure(bg=BG_ROOT)
        apply_scaled_geometry(self, 1140, 750, min_w=880, min_h=580, parent=parent)
        apply_windows_dark_chrome(self)
        self.transient(parent.winfo_toplevel())

        # Working copy of the 12 slots
        existing = [copy.deepcopy(b) for b in controller.config.buttons[:MAX_BUTTONS]]
        self.slots: list[ButtonConfig | None] = existing + [None] * (MAX_BUTTONS - len(existing))
        self.selected_slot: int = 0
        self._loading_slot = False

        # Console & UI working variables
        cfg = controller.config
        self._initial_yaml_lang: str | None = cfg.ui.language
        self.var_title = tk.StringVar(master=self, value=cfg.title)
        self.var_host = tk.StringVar(master=self, value=cfg.console.host)
        self.var_port = tk.StringVar(master=self, value=str(cfg.console.port))
        self.var_transport = tk.StringVar(master=self, value=cfg.console.transport)

        self.var_start_locked = tk.BooleanVar(master=self, value=cfg.ui.start_locked)
        self.var_always_on_top = tk.BooleanVar(master=self, value=cfg.ui.always_on_top)
        self.var_show_all_off = tk.BooleanVar(master=self, value=cfg.ui.show_all_off)
        self.var_window_mode = tk.StringVar(master=self, value=cfg.ui.window_mode)
        self.var_startup_delay = tk.StringVar(master=self, value=f"{cfg.ui.startup_delay_s:g}")

        self.var_autostart = tk.BooleanVar(master=self, value=autostart.is_enabled())

        # Selected slot form variables
        self.var_btn_enabled = tk.BooleanVar(master=self, value=True)
        self.var_btn_name = tk.StringVar(master=self)
        self.var_btn_desc = tk.StringVar(master=self)
        self.var_btn_color = tk.StringVar(master=self, value="amber")
        self.var_btn_mode = tk.StringVar(master=self, value="playback_level")
        self.var_btn_on_label = tk.StringVar(master=self, value=self._t("default_on"))
        self.var_btn_off_label = tk.StringVar(master=self, value=self._t("default_off"))
        self.var_btn_auto_on = tk.BooleanVar(master=self, value=False)

        self.var_pb_number = tk.StringVar(master=self, value="1")
        self.var_on_level = tk.StringVar(master=self, value="100")
        self.var_off_level = tk.StringVar(master=self, value="0")
        self.var_on_fade = tk.StringVar(master=self, value="")
        self.var_off_fade = tk.StringVar(master=self, value="")
        self.var_off_action = tk.StringVar(master=self, value="release")
        self.var_on_cue = tk.StringVar(master=self, value="1")
        self.var_off_cue = tk.StringVar(master=self, value="2")

        # Command assistant variables for custom mode
        self._cmd_ids = list(COMMANDS.keys())
        self.var_assist_cmd = tk.StringVar(master=self, value="playback_level")
        self.assist_param_vars: list[tk.StringVar] = []

        self._active_tab = "buttons"
        self._slot_row_widgets: list[tuple[tk.Frame, tk.Frame, tk.Label, tk.Label]] = []
        self._mode_buttons: dict[str, TactileButton] = {}
        self._color_buttons: dict[str, tk.Canvas] = {}
        self._color_photos: dict[str, tk.PhotoImage] = {}
        self._i18n_labels: list[tuple[tk.Label, str, str]] = []
        self._section_cards: list[RoundedCard] = []

        self._build_layout()
        self._bind_form_traces()
        self._select_slot(0)
        self._sync_sidebar_width()
        self.grab_set()
        self.focus_set()

    def _t(self, key: str, **kwargs: object) -> str:
        return tr(self.lang, key, **kwargs)

    # --- Live Language Switching ----------------------------------------------

    def set_language(self, lang: str) -> None:
        normalized = normalize_language(lang)
        if self._updating_lang:
            return
        self._updating_lang = True
        try:
            self.lang = normalized
            if self.var_lang.get() != normalized:
                self.var_lang.set(normalized)

            self.title(self._t("editor_win_title"))
            self.lbl_editor_heading.configure(text=self._t("editor_heading"))
            self.tab_switcher.set_options(
                (
                    ("buttons", self._t("tab_buttons")),
                    ("settings", self._t("tab_settings")),
                )
            )
            self._update_footer_path_label()
            self.btn_save.configure_style(text=self._t("btn_save"))
            self.btn_save_as.configure_style(text=self._t("btn_save_as"))
            self.btn_cancel.configure_style(text=self._t("btn_cancel"))

            self.btn_up.configure_style(text=self._t("btn_up"))
            self.btn_down.configure_style(text=self._t("btn_down"))
            self.btn_clear.configure_style(text=self._t("btn_clear"))

            self.sw_btn_enabled.set_text(self._t("slot_enabled_toggle"))
            self.sw_btn_auto_on.set_text(self._t("lbl_auto_on"))
            self.sw_start_locked.set_text(self._t("chk_start_locked"))
            self.sw_always_on_top.set_text(self._t("chk_always_on_top"))
            self.sw_show_all_off.set_text(self._t("chk_show_all_off"))
            self.sw_autostart.set_text(self._t("chk_autostart"))

            for lbl, key, suffix in self._i18n_labels:
                lbl.configure(text=f"{self._t(key)}{suffix}")

            for mode_id, mode_key in MODE_IDS:
                if mode_id in self._mode_buttons:
                    self._mode_buttons[mode_id].configure_style(text=self._t(mode_key))

            self.seg_off_action.set_options(
                (
                    ("release", self._t("opt_release")),
                    ("pause", self._t("opt_pause")),
                )
            )
            self.seg_transport.set_options(
                (
                    ("udp", self._t("opt_udp")),
                    ("tcp-slip", self._t("opt_tcp")),
                )
            )
            self.seg_window_mode.set_options(
                (
                    ("normal", self._t("wm_normal")),
                    ("maximized", self._t("wm_maximized")),
                    ("fullscreen", self._t("wm_fullscreen")),
                )
            )

            self.btn_add_on.configure_style(text=self._t("btn_add_on"))
            self.btn_add_off.configure_style(text=self._t("btn_add_off"))
            self.btn_test_on.configure_style(text=self._t("btn_test_on"))
            self.btn_test_off.configure_style(text=self._t("btn_test_off"))

            self._rebuild_assist_params()
            self._update_color_swatches()
            self._load_slot_into_form(self.selected_slot)
            self._refresh_slot_sidebar()
            self._refresh_autostart_preview()
            self._sync_sidebar_width()
            for card in self._section_cards:
                card.sync_height()

            if self._on_language_changed is not None:
                self._on_language_changed(normalized)
        finally:
            self._updating_lang = False

    # --- Layout construction --------------------------------------------------

    def _build_layout(self) -> None:
        pad_h = scale_px(self, 22)
        pad_v = scale_px(self, 12)
        gap = scale_px(self, 8)

        # Top seamless dark header
        header = tk.Frame(self, bg=BG_HEADER, padx=pad_h, pady=pad_v)
        header.pack(side="top", fill="x")
        tk.Frame(self, bg=BORDER_SUBTLE, height=1).pack(side="top", fill="x")

        self.lbl_editor_heading = tk.Label(
            header,
            text=self._t("editor_heading"),
            font=(self.font_ui, 13, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_HEADER,
        )
        self.lbl_editor_heading.pack(side="left")

        right_hdr = tk.Frame(header, bg=BG_HEADER)
        right_hdr.pack(side="right")

        self.lang_hdr_switch = SegmentedControl(
            right_hdr,
            (("de", "DE"), ("en", "EN"), ("ro", "RO")),
            variable=self.var_lang,
            command=self.set_language,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 8, "bold"),
            pad_x=9,
            pad_y=5,
            height=32,
        )
        self.lang_hdr_switch.pack(side="right", padx=(gap + scale_px(self, 4), 0))

        self.tab_switcher = SegmentedControl(
            right_hdr,
            (
                ("buttons", self._t("tab_buttons")),
                ("settings", self._t("tab_settings")),
            ),
            variable=self.var_active_tab,
            command=self._switch_tab,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 9, "bold"),
            pad_x=14,
            pad_y=6,
            height=34,
        )
        self.tab_switcher.pack(side="right")

        # Bottom action footer (auto-measuring buttons -> never clips at any DPI)
        tk.Frame(self, bg=BORDER_SUBTLE, height=1).pack(side="bottom", fill="x")
        footer = tk.Frame(self, bg=BG_HEADER, padx=pad_h, pady=pad_v)
        footer.pack(side="bottom", fill="x")

        self.lbl_footer_path = tk.Label(
            footer,
            text="",
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_HEADER,
            anchor="w",
        )
        self.lbl_footer_path.pack(side="left", fill="x", expand=True, padx=(0, gap))
        self._update_footer_path_label()

        self.btn_save = TactileButton(
            footer,
            self._t("btn_save"),
            command=self._on_save,
            bg_color=BTN_ON_BG,
            hover_color=BTN_ON_HOVER,
            active_color=BTN_ON_ACTIVE,
            border_color="",
            parent_bg=BG_HEADER,
            font=(self.font_ui, 10, "bold"),
            height=36,
            pad_x=18,
        )
        self.btn_save.pack(side="right")

        self.btn_save_as = TactileButton(
            footer,
            self._t("btn_save_as"),
            command=self._on_save_as,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            border_color=BTN_SECONDARY_BORDER,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 9, "bold"),
            height=36,
            pad_x=15,
        )
        self.btn_save_as.pack(side="right", padx=(0, gap))

        self.btn_cancel = TactileButton(
            footer,
            self._t("btn_cancel"),
            command=self.destroy,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            border_color=BTN_SECONDARY_BORDER,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 9, "bold"),
            height=36,
            pad_x=15,
        )
        self.btn_cancel.pack(side="right", padx=(0, gap))

        # Body container holding both tabs
        self.body = tk.Frame(self, bg=BG_ROOT)
        self.body.pack(side="top", fill="both", expand=True)

        self.tab_buttons_frame = tk.Frame(self.body, bg=BG_ROOT)
        self.tab_settings_frame = tk.Frame(self.body, bg=BG_ROOT)

        self._build_buttons_tab(self.tab_buttons_frame)
        self._build_settings_tab(self.tab_settings_frame)

        self.tab_buttons_frame.pack(fill="both", expand=True)

    def _update_footer_path_label(self) -> None:
        if self.controller.config_path is not None:
            self.lbl_footer_path.configure(
                text=self._t("footer_file_fmt", path=self.controller.config_path)
            )
        else:
            self.lbl_footer_path.configure(text=self._t("footer_no_file"))

    def _switch_tab(self, tab: str) -> None:
        self._commit_current_slot()
        self._active_tab = tab
        if self.var_active_tab.get() != tab:
            self.var_active_tab.set(tab)
        if tab == "buttons":
            self.tab_settings_frame.pack_forget()
            self.tab_buttons_frame.pack(fill="both", expand=True)
        else:
            self.tab_buttons_frame.pack_forget()
            self._refresh_autostart_preview()
            self.tab_settings_frame.pack(fill="both", expand=True)
            for card in self._section_cards:
                card.sync_height()

    # --- Tab 1: 12-Slot Button Editor -----------------------------------------

    def _build_buttons_tab(self, parent: tk.Frame) -> None:
        sb_pad = scale_px(self, 12)
        self.sidebar = tk.Frame(
            parent, bg=BG_SURFACE, width=scale_px(self, 300), padx=sb_pad, pady=sb_pad
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Frame(parent, bg=BORDER_SUBTLE, width=1).pack(side="left", fill="y")

        self.lbl_slot_summary = tk.Label(
            self.sidebar,
            text="",
            font=(self.font_ui, 9, "bold"),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
        )
        self.lbl_slot_summary.pack(side="top", fill="x", pady=(0, scale_px(self, 8)))

        # Pack bottom slot action bar BEFORE scrollable list so it never overflows off-screen
        tools = tk.Frame(self.sidebar, bg=BG_SURFACE)
        tools.pack(side="bottom", fill="x", pady=(scale_px(self, 8), 0))
        btn_gap = scale_px(self, 5)

        self.btn_up = TactileButton(
            tools,
            self._t("btn_up"),
            command=lambda: self._move_slot(-1),
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 8, "bold"),
            height=30,
            pad_x=10,
            pad_y=5,
        )
        self.btn_up.pack(side="left", padx=(0, btn_gap))

        self.btn_down = TactileButton(
            tools,
            self._t("btn_down"),
            command=lambda: self._move_slot(1),
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 8, "bold"),
            height=30,
            pad_x=10,
            pad_y=5,
        )
        self.btn_down.pack(side="left", padx=(0, btn_gap))

        self.btn_clear = TactileButton(
            tools,
            self._t("btn_clear"),
            command=self._clear_current_slot,
            bg_color=BTN_DANGER_BG,
            hover_color=BTN_DANGER_HOVER,
            active_color=BTN_DANGER_ACTIVE,
            border_color="",
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 8, "bold"),
            height=30,
            pad_x=11,
            pad_y=5,
        )
        self.btn_clear.pack(side="right")

        slots_scroll = ScrollableFrame(self.sidebar, bg=BG_SURFACE)
        slots_scroll.pack(side="top", fill="both", expand=True)
        slots_list = slots_scroll.inner

        self._slot_row_widgets.clear()
        row_py = scale_px(self, 5)
        row_px = scale_px(self, 8)
        for idx in range(MAX_BUTTONS):
            row = tk.Frame(
                slots_list,
                bg=BG_ELEVATED,
                highlightthickness=0,
                bd=0,
                cursor="hand2",
            )
            row.pack(fill="x", pady=scale_px(self, 2))

            bar = tk.Frame(row, bg=BG_ELEVATED, width=scale_px(self, 3))
            bar.pack(side="left", fill="y")

            dot = tk.Label(
                row,
                text="●",
                font=(self.font_ui, 9, "bold"),
                fg=TEXT_MUTED,
                bg=BG_ELEVATED,
                padx=row_px,
                pady=row_py,
            )
            dot.pack(side="left")

            lbl = tk.Label(
                row,
                text="",
                font=(self.font_ui, 9),
                fg=TEXT_SECONDARY,
                bg=BG_ELEVATED,
                anchor="w",
                pady=row_py,
            )
            lbl.pack(side="left", fill="x", expand=True, padx=(0, row_px))

            for w in (row, bar, dot, lbl):
                w.bind("<Button-1>", lambda _e, i=idx: self._select_slot(i))
            self._slot_row_widgets.append((row, bar, dot, lbl))

        # Right side: empty-slot state OR full form
        self.detail_host = tk.Frame(parent, bg=BG_ROOT)
        self.detail_host.pack(side="left", fill="both", expand=True)

        # Empty slot placeholder in a modern RoundedCard
        self.empty_slot_frame = tk.Frame(self.detail_host, bg=BG_ROOT)
        empty_card = RoundedCard(
            self.empty_slot_frame,
            bg_color=BG_SURFACE,
            border_color=BORDER_CARD,
            parent_bg=BG_ROOT,
            radius=16,
            pad_x=36,
            pad_y=32,
            auto_height=True,
        )
        empty_card.place(relx=0.5, rely=0.46, anchor="center", relwidth=0.78)
        self._section_cards.append(empty_card)

        eb = empty_card.body
        self.lbl_empty_slot_title = tk.Label(
            eb,
            text="",
            font=(self.font_ui, 15, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            justify="center",
        )
        self.lbl_empty_slot_title.pack(pady=(0, scale_px(self, 8)))

        self.lbl_empty_slot_body = tk.Label(
            eb,
            text=self._t("empty_slot_body"),
            font=(self.font_ui, 10),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            justify="center",
        )
        self.lbl_empty_slot_body.pack(fill="x", pady=(0, scale_px(self, 22)))
        self._i18n_labels.append((self.lbl_empty_slot_body, "empty_slot_body", ""))

        def _sync_empty_wrap(event: tk.Event[tk.Misc]) -> None:
            wrap = max(scale_px(self, 240), event.width - scale_px(self, 20))
            self.lbl_empty_slot_title.configure(wraplength=wrap)
            self.lbl_empty_slot_body.configure(wraplength=wrap)

        eb.bind("<Configure>", _sync_empty_wrap, add="+")

        self.btn_create_slot = TactileButton(
            eb,
            self._t("empty_slot_btn", n=1),
            command=self._create_in_current_slot,
            bg_color=BTN_PRIMARY_BG,
            hover_color=BTN_PRIMARY_HOVER,
            active_color=BTN_PRIMARY_ACTIVE,
            border_color="",
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 10, "bold"),
            height=42,
            pad_x=22,
        )
        self.btn_create_slot.pack()

        # Occupied slot scrollable form
        self.form_scroll = ScrollableFrame(self.detail_host, bg=BG_ROOT)
        form = self.form_scroll.inner
        form.configure(padx=scale_px(self, 22), pady=scale_px(self, 16))

        # Header row in form
        top_row = tk.Frame(form, bg=BG_ROOT)
        top_row.pack(fill="x", pady=(0, scale_px(self, 12)))
        self.lbl_form_slot_header = tk.Label(
            top_row,
            text="",
            font=(self.font_ui, 13, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_ROOT,
        )
        self.lbl_form_slot_header.pack(side="left")

        self.sw_btn_enabled = ToggleSwitch(
            top_row,
            self._t("slot_enabled_toggle"),
            self.var_btn_enabled,
            bg=BG_ROOT,
            fg=TEXT_PRIMARY,
            font=(self.font_ui, 9, "bold"),
            active_color=BTN_ON_BG,
        )
        self.sw_btn_enabled.pack(side="right")

        # Card 1: Name, Description, Color & Labels
        card_meta = self._make_section_card(form, "sec_appearance")

        grid_meta = tk.Frame(card_meta, bg=BG_SURFACE)
        grid_meta.pack(fill="x")
        grid_meta.columnconfigure(1, weight=1)
        grid_meta.columnconfigure(3, weight=1)

        row_pad = scale_px(self, 4)
        self._add_label(grid_meta, "lbl_name", 0, 0)
        self._make_entry(grid_meta, self.var_btn_name, width=28).grid(
            row=0, column=1, columnspan=3, sticky="ew", pady=row_pad
        )

        self._add_label(grid_meta, "lbl_desc", 1, 0)
        self._make_entry(grid_meta, self.var_btn_desc, width=28).grid(
            row=1, column=1, columnspan=3, sticky="ew", pady=row_pad
        )

        self._add_label(grid_meta, "lbl_on_text", 2, 0)
        self._make_entry(grid_meta, self.var_btn_on_label, width=12).grid(
            row=2, column=1, sticky="ew", pady=row_pad, padx=(0, scale_px(self, 14))
        )
        self._add_label(grid_meta, "lbl_off_text", 2, 2)
        self._make_entry(grid_meta, self.var_btn_off_label, width=12).grid(
            row=2, column=3, sticky="ew", pady=row_pad
        )

        # Accent color picker (clean 4 + 3 two-row pill grid -> never clips in DE/EN/RO)
        color_sec = tk.Frame(card_meta, bg=BG_SURFACE)
        color_sec.pack(fill="x", pady=(scale_px(self, 10), scale_px(self, 6)))
        lbl_acc = tk.Label(
            color_sec,
            text=f"{self._t('lbl_accent')}:",
            font=(self.font_ui, 9, "bold"),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
        )
        lbl_acc.pack(side="top", fill="x", pady=(0, scale_px(self, 6)))
        self._i18n_labels.append((lbl_acc, "lbl_accent", ":"))

        swatches_grid = tk.Frame(color_sec, bg=BG_SURFACE)
        swatches_grid.pack(fill="x")
        sw_gap = scale_px(self, 6)
        for idx, color_name in enumerate(ACCENT_COLORS):
            r, c = divmod(idx, 4)
            swatch = tk.Canvas(
                swatches_grid,
                width=80,
                height=30,
                bg=BG_SURFACE,
                highlightthickness=0,
                bd=0,
                cursor="hand2",
            )
            swatch.grid(row=r, column=c, sticky="w", padx=(0, sw_gap), pady=(0, sw_gap))
            swatch.bind("<Button-1>", lambda _e, col=color_name: self._select_color(col))
            self._color_buttons[color_name] = swatch

        self.sw_btn_auto_on = ToggleSwitch(
            card_meta,
            self._t("lbl_auto_on"),
            self.var_btn_auto_on,
            bg=BG_SURFACE,
            fg=TEXT_SECONDARY,
            font=(self.font_ui, 9),
        )
        self.sw_btn_auto_on.pack(fill="x", pady=(scale_px(self, 6), 0))

        # Card 2: Mode & Command Parameters
        self.card_mode_outer, card_mode = self._make_section_card_pair(form, "sec_mode")

        # 2x2 responsive mode grid so long localized titles never clip
        mode_grid = tk.Frame(card_mode, bg=BG_SURFACE)
        mode_grid.pack(fill="x", pady=(0, scale_px(self, 12)))
        mode_grid.columnconfigure(0, weight=1, uniform="mode_col")
        mode_grid.columnconfigure(1, weight=1, uniform="mode_col")
        m_gap = scale_px(self, 5)

        for idx, (mode_id, mode_key) in enumerate(MODE_IDS):
            r, c = divmod(idx, 2)
            b = TactileButton(
                mode_grid,
                self._t(mode_key),
                command=lambda m=mode_id: self._select_mode(m),
                parent_bg=BG_SURFACE,
                font=(self.font_ui, 9, "bold"),
                height=34,
                pad_x=14,
            )
            b.grid(
                row=r,
                column=c,
                sticky="ew",
                padx=(0, m_gap) if c == 0 else (m_gap, 0),
                pady=(0, m_gap) if r == 0 else 0,
            )
            self._mode_buttons[mode_id] = b

        self.mode_panels_host = tk.Frame(card_mode, bg=BG_SURFACE)
        self.mode_panels_host.pack(fill="x")

        self.panel_pb_level = tk.Frame(self.mode_panels_host, bg=BG_SURFACE)
        self._build_panel_pb_level(self.panel_pb_level)

        self.panel_pb_go = tk.Frame(self.mode_panels_host, bg=BG_SURFACE)
        self._build_panel_pb_go(self.panel_pb_go)

        self.panel_cue_pair = tk.Frame(self.mode_panels_host, bg=BG_SURFACE)
        self._build_panel_cue_pair(self.panel_cue_pair)

        self.panel_custom = tk.Frame(self.mode_panels_host, bg=BG_SURFACE)
        self._build_panel_custom(self.panel_custom)

        # Card 3: Live OSC Preview & Direct Test
        self.card_preview_outer, card_preview = self._make_section_card_pair(form, "sec_preview")

        preview_box = tk.Frame(
            card_preview,
            bg=BG_INPUT,
            padx=scale_px(self, 12),
            pady=scale_px(self, 10),
            highlightthickness=1,
            highlightbackground=BORDER_INPUT,
        )
        preview_box.pack(fill="x", pady=(0, scale_px(self, 8)))

        self.lbl_preview_on = tk.Label(
            preview_box,
            text="",
            font=(self.font_mono, 9),
            fg=STATUS_ON_FG,
            bg=BG_INPUT,
            anchor="w",
            justify="left",
        )
        self.lbl_preview_on.pack(fill="x", pady=(0, scale_px(self, 3)))

        self.lbl_preview_off = tk.Label(
            preview_box,
            text="",
            font=(self.font_mono, 9),
            fg=TEXT_PRIMARY,
            bg=BG_INPUT,
            anchor="w",
            justify="left",
        )
        self.lbl_preview_off.pack(fill="x")

        self.lbl_preview_status = tk.Label(
            card_preview,
            text="",
            font=(self.font_ui, 9),
            fg=STATUS_WARN_FG,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
        )
        self.lbl_preview_status.pack(fill="x", pady=(0, scale_px(self, 10)))
        self._bind_dynamic_wrap(card_preview, self.lbl_preview_status)
        self._bind_dynamic_wrap(preview_box, self.lbl_preview_on, self.lbl_preview_off)

        test_bar = tk.Frame(card_preview, bg=BG_SURFACE)
        test_bar.pack(fill="x")
        self.btn_test_on = TactileButton(
            test_bar,
            self._t("btn_test_on"),
            command=lambda: self._test_current_slot("on"),
            bg_color=BTN_ON_BG,
            hover_color=BTN_ON_HOVER,
            active_color=BTN_ON_ACTIVE,
            border_color="",
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 9, "bold"),
            height=34,
            pad_x=16,
        )
        self.btn_test_on.pack(side="left", padx=(0, scale_px(self, 8)))

        self.btn_test_off = TactileButton(
            test_bar,
            self._t("btn_test_off"),
            command=lambda: self._test_current_slot("off"),
            bg_color=BTN_OFF_ARMED_BG,
            hover_color=BTN_OFF_HOVER,
            active_color=BTN_OFF_ACTIVE,
            border_color="",
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 9, "bold"),
            height=34,
            pad_x=16,
        )
        self.btn_test_off.pack(side="left")

        self.lbl_test_feedback = tk.Label(
            test_bar,
            text="",
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
        )
        self.lbl_test_feedback.pack(
            side="left", fill="x", expand=True, padx=(scale_px(self, 12), 0)
        )

    def _build_panel_pb_level(self, p: tk.Frame) -> None:
        desc = tk.Label(
            p,
            text=self._t("desc_pb_level"),
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
        )
        desc.pack(fill="x", pady=(0, scale_px(self, 10)))
        self._i18n_labels.append((desc, "desc_pb_level", ""))
        self._bind_dynamic_wrap(p, desc)

        g = tk.Frame(p, bg=BG_SURFACE)
        g.pack(fill="x")
        pad_y = scale_px(self, 4)
        col_gap = scale_px(self, 18)

        self._add_label(g, "lbl_playback", 0, 0)
        self._make_stepper(g, self.var_pb_number, 0, 96).grid(
            row=0, column=1, sticky="w", pady=pad_y, padx=(0, col_gap)
        )

        self._add_label(g, "lbl_on_level", 1, 0)
        self._make_stepper(g, self.var_on_level, 0, 100).grid(
            row=1, column=1, sticky="w", pady=pad_y, padx=(0, col_gap)
        )
        self._add_label(g, "lbl_off_level", 1, 2)
        self._make_stepper(g, self.var_off_level, 0, 100).grid(
            row=1, column=3, sticky="w", pady=pad_y
        )

        self._add_label(g, "lbl_on_fade", 2, 0)
        self._make_entry(g, self.var_on_fade, width=9).grid(
            row=2, column=1, sticky="w", pady=pad_y, padx=(0, col_gap)
        )
        self._add_label(g, "lbl_off_fade", 2, 2)
        self._make_entry(g, self.var_off_fade, width=9).grid(
            row=2, column=3, sticky="w", pady=pad_y
        )

    def _build_panel_pb_go(self, p: tk.Frame) -> None:
        desc = tk.Label(
            p,
            text=self._t("desc_pb_go"),
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
        )
        desc.pack(fill="x", pady=(0, scale_px(self, 10)))
        self._i18n_labels.append((desc, "desc_pb_go", ""))
        self._bind_dynamic_wrap(p, desc)

        g = tk.Frame(p, bg=BG_SURFACE)
        g.pack(fill="x")
        pad_y = scale_px(self, 4)

        self._add_label(g, "lbl_playback", 0, 0)
        self._make_stepper(g, self.var_pb_number, 0, 96).grid(
            row=0, column=1, sticky="w", pady=pad_y
        )

        self._add_label(g, "lbl_off_action", 1, 0)
        self.seg_off_action = SegmentedControl(
            g,
            (
                ("release", self._t("opt_release")),
                ("pause", self._t("opt_pause")),
            ),
            variable=self.var_off_action,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 9, "bold"),
            pad_x=13,
            pad_y=5,
            height=32,
        )
        self.seg_off_action.grid(row=1, column=1, sticky="w", pady=pad_y)

    def _build_panel_cue_pair(self, p: tk.Frame) -> None:
        desc = tk.Label(
            p,
            text=self._t("desc_cue_pair"),
            font=(self.font_ui, 9),
            fg=STATUS_ON_FG,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
        )
        desc.pack(fill="x", pady=(0, scale_px(self, 10)))
        self._i18n_labels.append((desc, "desc_cue_pair", ""))
        self._bind_dynamic_wrap(p, desc)

        g = tk.Frame(p, bg=BG_SURFACE)
        g.pack(fill="x")
        pad_y = scale_px(self, 4)
        col_gap = scale_px(self, 18)

        self._add_label(g, "lbl_playback", 0, 0)
        self._make_stepper(g, self.var_pb_number, 0, 96).grid(
            row=0, column=1, sticky="w", pady=pad_y, padx=(0, col_gap)
        )
        self._add_label(g, "lbl_on_cue", 1, 0)
        self._make_entry(g, self.var_on_cue, width=9).grid(
            row=1, column=1, sticky="w", pady=pad_y, padx=(0, col_gap)
        )
        self._add_label(g, "lbl_off_cue", 1, 2)
        self._make_entry(g, self.var_off_cue, width=9).grid(row=1, column=3, sticky="w", pady=pad_y)

    def _build_panel_custom(self, p: tk.Frame) -> None:
        desc = tk.Label(
            p,
            text=self._t("desc_custom"),
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
        )
        desc.pack(fill="x", pady=(0, scale_px(self, 10)))
        self._i18n_labels.append((desc, "desc_custom", ""))
        self._bind_dynamic_wrap(p, desc)

        # Dark rounded command builder box
        assist_card = RoundedCard(
            p,
            bg_color=BG_ELEVATED,
            border_color=BORDER_CARD,
            parent_bg=BG_SURFACE,
            radius=11,
            pad_x=14,
            pad_y=12,
            auto_height=True,
        )
        assist_card.pack(fill="x", pady=(0, scale_px(self, 10)))
        self._section_cards.append(assist_card)
        assist = assist_card.body

        top_a = tk.Frame(assist, bg=BG_ELEVATED)
        top_a.pack(fill="x")
        lbl_b = tk.Label(
            top_a,
            text=f"{self._t('lbl_builder')}:",
            font=(self.font_ui, 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_ELEVATED,
        )
        lbl_b.pack(side="left", padx=(0, scale_px(self, 8)))
        self._i18n_labels.append((lbl_b, "lbl_builder", ":"))

        self.cmd_popup_menu = tk.Menu(
            self,
            tearoff=0,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            activebackground=BTN_PRIMARY_BG,
            activeforeground=TEXT_PRIMARY,
            bd=1,
            relief="flat",
            font=(self.font_mono, 9),
        )
        for cid in self._cmd_ids:
            self.cmd_popup_menu.add_command(
                label=cid,
                command=lambda c=cid: self._select_assist_cmd(c),
            )

        self.btn_assist_cmd = TactileButton(
            top_a,
            f"{self.var_assist_cmd.get()} ▼",
            command=self._show_assist_menu,
            bg_color=BG_INPUT,
            hover_color=BG_SURFACE,
            border_color=BORDER_INPUT,
            parent_bg=BG_ELEVATED,
            font=(self.font_mono, 9, "bold"),
            height=30,
            pad_x=12,
            pad_y=4,
        )
        self.btn_assist_cmd.pack(side="left")

        self.lbl_assist_summary = tk.Label(
            top_a,
            text="",
            font=(self.font_ui, 8),
            fg=TEXT_SECONDARY,
            bg=BG_ELEVATED,
            anchor="w",
        )
        self.lbl_assist_summary.pack(
            side="left", fill="x", expand=True, padx=(scale_px(self, 10), 0)
        )

        self.assist_params_frame = tk.Frame(assist, bg=BG_ELEVATED)
        self.assist_params_frame.pack(fill="x", pady=(scale_px(self, 8), scale_px(self, 8)))

        btn_a = tk.Frame(assist, bg=BG_ELEVATED)
        btn_a.pack(fill="x")
        self.btn_add_on = TactileButton(
            btn_a,
            self._t("btn_add_on"),
            command=lambda: self._append_assisted_command("on"),
            bg_color=BTN_PRIMARY_BG,
            hover_color=BTN_PRIMARY_HOVER,
            active_color=BTN_PRIMARY_ACTIVE,
            border_color="",
            parent_bg=BG_ELEVATED,
            font=(self.font_ui, 8, "bold"),
            height=30,
            pad_x=14,
            pad_y=4,
        )
        self.btn_add_on.pack(side="left", padx=(0, scale_px(self, 8)))

        self.btn_add_off = TactileButton(
            btn_a,
            self._t("btn_add_off"),
            command=lambda: self._append_assisted_command("off"),
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            border_color=BTN_SECONDARY_BORDER,
            parent_bg=BG_ELEVATED,
            font=(self.font_ui, 8, "bold"),
            height=30,
            pad_x=14,
            pad_y=4,
        )
        self.btn_add_off.pack(side="left")

        # Two side-by-side multiline text boxes for ON and OFF OSC commands
        cols = tk.Frame(p, bg=BG_SURFACE)
        cols.pack(fill="x")
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        half = scale_px(self, 6)

        lbl_on_c = tk.Label(
            cols,
            text=f"{self._t('lbl_cmds_on')}:",
            font=(self.font_ui, 9, "bold"),
            fg=STATUS_ON_FG,
            bg=BG_SURFACE,
            anchor="w",
        )
        lbl_on_c.grid(row=0, column=0, sticky="ew", padx=(0, half))
        self._i18n_labels.append((lbl_on_c, "lbl_cmds_on", ":"))

        lbl_off_c = tk.Label(
            cols,
            text=f"{self._t('lbl_cmds_off')}:",
            font=(self.font_ui, 9, "bold"),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
        )
        lbl_off_c.grid(row=0, column=1, sticky="ew", padx=(half, 0))
        self._i18n_labels.append((lbl_off_c, "lbl_cmds_off", ":"))

        txt_px = scale_px(self, 8)
        txt_py = scale_px(self, 6)
        self.txt_on_cmds = tk.Text(
            cols,
            height=4,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            font=(self.font_mono, 9),
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_INPUT,
            highlightcolor=BORDER_FOCUS,
            padx=txt_px,
            pady=txt_py,
        )
        self.txt_on_cmds.grid(
            row=1, column=0, sticky="ew", padx=(0, half), pady=(scale_px(self, 4), 0)
        )
        self.txt_on_cmds.bind("<KeyRelease>", lambda _e: self._on_form_changed())

        self.txt_off_cmds = tk.Text(
            cols,
            height=4,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            font=(self.font_mono, 9),
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_INPUT,
            highlightcolor=BORDER_FOCUS,
            padx=txt_px,
            pady=txt_py,
        )
        self.txt_off_cmds.grid(
            row=1, column=1, sticky="ew", padx=(half, 0), pady=(scale_px(self, 4), 0)
        )
        self.txt_off_cmds.bind("<KeyRelease>", lambda _e: self._on_form_changed())

        self._rebuild_assist_params()

    def _show_assist_menu(self) -> None:
        x = self.btn_assist_cmd.winfo_rootx()
        y = self.btn_assist_cmd.winfo_rooty() + self.btn_assist_cmd.winfo_height() + 4
        self.cmd_popup_menu.tk_popup(x, y)

    def _select_assist_cmd(self, cid: str) -> None:
        self.var_assist_cmd.set(cid)
        self.btn_assist_cmd.configure_style(text=f"{cid} ▼")
        self._rebuild_assist_params()

    def _rebuild_assist_params(self) -> None:
        for child in self.assist_params_frame.winfo_children():
            child.destroy()
        self.assist_param_vars.clear()

        cmd = COMMANDS[self.var_assist_cmd.get()]
        self.lbl_assist_summary.configure(text=f"{cmd.summary} {_status_badge(self.lang, cmd)}")
        all_specs = list(cmd.params) + list(cmd.optional)
        if not all_specs:
            tk.Label(
                self.assist_params_frame,
                text=self._t("lbl_no_params", example=cmd.example),
                font=(self.font_ui, 9),
                fg=TEXT_SECONDARY,
                bg=BG_ELEVATED,
            ).pack(side="left")
            return

        defaults = {"playback": "1", "cue": "1", "level": "100", "number": "1", "value": "1"}
        opt_suffix = self._t("lbl_opt_suffix")
        for idx, spec in enumerate(all_specs):
            is_opt = idx >= len(cmd.params)
            lbl_text = f"{spec.name} {opt_suffix}:" if is_opt else f"{spec.name}:"
            tk.Label(
                self.assist_params_frame,
                text=lbl_text,
                font=(self.font_ui, 9),
                fg=TEXT_SECONDARY,
                bg=BG_ELEVATED,
            ).pack(side="left", padx=(0 if idx == 0 else scale_px(self, 10), scale_px(self, 4)))
            var = tk.StringVar(master=self, value="" if is_opt else defaults.get(spec.name, ""))
            self.assist_param_vars.append(var)
            entry = ModernEntry(
                self.assist_params_frame,
                var,
                width_chars=7,
                font=(self.font_ui, 9),
                parent_bg=BG_ELEVATED,
            )
            entry.pack(side="left")

    def _append_assisted_command(self, side: str) -> None:
        cmd = COMMANDS[self.var_assist_cmd.get()]
        raw_vals: list[object] = []
        for idx, var in enumerate(self.assist_param_vars):
            txt = var.get().strip()
            if idx >= len(cmd.params) and not txt:
                raw_vals.append(None)
            else:
                raw_vals.append(txt)
        try:
            addr = cmd.build(*raw_vals)
        except ZerosValueError as exc:
            messagebox.showerror(self._t("dlg_invalid_cmd"), str(exc), parent=self)
            return

        widget = self.txt_on_cmds if side == "on" else self.txt_off_cmds
        current = widget.get("1.0", "end-1c").strip()
        new_text = f"{current}\n{addr}" if current else addr
        widget.delete("1.0", "end")
        widget.insert("1.0", new_text)
        self._on_form_changed()

    # --- Tab 2: Console, Window, Language & Autostart Settings ----------------

    def _build_settings_tab(self, parent: tk.Frame) -> None:
        scroll = ScrollableFrame(parent, bg=BG_ROOT)
        scroll.pack(fill="both", expand=True)
        wrap = scroll.inner
        wrap.configure(padx=scale_px(self, 28), pady=scale_px(self, 18))

        pad_y = scale_px(self, 5)

        # Console card
        c_console = self._make_section_card(wrap, "sec_console")
        g1 = tk.Frame(c_console, bg=BG_SURFACE)
        g1.pack(fill="x")
        g1.columnconfigure(1, weight=1)

        self._add_label(g1, "lbl_show_title", 0, 0)
        self._make_entry(g1, self.var_title, width=32).grid(
            row=0, column=1, sticky="ew", pady=pad_y
        )

        self._add_label(g1, "lbl_host", 1, 0)
        self._make_entry(g1, self.var_host, width=22).grid(row=1, column=1, sticky="w", pady=pad_y)

        self._add_label(g1, "lbl_port", 2, 0)
        self._make_entry(g1, self.var_port, width=9).grid(row=2, column=1, sticky="w", pady=pad_y)

        self._add_label(g1, "lbl_transport", 3, 0)
        self.seg_transport = SegmentedControl(
            g1,
            (
                ("udp", self._t("opt_udp")),
                ("tcp-slip", self._t("opt_tcp")),
            ),
            variable=self.var_transport,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 9, "bold"),
            pad_x=14,
            pad_y=5,
            height=32,
        )
        self.seg_transport.grid(row=3, column=1, sticky="w", pady=pad_y)

        # Window, Language & Event behavior card
        c_ui = self._make_section_card(wrap, "sec_window")

        g_lang = tk.Frame(c_ui, bg=BG_SURFACE)
        g_lang.pack(fill="x", pady=(0, scale_px(self, 10)))
        self._add_label(g_lang, "lbl_language", 0, 0)
        self.seg_language = SegmentedControl(
            g_lang,
            (
                ("de", "Deutsch (DE)"),
                ("en", "English (EN)"),
                ("ro", "Română (RO)"),
            ),
            variable=self.var_lang,
            command=self.set_language,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 9, "bold"),
            pad_x=14,
            pad_y=5,
            height=32,
        )
        self.seg_language.grid(row=0, column=1, sticky="w")

        sw_pad = scale_px(self, 4)
        self.sw_start_locked = ToggleSwitch(
            c_ui,
            self._t("chk_start_locked"),
            self.var_start_locked,
            bg=BG_SURFACE,
            font=(self.font_ui, 10),
        )
        self.sw_start_locked.pack(fill="x", pady=sw_pad)

        self.sw_always_on_top = ToggleSwitch(
            c_ui,
            self._t("chk_always_on_top"),
            self.var_always_on_top,
            bg=BG_SURFACE,
            font=(self.font_ui, 10),
        )
        self.sw_always_on_top.pack(fill="x", pady=sw_pad)

        self.sw_show_all_off = ToggleSwitch(
            c_ui,
            self._t("chk_show_all_off"),
            self.var_show_all_off,
            bg=BG_SURFACE,
            font=(self.font_ui, 10),
        )
        self.sw_show_all_off.pack(fill="x", pady=sw_pad)

        g2 = tk.Frame(c_ui, bg=BG_SURFACE)
        g2.pack(fill="x", pady=(scale_px(self, 8), 0))
        self._add_label(g2, "lbl_window_mode", 0, 0)
        self.seg_window_mode = SegmentedControl(
            g2,
            (
                ("normal", self._t("wm_normal")),
                ("maximized", self._t("wm_maximized")),
                ("fullscreen", self._t("wm_fullscreen")),
            ),
            variable=self.var_window_mode,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 9, "bold"),
            pad_x=14,
            pad_y=5,
            height=32,
        )
        self.seg_window_mode.grid(row=0, column=1, sticky="w", pady=pad_y)

        self._add_label(g2, "lbl_startup_delay", 1, 0)
        self._make_entry(g2, self.var_startup_delay, width=9).grid(
            row=1, column=1, sticky="w", pady=pad_y
        )

        # Windows Autostart card
        c_auto = self._make_section_card(wrap, "sec_autostart")
        lbl_auto_desc = tk.Label(
            c_auto,
            text=self._t("desc_autostart"),
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
        )
        lbl_auto_desc.pack(fill="x", pady=(0, scale_px(self, 10)))
        self._i18n_labels.append((lbl_auto_desc, "desc_autostart", ""))
        self._bind_dynamic_wrap(c_auto, lbl_auto_desc)

        self.sw_autostart = ToggleSwitch(
            c_auto,
            self._t("chk_autostart"),
            self.var_autostart,
            command=self._refresh_autostart_preview,
            bg=BG_SURFACE,
            font=(self.font_ui, 10, "bold"),
            active_color=BTN_ON_BG,
            disabled=not self.autostart.supported,
        )
        self.sw_autostart.pack(fill="x", pady=(0, scale_px(self, 8)))

        self.lbl_autostart_cmd = tk.Label(
            c_auto,
            text="",
            font=(self.font_mono, 9),
            fg=TEXT_SECONDARY,
            bg=BG_INPUT,
            anchor="w",
            justify="left",
            padx=scale_px(self, 12),
            pady=scale_px(self, 10),
        )
        self.lbl_autostart_cmd.pack(fill="x")
        self._bind_dynamic_wrap(c_auto, self.lbl_autostart_cmd)
        self._refresh_autostart_preview()

    def _refresh_autostart_preview(self) -> None:
        planned = build_autostart_command(config_path=self.controller.config_path)
        if not self.autostart.supported:
            self.lbl_autostart_cmd.configure(text=self._t("autostart_unsupported", cmd=planned))
            return
        state = (
            self._t("autostart_active")
            if self.var_autostart.get()
            else self._t("autostart_inactive")
        )
        self.lbl_autostart_cmd.configure(
            text=self._t("autostart_status_fmt", state=state, cmd=planned)
        )

    # --- Widget & Layout Helpers ----------------------------------------------

    def _make_section_card_pair(
        self, parent: tk.Misc, heading_key: str
    ) -> tuple[RoundedCard, tk.Frame]:
        card = RoundedCard(
            parent,
            bg_color=BG_SURFACE,
            border_color=BORDER_CARD,
            parent_bg=BG_ROOT,
            radius=14,
            pad_x=18,
            pad_y=15,
            auto_height=True,
        )
        card.pack(fill="x", pady=(0, scale_px(self, 14)))
        self._section_cards.append(card)
        body = card.body
        lbl = tk.Label(
            body,
            text=self._t(heading_key),
            font=(self.font_ui, 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            anchor="w",
        )
        lbl.pack(fill="x", pady=(0, scale_px(self, 10)))
        self._i18n_labels.append((lbl, heading_key, ""))
        return card, body

    def _make_section_card(self, parent: tk.Misc, heading_key: str) -> tk.Frame:
        _, body = self._make_section_card_pair(parent, heading_key)
        return body

    def _add_label(self, parent: tk.Misc, key: str, row: int, col: int) -> tk.Label:
        lbl = tk.Label(
            parent,
            text=f"{self._t(key)}:",
            font=(self.font_ui, 9, "bold"),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
        )
        lbl.grid(
            row=row,
            column=col,
            sticky="w",
            pady=scale_px(self, 4),
            padx=(0, scale_px(self, 12)),
        )
        self._i18n_labels.append((lbl, key, ":"))
        return lbl

    def _make_entry(self, parent: tk.Misc, var: tk.StringVar, width: int = 28) -> ModernEntry:
        return ModernEntry(
            parent,
            var,
            width_chars=width,
            font=(self.font_ui, 10),
            parent_bg=BG_SURFACE,
        )

    def _make_stepper(self, parent: tk.Misc, var: tk.StringVar, lo: int, hi: int) -> ModernStepper:
        return ModernStepper(
            parent,
            var,
            lo,
            hi,
            font=(self.font_ui, 10),
            parent_bg=BG_SURFACE,
        )

    def _bind_dynamic_wrap(self, container: tk.Misc, *labels: tk.Label) -> None:
        def _on_cfg(event: tk.Event[tk.Misc]) -> None:
            wrap = max(scale_px(self, 220), event.width - scale_px(self, 24))
            for lbl in labels:
                lbl.configure(wraplength=wrap)

        container.bind("<Configure>", _on_cfg, add="+")

    def _sync_sidebar_width(self) -> None:
        sb_pad = scale_px(self, 12)
        gap = scale_px(self, 5)
        tools_w = (
            int(self.btn_up.cget("width"))
            + int(self.btn_down.cget("width"))
            + int(self.btn_clear.cget("width"))
            + 2 * gap
            + 2 * sb_pad
            + scale_px(self, 14)
        )
        sum_w, _ = measure_text(self, (self.font_ui, 9, "bold"), self.lbl_slot_summary.cget("text"))
        needed = max(scale_px(self, 285), tools_w, sum_w + 2 * sb_pad + scale_px(self, 18))
        self.sidebar.configure(width=needed)

    # --- Slot state synchronization -------------------------------------------

    def _bind_form_traces(self) -> None:
        watched = (
            self.var_btn_enabled,
            self.var_btn_name,
            self.var_btn_desc,
            self.var_btn_color,
            self.var_btn_mode,
            self.var_btn_on_label,
            self.var_btn_off_label,
            self.var_btn_auto_on,
            self.var_pb_number,
            self.var_on_level,
            self.var_off_level,
            self.var_on_fade,
            self.var_off_fade,
            self.var_off_action,
            self.var_on_cue,
            self.var_off_cue,
        )
        for var in watched:
            var.trace_add("write", lambda *_args: self._on_form_changed())

    def _select_slot(self, index: int) -> None:
        if not self._loading_slot:
            self._commit_current_slot()
        self.selected_slot = index
        self._load_slot_into_form(index)
        self._refresh_slot_sidebar()

    def _create_in_current_slot(self) -> None:
        pb_num = min(self.selected_slot + 1, 96)
        self.slots[self.selected_slot] = ButtonConfig(
            name=f"Playback {pb_num}",
            description="",
            enabled=True,
            color=ACCENT_COLORS[self.selected_slot % len(ACCENT_COLORS)],
            mode="playback_level",
            on_label="EIN",
            off_label="AUS",
            playback=pb_num,
            on_level=100,
            off_level=0,
        )
        self._load_slot_into_form(self.selected_slot)
        self._refresh_slot_sidebar()

    def _clear_current_slot(self) -> None:
        if self.slots[self.selected_slot] is None:
            return
        self.slots[self.selected_slot] = None
        self._load_slot_into_form(self.selected_slot)
        self._refresh_slot_sidebar()

    def _move_slot(self, delta: int) -> None:
        self._commit_current_slot()
        target = self.selected_slot + delta
        if not 0 <= target < MAX_BUTTONS:
            return
        self.slots[self.selected_slot], self.slots[target] = (
            self.slots[target],
            self.slots[self.selected_slot],
        )
        self.selected_slot = target
        self._load_slot_into_form(target)
        self._refresh_slot_sidebar()

    def _load_slot_into_form(self, index: int) -> None:
        self._loading_slot = True
        try:
            btn = self.slots[index]
            self.lbl_test_feedback.configure(text="")
            if btn is None:
                self.form_scroll.pack_forget()
                self.lbl_empty_slot_title.configure(text=self._t("empty_slot_title", n=index + 1))
                self.btn_create_slot.configure_style(text=self._t("empty_slot_btn", n=index + 1))
                self.empty_slot_frame.pack(fill="both", expand=True)
                return

            self.empty_slot_frame.pack_forget()
            self.form_scroll.pack(fill="both", expand=True)
            self.lbl_form_slot_header.configure(text=self._t("slot_edit_header", n=index + 1))

            self.var_btn_enabled.set(btn.enabled)
            self.var_btn_name.set(btn.name)
            self.var_btn_desc.set(btn.description)
            self.var_btn_color.set(btn.color)
            self.var_btn_mode.set(btn.mode)
            self.var_btn_on_label.set(btn.on_label)
            self.var_btn_off_label.set(btn.off_label)
            self.var_btn_auto_on.set(btn.auto_on_at_startup)

            self.var_pb_number.set(str(btn.playback))
            self.var_on_level.set(str(btn.on_level))
            self.var_off_level.set(str(btn.off_level))
            self.var_on_fade.set(btn.on_fade or "")
            self.var_off_fade.set(btn.off_fade or "")
            self.var_off_action.set(btn.off_action)
            self.var_on_cue.set(btn.on_cue)
            self.var_off_cue.set(btn.off_cue)

            self.txt_on_cmds.delete("1.0", "end")
            self.txt_on_cmds.insert("1.0", "\n".join(btn.on_commands))
            self.txt_off_cmds.delete("1.0", "end")
            self.txt_off_cmds.insert("1.0", "\n".join(btn.off_commands))

            self._update_color_swatches()
            self._show_mode_panel(btn.mode)
            self._update_preview()
            for card in self._section_cards:
                card.sync_height()
        finally:
            self._loading_slot = False

    def _select_color(self, color: str) -> None:
        self.var_btn_color.set(color)
        self._update_color_swatches()
        self._on_form_changed()

    def _update_color_swatches(self) -> None:
        current = self.var_btn_color.get()
        for name, canvas in self._color_buttons.items():
            selected = name == current
            lbl_text = color_label(self.lang, name)
            font_spec = (self.font_ui, 8, "bold" if selected else "normal")
            tw, th = measure_text(self, font_spec, lbl_text)

            dot_d = scale_px(self, 9)
            pad_l = scale_px(self, 10)
            gap = scale_px(self, 7)
            pad_r = scale_px(self, 11)
            w = pad_l + dot_d + gap + tw + pad_r
            h = max(scale_px(self, 28), th + scale_px(self, 10))

            canvas.configure(width=w, height=h)
            canvas.delete("all")

            fill = BG_ELEVATED if selected else BG_INPUT
            border = ACCENT_HEX[name] if selected else BORDER_INPUT
            photo = render_rounded_photo(
                canvas,
                width=w,
                height=h,
                radius=scale_px(self, 8),
                fill=fill,
                border=border,
                border_width=2 if selected else 1,
                parent_bg=BG_SURFACE,
            )
            if photo is not None:
                self._color_photos[name] = photo
                canvas.create_image(0, 0, image=photo, anchor="nw")

            cy = h / 2
            canvas.create_oval(
                pad_l,
                cy - dot_d / 2,
                pad_l + dot_d,
                cy + dot_d / 2,
                fill=ACCENT_HEX[name],
                outline="",
            )
            canvas.create_text(
                pad_l + dot_d + gap,
                cy,
                text=lbl_text,
                anchor="w",
                fill=TEXT_PRIMARY if selected else TEXT_SECONDARY,
                font=font_spec,
            )

    def _select_mode(self, mode: str) -> None:
        if mode == "custom":
            on_txt = self.txt_on_cmds.get("1.0", "end-1c").strip()
            off_txt = self.txt_off_cmds.get("1.0", "end-1c").strip()
            if not on_txt and not off_txt:
                built, _ = self._build_slot_from_form()
                if built is not None:
                    try:
                        self.txt_on_cmds.insert("1.0", "\n".join(built.resolve_on_commands()))
                        self.txt_off_cmds.insert("1.0", "\n".join(built.resolve_off_commands()))
                    except ZerosValueError:
                        pass
        self.var_btn_mode.set(mode)
        self._show_mode_panel(mode)
        self._on_form_changed()

    def _show_mode_panel(self, mode: str) -> None:
        for panel in (
            self.panel_pb_level,
            self.panel_pb_go,
            self.panel_cue_pair,
            self.panel_custom,
        ):
            panel.pack_forget()
        for m_id, btn in self._mode_buttons.items():
            if m_id == mode:
                btn.configure_style(
                    bg_color=BTN_PRIMARY_BG,
                    hover_color=BTN_PRIMARY_HOVER,
                    border_color="",
                )
            else:
                btn.configure_style(
                    bg_color=BTN_SECONDARY_BG,
                    hover_color=BTN_SECONDARY_HOVER,
                    border_color=BTN_SECONDARY_BORDER,
                )

        if mode == "playback_level":
            self.panel_pb_level.pack(fill="x")
        elif mode == "playback_go_release":
            self.panel_pb_go.pack(fill="x")
        elif mode == "cue_pair":
            self.panel_cue_pair.pack(fill="x")
        elif mode == "custom":
            self.panel_custom.pack(fill="x")
        self.card_mode_outer.sync_height()

    def _raw_dict_from_form(self, existing_id: str = "") -> dict[str, object]:
        mode = self.var_btn_mode.get()
        d: dict[str, object] = {
            "id": existing_id,
            "name": self.var_btn_name.get(),
            "description": self.var_btn_desc.get(),
            "enabled": bool(self.var_btn_enabled.get()),
            "color": self.var_btn_color.get(),
            "mode": mode,
            "on_label": self.var_btn_on_label.get(),
            "off_label": self.var_btn_off_label.get(),
            "auto_on_at_startup": bool(self.var_btn_auto_on.get()),
        }
        if mode == "playback_level":
            d["playback"] = self.var_pb_number.get().strip()
            d["on_level"] = self.var_on_level.get().strip()
            d["off_level"] = self.var_off_level.get().strip()
            d["on_fade"] = self.var_on_fade.get().strip() or None
            d["off_fade"] = self.var_off_fade.get().strip() or None
        elif mode == "playback_go_release":
            d["playback"] = self.var_pb_number.get().strip()
            d["off_action"] = self.var_off_action.get()
        elif mode == "cue_pair":
            d["playback"] = self.var_pb_number.get().strip()
            d["on_cue"] = self.var_on_cue.get().strip()
            d["off_cue"] = self.var_off_cue.get().strip()
        elif mode == "custom":
            on_lines = [
                ln.strip()
                for ln in self.txt_on_cmds.get("1.0", "end-1c").splitlines()
                if ln.strip()
            ]
            off_lines = [
                ln.strip()
                for ln in self.txt_off_cmds.get("1.0", "end-1c").splitlines()
                if ln.strip()
            ]
            d["on_commands"] = on_lines
            d["off_commands"] = off_lines
        return d

    def _build_slot_from_form(self) -> tuple[ButtonConfig | None, list[str]]:
        cur = self.slots[self.selected_slot]
        if cur is None:
            return None, []
        probe = {
            "title": "Probe",
            "console": {"host": "127.0.0.1", "port": 8830, "transport": "udp"},
            "buttons": [self._raw_dict_from_form(existing_id=cur.id)],
        }
        parsed, res = parse_config(probe)
        if parsed is None or not res.ok:
            return None, res.errors
        return parsed.buttons[0], []

    def _commit_current_slot(self) -> bool:
        if self.slots[self.selected_slot] is None:
            return True
        built, errors = self._build_slot_from_form()
        if built is not None and not errors:
            self.slots[self.selected_slot] = built
            return True
        return False

    def _on_form_changed(self) -> None:
        if self._loading_slot or self.slots[self.selected_slot] is None:
            return
        self._commit_current_slot()
        self._update_preview()
        self._refresh_slot_sidebar()

    def _update_preview(self) -> None:
        on_tag = self._t("default_on")
        off_tag = self._t("default_off")
        built, errors = self._build_slot_from_form()
        if errors or built is None:
            self.lbl_preview_on.configure(text=f"{on_tag:<6} -> {self._t('preview_invalid')}")
            self.lbl_preview_off.configure(text=f"{off_tag:<6} -> -")
            self.lbl_preview_status.configure(
                text=self._t("preview_err_prefix") + "; ".join(errors),
                fg=STATUS_ERR_FG,
            )
            self.card_preview_outer.sync_height()
            return

        on_cmds = built.resolve_on_commands()
        off_cmds = built.resolve_off_commands()
        self.lbl_preview_on.configure(text=f"{on_tag:<6} -> " + " , ".join(on_cmds))
        self.lbl_preview_off.configure(text=f"{off_tag:<6} -> " + " , ".join(off_cmds))
        warns = built.warnings()
        if warns:
            self.lbl_preview_status.configure(
                text=self._t("preview_warn_prefix") + " | ".join(warns),
                fg=STATUS_WARN_FG,
            )
        else:
            self.lbl_preview_status.configure(
                text=self._t("preview_confirmed"),
                fg=STATUS_ON_FG,
            )
        self.card_preview_outer.sync_height()

    def _refresh_slot_sidebar(self) -> None:
        occupied = [b for b in self.slots if b is not None]
        active_count = sum(1 for b in occupied if b.enabled)
        self.lbl_slot_summary.configure(
            text=self._t("slot_summary_fmt", active=active_count, occupied=len(occupied))
        )
        for idx, (row, bar, dot, lbl) in enumerate(self._slot_row_widgets):
            is_sel = idx == self.selected_slot
            bg = "#1F283D" if is_sel else BG_ELEVATED
            row.configure(bg=bg)
            dot.configure(bg=bg)
            lbl.configure(bg=bg)

            btn = self.slots[idx]
            if btn is None:
                bar.configure(bg=BORDER_FOCUS if is_sel else bg)
                dot.configure(text="○", fg=TEXT_MUTED)
                lbl.configure(
                    text=f"{idx + 1}. {self._t('slot_free')}",
                    fg=TEXT_PRIMARY if is_sel else TEXT_MUTED,
                    font=(self.font_ui, 9, "bold" if is_sel else "normal"),
                )
            else:
                acc = ACCENT_HEX.get(btn.color, TEXT_SECONDARY)
                bar.configure(bg=BORDER_FOCUS if is_sel else (acc if btn.enabled else TEXT_MUTED))
                dot.configure(text="●", fg=acc if btn.enabled else TEXT_MUTED)
                prefix = "" if btn.enabled else self._t("slot_hidden_prefix")
                lbl.configure(
                    text=f"{idx + 1}. {prefix}{btn.name}",
                    fg=TEXT_PRIMARY if btn.enabled else TEXT_SECONDARY,
                    font=(self.font_ui, 9, "bold" if is_sel else "normal"),
                )

    def _test_current_slot(self, side: str) -> None:
        built, errors = self._build_slot_from_form()
        if errors or built is None:
            messagebox.showerror(
                self._t("dlg_test_err_title"),
                self._t("dlg_test_err_body") + "\n".join(errors),
                parent=self,
            )
            return
        entries = self.controller.trigger_button_config(built, "on" if side == "on" else "off")
        if entries and all(e.ok for e in entries):
            addrs = ", ".join(e.address for e in entries)
            mode_note = self._t("test_dry_note") if self.controller.dry_run else ""
            self.lbl_test_feedback.configure(
                text=self._t("test_sent_fmt", mode=mode_note, addrs=addrs),
                fg=STATUS_ON_FG,
            )
        else:
            err_msg = "; ".join(e.outcome for e in entries)
            self.lbl_test_feedback.configure(
                text=self._t("preview_err_prefix") + err_msg,
                fg=STATUS_ERR_FG,
            )

    # --- Full validation & saving ---------------------------------------------

    def _assemble_panel_config(self) -> tuple[PanelConfig | None, list[str]]:
        if self.slots[self.selected_slot] is not None:
            built, slot_errors = self._build_slot_from_form()
            if slot_errors or built is None:
                return None, [f"Slot {self.selected_slot + 1}: {e}" for e in slot_errors]
            self.slots[self.selected_slot] = built

        try:
            port_val: object = int(self.var_port.get().strip())
        except ValueError:
            port_val = self.var_port.get().strip()

        try:
            delay_val: object = float(self.var_startup_delay.get().strip())
        except ValueError:
            delay_val = self.var_startup_delay.get().strip()

        ui_dict: dict[str, object] = {
            "start_locked": bool(self.var_start_locked.get()),
            "always_on_top": bool(self.var_always_on_top.get()),
            "window_mode": self.var_window_mode.get(),
            "show_all_off": bool(self.var_show_all_off.get()),
            "startup_delay_s": delay_val,
        }
        if self._initial_yaml_lang is not None:
            ui_dict["language"] = self.lang

        raw_buttons = [b.to_dict() for b in self.slots if b is not None]
        raw = {
            "title": self.var_title.get().strip(),
            "console": {
                "host": self.var_host.get().strip(),
                "port": port_val,
                "transport": self.var_transport.get(),
            },
            "ui": ui_dict,
            "buttons": raw_buttons,
        }
        cfg, res = parse_config(raw)
        if cfg is None or not res.ok:
            return None, res.errors
        check_res = check(cfg.to_dict())
        if not check_res.ok:
            return None, check_res.errors
        return cfg, []

    def _apply_autostart_setting(self, target_path: Path | None) -> None:
        if not self.autostart.supported:
            return
        try:
            if self.var_autostart.get():
                self.autostart.enable(config_path=target_path)
            else:
                self.autostart.disable()
        except (AutostartNotSupportedError, OSError) as exc:
            messagebox.showwarning(
                self._t("dlg_autostart_warn"),
                self._t("dlg_autostart_err", err=exc),
                parent=self,
            )

    def _on_save(self) -> None:
        cfg, errors = self._assemble_panel_config()
        if errors or cfg is None:
            messagebox.showerror(
                self._t("dlg_incomplete_title"),
                self._t("dlg_incomplete_body") + "\n- ".join(errors),
                parent=self,
            )
            return
        if self.controller.config_path is None:
            self._save_to_chosen_path(cfg)
            return
        self._persist_and_close(cfg, self.controller.config_path)

    def _on_save_as(self) -> None:
        cfg, errors = self._assemble_panel_config()
        if errors or cfg is None:
            messagebox.showerror(
                self._t("dlg_incomplete_title"),
                self._t("dlg_incomplete_body") + "\n- ".join(errors),
                parent=self,
            )
            return
        self._save_to_chosen_path(cfg)

    def _save_to_chosen_path(self, cfg: PanelConfig) -> None:
        initial_dir = (
            str(self.controller.config_path.parent)
            if self.controller.config_path
            else str(Path.cwd())
        )
        chosen = filedialog.asksaveasfilename(
            parent=self,
            title=self._t("dlg_save_title"),
            initialdir=initial_dir,
            initialfile="playbacks.local.yaml",
            defaultextension=".yaml",
            filetypes=[
                (self._t("dlg_yaml_filter"), "*.yaml *.yml"),
                (self._t("dlg_all_filter"), "*.*"),
            ],
        )
        if not chosen:
            return
        self._persist_and_close(cfg, Path(chosen))

    def _persist_and_close(self, cfg: PanelConfig, target: Path) -> None:
        try:
            self.controller.save_to_file(cfg, target)
        except (OSError, ZerosValueError) as exc:
            messagebox.showerror(self._t("dlg_err_save"), str(exc), parent=self)
            return
        self._apply_autostart_setting(target)
        self._on_applied(cfg, target)
        self.destroy()

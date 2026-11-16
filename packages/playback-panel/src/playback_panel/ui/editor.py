"""12-slot playback button editor and console/autostart settings dialog."""

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
    WINDOW_MODES,
    ButtonConfig,
    PanelConfig,
    check,
    parse_config,
)
from ..controller import PanelController
from .theme import (
    ACCENT_HEX,
    ACCENT_LABELS_DE,
    BG_ELEVATED,
    BG_HEADER,
    BG_INPUT,
    BG_ROOT,
    BG_SURFACE,
    BORDER_CARD,
    BORDER_FOCUS,
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
    BTN_SECONDARY_HOVER,
    STATUS_ERR_FG,
    STATUS_ON_FG,
    STATUS_WARN_FG,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    ScrollableFrame,
    TactileButton,
    pick_font_family,
    pick_mono_family,
)

MODE_CHOICES: tuple[tuple[str, str], ...] = (
    ("playback_level", "Playback-Level (100 <-> 0)"),
    ("playback_go_release", "Playback Go / Release"),
    ("cue_pair", "Cue-Paar (belegt)"),
    ("custom", "Frei / Mehrfach"),
)

WINDOW_MODE_LABELS: dict[str, str] = {
    "normal": "Normal",
    "maximized": "Maximiert",
    "fullscreen": "Vollbild (Kiosk)",
}


def _status_badge_de(cmd: Command) -> str:
    if cmd.status is Status.BELEGT:
        return "[belegt]"
    if cmd.status is Status.FORUM:
        return "[ungetestet]"
    return "[vermutet]"


class ConfigEditorWindow(tk.Toplevel):
    """Modal configuration window for up to 12 buttons, console target and autostart."""

    def __init__(
        self,
        parent: tk.Misc,
        controller: PanelController,
        autostart: AutostartManager,
        on_applied: Callable[[PanelConfig, Path | None], None],
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.autostart = autostart
        self._on_applied = on_applied

        self.font_ui = pick_font_family(self)
        self.font_mono = pick_mono_family(self)

        self.title("Konfigurieren - FLX Playback-Panel")
        self.configure(bg=BG_ROOT)
        self.geometry("1080x740")
        self.minsize(940, 620)
        self.transient(parent.winfo_toplevel())

        # Working copy of the 12 slots
        existing = [copy.deepcopy(b) for b in controller.config.buttons[:MAX_BUTTONS]]
        self.slots: list[ButtonConfig | None] = existing + [None] * (MAX_BUTTONS - len(existing))
        self.selected_slot: int = 0
        self._loading_slot = False

        # Console & UI working variables
        cfg = controller.config
        self.var_title = tk.StringVar(value=cfg.title)
        self.var_host = tk.StringVar(value=cfg.console.host)
        self.var_port = tk.StringVar(value=str(cfg.console.port))
        self.var_transport = tk.StringVar(value=cfg.console.transport)

        self.var_start_locked = tk.BooleanVar(value=cfg.ui.start_locked)
        self.var_always_on_top = tk.BooleanVar(value=cfg.ui.always_on_top)
        self.var_show_all_off = tk.BooleanVar(value=cfg.ui.show_all_off)
        self.var_window_mode = tk.StringVar(value=cfg.ui.window_mode)
        self.var_startup_delay = tk.StringVar(value=f"{cfg.ui.startup_delay_s:g}")

        self.var_autostart = tk.BooleanVar(value=autostart.is_enabled())

        # Selected slot form variables
        self.var_btn_enabled = tk.BooleanVar(value=True)
        self.var_btn_name = tk.StringVar()
        self.var_btn_desc = tk.StringVar()
        self.var_btn_color = tk.StringVar(value="amber")
        self.var_btn_mode = tk.StringVar(value="playback_level")
        self.var_btn_on_label = tk.StringVar(value="EIN")
        self.var_btn_off_label = tk.StringVar(value="AUS")
        self.var_btn_auto_on = tk.BooleanVar(value=False)

        self.var_pb_number = tk.StringVar(value="1")
        self.var_on_level = tk.StringVar(value="100")
        self.var_off_level = tk.StringVar(value="0")
        self.var_on_fade = tk.StringVar(value="")
        self.var_off_fade = tk.StringVar(value="")
        self.var_off_action = tk.StringVar(value="release")
        self.var_on_cue = tk.StringVar(value="1")
        self.var_off_cue = tk.StringVar(value="2")

        # Command assistant variables for custom mode
        self._cmd_ids = list(COMMANDS.keys())
        self.var_assist_cmd = tk.StringVar(value="playback_level")
        self.assist_param_vars: list[tk.StringVar] = []

        self._active_tab = "buttons"
        self._slot_row_widgets: list[tuple[tk.Frame, tk.Label, tk.Label]] = []
        self._mode_buttons: dict[str, TactileButton] = {}
        self._color_buttons: dict[str, tk.Canvas] = {}

        self._build_layout()
        self._bind_form_traces()
        self._select_slot(0)
        self.grab_set()
        self.focus_set()

    # --- Layout construction --------------------------------------------------

    def _build_layout(self) -> None:
        # Top tab header
        header = tk.Frame(self, bg=BG_HEADER, padx=20, pady=12)
        header.pack(side="top", fill="x")
        tk.Frame(self, bg=BORDER_SUBTLE, height=1).pack(side="top", fill="x")

        title_lbl = tk.Label(
            header,
            text="Konfiguration bearbeiten",
            font=(self.font_ui, 14, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_HEADER,
        )
        title_lbl.pack(side="left")

        tab_bar = tk.Frame(header, bg=BG_HEADER)
        tab_bar.pack(side="right")

        self.btn_tab_buttons = TactileButton(
            tab_bar,
            "1 | Buttons programmieren (1-12)",
            command=lambda: self._switch_tab("buttons"),
            bg_color=BTN_PRIMARY_BG,
            hover_color=BTN_PRIMARY_HOVER,
            active_color=BTN_PRIMARY_ACTIVE,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 10, "bold"),
            width=245,
            height=34,
        )
        self.btn_tab_buttons.pack(side="left", padx=(0, 8))

        self.btn_tab_settings = TactileButton(
            tab_bar,
            "2 | Pult, Fenster & Autostart",
            command=lambda: self._switch_tab("settings"),
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 10, "bold"),
            width=225,
            height=34,
        )
        self.btn_tab_settings.pack(side="left")

        # Bottom action footer
        tk.Frame(self, bg=BORDER_SUBTLE, height=1).pack(side="bottom", fill="x")
        footer = tk.Frame(self, bg=BG_HEADER, padx=20, pady=12)
        footer.pack(side="bottom", fill="x")

        path_str = (
            str(self.controller.config_path)
            if self.controller.config_path
            else "Noch keine Datei gewählt (wird beim Speichern abgefragt)"
        )
        self.lbl_footer_path = tk.Label(
            footer,
            text=f"Datei: {path_str}",
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_HEADER,
        )
        self.lbl_footer_path.pack(side="left")

        TactileButton(
            footer,
            "Speichern & Übernehmen",
            command=self._on_save,
            bg_color=BTN_ON_BG,
            hover_color=BTN_ON_HOVER,
            active_color=BTN_ON_ACTIVE,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 10, "bold"),
            width=195,
            height=36,
        ).pack(side="right")

        TactileButton(
            footer,
            "Speichern unter...",
            command=self._on_save_as,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 10),
            width=145,
            height=36,
        ).pack(side="right", padx=(0, 8))

        TactileButton(
            footer,
            "Abbrechen",
            command=self.destroy,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 10),
            width=105,
            height=36,
        ).pack(side="right", padx=(0, 8))

        # Body container holding both tabs
        self.body = tk.Frame(self, bg=BG_ROOT)
        self.body.pack(side="top", fill="both", expand=True)

        self.tab_buttons_frame = tk.Frame(self.body, bg=BG_ROOT)
        self.tab_settings_frame = tk.Frame(self.body, bg=BG_ROOT)

        self._build_buttons_tab(self.tab_buttons_frame)
        self._build_settings_tab(self.tab_settings_frame)

        self.tab_buttons_frame.pack(fill="both", expand=True)

    def _switch_tab(self, tab: str) -> None:
        self._commit_current_slot()
        self._active_tab = tab
        if tab == "buttons":
            self.tab_settings_frame.pack_forget()
            self.tab_buttons_frame.pack(fill="both", expand=True)
            self.btn_tab_buttons.configure_style(
                bg_color=BTN_PRIMARY_BG, hover_color=BTN_PRIMARY_HOVER
            )
            self.btn_tab_settings.configure_style(
                bg_color=BTN_SECONDARY_BG, hover_color=BTN_SECONDARY_HOVER
            )
        else:
            self.tab_buttons_frame.pack_forget()
            self._refresh_autostart_preview()
            self.tab_settings_frame.pack(fill="both", expand=True)
            self.btn_tab_settings.configure_style(
                bg_color=BTN_PRIMARY_BG, hover_color=BTN_PRIMARY_HOVER
            )
            self.btn_tab_buttons.configure_style(
                bg_color=BTN_SECONDARY_BG, hover_color=BTN_SECONDARY_HOVER
            )

    # --- Tab 1: 12-Slot Button Editor -----------------------------------------

    def _build_buttons_tab(self, parent: tk.Frame) -> None:
        # Left sidebar: 12 slots
        sidebar = tk.Frame(parent, bg=BG_SURFACE, width=285, padx=12, pady=12)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Frame(parent, bg=BORDER_SUBTLE, width=1).pack(side="left", fill="y")

        self.lbl_slot_summary = tk.Label(
            sidebar,
            text="Plätze 1 bis 12",
            font=(self.font_ui, 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            anchor="w",
        )
        self.lbl_slot_summary.pack(fill="x", pady=(0, 8))

        slots_list = tk.Frame(sidebar, bg=BG_SURFACE)
        slots_list.pack(fill="both", expand=True)

        self._slot_row_widgets.clear()
        for idx in range(MAX_BUTTONS):
            row = tk.Frame(
                slots_list,
                bg=BG_ELEVATED,
                padx=8,
                pady=4,
                highlightthickness=1,
                highlightbackground=BORDER_CARD,
                cursor="hand2",
            )
            row.pack(fill="x", pady=2)
            dot = tk.Label(
                row,
                text="●",
                font=(self.font_ui, 10, "bold"),
                fg=TEXT_MUTED,
                bg=BG_ELEVATED,
            )
            dot.pack(side="left", padx=(0, 6))
            lbl = tk.Label(
                row,
                text=f"{idx + 1}. Frei",
                font=(self.font_ui, 9),
                fg=TEXT_SECONDARY,
                bg=BG_ELEVATED,
                anchor="w",
            )
            lbl.pack(side="left", fill="x", expand=True)

            for w in (row, dot, lbl):
                w.bind("<Button-1>", lambda _e, i=idx: self._select_slot(i))
            self._slot_row_widgets.append((row, dot, lbl))

        # Reorder / clear controls
        tools = tk.Frame(sidebar, bg=BG_SURFACE)
        tools.pack(fill="x", pady=(8, 0))
        TactileButton(
            tools,
            "▲ Hoch",
            command=lambda: self._move_slot(-1),
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 9, "bold"),
            width=76,
            height=30,
        ).pack(side="left", padx=(0, 4))
        TactileButton(
            tools,
            "▼ Runter",
            command=lambda: self._move_slot(1),
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 9, "bold"),
            width=82,
            height=30,
        ).pack(side="left", padx=(0, 4))
        TactileButton(
            tools,
            "Leeren",
            command=self._clear_current_slot,
            bg_color=BTN_DANGER_BG,
            hover_color=BTN_DANGER_HOVER,
            active_color=BTN_DANGER_ACTIVE,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 9, "bold"),
            width=86,
            height=30,
        ).pack(side="right")

        # Right side: empty-slot state OR full form
        self.detail_host = tk.Frame(parent, bg=BG_ROOT)
        self.detail_host.pack(side="left", fill="both", expand=True)

        # Empty slot placeholder
        self.empty_slot_frame = tk.Frame(self.detail_host, bg=BG_ROOT, padx=40, pady=60)
        self.lbl_empty_slot_title = tk.Label(
            self.empty_slot_frame,
            text="Platz ist frei",
            font=(self.font_ui, 15, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_ROOT,
        )
        self.lbl_empty_slot_title.pack(pady=(30, 8))
        tk.Label(
            self.empty_slot_frame,
            text=(
                "Nicht belegte Plätze werden im Bedienfenster ausgeblendet.\n"
                "Klicke unten, um diesen Button-Platz zu programmieren (Standard: "
                "EIN = Level 100 %, AUS = Level 0 % auf demselben Playback)."
            ),
            font=(self.font_ui, 10),
            fg=TEXT_SECONDARY,
            bg=BG_ROOT,
            justify="center",
        ).pack(pady=(0, 20))
        self.btn_create_slot = TactileButton(
            self.empty_slot_frame,
            "+ Diesen Button-Platz belegen",
            command=self._create_in_current_slot,
            bg_color=BTN_PRIMARY_BG,
            hover_color=BTN_PRIMARY_HOVER,
            active_color=BTN_PRIMARY_ACTIVE,
            parent_bg=BG_ROOT,
            font=(self.font_ui, 11, "bold"),
            width=260,
            height=42,
        )
        self.btn_create_slot.pack()

        # Occupied slot scrollable form
        self.form_scroll = ScrollableFrame(self.detail_host, bg=BG_ROOT)
        form = self.form_scroll.inner
        form.configure(padx=24, pady=18)

        # Header row in form
        top_row = tk.Frame(form, bg=BG_ROOT)
        top_row.pack(fill="x", pady=(0, 12))
        self.lbl_form_slot_header = tk.Label(
            top_row,
            text="Platz 1",
            font=(self.font_ui, 13, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_ROOT,
        )
        self.lbl_form_slot_header.pack(side="left")

        chk_enabled = tk.Checkbutton(
            top_row,
            text="Im Bedienfenster anzeigen (aktiv)",
            variable=self.var_btn_enabled,
            font=(self.font_ui, 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_ROOT,
            selectcolor=BG_INPUT,
            activebackground=BG_ROOT,
            activeforeground=TEXT_PRIMARY,
            highlightthickness=0,
            bd=0,
        )
        chk_enabled.pack(side="right")

        # Card 1: Name, Description, Color & Labels
        card_meta = self._make_section_card(form, "Darstellung & Kurzbeschreibung")

        grid_meta = tk.Frame(card_meta, bg=BG_SURFACE)
        grid_meta.pack(fill="x")
        grid_meta.columnconfigure(1, weight=1)
        grid_meta.columnconfigure(3, weight=1)

        self._add_label(grid_meta, "Name (Titel):", 0, 0)
        self._make_entry(grid_meta, self.var_btn_name).grid(
            row=0, column=1, columnspan=3, sticky="ew", pady=4
        )

        self._add_label(grid_meta, "Kurzbeschreibung:", 1, 0)
        self._make_entry(grid_meta, self.var_btn_desc).grid(
            row=1, column=1, columnspan=3, sticky="ew", pady=4
        )

        self._add_label(grid_meta, "Text EIN-Button:", 2, 0)
        self._make_entry(grid_meta, self.var_btn_on_label, width=14).grid(
            row=2, column=1, sticky="ew", pady=4, padx=(0, 14)
        )
        self._add_label(grid_meta, "Text AUS-Button:", 2, 2)
        self._make_entry(grid_meta, self.var_btn_off_label, width=14).grid(
            row=2, column=3, sticky="ew", pady=4
        )

        # Accent color picker
        color_row = tk.Frame(card_meta, bg=BG_SURFACE)
        color_row.pack(fill="x", pady=(8, 4))
        tk.Label(
            color_row,
            text="Farbakzent:",
            font=(self.font_ui, 9, "bold"),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            width=12,
            anchor="w",
        ).pack(side="left", padx=(0, 6))
        for color_name in ACCENT_COLORS:
            swatch = tk.Canvas(
                color_row,
                width=76,
                height=26,
                bg=BG_SURFACE,
                highlightthickness=0,
                cursor="hand2",
            )
            swatch.pack(side="left", padx=(0, 5))
            swatch.bind("<Button-1>", lambda _e, c=color_name: self._select_color(c))
            self._color_buttons[color_name] = swatch

        chk_auto_on = tk.Checkbutton(
            card_meta,
            text="Beim Programmstart automatisch einschalten (EIN nach Startverzögerung senden)",
            variable=self.var_btn_auto_on,
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            selectcolor=BG_INPUT,
            activebackground=BG_SURFACE,
            activeforeground=TEXT_PRIMARY,
            highlightthickness=0,
            bd=0,
        )
        chk_auto_on.pack(anchor="w", pady=(6, 0))

        # Card 2: Mode & Command Parameters
        card_mode = self._make_section_card(form, "Funktions-Programmierung (EIN / AUS)")

        mode_bar = tk.Frame(card_mode, bg=BG_SURFACE)
        mode_bar.pack(fill="x", pady=(0, 12))
        for mode_id, mode_title in MODE_CHOICES:
            b = TactileButton(
                mode_bar,
                mode_title,
                command=lambda m=mode_id: self._select_mode(m),
                parent_bg=BG_SURFACE,
                font=(self.font_ui, 9, "bold"),
                width=158,
                height=32,
            )
            b.pack(side="left", padx=(0, 6))
            self._mode_buttons[mode_id] = b

        self.mode_panels_host = tk.Frame(card_mode, bg=BG_SURFACE)
        self.mode_panels_host.pack(fill="x")

        # Subpanel A: playback_level
        self.panel_pb_level = tk.Frame(self.mode_panels_host, bg=BG_SURFACE)
        self._build_panel_pb_level(self.panel_pb_level)

        # Subpanel B: playback_go_release
        self.panel_pb_go = tk.Frame(self.mode_panels_host, bg=BG_SURFACE)
        self._build_panel_pb_go(self.panel_pb_go)

        # Subpanel C: cue_pair
        self.panel_cue_pair = tk.Frame(self.mode_panels_host, bg=BG_SURFACE)
        self._build_panel_cue_pair(self.panel_cue_pair)

        # Subpanel D: custom
        self.panel_custom = tk.Frame(self.mode_panels_host, bg=BG_SURFACE)
        self._build_panel_custom(self.panel_custom)

        # Card 3: Live OSC Preview & Direct Test
        card_preview = self._make_section_card(form, "Vorschau & Live-Test")
        self.lbl_preview_on = tk.Label(
            card_preview,
            text="EIN  -> -",
            font=(self.font_mono, 10),
            fg=STATUS_ON_FG,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
        )
        self.lbl_preview_on.pack(fill="x", pady=(0, 2))

        self.lbl_preview_off = tk.Label(
            card_preview,
            text="AUS  -> -",
            font=(self.font_mono, 10),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
        )
        self.lbl_preview_off.pack(fill="x", pady=(0, 6))

        self.lbl_preview_status = tk.Label(
            card_preview,
            text="",
            font=(self.font_ui, 9),
            fg=STATUS_WARN_FG,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
            wraplength=640,
        )
        self.lbl_preview_status.pack(fill="x", pady=(0, 8))

        test_bar = tk.Frame(card_preview, bg=BG_SURFACE)
        test_bar.pack(fill="x")
        TactileButton(
            test_bar,
            "EIN jetzt testen",
            command=lambda: self._test_current_slot("on"),
            bg_color=BTN_ON_BG,
            hover_color=BTN_ON_HOVER,
            active_color=BTN_ON_ACTIVE,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 9, "bold"),
            width=155,
            height=32,
        ).pack(side="left", padx=(0, 8))
        TactileButton(
            test_bar,
            "AUS jetzt testen",
            command=lambda: self._test_current_slot("off"),
            bg_color=BTN_OFF_ARMED_BG,
            hover_color=BTN_OFF_HOVER,
            active_color=BTN_OFF_ACTIVE,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 9, "bold"),
            width=155,
            height=32,
        ).pack(side="left")
        self.lbl_test_feedback = tk.Label(
            test_bar,
            text="",
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
        )
        self.lbl_test_feedback.pack(side="left", padx=(12, 0))

    def _build_panel_pb_level(self, p: tk.Frame) -> None:
        tk.Label(
            p,
            text=(
                "Standard-Modus: EIN setzt das gewählte Playback auf den Ein-Wert (z. B. 100 %), "
                "AUS setzt automatisch dasselbe Playback auf den Aus-Wert (Standard 0 %)."
            ),
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
            wraplength=640,
        ).pack(fill="x", pady=(0, 8))

        g = tk.Frame(p, bg=BG_SURFACE)
        g.pack(fill="x")
        self._add_label(g, "Playback (0-96):", 0, 0)
        self._make_spinbox(g, self.var_pb_number, 0, 96).grid(
            row=0, column=1, sticky="w", pady=4, padx=(0, 20)
        )

        self._add_label(g, "Level EIN (0-100 %):", 1, 0)
        self._make_spinbox(g, self.var_on_level, 0, 100).grid(
            row=1, column=1, sticky="w", pady=4, padx=(0, 20)
        )
        self._add_label(g, "Level AUS (0-100 %):", 1, 2)
        self._make_spinbox(g, self.var_off_level, 0, 100).grid(row=1, column=3, sticky="w", pady=4)

        self._add_label(g, "Fade EIN (Sek., opt.):", 2, 0)
        self._make_entry(g, self.var_on_fade, width=10).grid(
            row=2, column=1, sticky="w", pady=4, padx=(0, 20)
        )
        self._add_label(g, "Fade AUS (Sek., opt.):", 2, 2)
        self._make_entry(g, self.var_off_fade, width=10).grid(row=2, column=3, sticky="w", pady=4)

    def _build_panel_pb_go(self, p: tk.Frame) -> None:
        tk.Label(
            p,
            text=(
                "Startet das Playback mit Go (/zeros/playback/go/<playback>) und gibt es bei "
                "AUS frei (Release) oder hält es an (Pause)."
            ),
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
            wraplength=640,
        ).pack(fill="x", pady=(0, 8))

        g = tk.Frame(p, bg=BG_SURFACE)
        g.pack(fill="x")
        self._add_label(g, "Playback (0-96):", 0, 0)
        self._make_spinbox(g, self.var_pb_number, 0, 96).grid(
            row=0, column=1, sticky="w", pady=4, padx=(0, 20)
        )
        self._add_label(g, "Aktion bei AUS:", 1, 0)
        rb_frame = tk.Frame(g, bg=BG_SURFACE)
        rb_frame.grid(row=1, column=1, columnspan=3, sticky="w", pady=4)
        for val, label in (
            ("release", "Playback freigeben (release)"),
            ("pause", "Playback anhalten (pause)"),
        ):
            tk.Radiobutton(
                rb_frame,
                text=label,
                value=val,
                variable=self.var_off_action,
                font=(self.font_ui, 9),
                fg=TEXT_PRIMARY,
                bg=BG_SURFACE,
                selectcolor=BG_INPUT,
                activebackground=BG_SURFACE,
                activeforeground=TEXT_PRIMARY,
                highlightthickness=0,
                bd=0,
            ).pack(side="left", padx=(0, 14))

    def _build_panel_cue_pair(self, p: tk.Frame) -> None:
        tk.Label(
            p,
            text=(
                "Nutzt den im ZerOS-Handbuch belegten und am FLX S48 getesteten Befehl "
                "/zeros/cue/go/<playback>/<cue>: ein Cue für EIN und ein Cue für AUS."
            ),
            font=(self.font_ui, 9),
            fg=STATUS_ON_FG,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
            wraplength=640,
        ).pack(fill="x", pady=(0, 8))

        g = tk.Frame(p, bg=BG_SURFACE)
        g.pack(fill="x")
        self._add_label(g, "Playback (0-96):", 0, 0)
        self._make_spinbox(g, self.var_pb_number, 0, 96).grid(
            row=0, column=1, sticky="w", pady=4, padx=(0, 20)
        )
        self._add_label(g, "Cue bei EIN:", 1, 0)
        self._make_entry(g, self.var_on_cue, width=10).grid(
            row=1, column=1, sticky="w", pady=4, padx=(0, 20)
        )
        self._add_label(g, "Cue bei AUS:", 1, 2)
        self._make_entry(g, self.var_off_cue, width=10).grid(row=1, column=3, sticky="w", pady=4)

    def _build_panel_custom(self, p: tk.Frame) -> None:
        tk.Label(
            p,
            text=(
                "Volle Flexibilität: Kombiniere beliebige Befehle aus docs/02-flx-osc-referenz.md "
                "(auch mehrere Befehle gleichzeitig pro Tastendruck, eine Adresse je Zeile)."
            ),
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
            wraplength=620,
        ).pack(fill="x", pady=(0, 8))

        # Command builder assistant box
        assist = tk.Frame(
            p,
            bg=BG_ELEVATED,
            padx=10,
            pady=8,
            highlightthickness=1,
            highlightbackground=BORDER_CARD,
        )
        assist.pack(fill="x", pady=(0, 10))

        top_a = tk.Frame(assist, bg=BG_ELEVATED)
        top_a.pack(fill="x")
        tk.Label(
            top_a,
            text="Befehls-Baukasten:",
            font=(self.font_ui, 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_ELEVATED,
        ).pack(side="left", padx=(0, 8))

        cmd_menu = tk.OptionMenu(
            top_a,
            self.var_assist_cmd,
            *self._cmd_ids,
            command=lambda _v: self._rebuild_assist_params(),
        )
        cmd_menu.configure(
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            activebackground=BG_SURFACE,
            activeforeground=TEXT_PRIMARY,
            highlightthickness=1,
            highlightbackground=BORDER_CARD,
            font=(self.font_ui, 9),
        )
        cmd_menu["menu"].configure(bg=BG_INPUT, fg=TEXT_PRIMARY, font=(self.font_ui, 9))
        cmd_menu.pack(side="left")

        self.lbl_assist_summary = tk.Label(
            top_a,
            text="",
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_ELEVATED,
        )
        self.lbl_assist_summary.pack(side="left", padx=(10, 0))

        self.assist_params_frame = tk.Frame(assist, bg=BG_ELEVATED)
        self.assist_params_frame.pack(fill="x", pady=(6, 6))

        btn_a = tk.Frame(assist, bg=BG_ELEVATED)
        btn_a.pack(fill="x")
        TactileButton(
            btn_a,
            "+ Zu EIN hinzufügen",
            command=lambda: self._append_assisted_command("on"),
            bg_color=BTN_PRIMARY_BG,
            hover_color=BTN_PRIMARY_HOVER,
            parent_bg=BG_ELEVATED,
            font=(self.font_ui, 9, "bold"),
            width=155,
            height=28,
        ).pack(side="left", padx=(0, 8))
        TactileButton(
            btn_a,
            "+ Zu AUS hinzufügen",
            command=lambda: self._append_assisted_command("off"),
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            parent_bg=BG_ELEVATED,
            font=(self.font_ui, 9, "bold"),
            width=155,
            height=28,
        ).pack(side="left")

        # Two side-by-side multiline text boxes for ON and OFF OSC commands
        cols = tk.Frame(p, bg=BG_SURFACE)
        cols.pack(fill="x")
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        tk.Label(
            cols,
            text="OSC-Befehle bei EIN (1 pro Zeile):",
            font=(self.font_ui, 9, "bold"),
            fg=STATUS_ON_FG,
            bg=BG_SURFACE,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        tk.Label(
            cols,
            text="OSC-Befehle bei AUS (1 pro Zeile):",
            font=(self.font_ui, 9, "bold"),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.txt_on_cmds = tk.Text(
            cols,
            height=4,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            font=(self.font_mono, 10),
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_CARD,
            highlightcolor=BORDER_FOCUS,
            padx=8,
            pady=6,
        )
        self.txt_on_cmds.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(4, 0))
        self.txt_on_cmds.bind("<KeyRelease>", lambda _e: self._on_form_changed())

        self.txt_off_cmds = tk.Text(
            cols,
            height=4,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            font=(self.font_mono, 10),
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_CARD,
            highlightcolor=BORDER_FOCUS,
            padx=8,
            pady=6,
        )
        self.txt_off_cmds.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(4, 0))
        self.txt_off_cmds.bind("<KeyRelease>", lambda _e: self._on_form_changed())

        self._rebuild_assist_params()

    def _rebuild_assist_params(self) -> None:
        for child in self.assist_params_frame.winfo_children():
            child.destroy()
        self.assist_param_vars.clear()

        cmd = COMMANDS[self.var_assist_cmd.get()]
        self.lbl_assist_summary.configure(text=f"{cmd.summary} {_status_badge_de(cmd)}")
        all_specs = list(cmd.params) + list(cmd.optional)
        if not all_specs:
            tk.Label(
                self.assist_params_frame,
                text=f"Keine Parameter nötig ({cmd.example})",
                font=(self.font_ui, 9),
                fg=TEXT_SECONDARY,
                bg=BG_ELEVATED,
            ).pack(side="left")
            return

        defaults = {"playback": "1", "cue": "1", "level": "100", "number": "1", "value": "1"}
        for idx, spec in enumerate(all_specs):
            is_opt = idx >= len(cmd.params)
            lbl_text = f"{spec.name} (opt.):" if is_opt else f"{spec.name}:"
            tk.Label(
                self.assist_params_frame,
                text=lbl_text,
                font=(self.font_ui, 9),
                fg=TEXT_SECONDARY,
                bg=BG_ELEVATED,
            ).pack(side="left", padx=(0 if idx == 0 else 10, 4))
            var = tk.StringVar(value="" if is_opt else defaults.get(spec.name, ""))
            self.assist_param_vars.append(var)
            entry = self._make_entry(self.assist_params_frame, var, width=9)
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
            messagebox.showerror("Ungültiger Befehl", str(exc), parent=self)
            return

        widget = self.txt_on_cmds if side == "on" else self.txt_off_cmds
        current = widget.get("1.0", "end-1c").strip()
        new_text = f"{current}\n{addr}" if current else addr
        widget.delete("1.0", "end")
        widget.insert("1.0", new_text)
        self._on_form_changed()

    # --- Tab 2: Console, Window & Autostart Settings --------------------------

    def _build_settings_tab(self, parent: tk.Frame) -> None:
        scroll = ScrollableFrame(parent, bg=BG_ROOT)
        scroll.pack(fill="both", expand=True)
        wrap = scroll.inner
        wrap.configure(padx=32, pady=20)

        # Console card
        c_console = self._make_section_card(wrap, "FLX S48 - Netzwerkverbindung (OSC)")
        g1 = tk.Frame(c_console, bg=BG_SURFACE)
        g1.pack(fill="x")
        g1.columnconfigure(1, weight=1)

        self._add_label(g1, "Show-Titel:", 0, 0)
        self._make_entry(g1, self.var_title).grid(row=0, column=1, sticky="ew", pady=4)

        self._add_label(g1, "Pult IP-Adresse:", 1, 0)
        self._make_entry(g1, self.var_host, width=24).grid(row=1, column=1, sticky="w", pady=4)

        self._add_label(g1, "OSC-Port:", 2, 0)
        self._make_entry(g1, self.var_port, width=10).grid(row=2, column=1, sticky="w", pady=4)

        self._add_label(g1, "Transport-Protokoll:", 3, 0)
        tp_frame = tk.Frame(g1, bg=BG_SURFACE)
        tp_frame.grid(row=3, column=1, sticky="w", pady=4)
        for val, text in (
            ("udp", "UDP (Standard am FLX S48, empfohlen)"),
            ("tcp-slip", "TCP mit SLIP"),
        ):
            tk.Radiobutton(
                tp_frame,
                text=text,
                value=val,
                variable=self.var_transport,
                font=(self.font_ui, 9),
                fg=TEXT_PRIMARY,
                bg=BG_SURFACE,
                selectcolor=BG_INPUT,
                activebackground=BG_SURFACE,
                activeforeground=TEXT_PRIMARY,
                highlightthickness=0,
                bd=0,
            ).pack(side="left", padx=(0, 16))

        # Window & Event behavior card
        c_ui = self._make_section_card(wrap, "Bedienfenster & Event-Betrieb")
        for var, label in (
            (
                self.var_start_locked,
                "Gesperrt starten (Bedienmodus aktiv - schützt vor versehentlichem Verstellen)",
            ),
            (
                self.var_always_on_top,
                "Fenster immer im Vordergrund halten (Always on Top)",
            ),
            (
                self.var_show_all_off,
                "Sammelbutton »Alle Aus« in der oberen Leiste einblenden",
            ),
        ):
            tk.Checkbutton(
                c_ui,
                text=label,
                variable=var,
                font=(self.font_ui, 10),
                fg=TEXT_PRIMARY,
                bg=BG_SURFACE,
                selectcolor=BG_INPUT,
                activebackground=BG_SURFACE,
                activeforeground=TEXT_PRIMARY,
                highlightthickness=0,
                bd=0,
            ).pack(anchor="w", pady=3)

        g2 = tk.Frame(c_ui, bg=BG_SURFACE)
        g2.pack(fill="x", pady=(8, 0))
        self._add_label(g2, "Fenstergröße beim Start:", 0, 0)
        wm_frame = tk.Frame(g2, bg=BG_SURFACE)
        wm_frame.grid(row=0, column=1, sticky="w", pady=4)
        for wm in WINDOW_MODES:
            tk.Radiobutton(
                wm_frame,
                text=WINDOW_MODE_LABELS[wm],
                value=wm,
                variable=self.var_window_mode,
                font=(self.font_ui, 9),
                fg=TEXT_PRIMARY,
                bg=BG_SURFACE,
                selectcolor=BG_INPUT,
                activebackground=BG_SURFACE,
                activeforeground=TEXT_PRIMARY,
                highlightthickness=0,
                bd=0,
            ).pack(side="left", padx=(0, 14))

        self._add_label(g2, "Start-Verzögerung (Sek.):", 1, 0)
        self._make_entry(g2, self.var_startup_delay, width=10).grid(
            row=1, column=1, sticky="w", pady=4
        )

        # Windows Autostart card
        c_auto = self._make_section_card(wrap, "Windows-Autostart")
        tk.Label(
            c_auto,
            text=(
                "Startet das FLX Playback-Panel automatisch nach der Windows-Anmeldung "
                "(aktueller Benutzer unter HKCU\\...\\Run, keine Administratorrechte nötig) "
                "und lädt direkt die gespeicherte Konfigurationsdatei."
            ),
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
            justify="left",
            wraplength=760,
        ).pack(fill="x", pady=(0, 8))

        self.chk_autostart = tk.Checkbutton(
            c_auto,
            text="Mit Windows automatisch starten (Autostart aktivieren)",
            variable=self.var_autostart,
            command=self._refresh_autostart_preview,
            font=(self.font_ui, 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            selectcolor=BG_INPUT,
            activebackground=BG_SURFACE,
            activeforeground=TEXT_PRIMARY,
            highlightthickness=0,
            bd=0,
            state="normal" if self.autostart.supported else "disabled",
        )
        self.chk_autostart.pack(anchor="w", pady=(0, 6))

        self.lbl_autostart_cmd = tk.Label(
            c_auto,
            text="",
            font=(self.font_mono, 9),
            fg=TEXT_SECONDARY,
            bg=BG_INPUT,
            anchor="w",
            justify="left",
            padx=10,
            pady=8,
            wraplength=760,
        )
        self.lbl_autostart_cmd.pack(fill="x")
        self._refresh_autostart_preview()

    def _refresh_autostart_preview(self) -> None:
        planned = build_autostart_command(config_path=self.controller.config_path)
        if not self.autostart.supported:
            self.lbl_autostart_cmd.configure(
                text=(
                    "Hinweis: Auf diesem System nicht aktiv (Windows-Registry-Autostart steht "
                    f"unter Windows bereit).\nGeplanter Startbefehl: {planned}"
                )
            )
            return
        state = "AKTIV (wird beim Speichern gesetzt)" if self.var_autostart.get() else "INAKTIV"
        self.lbl_autostart_cmd.configure(text=f"Status: {state}\nBefehl: {planned}")

    # --- Widget helpers -------------------------------------------------------

    def _make_section_card(self, parent: tk.Misc, heading: str) -> tk.Frame:
        outer = tk.Frame(
            parent,
            bg=BG_SURFACE,
            padx=16,
            pady=14,
            highlightthickness=1,
            highlightbackground=BORDER_CARD,
        )
        outer.pack(fill="x", pady=(0, 14))
        tk.Label(
            outer,
            text=heading,
            font=(self.font_ui, 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            anchor="w",
        ).pack(fill="x", pady=(0, 10))
        return outer

    def _add_label(self, parent: tk.Misc, text: str, row: int, col: int) -> None:
        tk.Label(
            parent,
            text=text,
            font=(self.font_ui, 9, "bold"),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            anchor="w",
            width=21,
        ).grid(row=row, column=col, sticky="w", pady=4, padx=(0, 8))

    def _make_entry(self, parent: tk.Misc, var: tk.StringVar, width: int = 32) -> tk.Entry:
        return tk.Entry(
            parent,
            textvariable=var,
            width=width,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            font=(self.font_ui, 10),
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_CARD,
            highlightcolor=BORDER_FOCUS,
        )

    def _make_spinbox(self, parent: tk.Misc, var: tk.StringVar, lo: int, hi: int) -> tk.Spinbox:
        return tk.Spinbox(
            parent,
            from_=lo,
            to=hi,
            textvariable=var,
            width=8,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            buttonbackground=BG_ELEVATED,
            insertbackground=TEXT_PRIMARY,
            font=(self.font_ui, 10),
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_CARD,
            highlightcolor=BORDER_FOCUS,
        )

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
                self.lbl_empty_slot_title.configure(text=f"Platz {index + 1} ist frei")
                self.btn_create_slot.configure_style(
                    text=f"+ Platz {index + 1} jetzt programmieren"
                )
                self.empty_slot_frame.pack(fill="both", expand=True)
                return

            self.empty_slot_frame.pack_forget()
            self.form_scroll.pack(fill="both", expand=True)
            self.lbl_form_slot_header.configure(text=f"Platz {index + 1} bearbeiten")

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
        finally:
            self._loading_slot = False

    def _select_color(self, color: str) -> None:
        self.var_btn_color.set(color)
        self._update_color_swatches()
        self._on_form_changed()

    def _update_color_swatches(self) -> None:
        current = self.var_btn_color.get()
        for name, canvas in self._color_buttons.items():
            canvas.delete("all")
            selected = name == current
            bg = BG_ELEVATED if selected else BG_INPUT
            border = ACCENT_HEX[name] if selected else BORDER_CARD
            canvas.create_rectangle(
                1, 1, 74, 24, fill=bg, outline=border, width=2 if selected else 1
            )
            canvas.create_oval(6, 8, 15, 17, fill=ACCENT_HEX[name], outline="")
            canvas.create_text(
                45,
                13,
                text=ACCENT_LABELS_DE[name],
                fill=TEXT_PRIMARY if selected else TEXT_SECONDARY,
                font=(self.font_ui, 8, "bold" if selected else "normal"),
            )

    def _select_mode(self, mode: str) -> None:
        # Pre-populate custom commands from current button if custom boxes are empty
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
                btn.configure_style(bg_color=BTN_PRIMARY_BG, hover_color=BTN_PRIMARY_HOVER)
            else:
                btn.configure_style(bg_color=BTN_SECONDARY_BG, hover_color=BTN_SECONDARY_HOVER)

        if mode == "playback_level":
            self.panel_pb_level.pack(fill="x")
        elif mode == "playback_go_release":
            self.panel_pb_go.pack(fill="x")
        elif mode == "cue_pair":
            self.panel_cue_pair.pack(fill="x")
        elif mode == "custom":
            self.panel_custom.pack(fill="x")

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
        built, errors = self._build_slot_from_form()
        if errors or built is None:
            self.lbl_preview_on.configure(text="EIN  -> (Eingabe unvollständig / fehlerhaft)")
            self.lbl_preview_off.configure(text="AUS  -> -")
            self.lbl_preview_status.configure(text="Fehler: " + "; ".join(errors), fg=STATUS_ERR_FG)
            return

        on_cmds = built.resolve_on_commands()
        off_cmds = built.resolve_off_commands()
        self.lbl_preview_on.configure(text="EIN  -> " + " , ".join(on_cmds))
        self.lbl_preview_off.configure(text="AUS  -> " + " , ".join(off_cmds))
        warns = built.warnings()
        if warns:
            self.lbl_preview_status.configure(
                text="Hinweis: " + " | ".join(warns), fg=STATUS_WARN_FG
            )
        else:
            self.lbl_preview_status.configure(
                text="Status: belegt (laut ZerOS-Handbuch bestätigt).", fg=STATUS_ON_FG
            )

    def _refresh_slot_sidebar(self) -> None:
        occupied = [b for b in self.slots if b is not None]
        active_count = sum(1 for b in occupied if b.enabled)
        self.lbl_slot_summary.configure(
            text=f"Belegung: {active_count} aktiv ({len(occupied)} / {MAX_BUTTONS} programmiert)"
        )
        for idx, (row, dot, lbl) in enumerate(self._slot_row_widgets):
            is_sel = idx == self.selected_slot
            bg = BG_INPUT if is_sel else BG_ELEVATED
            border = BORDER_FOCUS if is_sel else BORDER_CARD
            row.configure(bg=bg, highlightbackground=border)
            dot.configure(bg=bg)
            lbl.configure(bg=bg)

            btn = self.slots[idx]
            if btn is None:
                dot.configure(text="●", fg=BORDER_CARD)
                lbl.configure(
                    text=f"{idx + 1}. - Frei -",
                    fg=TEXT_PRIMARY if is_sel else TEXT_MUTED,
                    font=(self.font_ui, 9),
                )
            else:
                dot.configure(
                    text="●",
                    fg=ACCENT_HEX.get(btn.color, TEXT_SECONDARY) if btn.enabled else TEXT_MUTED,
                )
                prefix = "" if btn.enabled else "[Ausgeblendet] "
                lbl.configure(
                    text=f"{idx + 1}. {prefix}{btn.name}",
                    fg=TEXT_PRIMARY if btn.enabled else TEXT_SECONDARY,
                    font=(self.font_ui, 9, "bold" if is_sel else "normal"),
                )

    def _test_current_slot(self, side: str) -> None:
        built, errors = self._build_slot_from_form()
        if errors or built is None:
            messagebox.showerror(
                "Test nicht möglich",
                "Bitte erst die Eingabefehler dieses Buttons beheben:\n\n" + "\n".join(errors),
                parent=self,
            )
            return
        entries = self.controller.trigger_button_config(built, "on" if side == "on" else "off")
        if entries and all(e.ok for e in entries):
            addrs = ", ".join(e.address for e in entries)
            mode_note = " (Dry-Run)" if self.controller.dry_run else ""
            self.lbl_test_feedback.configure(
                text=f"[OK] Gesendet{mode_note}: {addrs}", fg=STATUS_ON_FG
            )
        else:
            err_msg = "; ".join(e.outcome for e in entries)
            self.lbl_test_feedback.configure(text=f"Fehler: {err_msg}", fg=STATUS_ERR_FG)

    # --- Full validation & saving ---------------------------------------------

    def _assemble_panel_config(self) -> tuple[PanelConfig | None, list[str]]:
        if self.slots[self.selected_slot] is not None:
            built, slot_errors = self._build_slot_from_form()
            if slot_errors or built is None:
                return None, [f"Platz {self.selected_slot + 1}: {e}" for e in slot_errors]
            self.slots[self.selected_slot] = built

        try:
            port_val: object = int(self.var_port.get().strip())
        except ValueError:
            port_val = self.var_port.get().strip()

        try:
            delay_val: object = float(self.var_startup_delay.get().strip())
        except ValueError:
            delay_val = self.var_startup_delay.get().strip()

        raw_buttons = [b.to_dict() for b in self.slots if b is not None]
        raw = {
            "title": self.var_title.get().strip(),
            "console": {
                "host": self.var_host.get().strip(),
                "port": port_val,
                "transport": self.var_transport.get(),
            },
            "ui": {
                "start_locked": bool(self.var_start_locked.get()),
                "always_on_top": bool(self.var_always_on_top.get()),
                "window_mode": self.var_window_mode.get(),
                "show_all_off": bool(self.var_show_all_off.get()),
                "startup_delay_s": delay_val,
            },
            "buttons": raw_buttons,
        }
        cfg, res = parse_config(raw)
        if cfg is None or not res.ok:
            return None, res.errors
        # Preserve exact normalized objects when valid
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
                "Autostart-Hinweis",
                f"Autostart konnte nicht geändert werden:\n{exc}",
                parent=self,
            )

    def _on_save(self) -> None:
        cfg, errors = self._assemble_panel_config()
        if errors or cfg is None:
            messagebox.showerror(
                "Konfiguration unvollständig",
                "Bitte folgende Punkte korrigieren:\n\n- " + "\n- ".join(errors),
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
                "Konfiguration unvollständig",
                "Bitte folgende Punkte korrigieren:\n\n- " + "\n- ".join(errors),
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
            title="Konfiguration speichern unter",
            initialdir=initial_dir,
            initialfile="playbacks.local.yaml",
            defaultextension=".yaml",
            filetypes=[("YAML-Konfiguration", "*.yaml *.yml"), ("Alle Dateien", "*.*")],
        )
        if not chosen:
            return
        self._persist_and_close(cfg, Path(chosen))

    def _persist_and_close(self, cfg: PanelConfig, target: Path) -> None:
        try:
            self.controller.save_to_file(cfg, target)
        except (OSError, ZerosValueError) as exc:
            messagebox.showerror("Speichern fehlgeschlagen", str(exc), parent=self)
            return
        self._apply_autostart_setting(target)
        self._on_applied(cfg, target)
        self.destroy()

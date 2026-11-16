"""Main operator window for the FLX Playback-Panel."""

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
    STATUS_OFF_BG,
    STATUS_OFF_FG,
    STATUS_ON_BG,
    STATUS_ON_FG,
    STATUS_WARN_BG,
    STATUS_WARN_FG,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TactileButton,
    enable_windows_high_dpi,
    pick_font_family,
    pick_mono_family,
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
    outer: tk.Frame
    state_lbl: tk.Label
    title_lbl: tk.Label
    desc_lbl: tk.Label
    btn_on: TactileButton
    btn_off: TactileButton
    accent_hex: str


class PlaybackPanelApp:
    """Main Tkinter operator interface and coordinator."""

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

        self.font_ui = pick_font_family(root)
        self.font_mono = pick_mono_family(root)

        self.locked: bool = force_locked or controller.config.ui.start_locked
        self.fullscreen: bool = False
        self.log_expanded: bool = False
        self._editor_win: ConfigEditorWindow | None = None
        self.cards: list[_CardWidgets] = []

        self.controller._on_log = self._on_controller_log

        self.root.configure(bg=BG_ROOT)
        self.root.geometry("1080x700")
        self.root.minsize(720, 480)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self._build_ui()
        self._bind_shortcuts()
        self.refresh_all(apply_window_mode=True)

        if self._enable_timers:
            self._schedule_startup_actions()
            self.root.after(2000, self._poll_file_changes)
        if open_editor_on_start:
            self.root.after(150, self.open_editor)

    # --- UI construction ------------------------------------------------------

    def _build_ui(self) -> None:
        # Header bar
        self.header = tk.Frame(self.root, bg=BG_HEADER, padx=20, pady=12)
        self.header.pack(side="top", fill="x")
        tk.Frame(self.root, bg=BORDER_SUBTLE, height=1).pack(side="top", fill="x")

        left_hdr = tk.Frame(self.header, bg=BG_HEADER)
        left_hdr.pack(side="left", fill="x", expand=True)

        title_row = tk.Frame(left_hdr, bg=BG_HEADER)
        title_row.pack(fill="x")
        self.lbl_title = tk.Label(
            title_row,
            text="FLX Playback-Panel",
            font=(self.font_ui, 15, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_HEADER,
            anchor="w",
        )
        self.lbl_title.pack(side="left")

        self.lbl_dry_badge = tk.Label(
            title_row,
            text=" TESTMODUS (Dry-Run) ",
            font=(self.font_ui, 8, "bold"),
            fg=STATUS_WARN_FG,
            bg=STATUS_WARN_BG,
            padx=6,
            pady=2,
        )

        self.lbl_subtitle = tk.Label(
            left_hdr,
            text="",
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_HEADER,
            anchor="w",
        )
        self.lbl_subtitle.pack(fill="x", pady=(2, 0))

        # Right toolbar
        self.toolbar = tk.Frame(self.header, bg=BG_HEADER)
        self.toolbar.pack(side="right")

        self.btn_all_off = TactileButton(
            self.toolbar,
            "Alle Aus",
            command=self._on_all_off,
            bg_color=BTN_DANGER_BG,
            hover_color=BTN_DANGER_HOVER,
            active_color=BTN_DANGER_ACTIVE,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 10, "bold"),
            width=98,
            height=34,
        )
        self.btn_all_off.pack(side="left", padx=(0, 8))

        self.btn_dry_toggle = TactileButton(
            self.toolbar,
            "Dry-Run: Aus",
            command=self.toggle_dry_run,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 9, "bold"),
            width=112,
            height=34,
        )
        self.btn_dry_toggle.pack(side="left", padx=(0, 8))

        self.btn_file_menu = TactileButton(
            self.toolbar,
            "Datei ▼",
            command=self._show_file_menu,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 9, "bold"),
            width=92,
            height=34,
        )
        self.btn_file_menu.pack(side="left", padx=(0, 8))

        self.btn_configure = TactileButton(
            self.toolbar,
            "Konfigurieren",
            command=self.open_editor,
            bg_color=BTN_PRIMARY_BG,
            hover_color=BTN_PRIMARY_HOVER,
            active_color=BTN_PRIMARY_ACTIVE,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 10, "bold"),
            width=128,
            height=34,
        )
        self.btn_configure.pack(side="left", padx=(0, 8))

        self.btn_lock = TactileButton(
            self.toolbar,
            "Entsperrt",
            command=self.toggle_lock,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 9, "bold"),
            width=106,
            height=34,
        )
        self.btn_lock.pack(side="left")

        # File popup menu
        self.file_menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=BG_ELEVATED,
            fg=TEXT_PRIMARY,
            activebackground=BTN_PRIMARY_BG,
            activeforeground=TEXT_PRIMARY,
            font=(self.font_ui, 10),
        )
        self.file_menu.add_command(
            label="Neue Konfiguration erstellen...", command=self.action_new_config
        )
        self.file_menu.add_command(
            label="Konfigurationsdatei öffnen...", command=self.action_open_config
        )
        self.file_menu.add_command(
            label="Aktuelle Datei neu laden (F5)", command=self.action_reload
        )
        self.file_menu.add_separator()
        self.file_menu.add_command(
            label="Starter-Vorlage laden (4 Playbacks, Testmodus)",
            command=self.action_load_starter_demo,
        )

        # Bottom status bar & collapsible log drawer
        self.bottom_wrap = tk.Frame(self.root, bg=BG_HEADER)
        self.bottom_wrap.pack(side="bottom", fill="x")

        tk.Frame(self.bottom_wrap, bg=BORDER_SUBTLE, height=1).pack(side="top", fill="x")

        status_bar = tk.Frame(self.bottom_wrap, bg=BG_HEADER, padx=20, pady=8)
        status_bar.pack(side="top", fill="x")

        self.lbl_last_event = tk.Label(
            status_bar,
            text="Bereit - noch kein OSC-Befehl gesendet.",
            font=(self.font_ui, 9),
            fg=TEXT_SECONDARY,
            bg=BG_HEADER,
            anchor="w",
        )
        self.lbl_last_event.pack(side="left", fill="x", expand=True)

        tk.Label(
            status_bar,
            text="Einbahnstraße (UDP): Anzeige zeigt zuletzt hier gesendeten Befehl",
            font=(self.font_ui, 8),
            fg=TEXT_MUTED,
            bg=BG_HEADER,
        ).pack(side="left", padx=(12, 12))

        self.btn_log_toggle = TactileButton(
            status_bar,
            "Protokoll ▲",
            command=self.toggle_log_drawer,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            parent_bg=BG_HEADER,
            font=(self.font_ui, 9, "bold"),
            width=104,
            height=28,
        )
        self.btn_log_toggle.pack(side="right")

        self.log_drawer = tk.Frame(self.bottom_wrap, bg=BG_INPUT, padx=16, pady=8)
        self.txt_log = tk.Text(
            self.log_drawer,
            height=7,
            bg=BG_INPUT,
            fg=TEXT_SECONDARY,
            font=(self.font_mono, 9),
            relief="flat",
            state="disabled",
            highlightthickness=1,
            highlightbackground=BORDER_CARD,
        )
        log_scroll = tk.Scrollbar(self.log_drawer, orient="vertical", command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=log_scroll.set)
        self.txt_log.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        # Main workspace container (cards grid or empty state)
        self.main_area = tk.Frame(self.root, bg=BG_ROOT, padx=20, pady=18)
        self.main_area.pack(side="top", fill="both", expand=True)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<F11>", lambda _e: self.toggle_fullscreen())
        self.root.bind("<Escape>", lambda _e: self._exit_fullscreen())
        self.root.bind("<F5>", lambda _e: self.action_reload())

    # --- Rendering & Refresh --------------------------------------------------

    def refresh_all(self, *, apply_window_mode: bool = False) -> None:
        cfg = self.controller.config
        self.root.title(f"{cfg.title} - FLX Playback-Panel")
        self.lbl_title.configure(text=cfg.title)

        file_label = (
            self.controller.config_path.name
            if self.controller.config_path is not None
            else "ungespeichert"
        )
        active_n = len(cfg.active_buttons)
        self.lbl_subtitle.configure(
            text=(
                f"Datei: {file_label}   ·   "
                f"Pult: {self.controller.target_label}   ·   "
                f"{active_n} aktive{'r' if active_n == 1 else ''} "
                f"{'Button' if active_n == 1 else 'Buttons'}"
            )
        )

        # Dry-run indicator
        if self.controller.dry_run:
            self.lbl_dry_badge.pack(side="left", padx=(10, 0))
            self.btn_dry_toggle.configure_style(
                text="Dry-Run: AN",
                bg_color=STATUS_WARN_BG,
                hover_color="#78350F",
                fg_color=STATUS_WARN_FG,
                disabled=self.locked,
            )
        else:
            self.lbl_dry_badge.pack_forget()
            self.btn_dry_toggle.configure_style(
                text="Dry-Run: Aus",
                bg_color=BTN_SECONDARY_BG,
                hover_color=BTN_SECONDARY_HOVER,
                fg_color=TEXT_PRIMARY,
                disabled=self.locked,
            )

        # Show/hide Alle Aus
        if cfg.ui.show_all_off and active_n > 0:
            if not self.btn_all_off.winfo_ismapped():
                self.btn_all_off.pack(side="left", padx=(0, 8), before=self.btn_dry_toggle)
        else:
            self.btn_all_off.pack_forget()

        # Lock state
        if self.locked:
            self.btn_lock.configure_style(
                text="[Gesperrt]",
                bg_color=STATUS_WARN_BG,
                hover_color="#78350F",
                fg_color=STATUS_WARN_FG,
            )
            self.btn_configure.configure_style(disabled=True)
            self.btn_file_menu.configure_style(disabled=True)
        else:
            self.btn_lock.configure_style(
                text="Entsperrt",
                bg_color=BTN_SECONDARY_BG,
                hover_color=BTN_SECONDARY_HOVER,
                fg_color=TEXT_PRIMARY,
            )
            self.btn_configure.configure_style(disabled=False)
            self.btn_file_menu.configure_style(disabled=False)

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

        for idx, btn in enumerate(active_buttons):
            r, c = divmod(idx, cols)
            card = self._create_playback_card(grid, idx, btn)
            card.outer.grid(row=r, column=c, sticky="nsew", padx=8, pady=8)
            self.cards.append(card)

        self._refresh_card_states()

    def _build_empty_welcome_state(self) -> None:
        box = tk.Frame(
            self.main_area,
            bg=BG_SURFACE,
            padx=42,
            pady=38,
            highlightthickness=1,
            highlightbackground=BORDER_CARD,
        )
        box.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            box,
            text="Willkommen im FLX Playback-Panel",
            font=(self.font_ui, 16, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
        ).pack(pady=(0, 8))

        tk.Label(
            box,
            text=(
                "Aktuell sind noch keine aktiven Playback-Buttons geladen.\n"
                "Du kannst bis zu 12 Playbacks mit je einem EIN- und AUS-Button programmieren -\n"
                "angezeigt werden im Betrieb immer nur die tatsächlich belegten Plätze."
            ),
            font=(self.font_ui, 10),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
            justify="center",
        ).pack(pady=(0, 22))

        actions = tk.Frame(box, bg=BG_SURFACE)
        actions.pack()

        TactileButton(
            actions,
            "Buttons jetzt konfigurieren",
            command=self._unlock_and_open_editor,
            bg_color=BTN_PRIMARY_BG,
            hover_color=BTN_PRIMARY_HOVER,
            active_color=BTN_PRIMARY_ACTIVE,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 10, "bold"),
            width=215,
            height=40,
        ).pack(side="left", padx=6)

        TactileButton(
            actions,
            "Konfiguration öffnen...",
            command=self.action_open_config,
            bg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 10, "bold"),
            width=190,
            height=40,
        ).pack(side="left", padx=6)

        TactileButton(
            actions,
            "Starter-Vorlage (4 Buttons)",
            command=self.action_load_starter_demo,
            bg_color=BTN_ON_BG,
            hover_color=BTN_ON_HOVER,
            active_color=BTN_ON_ACTIVE,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 10, "bold"),
            width=215,
            height=40,
        ).pack(side="left", padx=6)

    def _create_playback_card(
        self, parent: tk.Misc, active_idx: int, button: ButtonConfig
    ) -> _CardWidgets:
        accent_hex = ACCENT_HEX.get(button.color, ACCENT_HEX["amber"])

        outer = tk.Frame(
            parent,
            bg=BG_SURFACE,
            highlightthickness=1,
            highlightbackground=BORDER_CARD,
        )

        # Top colored accent bar
        tk.Frame(outer, bg=accent_hex, height=4).pack(side="top", fill="x")

        inner = tk.Frame(outer, bg=BG_SURFACE, padx=16, pady=12)
        inner.pack(side="top", fill="both", expand=True)

        # Top badge & status row
        meta_row = tk.Frame(inner, bg=BG_SURFACE)
        meta_row.pack(side="top", fill="x")

        tk.Label(
            meta_row,
            text=f" {button.badge_text()} ",
            font=(self.font_mono, 8, "bold"),
            fg=accent_hex,
            bg=BG_ELEVATED,
            padx=6,
            pady=2,
        ).pack(side="left")

        for tag in button.status_tags():
            tk.Label(
                meta_row,
                text=f"[{tag}]",
                font=(self.font_ui, 8),
                fg=STATUS_WARN_FG,
                bg=BG_SURFACE,
                padx=4,
            ).pack(side="left")

        state_lbl = tk.Label(
            meta_row,
            text=" Bereit ",
            font=(self.font_ui, 8, "bold"),
            fg=TEXT_MUTED,
            bg=BG_ELEVATED,
            padx=6,
            pady=2,
        )
        state_lbl.pack(side="right")

        # Bottom tactile EIN / AUS button bar (packed at bottom so always anchored!)
        btn_row = tk.Frame(inner, bg=BG_SURFACE)
        btn_row.pack(side="bottom", fill="x", pady=(10, 0))
        btn_row.columnconfigure(0, weight=1, uniform=f"act_{active_idx}")
        btn_row.columnconfigure(1, weight=1, uniform=f"act_{active_idx}")

        btn_on = TactileButton(
            btn_row,
            button.on_label,
            command=lambda i=active_idx: self.trigger_button(i, "on"),
            bg_color=BTN_ON_BG,
            hover_color=BTN_ON_HOVER,
            active_color=BTN_ON_ACTIVE,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 11, "bold"),
            height=44,
            radius=8,
        )
        btn_on.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        btn_off = TactileButton(
            btn_row,
            button.off_label,
            command=lambda i=active_idx: self.trigger_button(i, "off"),
            bg_color=BTN_OFF_BG,
            hover_color=BTN_OFF_HOVER,
            active_color=BTN_OFF_ACTIVE,
            parent_bg=BG_SURFACE,
            font=(self.font_ui, 11, "bold"),
            height=44,
            radius=8,
        )
        btn_off.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # Middle text area (title + short description)
        text_box = tk.Frame(inner, bg=BG_SURFACE)
        text_box.pack(side="top", fill="both", expand=True, pady=(10, 4))

        title_lbl = tk.Label(
            text_box,
            text=button.name,
            font=(self.font_ui, 13, "bold"),
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
        desc_lbl.pack(side="top", fill="both", expand=True, pady=(3, 0))

        def _update_wrap(event: tk.Event[tk.Misc]) -> None:
            wrap = max(140, event.width - 8)
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
                card.outer.configure(highlightbackground=card.accent_hex)
                card.state_lbl.configure(text=" EIN ", fg=STATUS_ON_FG, bg=STATUS_ON_BG)
                card.btn_off.configure_style(bg_color=BTN_OFF_ARMED_BG, hover_color=BTN_OFF_HOVER)
            elif state == "off":
                card.outer.configure(highlightbackground=BORDER_CARD)
                card.state_lbl.configure(text=" AUS ", fg=STATUS_OFF_FG, bg=STATUS_OFF_BG)
                card.btn_off.configure_style(bg_color=BTN_OFF_BG, hover_color=BTN_OFF_HOVER)
            else:
                card.outer.configure(highlightbackground=BORDER_CARD)
                card.state_lbl.configure(text=" Bereit ", fg=TEXT_MUTED, bg=BG_ELEVATED)
                card.btn_off.configure_style(bg_color=BTN_OFF_BG, hover_color=BTN_OFF_HOVER)

    # --- Actions & Event handlers ---------------------------------------------

    def trigger_button(self, active_idx: int, side: ButtonSide) -> list[LogEntry]:
        entries = self.controller.trigger_active_button(active_idx, side)
        self._refresh_card_states()
        return entries

    def _on_all_off(self) -> None:
        self.controller.trigger_all_off()
        self._refresh_card_states()

    def _on_controller_log(self, entry: LogEntry) -> None:
        time_short = entry.timestamp.split(" ")[-1]
        side_de = "EIN" if entry.side == "on" else "AUS"
        prefix = "OK" if entry.ok else "FEHLER"
        color = (
            STATUS_WARN_FG
            if self.controller.dry_run and entry.ok
            else (STATUS_ON_FG if entry.ok else STATUS_ERR_FG)
        )
        self.lbl_last_event.configure(
            text=(
                f"[{prefix}] {time_short}  |  {entry.button_name} ({side_de})  ->  "
                f"{entry.address}  [{entry.outcome}]"
            ),
            fg=color,
        )
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", entry.line + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def toggle_log_drawer(self) -> None:
        self.log_expanded = not self.log_expanded
        if self.log_expanded:
            self.log_drawer.pack(side="bottom", fill="x")
            self.btn_log_toggle.configure_style(text="Protokoll ▼")
        else:
            self.log_drawer.pack_forget()
            self.btn_log_toggle.configure_style(text="Protokoll ▲")

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
        y = self.btn_file_menu.winfo_rooty() + self.btn_file_menu.winfo_height() + 2
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
            on_applied=self._on_editor_saved,
        )

    def _on_editor_saved(self, _cfg: PanelConfig, saved_path: Path | None) -> None:
        if saved_path is not None:
            self.settings.last_config_path = str(saved_path.resolve())
            self.settings.save(self._app_data_dir)
        self.refresh_all()

    def action_new_config(self) -> None:
        if self.locked:
            return
        chosen = filedialog.asksaveasfilename(
            parent=self.root,
            title="Neue Konfiguration anlegen",
            initialfile="playbacks.local.yaml",
            defaultextension=".yaml",
            filetypes=[("YAML-Konfiguration", "*.yaml *.yml"), ("Alle Dateien", "*.*")],
        )
        if not chosen:
            return
        starter = default_starter_config()
        try:
            saved = self.controller.save_to_file(starter, Path(chosen))
        except (OSError, ZerosValueError) as exc:
            messagebox.showerror("Fehler beim Anlegen", str(exc), parent=self.root)
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
            title="Konfigurationsdatei öffnen",
            filetypes=[("YAML-Konfiguration", "*.yaml *.yml"), ("Alle Dateien", "*.*")],
        )
        if not chosen:
            return
        try:
            self.controller.load_from_file(Path(chosen))
        except ZerosValueError as exc:
            messagebox.showerror("Ungültige Konfiguration", str(exc), parent=self.root)
            return
        self.settings.last_config_path = str(Path(chosen).resolve())
        self.settings.save(self._app_data_dir)
        self.locked = self.controller.config.ui.start_locked
        self.refresh_all(apply_window_mode=True)

    def action_reload(self) -> None:
        if self.controller.config_path is None:
            return
        try:
            self.controller.load_from_file(self.controller.config_path)
        except ZerosValueError as exc:
            messagebox.showerror("Fehler beim Neuladen", str(exc), parent=self.root)
            return
        self.refresh_all()

    def action_load_starter_demo(self) -> None:
        starter = default_starter_config(host="127.0.0.1")
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
                msg = f"✗ Datei-Änderung abgelehnt (bisherige Konfiguration bleibt aktiv): {err}"
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

"""User-interface localization for Deutsch (de), English (en) and Română (ro).

Only user-facing UI strings are localized here; technical OSC logs and CLI validation
messages keep their deterministic repository format.
"""

from __future__ import annotations

from typing import Literal

LanguageCode = Literal["de", "en", "ro"]

SUPPORTED_LANGUAGES: tuple[LanguageCode, ...] = ("de", "en", "ro")

LANGUAGE_SHORT_LABELS: dict[LanguageCode, str] = {
    "de": "DE",
    "en": "EN",
    "ro": "RO",
}

LANGUAGE_FULL_LABELS: dict[LanguageCode, str] = {
    "de": "Deutsch",
    "en": "English",
    "ro": "Română",
}

STANDARD_ON_LABELS: frozenset[str] = frozenset({"EIN", "ON", "PORNIT"})
STANDARD_OFF_LABELS: frozenset[str] = frozenset({"AUS", "OFF", "OPRIT"})

COLOR_LABELS: dict[LanguageCode, dict[str, str]] = {
    "de": {
        "amber": "Bernstein",
        "emerald": "Grün",
        "blue": "Blau",
        "violet": "Violett",
        "rose": "Rot",
        "cyan": "Türkis",
        "slate": "Neutral",
    },
    "en": {
        "amber": "Amber",
        "emerald": "Emerald",
        "blue": "Blue",
        "violet": "Violet",
        "rose": "Rose",
        "cyan": "Cyan",
        "slate": "Slate",
    },
    "ro": {
        "amber": "Chihlimbar",
        "emerald": "Verde",
        "blue": "Albastru",
        "violet": "Violet",
        "rose": "Roșu",
        "cyan": "Turcoaz",
        "slate": "Neutru",
    },
}

STRINGS: dict[LanguageCode, dict[str, str]] = {
    # ------------------------------------------------------------------ DEUTSCH
    "de": {
        # App header & toolbar
        "app_name": "FLX Playback-Panel",
        "dry_badge": "TESTMODUS",
        "file_unsaved": "ungespeichert",
        "subtitle_fmt": "Datei: {file}   |   Pult: {target}   |   {active}",
        "active_one": "1 aktiver Button",
        "active_many": "{n} aktive Buttons",
        "btn_all_off": "Alle Aus",
        "btn_dry_on": "Test: AN",
        "btn_dry_off": "Test: Aus",
        "btn_file": "Datei ▼",
        "btn_configure": "Konfigurieren",
        "btn_locked": "Gesperrt",
        "btn_unlocked": "Entsperrt",
        # File menu & dialogs
        "menu_new": "Neue Konfiguration anlegen...",
        "menu_open": "Konfigurationsdatei öffnen...",
        "menu_reload": "Aktuelle Datei neu laden (F5)",
        "menu_starter": "Starter-Vorlage laden (4 Playbacks)",
        "dlg_new_title": "Neue Konfiguration anlegen",
        "dlg_open_title": "Konfigurationsdatei öffnen",
        "dlg_save_title": "Konfiguration speichern unter",
        "dlg_yaml_filter": "YAML-Konfiguration",
        "dlg_all_filter": "Alle Dateien",
        "dlg_err_create": "Fehler beim Anlegen",
        "dlg_err_load": "Fehler beim Laden",
        "dlg_err_reload": "Neu laden fehlgeschlagen",
        "dlg_err_save": "Speichern fehlgeschlagen",
        "dlg_no_file_title": "Keine Datei",
        "dlg_no_file_body": "Aktuell ist noch keine gespeicherte Datei geöffnet.",
        # Empty / welcome state
        "welcome_kicker": "FLX S48 LICHTSTEUERUNG",
        "welcome_title": "Willkommen im FLX Playback-Panel",
        "welcome_body": (
            "Aktuell sind noch keine aktiven Playback-Buttons geladen. "
            "Du kannst bis zu 12 Playbacks mit je einem EIN- und AUS-Button programmieren - "
            "im Betrieb werden automatisch nur die belegten Plätze angezeigt."
        ),
        "welcome_btn_config": "Buttons konfigurieren",
        "welcome_btn_open": "Datei öffnen...",
        "welcome_btn_starter": "Starter-Vorlage (4)",
        # Cards & button states
        "default_on": "EIN",
        "default_off": "AUS",
        "state_ready": "Bereit",
        "state_on": "EIN",
        "state_off": "AUS",
        "badge_custom_one": "Frei | 1 / 1 Befehl",
        "badge_custom_many": "Frei | {on} / {off} Befehle",
        "tag_vermutet": "vermutet",
        "tag_ungetestet": "ungetestet",
        "tag_belegt": "belegt",
        # Bottom status bar & log drawer
        "status_idle": "Bereit - noch kein OSC-Befehl gesendet.",
        "status_udp_hint": "UDP-Einbahnstraße: zeigt zuletzt gesendeten Befehl",
        "status_ok": "OK",
        "status_err": "FEHLER",
        "btn_log_show": "Protokoll ▲",
        "btn_log_hide": "Protokoll ▼",
        # Editor header & footer
        "editor_win_title": "Konfigurieren - FLX Playback-Panel",
        "editor_heading": "Konfiguration bearbeiten",
        "tab_buttons": "1. Buttons (1-12)",
        "tab_settings": "2. Pult, Fenster & Autostart",
        "footer_no_file": "Noch keine Datei gewählt (wird beim Speichern abgefragt)",
        "footer_file_fmt": "Datei: {path}",
        "btn_cancel": "Abbrechen",
        "btn_save_as": "Speichern unter...",
        "btn_save": "Speichern & Übernehmen",
        # Editor sidebar
        "slot_summary_fmt": "{active} aktiv  |  {occupied}/12 belegt",
        "slot_free": "Frei",
        "slot_hidden_prefix": "[Aus] ",
        "btn_up": "▲ Hoch",
        "btn_down": "▼ Runter",
        "btn_clear": "Leeren",
        # Empty slot state
        "empty_slot_title": "Platz {n} ist frei",
        "empty_slot_body": (
            "Nicht belegte Plätze werden im Bedienfenster automatisch ausgeblendet.\n"
            "Lege hier einen Button an - standardmäßig setzt EIN das Playback auf 100 % "
            "und AUS dasselbe Playback auf 0 %."
        ),
        "empty_slot_btn": "+ Platz {n} programmieren",
        # Occupied slot form
        "slot_edit_header": "Platz {n} bearbeiten",
        "slot_enabled_toggle": "Im Bedienfenster anzeigen",
        "sec_appearance": "Darstellung & Kurzbeschreibung",
        "lbl_name": "Name (Titel)",
        "lbl_desc": "Kurzbeschreibung",
        "lbl_on_text": "Text EIN-Button",
        "lbl_off_text": "Text AUS-Button",
        "lbl_accent": "Farbakzent",
        "lbl_auto_on": "Beim Programmstart automatisch einschalten (nach Start-Verzögerung)",
        "sec_mode": "Funktions-Programmierung (EIN / AUS)",
        "mode_pb_level": "Playback-Level (100/0)",
        "mode_pb_go": "Go / Release",
        "mode_cue_pair": "Cue-Paar (belegt)",
        "mode_custom": "Frei / Mehrfach",
        # Mode subpanels
        "desc_pb_level": (
            "Standard: EIN setzt das gewählte Playback auf den Ein-Wert (z. B. 100 %), "
            "AUS setzt automatisch dasselbe Playback auf den Aus-Wert (Standard 0 %)."
        ),
        "lbl_playback": "Playback (0-96)",
        "lbl_on_level": "Level EIN (0-100 %)",
        "lbl_off_level": "Level AUS (0-100 %)",
        "lbl_on_fade": "Fade EIN (Sek., opt.)",
        "lbl_off_fade": "Fade AUS (Sek., opt.)",
        "desc_pb_go": (
            "Startet das Playback mit Go (/zeros/playback/go/<pb>) und gibt es bei AUS "
            "frei (Release) oder hält es an (Pause)."
        ),
        "lbl_off_action": "Aktion bei AUS",
        "opt_release": "Freigeben (Release)",
        "opt_pause": "Anhalten (Pause)",
        "desc_cue_pair": (
            "Nutzt den im ZerOS-Handbuch belegten und am FLX S48 getesteten Befehl "
            "/zeros/cue/go/<pb>/<cue>: ein Cue für EIN und ein Cue für AUS."
        ),
        "lbl_on_cue": "Cue bei EIN",
        "lbl_off_cue": "Cue bei AUS",
        "desc_custom": (
            "Volle Flexibilität: Beliebige Befehle aus docs/02-flx-osc-referenz.md kombinieren "
            "(auch mehrere Befehle gleichzeitig pro Klick, eine Adresse je Zeile)."
        ),
        "lbl_builder": "Befehls-Baukasten",
        "lbl_no_params": "Keine Parameter nötig ({example})",
        "lbl_opt_suffix": "(opt.)",
        "btn_add_on": "+ Zu EIN hinzufügen",
        "btn_add_off": "+ Zu AUS hinzufügen",
        "lbl_cmds_on": "OSC-Befehle bei EIN (1 pro Zeile)",
        "lbl_cmds_off": "OSC-Befehle bei AUS (1 pro Zeile)",
        # Preview & live test
        "sec_preview": "Vorschau & Live-Test",
        "preview_invalid": "(Eingabe unvollständig / fehlerhaft)",
        "preview_err_prefix": "Fehler: ",
        "preview_warn_prefix": "Hinweis: ",
        "preview_confirmed": "Status: belegt (laut ZerOS-Handbuch bestätigt).",
        "btn_test_on": "EIN testen",
        "btn_test_off": "AUS testen",
        "dlg_test_err_title": "Test nicht möglich",
        "dlg_test_err_body": "Bitte zuerst die Eingabefehler dieses Buttons beheben:\n\n",
        "test_sent_fmt": "[OK] Gesendet{mode}: {addrs}",
        "test_dry_note": " (Testmodus)",
        "dlg_invalid_cmd": "Ungültiger Befehl",
        "dlg_incomplete_title": "Konfiguration unvollständig",
        "dlg_incomplete_body": "Bitte folgende Punkte korrigieren:\n\n- ",
        # Settings tab
        "sec_console": "FLX S48 - Netzwerkverbindung (OSC)",
        "lbl_show_title": "Show-Titel",
        "lbl_host": "Pult IP-Adresse",
        "lbl_port": "OSC-Port",
        "lbl_transport": "Transport-Protokoll",
        "opt_udp": "UDP (Standard, empfohlen)",
        "opt_tcp": "TCP mit SLIP",
        "sec_window": "Bedienfenster, Sprache & Event-Betrieb",
        "lbl_language": "Sprache der Oberfläche",
        "chk_start_locked": "Gesperrt starten (schützt vor versehentlichem Verstellen)",
        "chk_always_on_top": "Fenster immer im Vordergrund halten (Always on Top)",
        "chk_show_all_off": "Sammelbutton »Alle Aus« in der Kopfleiste anzeigen",
        "lbl_window_mode": "Fenstergröße beim Start",
        "wm_normal": "Normal",
        "wm_maximized": "Maximiert",
        "wm_fullscreen": "Vollbild (Kiosk)",
        "lbl_startup_delay": "Start-Verzögerung (Sek.)",
        "sec_autostart": "System-Autostart (Windows & Linux)",
        "desc_autostart": (
            "Startet das FLX Playback-Panel automatisch nach der Benutzer-Anmeldung "
            "(unter Windows via HKCU\\...\\Run, unter Linux via ~/.config/autostart/*.desktop - "
            "keine Administrator-/Root-Rechte nötig) und lädt direkt die gespeicherte Datei."
        ),
        "chk_autostart": "Beim Anmelden automatisch starten (Autostart aktivieren)",
        "autostart_unsupported": (
            "Hinweis: Auf diesem System nicht unterstützt (verfügbar unter Windows und Linux).\n"
            "Geplanter Startbefehl: {cmd}"
        ),
        "autostart_active": "AKTIV (wird beim Speichern gesetzt)",
        "autostart_inactive": "INAKTIV",
        "autostart_status_fmt": "Status: {state}\nBefehl: {cmd}",
        "dlg_autostart_warn": "Autostart-Hinweis",
        "dlg_autostart_err": "Autostart konnte nicht geändert werden:\n{err}",
        # Starter template strings
        "starter_title": "Kleines Event - Lichtsteuerung",
        "starter_b1_name": "Bühne Grundlicht",
        "starter_b1_desc": "Warmweißes Frontlicht für Moderation und Redner",
        "starter_b2_name": "Hintergrund Ambiente",
        "starter_b2_desc": "Sanfte Akzentbeleuchtung im Bühnenhintergrund (70 %)",
        "starter_b3_name": "Saallicht",
        "starter_b3_desc": "Publikumsbeleuchtung für Einlass und Pause",
        "starter_b4_name": "Musik-Szene (Cue-Paar)",
        "starter_b4_desc": "Startet Cue 1 (Ein) bzw. Cue 2 (Aus) auf Playback 10",
    },
    # ------------------------------------------------------------------ ENGLISH
    "en": {
        # App header & toolbar
        "app_name": "FLX Playback-Panel",
        "dry_badge": "DRY-RUN",
        "file_unsaved": "unsaved",
        "subtitle_fmt": "File: {file}   |   Console: {target}   |   {active}",
        "active_one": "1 active button",
        "active_many": "{n} active buttons",
        "btn_all_off": "All Off",
        "btn_dry_on": "Dry-Run: ON",
        "btn_dry_off": "Dry-Run: Off",
        "btn_file": "File ▼",
        "btn_configure": "Configure",
        "btn_locked": "Locked",
        "btn_unlocked": "Unlocked",
        # File menu & dialogs
        "menu_new": "Create new configuration...",
        "menu_open": "Open configuration file...",
        "menu_reload": "Reload current file (F5)",
        "menu_starter": "Load starter template (4 playbacks)",
        "dlg_new_title": "Create new configuration",
        "dlg_open_title": "Open configuration file",
        "dlg_save_title": "Save configuration as",
        "dlg_yaml_filter": "YAML configuration",
        "dlg_all_filter": "All files",
        "dlg_err_create": "Could not create file",
        "dlg_err_load": "Could not load file",
        "dlg_err_reload": "Reload failed",
        "dlg_err_save": "Save failed",
        "dlg_no_file_title": "No file open",
        "dlg_no_file_body": "No saved configuration file is currently open.",
        # Empty / welcome state
        "welcome_kicker": "FLX S48 LIGHTING CONTROL",
        "welcome_title": "Welcome to FLX Playback-Panel",
        "welcome_body": (
            "No active playback buttons are loaded yet. "
            "Program up to 12 playbacks with dedicated ON and OFF buttons - "
            "during operation, only assigned slots are displayed."
        ),
        "welcome_btn_config": "Configure buttons",
        "welcome_btn_open": "Open file...",
        "welcome_btn_starter": "Starter template (4)",
        # Cards & button states
        "default_on": "ON",
        "default_off": "OFF",
        "state_ready": "Ready",
        "state_on": "ON",
        "state_off": "OFF",
        "badge_custom_one": "Custom | 1 / 1 cmd",
        "badge_custom_many": "Custom | {on} / {off} cmds",
        "tag_vermutet": "unconfirmed (vermutet)",
        "tag_ungetestet": "untested",
        "tag_belegt": "confirmed",
        # Bottom status bar & log drawer
        "status_idle": "Ready - no OSC command sent yet.",
        "status_udp_hint": "One-way UDP: shows last command sent from here",
        "status_ok": "OK",
        "status_err": "ERROR",
        "btn_log_show": "Log ▲",
        "btn_log_hide": "Log ▼",
        # Editor header & footer
        "editor_win_title": "Configure - FLX Playback-Panel",
        "editor_heading": "Edit Configuration",
        "tab_buttons": "1. Buttons (1-12)",
        "tab_settings": "2. Console, Window & Autostart",
        "footer_no_file": "No file selected yet (you will be prompted on save)",
        "footer_file_fmt": "File: {path}",
        "btn_cancel": "Cancel",
        "btn_save_as": "Save as...",
        "btn_save": "Save & Apply",
        # Editor sidebar
        "slot_summary_fmt": "{active} active  |  {occupied}/12 used",
        "slot_free": "Empty",
        "slot_hidden_prefix": "[Off] ",
        "btn_up": "▲ Up",
        "btn_down": "▼ Down",
        "btn_clear": "Clear",
        # Empty slot state
        "empty_slot_title": "Slot {n} is empty",
        "empty_slot_body": (
            "Unassigned slots are automatically hidden in the operator window.\n"
            "Create a button here - by default, ON sets the playback to 100% "
            "and OFF sets the same playback to 0%."
        ),
        "empty_slot_btn": "+ Program slot {n}",
        # Occupied slot form
        "slot_edit_header": "Edit Slot {n}",
        "slot_enabled_toggle": "Show in operator window",
        "sec_appearance": "Appearance & Short Description",
        "lbl_name": "Name (Title)",
        "lbl_desc": "Short description",
        "lbl_on_text": "ON button label",
        "lbl_off_text": "OFF button label",
        "lbl_accent": "Accent color",
        "lbl_auto_on": "Turn ON automatically at app startup (after startup delay)",
        "sec_mode": "Function Mode (ON / OFF)",
        "mode_pb_level": "Playback Level (100/0)",
        "mode_pb_go": "Go / Release",
        "mode_cue_pair": "Cue Pair (confirmed)",
        "mode_custom": "Custom / Multi",
        # Mode subpanels
        "desc_pb_level": (
            "Default mode: ON sets the chosen playback to the ON level (e.g. 100%), "
            "OFF automatically sets the exact same playback to the OFF level (default 0%)."
        ),
        "lbl_playback": "Playback (0-96)",
        "lbl_on_level": "ON level (0-100 %)",
        "lbl_off_level": "OFF level (0-100 %)",
        "lbl_on_fade": "ON fade (sec, opt.)",
        "lbl_off_fade": "OFF fade (sec, opt.)",
        "desc_pb_go": (
            "Triggers the playback via Go (/zeros/playback/go/<pb>) and either "
            "releases or pauses it when pressing OFF."
        ),
        "lbl_off_action": "OFF action",
        "opt_release": "Release playback",
        "opt_pause": "Pause playback",
        "desc_cue_pair": (
            "Uses /zeros/cue/go/<pb>/<cue> (confirmed in ZerOS manual & tested on FLX S48): "
            "one cue for ON and one cue for OFF."
        ),
        "lbl_on_cue": "Cue for ON",
        "lbl_off_cue": "Cue for OFF",
        "desc_custom": (
            "Full flexibility: combine any commands from docs/02-flx-osc-referenz.md "
            "(supports multiple commands per click, one OSC address per line)."
        ),
        "lbl_builder": "Command Builder",
        "lbl_no_params": "No parameters required ({example})",
        "lbl_opt_suffix": "(opt.)",
        "btn_add_on": "+ Add to ON",
        "btn_add_off": "+ Add to OFF",
        "lbl_cmds_on": "OSC commands for ON (1 per line)",
        "lbl_cmds_off": "OSC commands for OFF (1 per line)",
        # Preview & live test
        "sec_preview": "OSC Preview & Live Test",
        "preview_invalid": "(incomplete or invalid input)",
        "preview_err_prefix": "Error: ",
        "preview_warn_prefix": "Note: ",
        "preview_confirmed": "Status: confirmed in ZerOS manual (belegt).",
        "btn_test_on": "Test ON",
        "btn_test_off": "Test OFF",
        "dlg_test_err_title": "Cannot run test",
        "dlg_test_err_body": "Please fix the validation errors on this slot first:\n\n",
        "test_sent_fmt": "[OK] Sent{mode}: {addrs}",
        "test_dry_note": " (Dry-Run)",
        "dlg_invalid_cmd": "Invalid command",
        "dlg_incomplete_title": "Incomplete configuration",
        "dlg_incomplete_body": "Please check the following items:\n\n- ",
        # Settings tab
        "sec_console": "FLX S48 - Network Connection (OSC)",
        "lbl_show_title": "Show title",
        "lbl_host": "Console IP address",
        "lbl_port": "OSC port",
        "lbl_transport": "Transport protocol",
        "opt_udp": "UDP (standard, recommended)",
        "opt_tcp": "TCP with SLIP",
        "sec_window": "Operator Window, Language & Event Mode",
        "lbl_language": "Interface language",
        "chk_start_locked": "Start locked (prevents accidental edits during events)",
        "chk_always_on_top": "Keep window always on top",
        "chk_show_all_off": "Show »All Off« master button in header bar",
        "lbl_window_mode": "Startup window size",
        "wm_normal": "Normal",
        "wm_maximized": "Maximized",
        "wm_fullscreen": "Fullscreen (Kiosk)",
        "lbl_startup_delay": "Startup delay (sec)",
        "sec_autostart": "System Autostart (Windows & Linux)",
        "desc_autostart": (
            "Launches FLX Playback-Panel automatically after user login "
            "(on Windows via HKCU\\...\\Run, on Linux via ~/.config/autostart/*.desktop - "
            "no admin/root rights required) and loads the saved configuration file."
        ),
        "chk_autostart": "Launch automatically on login (enable Autostart)",
        "autostart_unsupported": (
            "Note: Not supported on this OS (available on Windows and Linux).\n"
            "Planned launch command: {cmd}"
        ),
        "autostart_active": "ENABLED (applied on save)",
        "autostart_inactive": "DISABLED",
        "autostart_status_fmt": "Status: {state}\nCommand: {cmd}",
        "dlg_autostart_warn": "Autostart notice",
        "dlg_autostart_err": "Could not update Windows Autostart:\n{err}",
        # Starter template strings
        "starter_title": "Small Event - Lighting Control",
        "starter_b1_name": "Stage Key Light",
        "starter_b1_desc": "Warm white front wash for speakers and hosts",
        "starter_b2_name": "Backdrop Ambience",
        "starter_b2_desc": "Soft accent lighting on the rear backdrop (70%)",
        "starter_b3_name": "House Lights",
        "starter_b3_desc": "Audience illumination for entry and intermission",
        "starter_b4_name": "Music Scene (Cue Pair)",
        "starter_b4_desc": "Triggers Cue 1 (On) and Cue 2 (Off) on Playback 10",
    },
    # ------------------------------------------------------------------ ROMÂNĂ
    "ro": {
        # App header & toolbar
        "app_name": "FLX Playback-Panel",
        "dry_badge": "MOD TEST",
        "file_unsaved": "nesalvat",
        "subtitle_fmt": "Fișier: {file}   |   Consolă: {target}   |   {active}",
        "active_one": "1 buton activ",
        "active_many": "{n} butoane active",
        "btn_all_off": "Oprește tot",
        "btn_dry_on": "Test: PORNIT",
        "btn_dry_off": "Test: Oprit",
        "btn_file": "Fișier ▼",
        "btn_configure": "Configurare",
        "btn_locked": "Blocat",
        "btn_unlocked": "Deblocat",
        # File menu & dialogs
        "menu_new": "Configurație nouă...",
        "menu_open": "Deschide fișier de configurare...",
        "menu_reload": "Reîncarcă fișierul curent (F5)",
        "menu_starter": "Încarcă șablon demonstrativ (4 playbacks)",
        "dlg_new_title": "Configurație nouă",
        "dlg_open_title": "Deschide fișier de configurare",
        "dlg_save_title": "Salvează configurația ca",
        "dlg_yaml_filter": "Configurație YAML",
        "dlg_all_filter": "Toate fișierele",
        "dlg_err_create": "Eroare la creare",
        "dlg_err_load": "Eroare la încărcare",
        "dlg_err_reload": "Reîncărcare eșuată",
        "dlg_err_save": "Salvare eșuată",
        "dlg_no_file_title": "Niciun fișier",
        "dlg_no_file_body": "Momentan nu este deschis niciun fișier salvat.",
        # Empty / welcome state
        "welcome_kicker": "CONTROL LUMINI FLX S48",
        "welcome_title": "Bun venit în FLX Playback-Panel",
        "welcome_body": (
            "Momentan nu sunt încărcate butoane active. "
            "Poți programa până la 12 playbacks cu butoane PORNIT și OPRIT - "
            "în timpul operării sunt afișate automat doar pozițiile ocupate."
        ),
        "welcome_btn_config": "Configurează butoanele",
        "welcome_btn_open": "Deschide fișier...",
        "welcome_btn_starter": "Șablon rapid (4)",
        # Cards & button states
        "default_on": "PORNIT",
        "default_off": "OPRIT",
        "state_ready": "Pregătit",
        "state_on": "PORNIT",
        "state_off": "OPRIT",
        "badge_custom_one": "Liber | 1 / 1 comandă",
        "badge_custom_many": "Liber | {on} / {off} comenzi",
        "tag_vermutet": "neconfirmat (vermutet)",
        "tag_ungetestet": "netestat",
        "tag_belegt": "confirmat",
        # Bottom status bar & log drawer
        "status_idle": "Pregătit - nicio comandă OSC trimisă încă.",
        "status_udp_hint": "UDP unidirecțional: afișează ultima comandă trimisă",
        "status_ok": "OK",
        "status_err": "EROARE",
        "btn_log_show": "Jurnal ▲",
        "btn_log_hide": "Jurnal ▼",
        # Editor header & footer
        "editor_win_title": "Configurare - FLX Playback-Panel",
        "editor_heading": "Editare configurație",
        "tab_buttons": "1. Butoane (1-12)",
        "tab_settings": "2. Consolă, Fereastră & Autostart",
        "footer_no_file": "Niciun fișier selectat încă (se alege la salvare)",
        "footer_file_fmt": "Fișier: {path}",
        "btn_cancel": "Anulează",
        "btn_save_as": "Salvează ca...",
        "btn_save": "Salvează și aplică",
        # Editor sidebar
        "slot_summary_fmt": "{active} active  |  {occupied}/12 ocupate",
        "slot_free": "Liber",
        "slot_hidden_prefix": "[Ascuns] ",
        "btn_up": "▲ Sus",
        "btn_down": "▼ Jos",
        "btn_clear": "Golește",
        # Empty slot state
        "empty_slot_title": "Poziția {n} este liberă",
        "empty_slot_body": (
            "Pozițiile neocupate sunt ascunse automat în fereastra principală.\n"
            "Creează un buton aici - implicit, PORNIT setează playback-ul la 100%, "
            "iar OPRIT setează același playback la 0%."
        ),
        "empty_slot_btn": "+ Programează poziția {n}",
        # Occupied slot form
        "slot_edit_header": "Editare poziția {n}",
        "slot_enabled_toggle": "Afișează în fereastra de operare",
        "sec_appearance": "Aspect și descriere scurtă",
        "lbl_name": "Nume (Titlu)",
        "lbl_desc": "Descriere scurtă",
        "lbl_on_text": "Text buton PORNIT",
        "lbl_off_text": "Text buton OPRIT",
        "lbl_accent": "Culoare accent",
        "lbl_auto_on": "Pornește automat la deschiderea aplicației (după întârzierea de start)",
        "sec_mode": "Mod de funcționare (PORNIT / OPRIT)",
        "mode_pb_level": "Nivel Playback (100/0)",
        "mode_pb_go": "Go / Release",
        "mode_cue_pair": "Pereche Cue (confirmat)",
        "mode_custom": "Liber / Multiplu",
        # Mode subpanels
        "desc_pb_level": (
            "Mod standard: PORNIT setează playback-ul ales la nivelul de pornire (ex. 100%), "
            "iar OPRIT aduce automat același playback la nivelul de oprire (implicit 0%)."
        ),
        "lbl_playback": "Playback (0-96)",
        "lbl_on_level": "Nivel PORNIT (0-100 %)",
        "lbl_off_level": "Nivel OPRIT (0-100 %)",
        "lbl_on_fade": "Fade PORNIT (sec, opț.)",
        "lbl_off_fade": "Fade OPRIT (sec, opț.)",
        "desc_pb_go": (
            "Pornește playback-ul cu Go (/zeros/playback/go/<pb>) și îl eliberează "
            "(Release) sau îl pune pe pauză (Pause) la apăsarea pe OPRIT."
        ),
        "lbl_off_action": "Acțiune la OPRIT",
        "opt_release": "Eliberează (Release)",
        "opt_pause": "Pauză (Pause)",
        "desc_cue_pair": (
            "Folosește comanda confirmată în manualul ZerOS și testată pe FLX S48 "
            "/zeros/cue/go/<pb>/<cue>: un Cue pentru PORNIT și unul pentru OPRIT."
        ),
        "lbl_on_cue": "Cue la PORNIT",
        "lbl_off_cue": "Cue la OPRIT",
        "desc_custom": (
            "Flexibilitate maximă: combină orice comenzi din docs/02-flx-osc-referenz.md "
            "(inclusiv mai multe comenzi simultan la o apăsare, câte o adresă pe linie)."
        ),
        "lbl_builder": "Generator de comenzi",
        "lbl_no_params": "Fără parametri ({example})",
        "lbl_opt_suffix": "(opț.)",
        "btn_add_on": "+ Adaugă la PORNIT",
        "btn_add_off": "+ Adaugă la OPRIT",
        "lbl_cmds_on": "Comenzi OSC la PORNIT (1 pe linie)",
        "lbl_cmds_off": "Comenzi OSC la OPRIT (1 pe linie)",
        # Preview & live test
        "sec_preview": "Previzualizare OSC și test live",
        "preview_invalid": "(date incomplete sau invalide)",
        "preview_err_prefix": "Eroare: ",
        "preview_warn_prefix": "Notă: ",
        "preview_confirmed": "Stare: confirmat în manualul ZerOS (belegt).",
        "btn_test_on": "Testează PORNIT",
        "btn_test_off": "Testează OPRIT",
        "dlg_test_err_title": "Testul nu poate fi rulat",
        "dlg_test_err_body": "Te rugăm să corectezi mai întâi erorile acestui buton:\n\n",
        "test_sent_fmt": "[OK] Trimis{mode}: {addrs}",
        "test_dry_note": " (Mod test)",
        "dlg_invalid_cmd": "Comandă invalidă",
        "dlg_incomplete_title": "Configurație incompletă",
        "dlg_incomplete_body": "Te rugăm să corectezi următoarele câmpuri:\n\n- ",
        # Settings tab
        "sec_console": "FLX S48 - Conexiune rețea (OSC)",
        "lbl_show_title": "Titlu eveniment",
        "lbl_host": "Adresă IP consolă",
        "lbl_port": "Port OSC",
        "lbl_transport": "Protocol transport",
        "opt_udp": "UDP (standard, recomandat)",
        "opt_tcp": "TCP cu SLIP",
        "sec_window": "Fereastră, Limbă & Mod Eveniment",
        "lbl_language": "Limba interfeței",
        "chk_start_locked": "Pornește blocat (protejează împotriva modificărilor accidentale)",
        "chk_always_on_top": "Menține fereastra mereu deasupra (Always on Top)",
        "chk_show_all_off": "Afișează butonul general »Oprește tot« în bara de sus",
        "lbl_window_mode": "Dimensiune fereastră la pornire",
        "wm_normal": "Normală",
        "wm_maximized": "Maximizată",
        "wm_fullscreen": "Ecran complet (Kiosk)",
        "lbl_startup_delay": "Întârziere la pornire (sec)",
        "sec_autostart": "Autostart Sistem (Windows & Linux)",
        "desc_autostart": (
            "Pornește automat FLX Playback-Panel după autentificarea utilizatorului "
            "(pe Windows în HKCU\\...\\Run, pe Linux în ~/.config/autostart/*.desktop - "
            "fără drepturi de administrator/root) și încarcă direct fișierul de configurare salvat."
        ),
        "chk_autostart": "Pornește automat la autentificare (activează Autostart)",
        "autostart_unsupported": (
            "Notă: Nesuportat pe acest sistem (disponibil pe Windows și Linux).\n"
            "Comandă planificată: {cmd}"
        ),
        "autostart_active": "ACTIV (se aplică la salvare)",
        "autostart_inactive": "INACTIV",
        "autostart_status_fmt": "Stare: {state}\nComandă: {cmd}",
        "dlg_autostart_warn": "Notă Autostart",
        "dlg_autostart_err": "Setarea Autostart nu a putut fi modificată:\n{err}",
        # Starter template strings
        "starter_title": "Eveniment Mic - Control Lumini",
        "starter_b1_name": "Lumină Frontală Scenă",
        "starter_b1_desc": "Lumină albă caldă pentru vorbitori și moderatori",
        "starter_b2_name": "Ambianță Fundal",
        "starter_b2_desc": "Iluminat ambiental discret în spatele scenei (70%)",
        "starter_b3_name": "Lumină Sală",
        "starter_b3_desc": "Iluminat general pentru public la intrare și pauză",
        "starter_b4_name": "Scenă Muzică (Pereche Cue)",
        "starter_b4_desc": "Pornește Cue 1 (Pornit) și Cue 2 (Oprit) pe Playback 10",
    },
}


def normalize_language(lang: object) -> LanguageCode:
    """Return a valid ``LanguageCode`` ('de', 'en', or 'ro'), defaulting to 'de'."""
    if isinstance(lang, str):
        low = lang.strip().lower()
        if low in ("de", "en", "ro"):
            return low  # type: ignore[return-value]
    return "de"


def tr(lang: str, key: str, **kwargs: object) -> str:
    """Translate ``key`` into ``lang`` with fallback to German."""
    code = normalize_language(lang)
    table = STRINGS.get(code, STRINGS["de"])
    template = table.get(key) or STRINGS["de"].get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template


def color_label(lang: str, color_name: str) -> str:
    """Return localized accent color name."""
    code = normalize_language(lang)
    return COLOR_LABELS.get(code, COLOR_LABELS["de"]).get(color_name, color_name)

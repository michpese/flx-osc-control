"""flxctl: subcommands, options, help text and map check/doc."""

from __future__ import annotations

import io
import socket
from pathlib import Path

import pytest
from pythonosc.osc_message import OscMessage

from zeros_osc.cli import build_parser, main
from zeros_osc.commands import COMMANDS, Status

EXAMPLE_MAPPING = Path(__file__).resolve().parents[3] / "shows" / "mapping.example.yaml"

VALID_MAPPING = """\
console: {host: 127.0.0.1, port: 8830, transport: udp}
sources:
  propresenter: {midi_port: "LX Bridge", channel: 15}
  ableton: {midi_port: "LX Bridge", channel: 16}
cues:
  - {note: 2, name: "Musik | ruhig", osc: "/zeros/cue/go/10/2"}
  - {note: 1, name: "Einlass", osc: "/zeros/cue/go/10/1", sources: [propresenter]}
  - {note: 5, name: "Blackout", osc: "/zeros/blackout/1"}
"""

BROKEN_MAPPING = """\
console: {host: 127.0.0.1, port: 8830, transport: udp}
sources:
  propresenter: {midi_port: "LX Bridge", channel: 15}
cues:
  - {note: 1, name: "Einlass", osc: "/zeros/cue/go/10/1"}
  - {note: 1, name: "Doppelt", osc: "/zeros/cue/go/10/2"}
  - {note: 2, osc: "/zeros/cue/go/10/3"}
  - {note: 3, name: "", osc: "/zeros/cue/go/10/4"}
  - {note: 4, name: "Erfunden", osc: "/zeros/release/all"}
  - {note: 5, name: "Zu hoch", osc: "/zeros/cue/go/97/1"}
  - {note: 6, name: "Fremde Quelle", osc: "/zeros/cue/go/10/5", sources: [ableton]}
"""


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = main(list(argv), out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def write(tmp_path: Path, text: str, name: str = "mapping.yaml") -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


# --- sending ----------------------------------------------------------------------


def test_dry_run_after_subcommand():
    code, out, _ = run("cue", "go", "10", "2", "--dry-run")
    assert code == 0
    assert "adresse=/zeros/cue/go/10/2" in out
    assert "DRY-RUN" in out


def test_dry_run_before_subcommand_with_host_and_port():
    code, out, _ = run(
        "--host", "192.168.1.10", "--port", "9000", "--dry-run", "cue", "go", "1", "5"
    )
    assert code == 0
    assert "ziel=192.168.1.10:9000/udp" in out


def test_without_host_nothing_is_sent():
    code, _, err = run("cue", "go", "10", "2")
    assert code == 2
    assert "kein Ziel" in err


@pytest.mark.parametrize(
    "argv",
    [
        ("cue", "go", "97", "1"),
        ("cue", "go", "1", "0"),
        ("playback", "level", "1", "101"),
        ("blackout", "2"),
    ],
)
def test_invalid_values_exit_2(argv):
    code, _, err = run(*argv, "--dry-run")
    assert code == 2
    assert err.startswith("Fehler:")


@pytest.mark.parametrize(
    ("argv", "address"),
    [
        (("cue", "go", "1", "5"), "/zeros/cue/go/1/5"),
        (("cue", "go-current", "4"), "/zeros/cue/go/4"),
        (("cue", "go-next"), "/zeros/cue/go"),
        (("cue", "pause", "1"), "/zeros/cue/pause/1"),
        (("cue", "next", "1", "6"), "/zeros/cue/next/1/6"),
        (("macro", "1"), "/zeros/macro/1"),
        (("playback", "go", "1"), "/zeros/playback/go/1"),
        (("playback", "pause", "1"), "/zeros/playback/pause/1"),
        (("playback", "level", "1", "100"), "/zeros/playback/level/1/100"),
        (("playback", "level", "1", "100", "--fade", "2"), "/zeros/playback/level/1/100/2"),
        (("playback", "release", "1"), "/zeros/playback/release/1"),
        (("playback", "view", "1"), "/zeros/playback/view/1"),
        (("grandmaster", "100"), "/zeros/grandmaster/100"),
        (("grandmaster", "0", "--fade", "3"), "/zeros/grandmaster/0/3"),
        (("blackout", "on"), "/zeros/blackout/1"),
        (("blackout", "0"), "/zeros/blackout/0"),
    ],
)
def test_one_subcommand_per_reference_command(argv, address):
    code, out, _ = run(*argv, "--dry-run")
    assert code == 0, out
    assert f"adresse={address} " in out


def test_untested_commands_warn_on_stderr():
    _, _, err = run("macro", "1", "--dry-run")
    assert "ungetestet" in err
    _, _, err = run("cue", "go", "10", "1", "--dry-run")
    assert "ungetestet" not in err


def test_cli_sends_udp_to_localhost():
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", 0))
    receiver.settimeout(2.0)
    try:
        port = str(receiver.getsockname()[1])
        code, out, _ = run("--host", "127.0.0.1", "--port", port, "cue", "go", "10", "2")
        data, _ = receiver.recvfrom(4096)
    finally:
        receiver.close()
    assert code == 0
    assert "gesendet" in out
    assert OscMessage(data).address == "/zeros/cue/go/10/2"


def test_config_supplies_target(tmp_path):
    path = write(tmp_path, VALID_MAPPING)
    code, out, _ = run("--config", path, "--dry-run", "cue", "go", "10", "2")
    assert code == 0
    assert "ziel=127.0.0.1:8830/udp" in out
    code, out, _ = run("--config", path, "--port", "9001", "--dry-run", "cue", "go", "10", "2")
    assert "ziel=127.0.0.1:9001/udp" in out


# --- help text --------------------------------------------------------------------


def test_help_marks_forum_commands_untested(capsys):
    for command in COMMANDS.values():
        with pytest.raises(SystemExit):
            build_parser().parse_args([*command.cli, "--help"])
        text = capsys.readouterr().out
        assert command.example in text
        if command.status is Status.FORUM:
            assert "UNGETESTET" in text, command.id
        else:
            assert "UNGETESTET" not in text, command.id
        if command.status is Status.VERMUTET:
            assert "UNBELEGT" in text, command.id
        else:
            assert "UNBELEGT" not in text, command.id


def test_group_help_lists_untested_tag(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["cue", "--help"])
    text = capsys.readouterr().out
    assert "[belegt]" in text  # cue go
    assert "[ungetestet]" in text  # cue go-current etc.
    assert "[vermutet]" in text  # cue pause, cue next


# --- map check / doc --------------------------------------------------------------


def test_map_check_accepts_example_mapping():
    if not EXAMPLE_MAPPING.exists():
        pytest.skip("shows/mapping.example.yaml not found")
    code, out, _ = run("map", "check", str(EXAMPLE_MAPPING))
    assert code == 0, out
    assert "Fehler" not in out


def test_map_check_valid(tmp_path):
    code, out, _ = run("map", "check", write(tmp_path, VALID_MAPPING))
    assert code == 0, out
    assert "blackout ist ungetestet" in out  # warning, not an error


def test_map_check_reports_problems(tmp_path):
    code, out, _ = run("map", "check", write(tmp_path, BROKEN_MAPPING))
    assert code == 1
    assert "doppelte Note 1" in out
    assert "cues[2] (Note 2): name fehlt" in out
    assert "cues[3] (Note 3): name fehlt" in out
    assert "/zeros/release/all passt zu keinem Befehl der Referenz" in out
    assert "Playback: 97" in out
    assert "'ableton' steht nicht unter sources" in out


def test_map_check_missing_file(tmp_path):
    code, out, _ = run("map", "check", str(tmp_path / "nope.yaml"))
    assert code == 1
    assert "nicht lesbar" in out


def test_map_check_invalid_yaml(tmp_path):
    code, out, _ = run("map", "check", write(tmp_path, "cues: [\n"))
    assert code == 1
    assert "YAML-Fehler" in out


def test_map_doc_writes_markdown_table(tmp_path):
    code, out, _ = run("map", "doc", write(tmp_path, VALID_MAPPING))
    assert code == 0
    lines = out.splitlines()
    header = "| Note | Name | Befehl | OSC-Adresse | Quellen | Hinweis |"
    assert header in lines
    rows = lines[lines.index(header) + 2 :]
    assert rows[0].startswith(
        "| 1 | Einlass | Cue auf einem Playback starten | `/zeros/cue/go/10/1`"
    )
    assert "| propresenter |" in rows[0]
    assert rows[1].startswith("| 2 | Musik \\| ruhig |")  # pipe escaped
    assert "ungetestet" in rows[2]


def test_map_doc_to_file(tmp_path):
    target = tmp_path / "spickzettel.md"
    code, _, _ = run("map", "doc", write(tmp_path, VALID_MAPPING), "-o", str(target))
    assert code == 0
    assert target.read_text(encoding="utf-8").startswith("# Spickzettel: mapping.yaml")


def test_map_doc_refuses_broken_mapping(tmp_path):
    code, out, err = run("map", "doc", write(tmp_path, BROKEN_MAPPING))
    assert code == 1
    assert out == ""
    assert "Kein Spickzettel" in err


# --- files and targets that used to end in a traceback --------------------------------

CP1252_MAPPING = VALID_MAPPING.replace("Einlass", "Musik kräftig").encode("cp1252")


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    code = main(argv, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_map_check_reports_non_utf8_file(tmp_path):
    path = tmp_path / "mapping.yaml"
    path.write_bytes(CP1252_MAPPING)
    code, out, _ = _run(["map", "check", str(path)])
    assert code == 1
    assert "nicht als UTF-8 gespeichert" in out


def test_map_doc_reports_non_utf8_file(tmp_path):
    path = tmp_path / "mapping.yaml"
    path.write_bytes(CP1252_MAPPING)
    code, _, err = _run(["map", "doc", str(path)])
    assert code == 1
    assert "nicht als UTF-8 gespeichert" in err


def test_config_reports_non_utf8_file(tmp_path):
    path = tmp_path / "mapping.yaml"
    path.write_bytes(CP1252_MAPPING)
    code, _, err = _run(["--config", str(path), "cue", "go", "10", "1"])
    assert code == 2
    assert "nicht als UTF-8 gespeichert" in err


def test_map_doc_reports_unwritable_output(tmp_path):
    path = tmp_path / "mapping.yaml"
    path.write_text(VALID_MAPPING, encoding="utf-8")
    target = tmp_path / "gibt" / "es" / "nicht" / "spick.md"
    code, _, err = _run(["map", "doc", str(path), "-o", str(target)])
    assert code == 1
    assert "nicht schreibbar" in err


@pytest.mark.parametrize("port", ["70000", "0", "-1"])
@pytest.mark.parametrize("extra", [[], ["--dry-run"]])
def test_port_out_of_range_is_an_error_even_in_dry_run(port, extra):
    argv = ["--host", "127.0.0.1", f"--port={port}", "cue", "go", "10", "2", *extra]
    code, out, err = _run(argv)
    assert code == 2
    assert "port muss eine ganze Zahl von 1 bis 65535 sein" in err
    assert out == ""


@pytest.mark.parametrize(
    "console",
    [
        'console: {host: 127.0.0.1, port: "8830", transport: udp}',
        "console: {host: 123, port: 8830, transport: udp}",
        "console: {host: 127.0.0.1, port: 8830.5, transport: udp}",
        "console: {host: 127.0.0.1, port: true, transport: udp}",
    ],
)
def test_config_with_wrong_types_is_an_error(tmp_path, console):
    path = tmp_path / "mapping.yaml"
    path.write_text(console + "\n", encoding="utf-8")
    code, _, err = _run(["--config", str(path), "cue", "go", "10", "1"])
    assert code == 2
    assert "Ziel:" in err


def _check(text, tmp_path):
    path = tmp_path / "mapping.yaml"
    path.write_text(text, encoding="utf-8")
    return _run(["map", "check", str(path)])


@pytest.mark.parametrize("value", [".inf", "-.inf", ".nan"])
def test_map_check_rejects_non_finite_debounce(tmp_path, value):
    code, out, _ = _check(VALID_MAPPING + f"debounce_ms: {value}\n", tmp_path)
    assert code == 1
    assert "debounce_ms muss eine endliche Zahl ab 0 sein" in out


def test_map_check_rejects_two_sources_on_same_port_and_channel(tmp_path):
    text = VALID_MAPPING.replace("channel: 16", "channel: 15")
    code, out, _ = _check(text, tmp_path)
    assert code == 1
    assert "gleicher midi_port und channel wie sources.propresenter" in out


def test_map_check_rejects_surrounding_spaces(tmp_path):
    text = VALID_MAPPING.replace("host: 127.0.0.1", 'host: " 127.0.0.1 "').replace(
        'ableton: {midi_port: "LX Bridge"', 'ableton: {midi_port: " LX Bridge"'
    )
    code, out, _ = _check(text, tmp_path)
    assert code == 1
    assert "console.host hat Leerzeichen" in out
    assert "sources.ableton.midi_port hat Leerzeichen" in out

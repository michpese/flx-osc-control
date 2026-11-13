"""Every address against the examples in docs/02-flx-osc-referenz.md."""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest

import zeros_osc as z
from zeros_osc.commands import COMMANDS, Status, ZerosValueError, address_warnings, match_address

REFERENCE = Path(__file__).resolve().parents[3] / "docs" / "02-flx-osc-referenz.md"

# (command id, builder call, expected address) - examples copied from the reference.
REFERENCE_EXAMPLES = [
    ("cue_go", lambda: z.cue_go(1, 5), "/zeros/cue/go/1/5"),
    ("cue_go_current", lambda: z.cue_go_current(4), "/zeros/cue/go/4"),
    ("cue_go_next", lambda: z.cue_go_next(), "/zeros/cue/go"),
    ("macro", lambda: z.macro(1), "/zeros/macro/1"),
    ("cue_pause", lambda: z.cue_pause(1), "/zeros/cue/pause/1"),
    ("cue_next", lambda: z.cue_next(1, 6), "/zeros/cue/next/1/6"),
    ("playback_go", lambda: z.playback_go(1), "/zeros/playback/go/1"),
    ("playback_pause", lambda: z.playback_pause(1), "/zeros/playback/pause/1"),
    ("playback_level", lambda: z.playback_level(1, 100), "/zeros/playback/level/1/100"),
    ("playback_level", lambda: z.playback_level(1, 100, 2), "/zeros/playback/level/1/100/2"),
    ("playback_release", lambda: z.playback_release(1), "/zeros/playback/release/1"),
    ("playback_view", lambda: z.playback_view(1), "/zeros/playback/view/1"),
    ("grand_master", lambda: z.grand_master(100), "/zeros/grandmaster/100"),
    ("grand_master", lambda: z.grand_master(0, 3), "/zeros/grandmaster/0/3"),
    ("blackout", lambda: z.blackout(1), "/zeros/blackout/1"),
    ("blackout", lambda: z.blackout(0), "/zeros/blackout/0"),
]


@pytest.mark.parametrize(("cid", "build", "expected"), REFERENCE_EXAMPLES)
def test_builder_matches_reference_example(cid, build, expected):
    assert build() == expected
    assert match_address(expected).command.id == cid


def test_every_command_has_an_example_test():
    assert {cid for cid, _, _ in REFERENCE_EXAMPLES} == set(COMMANDS)


def test_every_command_has_a_public_builder():
    for cid in COMMANDS:
        assert callable(getattr(z, cid)), cid


def test_command_example_field_is_built_by_builder():
    for command in COMMANDS.values():
        values = match_address(command.example).values
        assert command.build(*values) == command.example


# --- sync with docs/02 ------------------------------------------------------------


def _reference_rows():
    if not REFERENCE.exists():
        pytest.skip(f"{REFERENCE} not found")
    rows = []
    for line in REFERENCE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| `(\w+)` \|", line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        examples = re.findall(r"`(/zeros[^`]*)`", cells[3])
        rows.append((m.group(1), examples, cells[4]))
    assert rows, "command table not found in reference"
    return rows


def test_reference_table_and_code_list_the_same_commands():
    rows = _reference_rows()
    usable = {cid for cid, _, status in rows if status != "offen"}
    assert usable == set(COMMANDS)


def test_reference_status_matches_code():
    for cid, _, status in _reference_rows():
        if status == "offen":
            continue
        assert COMMANDS[cid].status.value == status, cid


def test_every_example_in_reference_matches_its_command():
    for cid, examples, status in _reference_rows():
        if status == "offen":
            continue
        assert examples, cid
        for example in examples:
            assert match_address(example).command.id == cid, example


# --- value checks -----------------------------------------------------------------


@pytest.mark.parametrize("playback", [0, 1, 96, "0", "96"])
def test_playback_range_ok(playback):
    assert z.cue_go(playback, 1) == f"/zeros/cue/go/{playback}/1"


@pytest.mark.parametrize("playback", [-1, 97, 1000, 1.5, "x", True, None])
def test_playback_rejected(playback):
    with pytest.raises(ZerosValueError):
        z.cue_go(playback, 1)


@pytest.mark.parametrize(
    ("cue", "expected"),
    [
        (1, "1"),
        (2.5, "2.5"),
        ("2.5", "2.5"),
        (Decimal("10.25"), "10.25"),
        ("3.0", "3"),
        (0.5, "0.5"),
    ],
)
def test_point_cues_allowed(cue, expected):
    assert z.cue_go(10, cue) == f"/zeros/cue/go/10/{expected}"


@pytest.mark.parametrize("cue", [0, -1, "0", "-2.5", "nan", "inf", "", "abc", False])
def test_cue_must_be_greater_than_zero(cue):
    with pytest.raises(ZerosValueError):
        z.cue_go(10, cue)
    with pytest.raises(ZerosValueError):
        z.cue_go_current(cue)
    with pytest.raises(ZerosValueError):
        z.cue_next(1, cue)


@pytest.mark.parametrize("level", [-1, 101, 50.5])
def test_level_rejected(level):
    with pytest.raises(ZerosValueError):
        z.playback_level(1, level)
    with pytest.raises(ZerosValueError):
        z.grand_master(level)


def test_fade_decimal_and_zero():
    assert z.playback_level(1, 50, 2.5) == "/zeros/playback/level/1/50/2.5"
    assert z.grand_master(0, 0) == "/zeros/grandmaster/0/0"
    with pytest.raises(ZerosValueError):
        z.grand_master(100, -1)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1, "1"), (0, "0"), (True, "1"), (False, "0"), ("on", "1"), ("off", "0"), ("TRUE", "1")],
)
def test_blackout_always_sends_1_or_0(value, expected):
    assert z.blackout(value) == f"/zeros/blackout/{expected}"


@pytest.mark.parametrize("value", [2, -1, "an", ""])
def test_blackout_rejected(value):
    with pytest.raises(ZerosValueError):
        z.blackout(value)


def test_macro_must_be_positive_integer():
    with pytest.raises(ZerosValueError):
        z.macro(0)
    with pytest.raises(ZerosValueError):
        z.macro(1.5)


# --- address matching -------------------------------------------------------------


@pytest.mark.parametrize(
    "address",
    [
        "/zeros/cue/go/97/1",  # playback out of range
        "/zeros/cue/go/1/0",  # cue 0
        "/zeros/cue/go/1/05",  # not normalised
        "/zeros/cue/go/*/1",  # wildcard
        "/zeros/cue/go/1/5/7",  # too many segments
        "/lx/q/go/1/5",  # short form: repo uses the long form only
        "/zeros/release/all",  # not in the reference
        "/zeros/blackout/on",  # repo sends 1/0 only
        "zeros/cue/go/1/5",  # no leading slash
        "/zeros/cue/go//5",  # empty segment
    ],
)
def test_addresses_outside_reference_are_rejected(address):
    with pytest.raises(ZerosValueError):
        match_address(address)


def test_point_cue_address_matches():
    m = match_address("/zeros/cue/go/10/2.5")
    assert m.command.id == "cue_go"
    assert m.values == ("10", "2.5")


def test_forum_commands_are_flagged_untested():
    assert COMMANDS["cue_go"].status is Status.BELEGT
    for cid, command in COMMANDS.items():
        if cid != "cue_go":
            assert command.status.untested, cid


def test_warnings():
    assert address_warnings(match_address("/zeros/cue/go/10/1")) == []
    assert any("Playback 0" in w for w in address_warnings(match_address("/zeros/cue/go/0/4")))
    assert any("ungetestet" in w for w in address_warnings(match_address("/zeros/macro/1")))

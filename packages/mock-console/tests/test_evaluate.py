"""Judging of OSC packets according to docs/02-flx-osc-referenz.md (no network)."""

from __future__ import annotations

import pytest

from mock_console import Reason, evaluate_message, evaluate_packet
from mock_console.evaluate import VERMUTET_NOTE
from mock_console.testing import CUE_5_ON_PLAYBACK_1, IMMEDIATELY, bundle, message
from zeros_osc import COMMANDS, Status


def only(data: bytes):
    parsed = evaluate_packet(data)
    assert len(parsed) == 1
    return parsed[0]


# --- the four equivalent forms -------------------------------------------------


@pytest.mark.parametrize("form", sorted(CUE_5_ON_PLAYBACK_1))
def test_each_form_is_cue_5_on_playback_1(form):
    verdict = only(CUE_5_ON_PLAYBACK_1[form]).verdict
    assert verdict.accepted
    assert verdict.command_id == "cue_go"
    assert verdict.path == "/zeros/cue/go/1/5"
    assert verdict.values == ("1", "5")
    assert verdict.status is Status.BELEGT


def test_all_four_forms_are_equivalent():
    verdicts = [only(data).verdict for data in CUE_5_ON_PLAYBACK_1.values()]
    assert len(verdicts) == 4
    assert all(v == verdicts[0] for v in verdicts)


def test_raw_address_and_arguments_are_kept():
    parsed = only(CUE_5_ON_PLAYBACK_1["both_as_arguments"])
    assert parsed.address == "/zeros/cue/go"
    assert parsed.args == ("1", "5")


def test_short_form_is_the_same_command():
    verdict = only(message("/lx/q/go/1/5")).verdict
    assert verdict.accepted
    assert verdict.path == "/zeros/cue/go/1/5"
    assert only(message("/lx/q/go", "1/5")).verdict == verdict


def test_integer_arguments_are_accepted():
    verdict = only(message("/zeros/cue/go", 1, 5)).verdict
    assert verdict.accepted and verdict.path == "/zeros/cue/go/1/5"


def test_point_cue_as_argument():
    verdict = only(message("/zeros/cue/go/1", "2.5")).verdict
    assert verdict.accepted and verdict.path == "/zeros/cue/go/1/2.5"


# --- status from the reference ---------------------------------------------------


def test_status_belegt():
    verdict = evaluate_message("/zeros/cue/go/10/2")
    assert verdict.status is Status.BELEGT
    assert verdict.notes == ()


def test_status_forum():
    verdict = evaluate_message("/zeros/macro/1")
    assert verdict.accepted
    assert verdict.command_id == "macro"
    assert verdict.status is Status.FORUM
    assert any("ungetestet" in n for n in verdict.notes)


def test_status_vermutet_is_flagged():
    verdict = evaluate_message("/zeros/blackout/1")
    assert verdict.accepted
    assert verdict.command_id == "blackout"
    assert verdict.status is Status.VERMUTET
    assert verdict.notes[0] == VERMUTET_NOTE
    assert "das echte Pult kann sie ablehnen" in VERMUTET_NOTE


def test_status_comes_from_zeros_osc():
    for command in COMMANDS.values():
        verdict = evaluate_message(command.example)
        assert verdict.accepted, command.example
        assert verdict.command_id == command.id
        assert verdict.status is command.status


def test_master_playback_warning_from_reference():
    verdict = evaluate_message("/zeros/cue/go/0/4")
    assert verdict.accepted
    assert any("Playback 0" in n for n in verdict.notes)


# --- the three reasons for ignoring ------------------------------------------------


@pytest.mark.parametrize("address", ["/zeros/cue/go/*/1", "/zeros/cue/go/1/?", "/zeros/cue/{go}"])
def test_wildcard_is_ignored(address):
    verdict = only(message(address)).verdict
    assert not verdict.accepted
    assert verdict.reason is Reason.WILDCARD
    assert verdict.command_id is None and verdict.status is None


def test_wildcard_with_arguments_is_ignored():
    verdict = only(message("/zeros/cue/*", "1", "5")).verdict
    assert verdict.reason is Reason.WILDCARD


def test_bundle_with_timetag_is_ignored_completely():
    timetag = 0xE5F3_1234_0000_0000
    parsed = evaluate_packet(
        bundle(timetag, message("/zeros/cue/go/1/5"), message("/zeros/macro/1"))
    )
    assert len(parsed) == 2
    for p in parsed:
        assert not p.verdict.accepted
        assert p.verdict.reason is Reason.BUNDLE_TIMETAG
        assert p.bundle_timetag == timetag


def test_bundle_with_timetag_discards_nested_immediate_bundle():
    inner = bundle(IMMEDIATELY, message("/zeros/cue/go/1/5"))
    parsed = evaluate_packet(bundle(42, inner))
    assert [p.verdict.reason for p in parsed] == [Reason.BUNDLE_TIMETAG]


@pytest.mark.parametrize(
    "data",
    [
        message("/zeros/release/all"),
        message("/zeros/cue/go/1/5/7"),
        message("/zeros/cue/go/200/1"),  # playback outside 0..96
        message("/zeros/cue/go/1", "5", "7"),
        message("/foo"),
    ],
)
def test_unknown_address_is_ignored(data):
    verdict = only(data).verdict
    assert not verdict.accepted
    assert verdict.reason is Reason.UNKNOWN_ADDRESS
    assert verdict.detail


def test_argument_without_value_type_is_unknown():
    verdict = only(message("/zeros/cue/go/1", b"\x05")).verdict
    assert verdict.reason is Reason.UNKNOWN_ADDRESS


# --- accepted bundles and broken packets -------------------------------------------


def test_immediate_bundle_is_judged_message_by_message():
    parsed = evaluate_packet(
        bundle(IMMEDIATELY, message("/zeros/cue/go", "1/5"), message("/zeros/release/all"))
    )
    assert [p.verdict.accepted for p in parsed] == [True, False]
    assert parsed[0].verdict.path == "/zeros/cue/go/1/5"
    assert parsed[0].bundle_timetag == IMMEDIATELY
    assert parsed[1].verdict.reason is Reason.UNKNOWN_ADDRESS


def test_nested_bundle_with_timetag_inside_immediate_bundle_is_ignored():
    inner = bundle(99, message("/zeros/cue/go/1/5"))
    parsed = evaluate_packet(bundle(IMMEDIATELY, message("/zeros/macro/1"), inner))
    assert [p.verdict.reason for p in parsed] == [None, Reason.BUNDLE_TIMETAG]


@pytest.mark.parametrize("data", [b"", b"garbage", b"#bundle\x00\x00", b"\xff\xfe\x00\x00"])
def test_invalid_packet(data):
    verdict = only(data).verdict
    assert not verdict.accepted
    assert verdict.reason is Reason.INVALID

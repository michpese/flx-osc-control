"""Network tests on 127.0.0.1 only, against the mock console (never a real console)."""

from __future__ import annotations

import json
import logging
import socket

import pytest

from mock_console import MockConsole, Reason
from mock_console.cli import build_parser, main
from mock_console.testing import CUE_5_ON_PLAYBACK_1, bundle, message
from zeros_osc import Status, UdpClient, cue_go

LOCALHOST = "127.0.0.1"


@pytest.fixture
def sender():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    yield sock
    sock.close()


def test_fixture_listens_on_free_local_port(mock_console):
    assert mock_console.host == LOCALHOST
    assert mock_console.port not in (0, 8830)
    assert mock_console.messages == []


def test_zeros_osc_client_is_received(mock_console):
    with UdpClient(mock_console.host, mock_console.port) as client:
        client.send(cue_go(10, 2))
    (record,) = mock_console.wait_for(1)
    assert record.accepted
    assert record.address == "/zeros/cue/go/10/2"
    assert record.args == ()
    assert record.command_id == "cue_go"
    assert record.status is Status.BELEGT
    assert record.sender.startswith(LOCALHOST + ":")


def test_four_forms_over_udp_are_equivalent(mock_console, sender):
    for data in CUE_5_ON_PLAYBACK_1.values():
        sender.sendto(data, (mock_console.host, mock_console.port))
    records = mock_console.wait_for(4)
    assert len(records) == 4
    assert {(r.accepted, r.command_id, r.path, r.status) for r in records} == {
        (True, "cue_go", "/zeros/cue/go/1/5", Status.BELEGT)
    }
    assert len({(r.address, r.args) for r in records}) == 4  # raw forms kept apart


def test_three_reasons_over_udp(mock_console, sender):
    target = (mock_console.host, mock_console.port)
    sender.sendto(message("/zeros/cue/go/*/1"), target)
    sender.sendto(bundle(12345, message("/zeros/cue/go/1/5")), target)
    sender.sendto(message("/zeros/release/all"), target)
    records = mock_console.wait_for(3)
    assert [r.reason for r in records] == [
        Reason.WILDCARD,
        Reason.BUNDLE_TIMETAG,
        Reason.UNKNOWN_ADDRESS,
    ]
    assert all(r.ignored for r in records)
    assert mock_console.accepted == []
    assert len(mock_console.ignored) == 3


def test_status_forum_and_vermutet_over_udp(mock_console, sender):
    target = (mock_console.host, mock_console.port)
    sender.sendto(message("/zeros/macro/1"), target)
    sender.sendto(message("/zeros/blackout", "1"), target)
    forum, vermutet = mock_console.wait_for(2)
    assert forum.status is Status.FORUM
    assert vermutet.status is Status.VERMUTET
    assert vermutet.path == "/zeros/blackout/1"


def test_log_line_per_message(mock_console, sender, caplog):
    caplog.set_level(logging.INFO, logger="mock_console")
    target = (mock_console.host, mock_console.port)
    sender.sendto(message("/zeros/cue/go", "1", "5"), target)
    sender.sendto(message("/zeros/blackout/1"), target)
    sender.sendto(message("/zeros/cue/go/*/1"), target)
    mock_console.wait_for(3)
    lines = [r.getMessage() for r in caplog.records if "adresse=" in r.getMessage()]
    assert len(lines) == 3
    assert "quelle=127.0.0.1:" in lines[0]
    assert 'adresse=/zeros/cue/go argumente=["1", "5"]' in lines[0]
    assert "akzeptiert befehl=cue_go pfad=/zeros/cue/go/1/5 status=belegt" in lines[0]
    assert "status=vermutet" in lines[1]
    assert "das echte Pult kann sie ablehnen" in lines[1]
    assert "ignoriert grund=wildcard" in lines[2]
    assert all("\n" not in line for line in lines)


def test_jsonl_file(tmp_path, sender):
    path = tmp_path / "empfang.jsonl"
    with MockConsole(host=LOCALHOST, port=0, jsonl=path) as console:
        target = (console.host, console.port)
        sender.sendto(message("/zeros/cue/go/1", "5"), target)
        sender.sendto(bundle(7, message("/zeros/cue/go/1/5")), target)
        console.wait_for(2)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["address"] == "/zeros/cue/go/1"
    assert rows[0]["args"] == ["5"]
    assert rows[0]["result"] == "accepted"
    assert rows[0]["status"] == "belegt"
    assert rows[0]["path"] == "/zeros/cue/go/1/5"
    assert rows[0]["sender"].startswith(LOCALHOST + ":")
    assert "T" in rows[0]["time"]
    assert rows[1]["result"] == "ignored"
    assert rows[1]["reason"] == "bundle_timetag"
    assert rows[1]["bundle_timetag"] == 7


def test_wait_for_times_out(mock_console):
    with pytest.raises(TimeoutError):
        mock_console.wait_for(1, timeout=0.2)


def test_clear(mock_console, sender):
    sender.sendto(message("/zeros/macro/1"), (mock_console.host, mock_console.port))
    mock_console.wait_for(1)
    mock_console.clear()
    assert mock_console.messages == []


def test_mock_never_answers(mock_console, sender):
    sender.settimeout(0.3)
    sender.sendto(message("/zeros/cue/go/1/5"), (mock_console.host, mock_console.port))
    mock_console.wait_for(1)
    with pytest.raises((TimeoutError, ConnectionResetError)):
        sender.recvfrom(4096)


def test_default_port_is_8830():
    assert MockConsole().port == 8830
    args = build_parser().parse_args([])
    assert (args.host, args.port, args.jsonl) == ("0.0.0.0", 8830, None)
    args = build_parser().parse_args(["--port", "9000", "--jsonl", "x.jsonl"])
    assert (args.port, args.jsonl) == (9000, "x.jsonl")


def test_cli_reports_busy_port(capsys):
    with MockConsole(host=LOCALHOST, port=0) as console:
        code = main(["--host", LOCALHOST, "--port", str(console.port)])
    assert code == 1
    assert "nicht verfügbar" in capsys.readouterr().err

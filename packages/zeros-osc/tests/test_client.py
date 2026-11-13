"""Network tests on 127.0.0.1 only, never against a real console.

zeros-osc must not depend on mock-console (mock-console depends on
zeros-osc), so these tests use a plain local socket as the receiver.
"""

from __future__ import annotations

import socket
import threading

import pytest
from pythonosc.osc_message import OscMessage

from zeros_osc import (
    TcpSlipClient,
    UdpClient,
    ZerosValueError,
    cue_go,
    encode_message,
    make_client,
    slip_decode,
    slip_encode,
)

LOCALHOST = "127.0.0.1"


@pytest.fixture
def udp_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LOCALHOST, 0))
    sock.settimeout(2.0)
    yield sock
    sock.close()


def test_udp_packet_is_received_and_decoded(udp_receiver):
    port = udp_receiver.getsockname()[1]
    address = cue_go(10, 2)
    with UdpClient(LOCALHOST, port) as client:
        sent = client.send(address)
    data, _ = udp_receiver.recvfrom(4096)
    assert data == sent
    message = OscMessage(data)
    assert message.address == "/zeros/cue/go/10/2"
    assert list(message.params) == []  # everything in the path, no arguments


def test_udp_point_cue_is_received(udp_receiver):
    port = udp_receiver.getsockname()[1]
    with make_client(LOCALHOST, port, "udp") as client:
        client.send(cue_go(1, 2.5))
    data, _ = udp_receiver.recvfrom(4096)
    assert OscMessage(data).address == "/zeros/cue/go/1/2.5"


def test_datagram_is_osc_padded():
    data = encode_message("/zeros/cue/go/10/2")
    assert len(data) % 4 == 0
    assert data.startswith(b"/zeros/cue/go/10/2\x00")
    assert data.endswith(b",\x00\x00\x00")


def test_client_refuses_addresses_outside_reference(udp_receiver):
    port = udp_receiver.getsockname()[1]
    with UdpClient(LOCALHOST, port) as client:
        with pytest.raises(ZerosValueError):
            client.send("/zeros/release/all")
        with pytest.raises(ZerosValueError):
            client.send("/zeros/cue/go/*/1")


def test_slip_roundtrip_with_special_bytes():
    payload = bytes([0x01, 0xC0, 0x02, 0xDB, 0x03])
    frame = slip_encode(payload)
    assert frame[0] == 0xC0 and frame[-1] == 0xC0
    assert 0xC0 not in frame[1:-1]
    assert slip_decode(frame) == payload


def test_tcp_slip_packet_is_received_and_decoded():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((LOCALHOST, 0))
    server.listen(1)
    server.settimeout(2.0)
    port = server.getsockname()[1]
    received: list[bytes] = []

    def accept_one():
        conn, _ = server.accept()
        conn.settimeout(2.0)
        buf = b""
        with conn:
            # Read until the closing END byte of the first frame.
            while buf.count(b"\xc0") < 2:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk
        received.append(buf)

    thread = threading.Thread(target=accept_one)
    thread.start()
    try:
        with TcpSlipClient(LOCALHOST, port) as client:
            client.send(cue_go(10, 2))
        thread.join(timeout=3.0)
    finally:
        server.close()

    assert received, "no TCP data received"
    message = OscMessage(slip_decode(received[0]))
    assert message.address == "/zeros/cue/go/10/2"


def test_unknown_transport():
    with pytest.raises(ValueError):
        make_client(LOCALHOST, 8830, "http")

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


def test_slip_decode_rejects_unescaped_end_inside_frame():
    with pytest.raises(ValueError, match="unescaped SLIP END"):
        slip_decode(bytes([0xC0, 0x01, 0xC0, 0x02, 0xC0]))


def test_tcp_slip_failed_connect_is_not_retried(monkeypatch):
    """One send may wait one timeout, not two (a retry doubled it)."""
    attempts = []

    def fake_create_connection(address, timeout=None):
        attempts.append(address)
        raise TimeoutError("timed out")

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    client = TcpSlipClient(LOCALHOST, 9, timeout=0.2)
    with pytest.raises(OSError):
        client.send(cue_go(10, 1))
    assert len(attempts) == 1


def test_tcp_slip_reconnects_before_sending_after_peer_closed():
    """The first message after the console closed the connection must arrive."""
    import time

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((LOCALHOST, 0))
    server.listen(2)
    server.settimeout(5.0)
    port = server.getsockname()[1]
    received: list[bytes] = []
    first_closed = threading.Event()

    def read_frame(conn):
        conn.settimeout(5.0)
        buf = b""
        while buf.count(b"\xc0") < 2:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
        return buf

    def serve():
        # Connection 1: read one frame, then close like a restarting console.
        conn, _ = server.accept()
        received.append(read_frame(conn))
        conn.close()
        first_closed.set()
        # Connection 2: the client has to come back on its own.
        conn, _ = server.accept()
        with conn:
            received.append(read_frame(conn))

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        with TcpSlipClient(LOCALHOST, port) as client:
            client.send(cue_go(10, 1))
            assert first_closed.wait(5.0)
            time.sleep(0.3)  # let the close reach the client socket
            client.send(cue_go(10, 2))
            thread.join(timeout=6.0)
    finally:
        server.close()

    assert len(received) == 2, "second message was lost after the peer closed"
    assert OscMessage(slip_decode(received[1])).address == "/zeros/cue/go/10/2"

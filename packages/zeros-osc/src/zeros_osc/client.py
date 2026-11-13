"""Send ZerOS OSC addresses to the console.

Two separate transports, matching the console setting "Transport":

* ``UdpClient``     - UDP, the ZerOS default.
* ``TcpSlipClient`` - TCP with SLIP framing (OSC 1.1, double END).

Both send the address as an OSC message without arguments. Before sending,
the address is checked against the reference (``match_address``); anything
else is refused. The console never answers, so a successful send only means
the packet left this computer.
"""

from __future__ import annotations

import select
import socket
from typing import Protocol

from pythonosc.osc_message_builder import OscMessageBuilder

from .commands import match_address

DEFAULT_PORT = 8830
TRANSPORTS = ("udp", "tcp-slip")

# SLIP (RFC 1055)
SLIP_END = 0xC0
SLIP_ESC = 0xDB
SLIP_ESC_END = 0xDC
SLIP_ESC_ESC = 0xDD


def encode_message(address: str) -> bytes:
    """OSC datagram for ``address`` with no arguments. Checks the address first."""
    match_address(address)
    return OscMessageBuilder(address=address).build().dgram


def slip_encode(packet: bytes) -> bytes:
    """Frame a packet with SLIP, END byte at both ends (OSC 1.1)."""
    out = bytearray([SLIP_END])
    for byte in packet:
        if byte == SLIP_END:
            out += bytes([SLIP_ESC, SLIP_ESC_END])
        elif byte == SLIP_ESC:
            out += bytes([SLIP_ESC, SLIP_ESC_ESC])
        else:
            out.append(byte)
    out.append(SLIP_END)
    return bytes(out)


def slip_decode(frame: bytes) -> bytes:
    """Inverse of ``slip_encode`` for a single frame (used by tests and tools)."""
    body = frame.strip(bytes([SLIP_END]))
    out = bytearray()
    escaped = False
    for byte in body:
        if escaped:
            if byte == SLIP_ESC_END:
                out.append(SLIP_END)
            elif byte == SLIP_ESC_ESC:
                out.append(SLIP_ESC)
            else:
                raise ValueError(f"invalid SLIP escape 0x{byte:02x}")
            escaped = False
        elif byte == SLIP_ESC:
            escaped = True
        elif byte == SLIP_END:
            # END inside the body means two frames or a damaged one.
            raise ValueError("unescaped SLIP END inside frame")
        else:
            out.append(byte)
    if escaped:
        raise ValueError("SLIP frame ends inside an escape sequence")
    return bytes(out)


class Client(Protocol):
    host: str
    port: int

    def send(self, address: str) -> bytes: ...

    def close(self) -> None: ...


class UdpClient:
    """Send OSC over UDP. One socket per client; no connection, no answer."""

    transport = "udp"

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        self._sock = socket.socket(family, socket.SOCK_DGRAM)

    def send(self, address: str) -> bytes:
        """Send ``address``; returns the datagram that was sent."""
        packet = encode_message(address)
        self._sock.sendto(packet, (self.host, self.port))
        return packet

    def close(self) -> None:
        self._sock.close()

    def __enter__(self) -> UdpClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class TcpSlipClient:
    """Send OSC over TCP with SLIP framing.

    Connects on the first send. Before each send it checks whether the peer
    has closed the connection (console restarted, OSC switched off and on)
    and reconnects first; otherwise the first message after such a close
    would be accepted by the operating system and lost without an error.
    If sending on an existing connection fails, it reconnects once. A failed
    connection attempt is not repeated, so one send waits at most one timeout.
    """

    transport = "tcp-slip"

    def __init__(self, host: str, port: int = DEFAULT_PORT, timeout: float = 2.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: socket.socket | None = None

    def _connect(self) -> socket.socket:
        if self._sock is None:
            self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        return self._sock

    def send(self, address: str) -> bytes:
        """Send ``address``; returns the SLIP frame that was sent."""
        frame = slip_encode(encode_message(address))
        if self._sock is not None and self._peer_closed(self._sock):
            self.close()
        had_connection = self._sock is not None
        try:
            self._connect().sendall(frame)
        except OSError:
            self.close()
            if not had_connection:
                raise  # connecting failed; a second attempt would double the wait
            self._connect().sendall(frame)
        return frame

    @staticmethod
    def _peer_closed(sock: socket.socket) -> bool:
        """True if the peer closed or reset the connection (no data is consumed)."""
        try:
            readable, _, _ = select.select([sock], [], [], 0)
            if not readable:
                return False
            return sock.recv(1, socket.MSG_PEEK) == b""
        except (OSError, ValueError):
            return True

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self) -> TcpSlipClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def make_client(host: str, port: int = DEFAULT_PORT, transport: str = "udp") -> Client:
    """Create the client for ``transport`` ("udp" or "tcp-slip")."""
    if transport == "udp":
        return UdpClient(host, port)
    if transport == "tcp-slip":
        return TcpSlipClient(host, port)
    raise ValueError(f"unknown transport {transport!r}, expected one of {TRANSPORTS}")

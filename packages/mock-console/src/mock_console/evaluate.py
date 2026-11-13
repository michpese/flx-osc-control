"""Judge incoming OSC packets the way ZerOS does, according to the reference.

Rules (``docs/02-flx-osc-referenz.md``):

* Values may stand in the path or be sent as arguments. The four equivalent
  forms of "cue 5 on playback 1" all become ``/zeros/cue/go/1/5``.
* ``/lx/q/go`` is the short form of ``/zeros/cue/go``.
* Addresses with wildcards are ignored.
* Bundles with a time tag are ignored completely; only "immediately"
  (raw time tag 1) is accepted.
* Anything that does not match a command of the reference is ignored.

The list of known addresses and their status come from ``zeros_osc``; this
module keeps no copy of its own. Nothing here simulates lights or cue states.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import Enum

from pythonosc.osc_message import OscMessage, ParseError

from zeros_osc import Status, ZerosValueError, address_warnings, match_address
from zeros_osc.commands import WILDCARD_CHARS

BUNDLE_PREFIX = b"#bundle\x00"
TIMETAG_IMMEDIATELY = 1  # OSC 1.0: 63 zero bits followed by a one
SHORT_PREFIX = "/lx/q/go"
LONG_PREFIX = "/zeros/cue/go"

# Shown with every accepted command whose status is "vermutet" (German, for operators).
VERMUTET_NOTE = (
    "Schreibweise nur angenommen, weil sie in der Referenz steht (Status vermutet); "
    "das echte Pult kann sie ablehnen"
)
FORUM_NOTE = "nur im Forum genannt, ungetestet (Status Forum)"


class Reason(Enum):
    """Why a message is ignored."""

    WILDCARD = "wildcard"
    BUNDLE_TIMETAG = "bundle_timetag"
    UNKNOWN_ADDRESS = "unknown_address"
    INVALID = "invalid"  # not a decodable OSC packet at all


@dataclass(frozen=True)
class Verdict:
    """Result of judging one OSC message."""

    accepted: bool
    reason: Reason | None = None
    detail: str = ""  # German explanation for the log
    command_id: str | None = None
    status: Status | None = None
    path: str | None = None  # normalised path form, e.g. /zeros/cue/go/1/5
    values: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ParsedMessage:
    """One OSC message from a packet, with its verdict."""

    address: str
    args: tuple[object, ...]
    verdict: Verdict
    bundle_timetag: int | None = None  # raw 64-bit time tag, None outside bundles


def _arg_segment(arg: object) -> str | None:
    """Path segment for an argument, or None if the type cannot carry a value."""
    if isinstance(arg, str):
        return arg
    if isinstance(arg, int) and not isinstance(arg, bool):
        return str(arg)
    if isinstance(arg, float):
        # OSC floats are 32 bit: 2.3 arrives as 2.299999952316284 and 5.0 would
        # print as "5.0". Seven significant digits give back what was sent.
        return format(arg, ".7g")
    return None


def _ignored(reason: Reason, detail: str) -> Verdict:
    return Verdict(accepted=False, reason=reason, detail=detail)


def evaluate_message(address: str, args: tuple[object, ...] | list[object] = ()) -> Verdict:
    """Judge a single message (not part of a bundle with a time tag)."""
    if WILDCARD_CHARS & set(address):
        return _ignored(Reason.WILDCARD, f"Adresse {address} enthält Wildcards")

    segments: list[str] = []
    for arg in args:
        segment = _arg_segment(arg)
        if segment is None:
            return _ignored(
                Reason.UNKNOWN_ADDRESS,
                f"Argument {arg!r} hat einen Typ, der keinen Wert tragen kann",
            )
        segments.append(segment)

    path = "/".join([address, *segments]) if segments else address
    if path == SHORT_PREFIX or path.startswith(SHORT_PREFIX + "/"):
        path = LONG_PREFIX + path[len(SHORT_PREFIX) :]

    try:
        match = match_address(path)
    except ZerosValueError as exc:
        return _ignored(Reason.UNKNOWN_ADDRESS, str(exc))

    status = match.command.status
    notes = list(address_warnings(match))
    if status is Status.VERMUTET:
        notes.insert(0, VERMUTET_NOTE)
    elif status is Status.FORUM:
        notes.insert(0, FORUM_NOTE)
    return Verdict(
        accepted=True,
        command_id=match.command.id,
        status=status,
        path=path,
        values=match.values,
        notes=tuple(notes),
    )


def _parse_bundle(data: bytes, outer_timetag: int | None) -> list[ParsedMessage]:
    if len(data) < 16:
        raise ParseError("bundle shorter than 16 bytes")
    (timetag,) = struct.unpack(">Q", data[8:16])
    # A bundle inside a bundle with a time tag is discarded as well.
    effective = timetag if outer_timetag in (None, TIMETAG_IMMEDIATELY) else outer_timetag
    result: list[ParsedMessage] = []
    index = 16
    while index < len(data):
        if index + 4 > len(data):
            raise ParseError("bundle element size truncated")
        (size,) = struct.unpack(">i", data[index : index + 4])
        index += 4
        if size <= 0 or size % 4 or index + size > len(data):
            raise ParseError(f"bad bundle element size {size}")
        element = data[index : index + size]
        index += size
        if element.startswith(BUNDLE_PREFIX):
            result.extend(_parse_bundle(element, effective))
        else:
            result.append(_parse_message(element, effective))
    return result


def _parse_message(data: bytes, bundle_timetag: int | None) -> ParsedMessage:
    message = OscMessage(data)  # raises ParseError
    address = message.address
    args = tuple(message.params)
    if bundle_timetag is not None and bundle_timetag != TIMETAG_IMMEDIATELY:
        verdict = _ignored(
            Reason.BUNDLE_TIMETAG,
            f"Bundle mit Zeitstempel 0x{bundle_timetag:016x}; nur 'sofort' (1) wird ausgeführt",
        )
    else:
        verdict = evaluate_message(address, args)
    return ParsedMessage(address, args, verdict, bundle_timetag)


def evaluate_packet(data: bytes) -> list[ParsedMessage]:
    """Split a UDP datagram into messages and judge each of them.

    A packet that cannot be decoded yields one entry with reason ``INVALID``.
    """
    try:
        if data.startswith(BUNDLE_PREFIX):
            return _parse_bundle(data, None)
        return [_parse_message(data, None)]
    except (ParseError, struct.error, UnicodeDecodeError) as exc:
        detail = f"kein gültiges OSC-Paket: {exc}"
    except Exception as exc:  # a packet must never kill the receiver
        detail = f"Paket nicht auswertbar: {type(exc).__name__}: {exc}"
    return [ParsedMessage(address="", args=(), verdict=_ignored(Reason.INVALID, detail))]

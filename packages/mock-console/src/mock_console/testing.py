"""Build raw OSC datagrams for tests. Nothing here sends anything.

zeros-osc only builds the path form and refuses wildcards, so tests that need
the argument forms, wildcards or bundles build their datagrams here.
"""

from __future__ import annotations

import struct

from pythonosc.osc_message_builder import OscMessageBuilder

IMMEDIATELY = 1


def message(address: str, *args: object) -> bytes:
    builder = OscMessageBuilder(address=address)
    for arg in args:
        builder.add_arg(arg)
    return builder.build().dgram


def bundle(timetag: int, *elements: bytes) -> bytes:
    body = b"".join(struct.pack(">i", len(e)) + e for e in elements)
    return b"#bundle\x00" + struct.pack(">Q", timetag) + body


# The four equivalent forms of "cue 5 on playback 1" from the reference.
CUE_5_ON_PLAYBACK_1 = {
    "path": message("/zeros/cue/go/1/5"),
    "cue_as_argument": message("/zeros/cue/go/1", "5"),
    "both_as_arguments": message("/zeros/cue/go", "1", "5"),
    "one_argument_with_slash": message("/zeros/cue/go", "1/5"),
}

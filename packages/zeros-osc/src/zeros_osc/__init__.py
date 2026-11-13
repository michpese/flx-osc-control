"""Build, validate and send ZerOS OSC commands (CLI: flxctl).

Only commands from docs/02-flx-osc-referenz.md are available.
"""

__version__ = "0.1.0"

from .client import (  # noqa: E402
    DEFAULT_PORT,
    TcpSlipClient,
    UdpClient,
    encode_message,
    make_client,
    slip_decode,
    slip_encode,
)
from .commands import (  # noqa: E402
    COMMANDS,
    Command,
    Match,
    Status,
    ZerosValueError,
    address_warnings,
    blackout,
    cue_go,
    cue_go_current,
    cue_go_next,
    cue_next,
    cue_pause,
    grand_master,
    macro,
    match_address,
    playback_go,
    playback_level,
    playback_pause,
    playback_release,
    playback_view,
)

__all__ = [
    "COMMANDS",
    "DEFAULT_PORT",
    "Command",
    "Match",
    "Status",
    "TcpSlipClient",
    "UdpClient",
    "ZerosValueError",
    "address_warnings",
    "blackout",
    "cue_go",
    "cue_go_current",
    "cue_go_next",
    "cue_next",
    "cue_pause",
    "encode_message",
    "grand_master",
    "macro",
    "make_client",
    "match_address",
    "playback_go",
    "playback_level",
    "playback_pause",
    "playback_release",
    "playback_view",
    "slip_decode",
    "slip_encode",
]

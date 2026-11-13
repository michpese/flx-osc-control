"""Stand-in for the Zero 88 FLX S24 that records and judges incoming OSC messages."""

__version__ = "0.1.0"

from .evaluate import (  # noqa: E402
    ParsedMessage,
    Reason,
    Verdict,
    evaluate_message,
    evaluate_packet,
)
from .server import MockConsole, Received  # noqa: E402

__all__ = [
    "MockConsole",
    "ParsedMessage",
    "Reason",
    "Received",
    "Verdict",
    "evaluate_message",
    "evaluate_packet",
]

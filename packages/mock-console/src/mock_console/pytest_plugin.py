"""pytest fixture ``mock_console``, registered through the ``pytest11`` entry point.

Starts a mock console on 127.0.0.1 with a free port and stops it after the
test. Send to ``mock_console.host`` / ``mock_console.port``; read the results
with ``mock_console.wait_for(n)`` or ``mock_console.messages``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from .server import MockConsole


@pytest.fixture
def mock_console() -> Iterator[MockConsole]:
    with MockConsole(host="127.0.0.1", port=0) as console:
        yield console

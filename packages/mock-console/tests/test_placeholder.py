"""Placeholder test until the first real feature lands."""

import mock_console


def test_package_imports() -> None:
    assert mock_console.__version__ == "0.1.0"

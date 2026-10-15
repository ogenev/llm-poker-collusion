import socket
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def inspect_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Allow local event-loop sockets, but fail any external network connection."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "inspect-data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "inspect-cache"))
    connect = socket.socket.connect

    def offline_connect(sock: socket.socket, address: Any) -> None:
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError("Offline integration tests must not connect to a network")
        connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", offline_connect)

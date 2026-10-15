"""Shared exclusive, synchronously durable JSONL storage."""

import os
from pathlib import Path
from types import TracebackType
from typing import Self

from poker_collusion.serialization import canonical


class RecordingError(OSError):
    """Persistence failed. Stop execution; a journal may have an incomplete tail."""


class DurableJsonl:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self._file = os.fdopen(descriptor, "w", encoding="utf-8", newline="\n")
        self.count = 0
        self._broken = False

    def write(self, record: object) -> None:
        if self._broken or self._file.closed:
            raise RecordingError("Recorder is closed or failed")
        try:
            self._file.write(canonical(record) + "\n")
            self._file.flush()
            os.fsync(self._file.fileno())
            if self.count == 0:
                directory = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
        except (OSError, TypeError, ValueError) as error:
            self._broken = True
            raise RecordingError("Could not durably record event") from error
        self.count += 1

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._file.close()

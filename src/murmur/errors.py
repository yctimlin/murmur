"""Exit statuses and the launcher's error type."""

from __future__ import annotations

EXIT_OK = 0
EXIT_CODEX_FAILED = 1
EXIT_CAPPED = 2
EXIT_LAUNCHER = 3
EXIT_INCOMPLETE = 4
EXIT_INTERRUPTED = 130


class MurmurError(Exception):
    def __init__(self, message: str, code: int = EXIT_LAUNCHER) -> None:
        super().__init__(message)
        self.code = code


def fail(message: str, code: int = EXIT_LAUNCHER) -> None:
    raise MurmurError(message, code)

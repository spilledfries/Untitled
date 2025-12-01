from __future__ import annotations


class ReuseKitError(Exception):
    """
    ReuseKit base error.

    Why: Provide a single exception type for callers to catch.
    """
    def __init__(self, code: str, hint: str = "", recoverable: bool = False) -> None:
        super().__init__(f"{code}: {hint}" if hint else code)
        self.code = code
        self.hint = hint
        self.recoverable = recoverable

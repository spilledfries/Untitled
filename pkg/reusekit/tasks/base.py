from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:  # avoid import cycle
    from ..session import Session  # pragma: no cover


@dataclass(slots=True)
class Task:
    """
    Base task. Subclasses must implement run(session) -> Artifact.
    """
    name: str

    def run(self, session: "Session"):  # pragma: no cover
        raise NotImplementedError

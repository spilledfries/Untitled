from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Storage:
    name: str
    path: str
    size_bytes: int
    transport: str


@dataclass(slots=True)
class Device:
    id: str
    vendor: str
    model: str
    serial: str | None
    storage: list[Storage]
    created_at: datetime


@dataclass(slots=True)
class Artifact:
    kind: str
    path: str
    sha256: str
    meta: dict[str, Any]
    created_at: datetime | None = None

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .base import Task
from ..models import Artifact


class Inventory(Task):
    """
    Emits inventory.json derived from session.device.
    """

    def __init__(self) -> None:
        super().__init__(name="inventory")

    def run(self, session) -> Artifact:
        # why: single source of truth for device facts
        device = session.device
        facts = {
            "id": getattr(device, "id", None),
            "storage": [getattr(s, "name", None) for s in getattr(device, "storage", [])],
        }
        out: Path = session.workdir / "inventory.json"
        out.write_text(json.dumps(facts, indent=2), encoding="utf-8")
        sha = hashlib.sha256(out.read_bytes()).hexdigest()
        return Artifact(
            kind="inventory",
            path=str(out),
            sha256=sha,
            meta={},
            created_at=getattr(device, "created_at", None),
        )

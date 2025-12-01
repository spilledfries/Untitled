from __future__ import annotations

import json
import hashlib
import time
from pathlib import Path
from typing import Any


class Logger:
    """
    Append-only JSONL logger with a simple hash chain.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._prev = ""

    def event(self, kind: str, data: dict[str, Any]) -> None:
        ts = int(time.time())
        payload = {"ts": ts, "kind": kind, "data": data, "prev": self._prev}
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        h = hashlib.sha256(line.encode("utf-8")).hexdigest()
        self._prev = h
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()

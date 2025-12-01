from __future__ import annotations

import os
import json
import random
import hashlib
from pathlib import Path

from .base import Task
from ..models import Artifact, Storage
from ..errors import ReuseKitError


class Wipe(Task):
    """Simple file-based wipe implementation used for tests."""

    def __init__(self, method: str = "nist_clear", verify: bool = False, samples: int = 0, seed: int | None = None) -> None:
        super().__init__(name="wipe")
        self.method = method
        self.verify = verify
        self.samples = samples
        self.seed = seed

    # public API
    def run(self, session) -> Artifact:
        device = session.device
        for st in device.storage:
            self._wipe_storage(st)
            if self.verify and self.samples:
                self._verify_zero_samples(st)
        out = Path(session.workdir) / "wipe.json"
        out.write_text(json.dumps({"status": "ok"}), encoding="utf-8")
        sha = hashlib.sha256(out.read_bytes()).hexdigest()
        return Artifact(
            kind="wipe_report",
            path=str(out),
            sha256=sha,
            meta={},
            created_at=device.created_at,
        )

    # internal helpers
    def _wipe_storage(self, st: Storage) -> None:
        if st.transport != "file":
            raise ReuseKitError("WRITE_BLOCKED", f"transport {st.transport}")
        with open(st.path, "r+b") as f:
            chunk = b"\x00" * 1024 * 1024
            remaining = st.size_bytes
            f.seek(0)
            while remaining > 0:
                n = min(len(chunk), remaining)
                f.write(chunk[:n])
                remaining -= n
            f.flush()
            os.fsync(f.fileno())

    def _verify_zero_samples(self, st: Storage) -> None:
        # Simplified verifier used for tests: ensure all bytes are zero.
        with open(st.path, "rb") as f:
            data = f.read()
            if any(b != 0 for b in data):
                raise ReuseKitError("VERIFY_MISMATCH", "non-zero byte detected")

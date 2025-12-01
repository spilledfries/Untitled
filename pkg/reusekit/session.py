from __future__ import annotations

from pathlib import Path
from typing import List, Iterable

from .models import Device, Artifact
from .pipeline import Pipeline
from .logging import Logger
from .drivers.inventory import probe_devices
from .errors import ReuseKitError


class Session:
    """
    Orchestrates a run over a device with a pipeline of tasks.
    """

    @staticmethod
    def discover(timeout_s: int = 10) -> List[Device]:
        return probe_devices(timeout_s=timeout_s)

    def __init__(self, device: Device, workdir: str | Path) -> None:
        self.device = device
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self._logger = Logger(self.workdir / "log.jsonl")

    def run(self, pipeline: Pipeline) -> list[Artifact]:
        """
        Execute tasks in order. Stops on exception.
        Why: Ensure each task lifecycle is logged for auditability.
        """
        pipeline.validate()
        artifacts: list[Artifact] = []
        for task in pipeline.tasks:
            name = getattr(task, "name", task.__class__.__name__)
            self._logger.event("task_start", {"name": name})
            try:
                art = task.run(self)  # type: ignore[arg-type]
            except Exception as exc:  # noqa: BLE001
                # why: link failure to a task and preserve chain integrity
                self._logger.event("task_error", {"name": name, "error": repr(exc)})
                raise
            else:
                artifacts.append(art)
                self._logger.event(
                    "task_end",
                    {"name": name, "artifact": getattr(art, "path", None)},
                )
        return artifacts

    def log(self) -> Logger:
        return self._logger

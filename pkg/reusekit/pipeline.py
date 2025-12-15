from __future__ import annotations

from typing import List, Iterable

from .tasks.base import Task
from .errors import ReuseKitError


class Pipeline:
    """
    Simple linear pipeline of Tasks.
    """

    def __init__(self, tasks: List[Task] | None = None) -> None:
        self.tasks: List[Task] = list(tasks) if tasks else []

    def add(self, task: Task) -> None:
        self.tasks.append(task)

    def extend(self, tasks: Iterable[Task]) -> None:
        self.tasks.extend(tasks)

    def validate(self) -> None:
        if not self.tasks:
            raise ReuseKitError("EMPTY_PIPELINE", "add at least one task", recoverable=True)
        for i, t in enumerate(self.tasks):
            if not isinstance(t, Task):
                raise ReuseKitError("INVALID_TASK", f"index {i} is not a Task")
            if not getattr(t, "name", ""):
                raise ReuseKitError("MISSING_TASK_NAME", f"index {i}")

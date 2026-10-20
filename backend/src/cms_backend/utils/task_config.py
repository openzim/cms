import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.orm import Session as OrmSession

from cms_backend.utils.datetime import getnow


@dataclass
class TaskConfig:
    """Configuration for a background task with interval-based execution."""

    func: Callable[[OrmSession], None]
    interval: dt.timedelta
    name: str | None = None
    enabled: bool = True
    _last_run: dt.datetime = field(
        default_factory=lambda: dt.datetime.fromtimestamp(0).replace(tzinfo=None)
    )

    @property
    def task_name(self) -> str:
        return self.name or self.func.__name__

    def should_run(self, now: dt.datetime) -> bool:
        """Check if this task is enabled and due based on its interval."""
        return self.enabled and now - self._last_run >= self.interval

    def execute(self, session: OrmSession) -> None:
        """Execute the task and update the last run timestamp."""
        self.func(session)
        self._last_run = getnow()

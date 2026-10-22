"""Timer related code."""

from __future__ import annotations

import logging
import time
from types import TracebackType

LOG = logging.getLogger(__name__)


class Timer:
    """Timer object."""

    def __init__(self, name: str, active: bool = True) -> None:
        self.name = name
        self.active = active
        self.start_tmstmp = 0

    def __enter__(self) -> Timer:
        self.start_tmstmp = time.time_ns()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.active:
            LOG.debug(
                "Timer %s finished. Took %s ms.",
                self.name,
                round((time.time_ns() - self.start_tmstmp) / 1_000_000, 3),
            )

"""Decides when an alert has to be sent, in the spirit of Prometheus Alertmanager.

- A state change (normal -> warning, warning -> normal) is sent as soon as it
  happens.
- "Already told" means the last state that was actually *delivered*, so a
  message lost to an outage is not forgotten.
- A failed send is retried with a growing delay, not on every check.
- While a metric stays in warning, a reminder is sent every `repeat_interval`
  seconds (0 turns reminders off).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable, Mapping


class AlertKind(str, Enum):
    FIRING = "firing"
    RESOLVED = "resolved"
    REMINDER = "reminder"


@dataclass(frozen=True)
class RetryPolicy:
    base_delay: int = 30
    max_delay: int = 300


class AlertTracker:
    def __init__(
        self,
        keys: Iterable[str],
        repeat_interval: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        retry_policy: RetryPolicy = RetryPolicy(),
    ):
        self._repeat_interval = repeat_interval
        self._clock = clock
        self._retry_policy = retry_policy

        self._notified = {key: False for key in keys}
        self._notified_at: dict[str, float | None] = {key: None for key in keys}

        self._failures = 0
        self._retry_at = 0.0

    @property
    def failures(self) -> int:
        return self._failures

    def pending(self, warnings: Mapping[str, bool]) -> dict[str, AlertKind]:
        """Alerts to send now, as {key: FIRING | RESOLVED | REMINDER}."""
        now = self._clock()
        pending: dict[str, AlertKind] = {}

        for key, is_warning in warnings.items():
            if is_warning != self._notified[key]:
                pending[key] = AlertKind.FIRING if is_warning else AlertKind.RESOLVED
            elif (
                is_warning
                and self._repeat_interval
                and self._notified_at[key] is not None
                and now - self._notified_at[key] >= self._repeat_interval
            ):
                pending[key] = AlertKind.REMINDER

        return pending

    def backing_off(self) -> bool:
        """True while waiting to retry after a failed send."""
        return self._clock() < self._retry_at

    def delivered(self, pending: Mapping[str, AlertKind]) -> int:
        """Record a successful send; returns how many sends failed before it."""
        now = self._clock()
        for key, kind in pending.items():
            self._notified[key] = kind != AlertKind.RESOLVED
            self._notified_at[key] = now

        failures = self._failures
        self.forget_failures()
        return failures

    def abandon(self, pending: Mapping[str, AlertKind]) -> None:
        """Stop retrying these alerts after a permanent delivery error.

        The current state is recorded as the last known state, so the next
        check does not retry the same undeliverable message in a loop. A later
        state change (or reminder) can still attempt delivery again.
        """
        now = self._clock()
        for key, kind in pending.items():
            self._notified[key] = kind != AlertKind.RESOLVED
            self._notified_at[key] = now

        self.forget_failures()

    def failed(self, retry_after: int | None = None) -> tuple[int, int]:
        """Record a failed send; returns (failures so far, seconds until retry)."""
        self._failures += 1
        exponent = min(self._failures - 1, 10)
        backoff = min(
            self._retry_policy.base_delay * 2**exponent,
            self._retry_policy.max_delay,
        )
        delay = max(backoff, retry_after or 0)
        self._retry_at = self._clock() + delay
        return self._failures, delay

    def forget_failures(self) -> None:
        self._failures = 0
        self._retry_at = 0.0

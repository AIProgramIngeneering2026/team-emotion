"""Проверка (Job) и её жизненный цикл. Правило переходов живёт здесь, а не в вызывающем коде."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from .errors import InvalidTransition
from .tool import ToolResult


class Status(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    CANCELLED = "cancelled"


FINAL = frozenset({Status.PASSED, Status.FAILED, Status.ERROR, Status.CANCELLED})

ALLOWED: dict[Status, frozenset[Status]] = {
    Status.QUEUED: frozenset({Status.RUNNING, Status.CANCELLED}),
    Status.RUNNING: frozenset({Status.PASSED, Status.FAILED, Status.ERROR, Status.CANCELLED}),
    Status.PASSED: frozenset(),
    Status.FAILED: frozenset(),
    Status.ERROR: frozenset(),
    Status.CANCELLED: frozenset(),
}

RUNNING_TIMEOUT = timedelta(minutes=10)


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Check:
    repo: str
    pr_number: int
    checks: tuple[str, ...]
    params: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: Status = Status.QUEUED
    head_sha: str | None = None
    error_reason: str | None = None
    results: dict[str, ToolResult] = field(default_factory=dict)
    started_at: datetime | None = None

    @property
    def is_final(self) -> bool:
        return self.status in FINAL

    def _move(self, target: Status) -> None:
        if target not in ALLOWED[self.status]:
            raise InvalidTransition(
                f"Переход {self.status.value} → {target.value} запрещён",
                **{"from": self.status.value, "to": target.value},
            )
        self.status = target

    def start(self, head_sha: str, now: datetime | None = None) -> None:
        self._move(Status.RUNNING)
        self.head_sha = head_sha
        self.started_at = now or _now()

    def record(self, name: str, result: ToolResult) -> None:
        """Сохранить результат одного Tool. Только в running и только один раз на Tool."""
        if self.status is not Status.RUNNING:
            raise InvalidTransition(
                f"Результат нельзя записать в состоянии {self.status.value}",
                **{"from": self.status.value, "check": name},
            )
        if name not in self.checks:
            raise InvalidTransition(f"Проверка {name} не входит в эту Проверку", check=name)
        if name in self.results:
            raise InvalidTransition(f"Результат {name} уже записан", check=name)
        self.results[name] = result

    def finish(self) -> Status:
        """Итог по правилу: есть error → error, иначе есть failed → failed, иначе passed."""
        missing = [n for n in self.checks if n not in self.results]
        if self.status is Status.RUNNING and missing:
            raise InvalidTransition("Не все Tool завершились", missing=missing)
        statuses = {r.status for r in self.results.values()}
        if "error" in statuses:
            self.error_reason = next(r.error_reason for r in self.results.values() if r.status == "error")
            self._move(Status.ERROR)
        elif "failed" in statuses:
            self._move(Status.FAILED)
        else:
            self._move(Status.PASSED)
        return self.status

    def fail(self, reason: str) -> None:
        self._move(Status.ERROR)
        self.error_reason = reason

    def cancel(self) -> None:
        self._move(Status.CANCELLED)

    def expire_if_stuck(self, now: datetime | None = None) -> bool:
        """Перевести зависшую в running Проверку в error по таймауту. Вызывает Worker."""
        now = now or _now()
        if self.status is Status.RUNNING and self.started_at and now - self.started_at > RUNNING_TIMEOUT:
            self.fail("timeout")
            return True
        return False

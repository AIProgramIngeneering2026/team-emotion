"""Реализации портов в памяти: для тестов и прототипа до практики 4."""
from __future__ import annotations

from .check import Check, Status
from .tool import FileTooLarge, PRFile, PullRequestTooLarge

MAX_FILES = 300
MAX_FILE_BYTES = 1024 * 1024


class InMemorySource:
    """files — файлы, изменённые в PR. base — остальные файлы репозитория, например шаблоны:
    их можно прочитать, но в list_files их нет, как у настоящего PR."""

    def __init__(self, files: dict[str, str], base: dict[str, str] | None = None) -> None:
        self._files = files
        self._base = base or {}

    def list_files(self) -> list[PRFile]:
        if len(self._files) > MAX_FILES:
            raise PullRequestTooLarge()
        return [PRFile(p) for p in self._files]

    def read_file(self, path: str) -> str:
        text = self._files[path] if path in self._files else self._base[path]
        if len(text.encode()) > MAX_FILE_BYTES:
            raise FileTooLarge(path)
        return text


class InMemoryCheckRepository:
    def __init__(self) -> None:
        self._items: dict[str, Check] = {}

    def add(self, check: Check) -> None:
        self._items[check.id] = check

    def get(self, check_id: str) -> Check | None:
        return self._items.get(check_id)

    def next_queued(self) -> Check | None:
        return next((c for c in self._items.values() if c.status is Status.QUEUED), None)

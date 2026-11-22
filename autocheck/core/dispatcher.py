"""Dispatcher: ведёт Проверку по состояниям. Конкретных Tool не знает — только Registry и контракт Tool."""
from __future__ import annotations

from .check import Check, Status
from .registry import Registry
from .tool import CheckContext, PullRequestSource, ToolResult


class Dispatcher:
    def __init__(self, registry: Registry) -> None:
        self._registry = registry

    def run(self, check: Check, source: PullRequestSource, head_sha: str) -> Status:
        check.start(head_sha)
        for name in check.checks:
            if check.status is not Status.RUNNING:  # отменили во время выполнения
                return check.status
            tool = self._registry.get(name)
            ctx = CheckContext(check.repo, check.pr_number, head_sha, check.params.get(name, {}), source)
            try:
                result = tool.run(ctx)
                if not isinstance(result, ToolResult):
                    result = ToolResult.error("tool_error")
            except Exception:  # падение Tool не роняет Проверку, а превращается в error
                result = ToolResult.error("tool_error")
            if check.status is not Status.RUNNING:
                # Tool ответил после отмены или таймаута: результат опоздал, Проверку не трогаем
                return check.status
            check.record(name, result)
        return check.finish()

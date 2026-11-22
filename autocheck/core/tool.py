"""Контракт Tool из docs/tool-contract.md."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


@dataclass(frozen=True)
class PRFile:
    path: str
    status: Literal["added", "modified", "removed", "renamed"] = "added"


class SourceUnavailable(Exception):
    reason = "github_unavailable"


class PullRequestNotFound(Exception):
    reason = "pr_not_found"


class BadSourceResponse(Exception):
    reason = "bad_github_response"


class PullRequestTooLarge(Exception):
    reason = "pr_too_large"


class FileTooLarge(Exception):
    pass


SOURCE_ERRORS = (SourceUnavailable, PullRequestNotFound, BadSourceResponse, PullRequestTooLarge)


class PullRequestSource(Protocol):
    """Источник данных PR. Реализует GitHubAdapter, в тестах — InMemorySource."""

    def list_files(self) -> list[PRFile]: ...

    def read_file(self, path: str) -> str: ...


@dataclass(frozen=True)
class CheckContext:
    repo: str
    pr_number: int
    head_sha: str
    params: dict
    source: PullRequestSource


@dataclass(frozen=True)
class Problem:
    message: str
    path: str | None = None


@dataclass(frozen=True)
class ToolResult:
    status: Literal["passed", "failed", "error"]
    problems: tuple[Problem, ...] = field(default_factory=tuple)
    error_reason: str | None = None

    @classmethod
    def passed(cls) -> "ToolResult":
        return cls("passed")

    @classmethod
    def failed(cls, *problems: Problem) -> "ToolResult":
        return cls("failed", tuple(problems))

    @classmethod
    def error(cls, reason: str) -> "ToolResult":
        return cls("error", (), reason)


class Tool(Protocol):
    name: str
    params_schema: dict

    def run(self, ctx: CheckContext) -> ToolResult: ...

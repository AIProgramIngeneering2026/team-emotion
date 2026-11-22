"""Dispatcher: обычный путь, падение Tool, новый Tool без правки Dispatcher, ответ после отмены."""
from autocheck.core.check import Check, Status
from autocheck.core.dispatcher import Dispatcher
from autocheck.core.memory import InMemoryCheckRepository, InMemorySource
from autocheck.core.registry import Registry
from autocheck.core.tool import ToolResult
from autocheck.tools import SectionsTool, StructureTool

FILES = {"teams/emotion/p1.md": "## Тема\nAutoCheck\n"}
BASE = {"templates/p1.md": "## Тема\n<!-- -->\n"}
PARAMS = {"structure": {"root": "teams/emotion/"}, "sections": {"template": "templates/p1.md"}}


def make(*extra_tools):
    r = Registry()
    for t in (StructureTool(), SectionsTool(), *extra_tools):
        r.register(t)
    return Dispatcher(r)


def new_check(checks=("structure", "sections"), params=PARAMS):
    return Check("org/repo", 1, tuple(checks), dict(params))


def test_normal_path_through_repository():
    repo = InMemoryCheckRepository()
    repo.add(new_check())
    check = repo.next_queued()
    status = make().run(check, InMemorySource(FILES, BASE), "sha1")
    assert status is Status.PASSED
    assert check.head_sha == "sha1"
    assert set(check.results) == {"structure", "sections"}
    assert repo.next_queued() is None


def test_failed_result():
    files = {**FILES, "README.md": "x"}
    c = new_check()
    assert make().run(c, InMemorySource(files, BASE), "sha1") is Status.FAILED


class CrashingTool:
    name = "crash"
    params_schema = {"type": "object"}

    def run(self, ctx):
        raise RuntimeError("boom")


def test_tool_crash_becomes_error_and_other_tools_still_run():
    c = new_check(("crash", "structure"), {"structure": PARAMS["structure"]})
    assert make(CrashingTool()).run(c, InMemorySource(FILES, BASE), "sha1") is Status.ERROR
    assert c.error_reason == "tool_error"
    assert c.results["structure"].status == "passed"


class WrongReturnTool:
    name = "wrong"
    params_schema = {"type": "object"}

    def run(self, ctx):
        return "ok"


def test_tool_returning_garbage_becomes_error():
    c = new_check(("wrong",), {})
    assert make(WrongReturnTool()).run(c, InMemorySource(FILES, BASE), "sha1") is Status.ERROR


class NewTool:
    """Третий Tool: регистрируется, Dispatcher при этом не меняется."""
    name = "size"
    params_schema = {"type": "object"}

    def run(self, ctx):
        return ToolResult.passed() if len(ctx.source.list_files()) <= 50 else ToolResult.failed()


def test_new_tool_added_without_changing_dispatcher():
    c = new_check(("size",), {})
    assert make(NewTool()).run(c, InMemorySource(FILES, BASE), "sha1") is Status.PASSED


class CancelDuringRun:
    """Пока Tool работает, клиент отменяет Проверку. Tool всё равно отвечает успехом (З3)."""
    name = "slow"
    params_schema = {"type": "object"}

    def __init__(self):
        self.check = None

    def run(self, ctx):
        self.check.cancel()
        return ToolResult.passed()


def test_z3_late_tool_answer_after_cancel_is_ignored():
    tool = CancelDuringRun()
    c = new_check(("slow", "structure"), {"structure": PARAMS["structure"]})
    tool.check = c
    assert make(tool).run(c, InMemorySource(FILES, BASE), "sha1") is Status.CANCELLED
    assert c.results == {}


def test_z6_dispatcher_cannot_rerun_finished_check():
    import pytest
    from autocheck.core.errors import InvalidTransition

    d = make()
    c = new_check()
    d.run(c, InMemorySource(FILES, BASE), "sha1")
    with pytest.raises(InvalidTransition):
        d.run(c, InMemorySource(FILES, BASE), "sha2")
    assert c.status is Status.PASSED and c.head_sha == "sha1"

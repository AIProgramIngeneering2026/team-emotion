"""Жизненный цикл Проверки: обычный путь и злодейства З1–З6 с пары 3."""
from datetime import datetime, timedelta, timezone

import pytest

from autocheck.core.check import Check, Status
from autocheck.core.errors import InvalidTransition
from autocheck.core.tool import ToolResult

T0 = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def new_check(*checks: str) -> Check:
    return Check(repo="org/repo", pr_number=1, checks=checks or ("structure",))


def test_normal_path_queued_running_passed():
    c = new_check("structure", "sections")
    assert c.status is Status.QUEUED
    c.start("sha1", now=T0)
    assert c.status is Status.RUNNING
    c.record("structure", ToolResult.passed())
    c.record("sections", ToolResult.passed())
    assert c.finish() is Status.PASSED
    assert c.is_final


def test_failed_when_any_tool_failed():
    c = new_check("structure", "sections")
    c.start("sha1")
    c.record("structure", ToolResult.failed())
    c.record("sections", ToolResult.passed())
    assert c.finish() is Status.FAILED


def test_error_wins_over_failed():
    c = new_check("structure", "sections")
    c.start("sha1")
    c.record("structure", ToolResult.failed())
    c.record("sections", ToolResult.error("github_unavailable"))
    assert c.finish() is Status.ERROR
    assert c.error_reason == "github_unavailable"


# --- З1 Двойная работа ---------------------------------------------------------

def test_z1_second_start_rejected():
    c = new_check()
    c.start("sha1")
    with pytest.raises(InvalidTransition):
        c.start("sha2")
    assert c.status is Status.RUNNING and c.head_sha == "sha1"


def test_z1_same_tool_result_twice_rejected():
    c = new_check("structure", "sections")
    c.start("sha1")
    c.record("structure", ToolResult.passed())
    with pytest.raises(InvalidTransition):
        c.record("structure", ToolResult.failed())
    assert c.results["structure"].status == "passed"


# --- З2 Вечная работа ----------------------------------------------------------

def test_z2_running_after_restart_expires_to_error():
    c = new_check()
    c.start("sha1", now=T0)
    assert not c.expire_if_stuck(now=T0 + timedelta(minutes=5))
    assert c.expire_if_stuck(now=T0 + timedelta(minutes=11))
    assert c.status is Status.ERROR and c.error_reason == "timeout"


# --- З3 Отменённое стало готовым -----------------------------------------------

def test_z3_cancelled_cannot_finish():
    c = new_check()
    c.start("sha1")
    c.cancel()
    with pytest.raises(InvalidTransition):
        c.record("structure", ToolResult.passed())
    with pytest.raises(InvalidTransition):
        c.finish()
    assert c.status is Status.CANCELLED


def test_z3_cancelled_in_queue_cannot_start():
    c = new_check()
    c.cancel()
    with pytest.raises(InvalidTransition):
        c.start("sha1")
    assert c.status is Status.CANCELLED


# --- З4 Два итога --------------------------------------------------------------

def test_z4_error_cannot_become_passed():
    c = new_check()
    c.start("sha1", now=T0)
    c.expire_if_stuck(now=T0 + timedelta(minutes=11))
    with pytest.raises(InvalidTransition):
        c.record("structure", ToolResult.passed())  # Tool ответил после таймаута
    with pytest.raises(InvalidTransition):
        c.finish()
    assert c.status is Status.ERROR


@pytest.mark.parametrize("final", ["passed", "failed", "error"])
def test_z4_final_state_cannot_be_cancelled(final):
    c = new_check()
    c.start("sha1")
    c.record("structure", ToolResult(final))
    c.finish()
    with pytest.raises(InvalidTransition):
        c.cancel()


# --- З5 Успех без работы -------------------------------------------------------

def test_z5_queued_cannot_finish():
    c = new_check()
    with pytest.raises(InvalidTransition):
        c.finish()
    assert c.status is Status.QUEUED


def test_z5_running_without_results_cannot_finish():
    c = new_check("structure", "sections")
    c.start("sha1")
    c.record("structure", ToolResult.passed())
    with pytest.raises(InvalidTransition):
        c.finish()
    assert c.status is Status.RUNNING


# --- З6 Повтор успешного -------------------------------------------------------

def test_z6_passed_cannot_start_again():
    c = new_check()
    c.start("sha1")
    c.record("structure", ToolResult.passed())
    c.finish()
    with pytest.raises(InvalidTransition):
        c.start("sha2")
    assert c.status is Status.PASSED


def test_invalid_transition_error_has_details():
    c = new_check()
    c.start("sha1")
    c.cancel()
    with pytest.raises(InvalidTransition) as e:
        c.cancel()
    assert e.value.code == "invalid_transition"
    assert e.value.details == {"from": "cancelled", "to": "cancelled"}

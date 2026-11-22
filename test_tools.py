"""Registry и проверка параметров: неизвестная операция и неверные параметры."""
import pytest

from autocheck.core.errors import UnknownCheck, ValidationError
from autocheck.core.registry import Registry
from autocheck.tools import SectionsTool, StructureTool


@pytest.fixture
def registry():
    r = Registry()
    r.register(StructureTool())
    r.register(SectionsTool())
    return r


def test_get_returns_tool_by_name(registry):
    assert registry.get("structure").name == "structure"
    assert registry.names() == ["sections", "structure"]


def test_unknown_check(registry):
    with pytest.raises(UnknownCheck) as e:
        registry.get("spellcheck")
    assert e.value.code == "unknown_check"
    assert e.value.details == {"check": "spellcheck"}


def test_unknown_check_in_request(registry):
    with pytest.raises(UnknownCheck):
        registry.validate_request(["structure", "spellcheck"], {"structure": {"root": "a/"}})


def test_duplicate_registration_rejected(registry):
    with pytest.raises(ValueError):
        registry.register(StructureTool())


@pytest.mark.parametrize(
    "checks, params, field",
    [
        ([], {}, "checks"),
        (["structure", "structure"], {"structure": {"root": "a/"}}, "checks"),
        (["structure"], {}, "params.structure.root"),
        (["structure"], {"structure": {"root": 5}}, "params.structure.root"),
        (["structure"], {"structure": {"root": "teams/emotion"}}, "params.structure.root"),
        (["structure"], {"structure": {"root": "/etc/"}}, "params.structure.root"),
        (["structure"], {"structure": {"root": "../"}}, "params.structure.root"),
        (["structure"], {"structure": {"root": "teams/../"}}, "params.structure.root"),
        (["structure"], {"structure": {"root": "a/", "deep": True}}, "params.structure.deep"),
        (["sections"], {"sections": {"template": "templates/p1.txt"}}, "params.sections.template"),
        (["structure"], {"structure": {"root": "a/"}, "sections": {}}, "params.sections"),
    ],
)
def test_invalid_params_report_field(registry, checks, params, field):
    with pytest.raises(ValidationError) as e:
        registry.validate_request(checks, params)
    assert e.value.code == "validation_error"
    assert e.value.details["field"] == field


def test_valid_request_passes(registry):
    registry.validate_request(
        ["structure", "sections"],
        {"structure": {"root": "teams/emotion/"}, "sections": {"template": "templates/p1.md"}},
    )

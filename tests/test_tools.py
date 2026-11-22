"""Tool structure и sections через общий контракт."""
from autocheck.core.memory import InMemorySource
from autocheck.core.tool import CheckContext, SourceUnavailable
from autocheck.tools import SectionsTool, StructureTool

TEMPLATE = "# Шаблон\n\n## Тема\n<!-- что делаете -->\n\n## Стек\n<!-- язык -->\n"


BASE = {"templates/p1.md": TEMPLATE}


def ctx(files, params, source=None):
    return CheckContext("org/repo", 1, "sha1", params, source or InMemorySource(files, BASE))


def test_structure_passed():
    r = StructureTool().run(ctx({"teams/emotion/p1.md": "x"}, {"root": "teams/emotion/"}))
    assert r.status == "passed" and r.problems == ()


def test_structure_failed_lists_every_outside_file():
    files = {"teams/emotion/p1.md": "x", "README.md": "x", "teams/other/p1.md": "x"}
    r = StructureTool().run(ctx(files, {"root": "teams/emotion/"}))
    assert r.status == "failed"
    assert [p.path for p in r.problems] == ["README.md", "teams/other/p1.md"]


def test_sections_passed():
    files = {"teams/emotion/p1.md": "## Тема\nAutoCheck\n## Стек\nPython\n"}
    r = SectionsTool().run(ctx(files, {"template": "templates/p1.md"}))
    assert r.status == "passed"


def test_sections_missing_and_empty():
    files = {"teams/emotion/p1.md": "## Тема\n<!-- пусто -->\n"}
    r = SectionsTool().run(ctx(files, {"template": "templates/p1.md"}))
    messages = {p.message for p in r.problems}
    assert r.status == "failed"
    assert messages == {"раздел «## Тема» пустой", "нет раздела «## Стек»"}


def test_sections_big_file_is_warning_not_failure():
    big = "## Тема\n" + "x" * (1024 * 1024 + 1)
    files = {"teams/emotion/big.md": big}
    r = SectionsTool().run(ctx(files, {"template": "templates/p1.md"}))
    assert r.status == "passed"
    assert r.problems[0].message == "файл больше 1 МБ, не проверяется"


class DownSource:
    def list_files(self):
        raise SourceUnavailable()

    def read_file(self, path):
        raise SourceUnavailable()


def test_source_unavailable_gives_error():
    for tool, params in [(StructureTool(), {"root": "a/"}), (SectionsTool(), {"template": "t.md"})]:
        r = tool.run(ctx({}, params, DownSource()))
        assert r.status == "error" and r.error_reason == "github_unavailable"


def test_pr_too_large_gives_error():
    files = {f"teams/emotion/{i}.md": "x" for i in range(301)}
    r = StructureTool().run(ctx(files, {"root": "teams/emotion/"}))
    assert r.status == "error" and r.error_reason == "pr_too_large"


def test_sections_missing_template_gives_error():
    r = SectionsTool().run(ctx({"teams/emotion/p1.md": "x"}, {"template": "templates/nope.md"}))
    assert r.status == "error"

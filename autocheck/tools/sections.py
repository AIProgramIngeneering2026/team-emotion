"""Tool sections: в каждом .md файле PR есть все разделы ## шаблона, и они не пустые."""
import re

from autocheck.core.tool import SOURCE_ERRORS, CheckContext, FileTooLarge, Problem, ToolResult

_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _sections(text: str) -> dict[str, bool]:
    result, current = {}, None
    for line in _COMMENT.sub("", text).splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            result[current] = False
        elif current and line.strip():
            result[current] = True
    return result


class SectionsTool:
    name = "sections"
    params_schema = {
        "type": "object",
        "required": ["template"],
        "additionalProperties": False,
        "properties": {"template": {"type": "string", "pattern": r".+\.md$"}},
    }

    def run(self, ctx: CheckContext) -> ToolResult:
        try:
            template = _sections(ctx.source.read_file(ctx.params["template"]))
            files = [f for f in ctx.source.list_files() if f.path.endswith(".md") and f.status != "removed"]
        except KeyError:
            return ToolResult.error("bad_github_response")
        except SOURCE_ERRORS as e:
            return ToolResult.error(e.reason)

        problems, warnings = [], []
        for f in files:
            try:
                filled = _sections(ctx.source.read_file(f.path))
            except FileTooLarge:
                warnings.append(Problem("файл больше 1 МБ, не проверяется", f.path))
                continue
            except SOURCE_ERRORS as e:
                return ToolResult.error(e.reason)
            for heading in template:
                if heading not in filled:
                    problems.append(Problem(f"нет раздела «## {heading}»", f.path))
                elif not filled[heading]:
                    problems.append(Problem(f"раздел «## {heading}» пустой", f.path))
        if problems:
            return ToolResult.failed(*problems, *warnings)
        return ToolResult("passed", tuple(warnings))

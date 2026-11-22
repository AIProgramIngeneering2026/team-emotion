"""Tool structure: все файлы PR лежат внутри root."""
from autocheck.core.tool import SOURCE_ERRORS, CheckContext, Problem, ToolResult


class StructureTool:
    name = "structure"
    params_schema = {
        "type": "object",
        "required": ["root"],
        "additionalProperties": False,
        # root заканчивается на /, не начинается с /, не содержит сегмента ..
        "properties": {"root": {"type": "string", "pattern": r"^(?!/)(?!.*(^|/)\.\.(/|$)).+/$"}},
    }

    def run(self, ctx: CheckContext) -> ToolResult:
        root = ctx.params["root"]
        try:
            files = ctx.source.list_files()
        except SOURCE_ERRORS as e:
            return ToolResult.error(e.reason)
        problems = [Problem("файл вне вашей папки", f.path) for f in files if not f.path.startswith(root)]
        return ToolResult.failed(*problems) if problems else ToolResult.passed()

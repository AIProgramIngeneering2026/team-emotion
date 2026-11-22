"""Ядро не зависит от веб-фреймворка и драйвера БД."""
import ast
import pathlib

FORBIDDEN = {"fastapi", "starlette", "flask", "django", "sqlalchemy", "sqlite3", "psycopg", "psycopg2", "alembic", "httpx", "requests"}
ROOT = pathlib.Path(__file__).resolve().parent.parent / "autocheck"


def test_core_and_tools_import_nothing_forbidden():
    for path in [*ROOT.joinpath("core").rglob("*.py"), *ROOT.joinpath("tools").rglob("*.py")]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            for n in names:
                assert n.split(".")[0] not in FORBIDDEN, f"{path.name} импортирует {n}"

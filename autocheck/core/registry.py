"""Registry: имя проверки → Tool. Знает про конкретные Tool только через регистрацию."""
from __future__ import annotations

from .errors import UnknownCheck, ValidationError
from .params import validate
from .tool import Tool


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name} уже зарегистрирован")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise UnknownCheck(f"Неизвестная проверка: {name}", check=name) from None

    def names(self) -> list[str]:
        return sorted(self._tools)

    def validate_request(self, checks: list[str], params: dict) -> None:
        """Проверка до создания Проверки: имена есть в реестре, параметры подходят под схему.
        По контракту параметры проверяет вызывающий, а не Tool."""
        if not checks:
            raise ValidationError("checks: нужен хотя бы один элемент", field="checks")
        if len(set(checks)) != len(checks):
            raise ValidationError("checks: повторяющиеся имена", field="checks")
        for name in checks:
            self.get(name)
        for name in params:
            if name not in checks:
                raise ValidationError(f"params.{name}: такой проверки нет в checks", field=f"params.{name}")
        for name in checks:
            validate(params.get(name, {}), self.get(name).params_schema, f"params.{name}")

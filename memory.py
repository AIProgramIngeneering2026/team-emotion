"""Проверка параметров Tool по params_schema. Минимальное подмножество JSON Schema, без внешних библиотек."""
from __future__ import annotations

import re

from .errors import ValidationError

_TYPES = {"string": str, "object": dict, "integer": int, "boolean": bool}


def validate(value, schema: dict, path: str) -> None:
    expected = schema.get("type")
    if expected:
        py_type = _TYPES[expected]
        if not isinstance(value, py_type) or (expected == "integer" and isinstance(value, bool)):
            raise ValidationError(f"{path}: ожидается {expected}", field=path)
    if expected == "object":
        props = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                raise ValidationError(f"{path}.{name}: обязательное поле", field=f"{path}.{name}")
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(props))
            if extra:
                raise ValidationError(f"{path}.{extra[0]}: неизвестное поле", field=f"{path}.{extra[0]}")
        for name, sub in props.items():
            if name in value:
                validate(value[name], sub, f"{path}.{name}")
    if expected == "string" and "pattern" in schema and not re.search(schema["pattern"], value):
        raise ValidationError(f"{path}: недопустимое значение", field=path)

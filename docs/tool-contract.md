# Контракт исполнителя (Tool)

Tool — одна формальная проверка PR. Dispatcher вызывает все Tool одинаково и не знает, что внутри.

## Интерфейс

```python
from dataclasses import dataclass, field
from typing import Literal, Protocol


@dataclass(frozen=True)
class PRFile:
    path: str
    status: Literal["added", "modified", "removed", "renamed"]


class PullRequestSource(Protocol):
    """Источник данных PR. Реализует GitHubAdapter, в тестах — fake."""

    def list_files(self) -> list[PRFile]: ...
    def read_file(self, path: str) -> str: ...


@dataclass(frozen=True)
class CheckContext:
    repo: str                  # owner/name
    pr_number: int
    head_sha: str              # коммит PR, зафиксированный при старте Проверки
    params: dict               # уже проверены по params_schema
    source: PullRequestSource


@dataclass(frozen=True)
class Problem:
    message: str
    path: str | None = None


@dataclass(frozen=True)
class ToolResult:
    status: Literal["passed", "failed", "error"]
    problems: list[Problem] = field(default_factory=list)
    error_reason: str | None = None


class Tool(Protocol):
    name: str                  # уникальное имя в Registry
    params_schema: dict        # JSON Schema параметров

    def run(self, ctx: CheckContext) -> ToolResult: ...
```

## Что Tool получает

- `CheckContext`: репозиторий, номер PR, параметры и `PullRequestSource` для чтения файлов
- Tool не ходит в сеть сам и не знает про GitHub API: только через `PullRequestSource`
- Все Tool одной Проверки читают файлы одного коммита `head_sha`. Если студент запушил новый коммит во время Проверки, она всё равно проверяет тот коммит, с которого начала

## Ограничения входа

| Что | Предел | Что будет |
|---|---|---|
| Файлов в PR | 300 | `PullRequestSource` бросает `PullRequestTooLarge`, Tool возвращает `error` с причиной `pr_too_large`. Tool не запускаются на неполном списке |
| Размер одного файла | 1 МБ | `read_file` бросает `FileTooLarge`, `sections` добавляет `Problem(path, "файл больше 1 МБ, не проверяется")` и продолжает с остальными файлами |

## Что Tool возвращает

| Статус | Когда | `problems` | `error_reason` |
|---|---|---|---|
| `passed` | Нарушений нет | пусто | нет |
| `failed` | Работа нарушает правило | список: файл и описание | нет |
| `error` | Проверку выполнить не удалось | пусто | `github_unavailable`, `pr_not_found`, `bad_github_response`, `pr_too_large` |

## Какими ошибками отказывает

- Нарушение правил в работе — это не ошибка Tool, а `failed`
- Сбой источника данных: `PullRequestSource` бросает `SourceUnavailable`, `PullRequestNotFound`, `BadSourceResponse` или `PullRequestTooLarge`. Tool перехватывает их и возвращает `error` с соответствующей причиной
- Что считается сбоем, решает GitHubAdapter, а не Tool:
  - нет ответа за 5 секунд или ответ `5xx` — до 3 попыток, потом `SourceUnavailable`
  - `404` — без повторов, `PullRequestNotFound`
  - тело не JSON или в нём нет обязательных полей, например GitHub переименовал `filename` — без повторов, `BadSourceResponse`
  - `403` с исчерпанным лимитом запросов — без ожидания сброса лимита, `SourceUnavailable`
- Любое другое исключение из `run` перехватывает Dispatcher и записывает `error` с причиной `tool_error`. Остальные Tool продолжают выполняться

## Кто проверяет параметры

Вызывающий. Имя проверки и параметры проверяются в CheckService **до создания Проверки**:
- имени нет в Registry → `400 unknown_check`
- параметры не подходят под `params_schema` → `400 validation_error`, в `details.field` путь, например `params.structure.root`

Поэтому внутри `run` параметры уже корректны, Tool их повторно не проверяет.

## Tool 1: `structure`

Проверяет, что PR меняет файлы только в разрешённой папке.

| Поле | Значение |
|---|---|
| `name` | `structure` |
| `params_schema` | `{"type": "object", "required": ["root"], "properties": {"root": {"type": "string", "pattern": "^(?!.*(?:^|/)\\.\\.(?:/|$))[^/].*/$"}}}` |
| Читает | `list_files()` |
| `passed` | Все пути начинаются с `root` |
| `failed` | Для каждого файла вне `root`: `Problem(path, "файл вне вашей папки")` |
| `error` | Источник недоступен или PR не найден |

Пример: `root = "teams/emotion/"`, в PR есть `README.md` → `failed`, проблема `README.md: файл вне вашей папки`.

## Tool 2: `sections`

Проверяет, что в каждом Markdown-файле PR есть все разделы `## ...` шаблона и они не пустые.

| Поле | Значение |
|---|---|
| `name` | `sections` |
| `params_schema` | `{"type": "object", "required": ["template"], "properties": {"template": {"type": "string"}}}` — путь к шаблону в том же репозитории |
| Читает | `list_files()`, `read_file()` для каждого `.md` и для шаблона |
| `passed` | Все разделы шаблона есть и в каждом есть текст, комментарии `<!-- -->` не считаются |
| `failed` | `Problem(path, "нет раздела «## Тема»")` или `Problem(path, "раздел «## Тема» пустой")` |
| `error` | Источник недоступен, PR не найден или шаблон не удалось прочитать |

## Как добавить новый Tool

1. Написать класс с `name`, `params_schema` и `run`.
2. Зарегистрировать его в Registry.
3. Dispatcher, API и хранилище не меняются. Так же во втором семестре добавится `llm_review`.

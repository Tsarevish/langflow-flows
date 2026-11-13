# Инструменты и их поведение

Что реально умеет официальный MCP-сервер Langflow (`/api/v1/agentic/mcp`).
Наблюдалось на Langflow 1.12.2, сервер `langflow-mcp 1.28.1`, 31 инструмент.

## Сборка

| Инструмент | Что делает | Замечания |
|---|---|---|
| `create_flow_from_spec` | создаёт флоу из спеки | `validate: true` по умолчанию; при ошибке флоу **не создаётся** |
| `update_flow_from_spec` | заменяет узлы/связи существующего флоу | сохраняет `flow_id`; перезаписывает целиком |
| `add_component` / `remove_component` | точечная правка | после — `layout_flow` |
| `configure_component` | меняет поля узла | **портит привязку переменных**, см. ниже |
| `connect_components` / `disconnect_components` | правка связей | тип соединения проверяется |
| `layout_flow` | раскладка по Sugiyama | идемпотентен на простых схемах |
| `duplicate_flow` / `rename_flow` / `delete_flow` | управление | |

## Разведка

| Инструмент | Что даёт |
|---|---|
| `search_component_types` | поиск по имени/категории/типу выхода; без аргументов — всё |
| `describe_component_type` | `inputs` (соединяемые), `outputs`, `fields`, `advanced_fields` |
| `components` | поиск и описание одним вызовом |
| `list_components` | узлы внутри флоу с их id |
| `get_component_info` | текущие значения полей конкретного узла |
| `get_flow_info` | состав флоу + ASCII-диаграмма |
| `list_flows` | список флоу, у каждого ASCII-диаграмма |
| `export_flow` | полный JSON (секреты вырезаны) |

## Проверка и запуск

| Инструмент | Правда о поведении |
|---|---|
| `run_flow` | запускает; при падении возвращает буквально `False` — без причины |
| `validate_flow` | `{"valid": bool, "errors": [{component_id, error}]}`; подробность зависит от версии: на 1.13 называет узел и причину, на 1.12 — общее `Build error` |
| `build_flow` | запускает серверную сборку, отдаёт `job_id` |
| `get_build_results` | что реально собралось: по узлам `valid` + вывод |
| `get_component_output` | вывод конкретного узла после прогона |

**Вывод для практики:** смотри версию в профиле. На 1.13 начни с `validate_flow` —
он может сразу сказать «`OPENAI_API_KEY variable not found`». На 1.12 причину даёт
только build-стрим (см. `errors.md`).

## Прочее

`list_starter_projects` / `use_starter_project` — готовые флоу как отправная точка.
`freeze_component` / `unfreeze_component` — кэшировать выход узла, чтобы не гонять дорогой
шаг при отладке следующего.
`notify_done` — обязательный финальный вызов: без него UI не перерисуется.
`batch` — несколько действий за раз, ссылки `$1.field` на результат предыдущего шага.

## `configure_component`: главная ловушка

Поле, привязанное к переменной (у модели `api_key`), выглядит так:

```
value: "OPENAI_API_KEY", load_from_db: true
```

Вызов `configure_component({"api_key": "OPENAI_API_KEY"})` записывает **строку** и ставит
`load_from_db: false`. Модель начинает получать в качестве ключа текст `OPENAI_API_KEY`:

```
AuthenticationError — rpc error: code = Unauthenticated desc = Unknown api key 'OPEN****_KEY'
```

Правила:

1. Поля-переменные не трогать. У нового компонента привязка уже стоит.
2. Нужно поменять значение переменной — менять переменную, не поле.
3. Привязка уже сломана — вернуть `load_from_db: true` через `PUT /api/v1/flows/{id}`
   с полным `data`.

## `tweaks` в `run_flow`

Позволяет подменить поле на время запуска, не меняя флоу:
`{"SQLComponent-abc": {"database_url": "..."}}`.

Но защищённые поля отклоняются:

```
Refused tweak keys ['database_url']: The field is protected and keeps the value set by the flow author.
```

Значит `tweaks` — для экспериментов с моделью/промптом, не для секретов.

## Ограничения прав

Не суперюзер может: создавать/читать/удалять свои флоу, читать `/api/v1/variables/`,
`/api/v1/models`, `/api/v1/all`. Кастомные компоненты зависят от `allow_custom_components`
на инстансе и от роли — проверяй фактом, а не предположением.

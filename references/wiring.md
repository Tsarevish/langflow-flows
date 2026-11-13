# Соединения: правила и типы

## Как читать соединение

```
A.message -> B.input_value
 ↑    ↑         ↑     ↑
 id  выход     id    вход
```

Соединять можно **выход** с **входом**. Поля (`fields`) — это конфигурация, не порты:
`model_name` нельзя «соединить», его можно только задать.

## Типы

Каждый выход объявляет типы (`Message`, `Data`, `JSON`, `Table`, `DataFrame`, `Tool`,
`model`), каждый вход — допустимые типы (`input_types`).

Правило: тип выхода должен входить в `input_types` входа. Практически:

| Выход | Куда идёт |
|---|---|
| `message` (ChatInput, ChatOutput) | `input_value`, `system_prompt`, `input_text`, `query` |
| `prompt` (Prompt Template) | `input_value` модели, `system_prompt` агента |
| `model_output` (модель) | `model` агента |
| `text_output` (модель) | `input_value` промпта/выхода |
| `component_as_tool` | `tools` агента |
| `response` (Agent) | `input_value`, `input_text`, `query` |
| `run_sql_query` (Table) | `input_value` ChatOutput (принимает Table), `input_data` конвертера |

`ChatOutput.input_value` принимает почти всё (Data, JSON, DataFrame, Table, Message) —
он удобен как «универсальный сток», но не как промежуточный узел.

## Специальные приёмы

**Промпт → агент.** `Prompt.prompt -> Agent.system_prompt`. Промпт-узел удобен тем, что
его текст можно править и версионировать отдельно от агента.

**Модель → агент.** `Model.model_output -> Agent.model`. Не `text_output`: агент ждёт
объект модели, а не текст.

**Инструменты.** У любого компонента есть выход `component_as_tool`, если он поддерживает
tool_mode. Соединяется в `Agent.tools`; несколько инструментов — несколько связей в тот же вход.
Входы с `tool_mode: true` становятся параметрами, которые модель заполняет при вызове;
остальные поля остаются статической настройкой.

**Ветвление.** У `ConditionalRouter` два выхода: `true_result`, `false_result`.
Оба надо куда-то привести, иначе ветка молча исчезнет из результата. Если «нет» —
это просто ответ пользователю, поставь `ChatOutput`.

**Таблица → текст.** `Table` не пролезет туда, где ждут `Message`. Мост —
`TypeConverterComponent` (`dataframe_output` / `message_output`) или `ParserComponent`.

## Чего не соединять

- два «источника» в один вход без merge-узла: победит один, второй потеряется молча;
- `model` в `input_value` (это объект модели, не текст);
- `prompt` в `ChatOutput` напрямую, если нужен финальный текст ответа модели;
- выход, тип которого не заявлен во `input_types` — сборка пройдёт, запуск упадёт.

## Самопроверка после соединений

1. У каждого узла, кроме входов, есть входящая связь? У каждого выхода, кроме выходов, —
   исходящая?
2. `Agent` без `model` — ошибка сборки, а не пустой ответ.
3. У `ConditionalRouter` оба выхода подключены?
4. Нет ли цикла, который не ограничен `max_iterations`?
5. `ChatOutput` в конце — есть? Без него Playground покажет пустоту.

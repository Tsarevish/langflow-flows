# Компоненты: карта и порты

Справочник «что взять» и «куда соединять». Каждый факт ниже проверен на инстансе
Langflow 1.12.2. Перед использованием спорного узла — `describe_component_type`.

## Категории (`/api/v1/all`)

`input_output`, `models_and_agents`, `llm_operations`, `processing`, `agents`,
`flow_controls`, `tools`, `embeddings`, `data_source`, `files_and_knowledge`,
`files_ingestion`, `prototype`, `langchain_utilities`, `crewai`, `custom_component`.

## Входы и выходы

| Тип | Выходы | Входы |
|---|---|---|
| `ChatInput` | `message` | — |
| `ChatOutput` | `message` | `input_value` (Data, JSON, DataFrame, Table, Message) |
| `TextInput` | `text` | — |

`ChatInput.input_value` — поле, а не вход: это текст по умолчанию для Playground.

## Промпты и модели

| Тип | Выходы | Входы | Поля |
|---|---|---|---|
| `Prompt Template` | `prompt`, `component_as_tool` | **нет** (появляются из `{переменных}`) | `template` |
| `ext:openai:OpenAIModelComponent@official` | `text_output`, `model_output`, `component_as_tool` | `input_value` | `model_name`, `openai_api_base`, `temperature`, `max_tokens`, `api_key` |

**`Prompt Template` — главная тонкость.** В описании типа `inputs: []`. Вход создаётся
переменной в шаблоне:

```
config:
  P.template: |
    Ответь на вопрос: {question}
```

после этого появляется порт `question`, и работает `A.message -> P.question`.
Имя порта — ровно имя переменной, регистр значим.

Занятые имена переменных: `status`, `code`, `template`, `template_format`,
`input_variables`, `output_parser`, `partial_variables`, `validate_template`.
Имя без пробелов и знаков препинания, не с цифры и не с подчёркивания.
JSON с фигурными скобками в промпте создаёт лишние переменные — включай `use_double_brackets`.

Двойные фигурные скобки включаются полем `use_double_brackets` — по умолчанию `false`,
то есть `{x}` в шаблоне считается переменной.

## Агент

| Тип | Выходы | Входы |
|---|---|---|
| `Agent` | `response`, `structured_response`, `component_as_tool` | `input_value`, `model` (обязателен), `system_prompt`, `tools` |

Минимальный агент — четыре узла вокруг него: вход, промпт (в `system_prompt`),
модель (в `model`), выход. `tools` заполняется выходами `component_as_tool`.

Полезные поля: `max_iterations` (**по умолчанию 15**, на лимите ответ
`Model call limits exceeded: run limit (15/15)`), `handle_parsing_errors`,
`n_messages` (память диалога).

Инструменты «калькулятор» и «текущая дата» у агента есть всегда, даже при пустом `tools`.
Без подключённой модели — `No model selected. Please select a language model…`.

## Ветвление

| Тип | Выходы | Входы | Поля |
|---|---|---|---|
| `ConditionalRouter` | `true_result`, `false_result` | `input_text`, `match_text` | `operator`, `case_sensitive`, `default_route` |

`operator`: `equals`, `not equals`, `contains`, `starts with`, `ends with`, `regex`,
`less than`, `greater than` и варианты «or equal».
`match_text` — тоже **вход** (можно подставить из другого узла), а не только поле.

## Данные и БД

| Тип | Выходы | Входы | Замечания |
|---|---|---|---|
| `SQLComponent` | `run_sql_query` (Table), `component_as_tool` | `database_url`, `query` | `database_url` — защищённое поле, только в флоу |
| `TypeConverterComponent` | `message_output`, `data_output`, `dataframe_output` | `input_data` | мост между Message / JSON / Table |
| `ParserComponent` | `parsed_text` | `input_data` | шаблон `{result}` |
| `Operations` | `message_output` | много (`text_input`, `data`, `df`…) | `operation` — список, в спеке не задаётся |
| `PythonREPLComponent` | `results` | — | `global_imports` + `python_code` |

Связка «таблица → текст» почти всегда требует `TypeConverterComponent`:
`Table` не входит туда, где ждут `Message`.

## Файлы

`File` — читает файл, выход `message`. `SaveToFile` / `SaveExcelWithStyle` — запись.
Файловые узлы зависят от загруженных в сессию файлов: при сборке через API их надо
загружать отдельно, иначе узел пуст.

## Управление потоком и обработка

| Тип | Выходы | Входы | Главное |
|---|---|---|---|
| `LoopComponent` | `item`, `done` | `data` + порт `∞` (возврат тела) | цикл по строкам; без связи в `∞` тело не запустится |
| `HumanInput` | по варианту решения (`branch_approve`, `branch_reject`) | `prompt` | пауза; внутри `RunFlow` не работает |
| `SmartRouter` | по одному на категорию + `else_result` | `input_text`, `model` | категории из `routes`, каждый запуск — запрос к модели |
| `StructuredOutput` | `structured_output`, `dataframe_output` | `input_value`, `model`, `output_schema` | несколько объектов → поле `results`, нужен выход Table |
| `BatchRunComponent` | `batch_results` | `df`, `model` | модель по строкам параллельно; сбой строки рушит весь блок |
| `Memory` | `messages_text`, `dataframe` | `message` | `Retrieve` отдаёт историю «Имя: сообщение» |
| `RunFlow` | по выходам подпотока | по входам подпотока | Beta; после импорта поток выбирать заново |
| `ParserComponent` | `parsed_text` | `input_data` | данные → текст по шаблону `{поле}` |
| `APIRequest` | `data` | — | ответ в `result`, ошибка не останавливает поток |
| `UnifiedWebSearch` | `results` | `query` | Web / News / RSS |
| `File` | `message`, `dataframe` | — | после импорта файл выбирать заново |

Подробности и точные тексты ошибок по каждому — `guide.md`.

## Компоненты расширений

Тип вида `ext:<вендор>:<Класс>@official` — это компонент расширения (например провайдеры
моделей). Правила те же, но:

- имя нельзя сокращать: `OpenAIModelComponent` не найдётся, нужно полное;
- набор таких компонентов зависит от установленных расширений, поэтому «есть в доках» ≠
  «есть на инстансе». Проверяй `search_component_types`.

## Кастомные компоненты

Свой компонент — это код Python, а не декларация. В спеку он не входит: создаётся
отдельным путём (кастомный компонент в UI или через соответствующий API).
В эталонном флоу владельца три таких компонента (`SQLCodeCleaner`, `SQLResultChecker`,
`SaveExcelWithStyle`) — то есть путь рабочий, но проверять права нужно заранее.

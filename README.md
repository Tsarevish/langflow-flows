# langflow-flows

Скилл для агента: собирает, правит и диагностирует цепочки (флоу) в [Langflow](https://www.langflow.org).

Не «сгенерировать JSON, который выглядит как флоу», а собрать граф, который запускается
и отвечает. Скилл задаёт порядок работы и хранит проверенные знания о Langflow, а всё
зависящее от конкретной установки — версию, провайдеров, модель, лимиты — снимает
в отдельный профиль стенда.

## Зачем

Langflow уже даёт агенту инструменты через встроенный MCP-сервер (`/api/v1/agentic/mcp`):
`create_flow_from_spec`, `describe_component_type`, `validate_flow`, `run_flow`, `layout_flow`.
Не хватает не «рук», а «головы»:

- агент пишет имена типов и портов по памяти — и падает на этом;
- строит сразу «полный» флоу с RAG, памятью и четырьмя инструментами;
- получает от инструментов `False` вместо причины падения;
- не знает, что у модели два разных выхода, и подключает не тот.

Скилл закрывает это: гейты, диагностика по build-стриму, каталог ловушек и профиль стенда.

## Что внутри

```
SKILL.md                  правила: профиль, 7 шагов с гейтами, 8 ловушек
references/
  recon.md                как снять профиль нового стенда
  spec-format.md          грамматика компактной спеки
  tools.md                поведение MCP-инструментов
  workflow.md             процесс подробно, шаблоны отчётов
  components.md           карта компонентов и портов
  wiring.md               правила соединений
  patterns.md             типовые цепочки
  errors.md               диагностика: где искать настоящую причину
  versions.md             что меняется между версиями Langflow
  guide.md                словарь курса и точные тексты ошибок (материалы курса)
  course-flows.md         41 схема соединений (материалы курса)
examples/                 три проверенные спеки
scripts/
  probe_stand.py          снять профиль стенда + снапшот схем
  validate_spec.py        офлайн-проверка спеки
  dump_schema.py          только снапшот схем
  install.ps1             установка в DSH (Windows)
  install.sh              установка в DSH (macOS / Linux)
tests/                    регрессионные тесты валидатора
VERIFICATION.md           что проверено и что нет
NOTICE.md                 источники и права на материалы курса
```

## Установка

### DSH (DeepSeek Harness)

DSH находит скиллы в файловой системе: каталог `<dshHome>/skills/<имя>/SKILL.md`.

```
git clone <этот репозиторий>
cd langflow-flows
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
```

Скрипт кладёт скилл в `%USERPROFILE%\.dsh\skills\langflow-flows`. Другой путь — параметр
`-Target`. Обновление после `git pull` — тем же скриптом.

### Другие агенты (Claude Code, Claude Desktop, Codex)

Скилл — обычный `SKILL.md` с подкаталогами:

```
cp -r . ~/.claude/skills/langflow-flows      # macOS / Linux
xcopy . %USERPROFILE%\.claude\skills\langflow-flows /E /I   # Windows
```

## Подключение Langflow

Нужен запущенный Langflow и API-ключ (интерфейс → аватар → Settings → Langflow API → Add New).

### 1. Профиль стенда

```
python scripts/probe_stand.py --url http://localhost:7860 --key sk-...
```

Создаст `profiles/stand-<host>/`:

| Файл | Что внутри |
|---|---|
| `profile.md` | версия, доступ, провайдеры, MCP, ограничения |
| `profile.json` | то же машинно |
| `components.json` | снапшот схем компонентов этой версии |

Разделы «Ограничения» и «Особенности» скрипт заполнить не может — там лимит времени
запуска, параллельность запросов, политика записи файлов, читаемые форматы. Их уточняют
у эксплуатации или проверяют опытом: рецепты в `references/recon.md`.

### 2. MCP-сервер в DSH

Встроенный сервер Langflow отдаёт те же инструменты по адресу `/api/v1/agentic/mcp`.
Строка для `cordis.patch.yml` профиля DSH:

```yaml
- insert:
    - id: langflow-mcp
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: langflow
        transport: streamable-http
        url: 'http://127.0.0.1:7860/api/v1/agentic/mcp'
        headers:
          x-api-key: '<ключ>'
        failOnStartupError: false
        toolCallTimeoutMs: 180000
```

После этого у агента появляются инструменты `mcp__langflow__*`.

## Проверка

```
python scripts/validate_spec.py examples/03-agent-sql.spec
python tests/run_tests.py
```

Валидатор проверяет спеку без обращения к серверу: неизвестные типы, несуществующие порты,
несовпадение переменных промпта, секреты в полях-переменных, неподключённые ветки.
Коды и расшифровка — в `SKILL.md`. Снапшот берётся из профиля; при нескольких профилях
укажи `--profile` или `LANGFLOW_PROFILE`.

## Как это проверялось

Два стенда: Langflow 1.12.2 (сервер) и 1.13.0 (локальный Desktop). 12 сценариев сборки
прошли с первого прохода, вердикты валидатора сверены с ответами сервера, поведение
на двух версиях сравнено. Подробности и честный список непроверенного — в
[VERIFICATION.md](VERIFICATION.md).

## Лицензия

MIT — см. [LICENSE](LICENSE).

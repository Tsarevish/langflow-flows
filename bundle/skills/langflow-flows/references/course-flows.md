# Связки курса: узлы и связи

41 флоу из учебного гайда, разобранные по узлам и связям. Ключи (a1, b2, c1…) совпадают
с индексом в guide.md. Используй как образец соединений: здесь видно, какой выход
в какой вход идёт в проверенной авторской схеме.

# Флоу из гайда: состав и связи


## a1 — 01 Запрос к модели
- `In` — ChatInput (Обращение)
- `P` — Prompt Template (Промпт: тема)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `Out` — ChatOutput (Ответ)
- In.message → P.obrashchenie
- P.prompt → M.input_value
- M.text_output → Out.input_value

## a2 — 02 Цепочка шагов
- `In` — ChatInput (Обращение)
- `P1` — Prompt Template (Промпт: тема)
- `M1` — ext:openai:OpenAIModelComponent@official (Модель: тема)
- `P2` — Prompt Template (Промпт: черновик)
- `M2` — ext:openai:OpenAIModelComponent@official (Модель: черновик)
- `Out` — ChatOutput (Ответ)
- In.message → P1.obrashchenie
- P1.prompt → M1.input_value
- M1.text_output → P2.tema
- In.message → P2.obrashchenie
- P2.prompt → M2.input_value
- M2.text_output → Out.input_value

## b1 — 03 Развилка по правилу
- `In` — ChatInput (Обращение)
- `IF` — ConditionalRouter (Есть контакт?)
- `P` — Prompt Template (Промпт: черновик)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `Out` — ChatOutput (Черновик)
- `Out2` — ChatOutput (Специалисту)
- In.message → IF.input_text
- IF.true_result → P.tekst
- P.prompt → M.input_value
- M.text_output → Out.input_value
- IF.false_result → Out2.input_value

## b2 — 04 Развилка по теме
- `In` — ChatInput (Обращение)
- `LM` — ext:openai:OpenAIModelComponent@official (Модель для блока)
- `SR` — SmartRouter (Развилка по теме)
- `Out1` — ChatOutput (Ветка «срок»)
- `Out2` — ChatOutput (Ветка «документы»)
- In.message → SR.input_text
- LM.model_output → SR.model
- SR.category_1_result → Out1.input_value
- SR.category_2_result → Out2.input_value

## b3 — 05 Подтверждение человеком
- `In` — ChatInput (Обращение)
- `P` — Prompt Template (Промпт: черновик)
- `M` — ext:openai:OpenAIModelComponent@official (Модель: черновик)
- `H` — HumanInput (Подтверждение специалиста)
- `Out` — ChatOutput (Ответ заявителю)
- `Out2` — ChatOutput (На доработку)
- In.message → P.t
- P.prompt → M.input_value
- M.text_output → H.prompt
- H.branch_approve → Out.input_value
- H.branch_reject → Out2.input_value

## b4 — 06 Ветка «нет ответа»
- `In` — ChatInput (Вопрос)
- `P` — Prompt Template (Промпт: ответ по регламенту)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `IF` — ConditionalRouter (Ответ есть?)
- `Out2` — ChatOutput (Специалисту)
- `Out` — ChatOutput (Ответ)
- In.message → P.vopros
- P.prompt → M.input_value
- M.text_output → IF.input_text
- IF.true_result → Out2.input_value
- IF.false_result → Out.input_value

## c1 — 07 Цикл по списку
- `In` — ChatInput (Список обращений)
- `SP` — SplitText (Разбить по строкам)
- `L` — LoopComponent (Цикл)
- `PA` — ParserComponent (Текст строки)
- `PT` — Prompt Template (Промпт: тема)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `PD` — ParserComponent (Собрать результат)
- `Out` — ChatOutput (Ответ)
- In.message → SP.data_inputs
- SP.dataframe → L.data
- L.item → PA.input_data
- PA.parsed_text → PT.stroka
- PT.prompt → M.input_value
- M.text_output → L.None
- L.done → PD.input_data
- PD.parsed_text → Out.input_value

## c2 — 08 Цикл с возвратом
- `In` — ChatInput (Задание)
- `RP` — CustomComponent (Точка возврата)
- `PW` — Prompt Template (Промпт: написать)
- `MW` — ext:openai:OpenAIModelComponent@official (Модель: пишет)
- `PR` — Prompt Template (Промпт: проверить)
- `MR` — ext:openai:OpenAIModelComponent@official (Модель: проверяет)
- `IF` — ConditionalRouter (Готово?)
- `IF2` — ConditionalRouter (Есть текст?)
- `Out` — ChatOutput (Ответ)
- `Out2` — ChatOutput (Специалисту)
- In.message → RP.vhod
- RP.dalshe → PW.zadanie
- PW.prompt → MW.input_value
- MW.text_output → PR.tekst
- PR.prompt → MR.input_value
- MR.text_output → IF.input_text
- MW.text_output → IF.true_case_message
- IF.true_result → IF2.input_text
- IF2.true_result → Out.input_value
- IF2.false_result → Out2.input_value
- IF.false_result → RP.None

## c3 — 09 Ведёт до данных
- `In` — ChatInput (Сообщение)
- `Mem` — Memory (Память диалога)
- `P` — Prompt Template (Промпт: уточнить)
- `M` — ext:openai:OpenAIModelComponent@official (Модель: уточняет)
- `IF` — ConditionalRouter (Всё известно?)
- `Q` — ChatOutput (Вопрос пользователю)
- `P1` — Prompt Template (Промпт: написать SQL)
- `M1` — ext:openai:OpenAIModelComponent@official (Модель: SQL)
- `SQL` — CustomComponent (Выполнить SQL)
- `P2` — Prompt Template (Промпт: описать)
- `M2` — ext:openai:OpenAIModelComponent@official (Модель: ответ)
- `Out` — ChatOutput (Ответ с данными)
- Mem.messages_text → P.history
- P.prompt → M.system_message
- In.message → M.input_value
- M.text_output → IF.input_text
- IF.false_result → Q.input_value
- IF.true_result → P1.zapros
- P1.prompt → M1.input_value
- M1.text_output → SQL.sql
- SQL.table → P2.rez
- P2.prompt → M2.input_value
- M2.text_output → Out.input_value

## d1 — 10 Диалог с памятью
- `In` — ChatInput (Сообщение)
- `Mem` — Memory (Память диалога)
- `P` — Prompt Template (Системный промпт)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `Out` — ChatOutput (Ответ)
- Mem.messages_text → P.history
- P.prompt → M.system_message
- In.message → M.input_value
- M.text_output → Out.input_value

## d2 — 11 Агент
- `In` — ChatInput (Сообщение)
- `LM` — ext:openai:OpenAIModelComponent@official (Модель для блока)
- `A` — Agent (Агент)
- `Out` — ChatOutput (Ответ)
- In.message → A.input_value
- LM.model_output → A.model
- A.response → Out.input_value

## d3 — 12 Агент с инструментом
- `In` — ChatInput (Сообщение)
- `LM` — ext:openai:OpenAIModelComponent@official (Модель для блока)
- `T` — APIRequest (Курсы ЦБ (инструмент))
- `A` — Agent (Агент)
- `Out` — ChatOutput (Ответ)
- In.message → A.input_value
- LM.model_output → A.model
- T.component_as_tool → A.tools
- A.response → Out.input_value

## d4 — 13 Агент и MCP
- `In` — ChatInput (Сообщение)
- `LM` — ext:openai:OpenAIModelComponent@official (Модель для блока)
- `T` — MCPTools (MCP: DeepWiki)
- `A` — Agent (Агент)
- `Out` — ChatOutput (Ответ)
- In.message → A.input_value
- LM.model_output → A.model
- T.component_as_tool → A.tools
- A.response → Out.input_value

## e1 — 14 Извлечение полей
- `In` — ChatInput (Письмо)
- `LM` — ext:openai:OpenAIModelComponent@official (Модель для блока)
- `SO` — StructuredOutput (Извлечь поля)
- `PA` — ParserComponent (В текст)
- `Out` — ChatOutput (Карточка)
- In.message → SO.input_value
- LM.model_output → SO.model
- SO.structured_output → PA.input_data
- PA.parsed_text → Out.input_value

## e2 — 15 Таблица построчно
- `In` — ChatInput (Таблица CSV)
- `TC` — TypeConverterComponent (В таблицу)
- `LM` — ext:openai:OpenAIModelComponent@official (Модель для блока)
- `BR` — BatchRunComponent (Модель по строкам)
- `PA` — ParserComponent (В текст)
- `Out` — ChatOutput (Ответ)
- In.message → TC.input_data
- TC.dataframe_output → BR.df
- LM.model_output → BR.model
- BR.batch_results → PA.input_data
- PA.parsed_text → Out.input_value

## e3 — 16 Запрос к базе SQL
- `In` — ChatInput (Вопрос)
- `P1` — Prompt Template (Промпт: написать SQL)
- `M1` — ext:openai:OpenAIModelComponent@official (Модель: SQL)
- `SQL` — CustomComponent (Выполнить SQL)
- `P2` — Prompt Template (Промпт: описать)
- `M2` — ext:openai:OpenAIModelComponent@official (Модель: ответ)
- `Out` — ChatOutput (Ответ)
- In.message → P1.vopros
- P1.prompt → M1.input_value
- M1.text_output → SQL.sql
- SQL.table → P2.rez
- In.message → P2.vopros
- P2.prompt → M2.input_value
- M2.text_output → Out.input_value

## e4 — 17 Внешний API
- `In` — ChatInput (Вопрос)
- `API` — APIRequest (Курсы ЦБ)
- `PA` — ParserComponent (В текст)
- `P` — Prompt Template (Промпт)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `Out` — ChatOutput (Ответ)
- In.message → P.vopros
- API.data → PA.input_data
- PA.parsed_text → P.dannye
- P.prompt → M.input_value
- M.text_output → Out.input_value

## e5 — 18 Поиск в сети
- `In` — ChatInput (Запрос)
- `WS` — UnifiedWebSearch (Поиск)
- `PA` — ParserComponent (В текст)
- `P` — Prompt Template (Промпт)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `Out` — ChatOutput (Ответ)
- In.message → P.zapros
- In.message → WS.query
- WS.results → PA.input_data
- PA.parsed_text → P.naideno
- P.prompt → M.input_value
- M.text_output → Out.input_value

## e6 — 19 Файл по частям
- `F` — File (Документ)
- `SP` — SplitText (Разбить на части)
- `L` — LoopComponent (Цикл)
- `PA` — ParserComponent (Текст части)
- `P` — Prompt Template (Промпт: разметить)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `PD` — ParserComponent (Собрать результат)
- `Out` — ChatOutput (Результат)
- F.message → SP.data_inputs
- SP.dataframe → L.data
- L.item → PA.input_data
- PA.parsed_text → P.punkt
- P.prompt → M.input_value
- M.text_output → L.None
- L.done → PD.input_data
- PD.parsed_text → Out.input_value

## e7 — 20 Вопрос по документу
- `F` — File (Документ)
- `In` — ChatInput (Вопрос)
- `P` — Prompt Template (Промпт)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `Out` — ChatOutput (Ответ)
- F.message → P.dokument
- In.message → P.vopros
- P.prompt → M.input_value
- M.text_output → Out.input_value

## f1 — 21 Код Python
- `PY` — PythonREPLComponent (Сверка кодом)
- `PA` — ParserComponent (В текст)
- `Out` — ChatOutput (Результат)
- PY.results → PA.input_data
- PA.parsed_text → Out.input_value

## f2 — 22 Подпоток
- `In` — ChatInput (Обращение)
- `RF` — RunFlow (Подпоток: 01 Запрос к модели)
- `P` — Prompt Template (Промпт: черновик)
- `M` — ext:openai:OpenAIModelComponent@official (Модель: черновик)
- `Out` — ChatOutput (Ответ)
- In.message → RF.In~input_value
- RF.Out~message → P.tema
- In.message → P.t
- P.prompt → M.input_value
- M.text_output → Out.input_value

## j1 — 41 Ответ по базе Jay Hub
- `In` — ChatInput (Вопрос)
- `Khub` — KhubSearch (Поиск в Jay Hub)
- `Prompt` — Prompt Template (Задание: ответ по базе)
- `Model` — ext:openai:OpenAIModelComponent@official (Модель: ответ)
- `Out` — ChatOutput (Ответ)
- In.message → Khub.query
- In.message → Prompt.vopros
- Khub.chunks → Prompt.fragmenty
- Prompt.prompt → Model.input_value
- Model.text_output → Out.input_value

## n16 — 37 Порог по числу
- `In` — ChatInput (Результат)
- `P` — Prompt Template (Промпт: число)
- `M` — ext:openai:OpenAIModelComponent@official (Модель: число)
- `IF` — ConditionalRouter (Не ниже порога?)
- `Oa` — ChatOutput (Автоматически)
- `Ob` — ChatOutput (Человеку)
- In.message → P.t
- P.prompt → M.input_value
- M.text_output → IF.input_text
- IF.true_result → Oa.input_value
- IF.false_result → Ob.input_value

## n9 — 30 JSON с проверкой кодом
- `In` — ChatInput (Письмо)
- `RP` — CustomComponent (Точка возврата)
- `P` — Prompt Template (Промпт: JSON)
- `M` — ext:openai:OpenAIModelComponent@official (Модель: JSON)
- `C` — CustomComponent (Проверка JSON)
- `IF` — ConditionalRouter (Готово?)
- `Out` — ChatOutput (JSON)
- In.message → RP.vhod
- RP.dalshe → P.zadanie
- P.prompt → M.input_value
- M.text_output → C.tekst
- C.rezultat → IF.input_text
- M.text_output → IF.true_case_message
- IF.true_result → Out.input_value
- IF.false_result → RP.None

## n2 — 24 Агент вызывает агента
- `In` — ChatInput (Запрос)
- `LM` — ext:openai:OpenAIModelComponent@official (Модель главного)
- `LS` — ext:openai:OpenAIModelComponent@official (Модель проверяющего)
- `S` — Agent (Агент-проверяющий (инструмент))
- `A` — Agent (Главный агент)
- `Out` — ChatOutput (Ответ)
- In.message → A.input_value
- LM.model_output → A.model
- LS.model_output → S.model
- S.component_as_tool → A.tools
- A.response → Out.input_value

## n13 — 34 Агент с двумя инструментами
- `In` — ChatInput (Запрос)
- `LM` — ext:openai:OpenAIModelComponent@official (Модель для блока)
- `T1` — UnifiedWebSearch (Поиск в сети (инструмент))
- `T2` — URLComponent (Чтение страницы (инструмент))
- `A` — Agent (Агент)
- `Out` — ChatOutput (Ответ)
- In.message → A.input_value
- LM.model_output → A.model
- T1.component_as_tool → A.tools
- T2.component_as_tool → A.tools
- A.response → Out.input_value

## n17 — 38 Цепочка агентов с ролями
- `In` — ChatInput (Запрос)
- `L1` — ext:openai:OpenAIModelComponent@official (Модель аналитика)
- `A1` — Agent (Агент-аналитик)
- `L2` — ext:openai:OpenAIModelComponent@official (Модель автора)
- `A2` — Agent (Агент-автор)
- `L3` — ext:openai:OpenAIModelComponent@official (Модель редактора)
- `A3` — Agent (Агент-редактор)
- `Out` — ChatOutput (Письмо)
- In.message → A1.input_value
- L1.model_output → A1.model
- A1.response → A2.input_value
- L2.model_output → A2.model
- A2.response → A3.input_value
- L3.model_output → A3.model
- A3.response → Out.input_value

## n18 — 39 Карточка из открытых источников
- `In` — ChatInput (Организация)
- `L1` — ext:openai:OpenAIModelComponent@official (Модель агента)
- `T` — UnifiedWebSearch (Поиск в сети (инструмент))
- `A` — Agent (Агент-сборщик)
- `L2` — ext:openai:OpenAIModelComponent@official (Модель полей)
- `SO` — StructuredOutput (Разложить по полям)
- `PA` — ParserComponent (В текст)
- `Out` — ChatOutput (Карточка)
- In.message → A.input_value
- L1.model_output → A.model
- T.component_as_tool → A.tools
- A.response → SO.input_value
- L2.model_output → SO.model
- SO.dataframe_output → PA.input_data
- PA.parsed_text → Out.input_value

## n11 — 32 Скан или скриншот
- `In` — ChatInput (Скан или скриншот)
- `M` — ext:openai:OpenAIModelComponent@official (Модель: распознать)
- `IF` — ConditionalRouter (Распознано?)
- `O2` — ChatOutput (Специалисту)
- `P` — Prompt Template (Промпт: поля)
- `M2` — ext:openai:OpenAIModelComponent@official (Модель: поля)
- `Out` — ChatOutput (Карточка)
- In.message → M.input_value
- M.text_output → IF.input_text
- IF.true_result → O2.input_value
- IF.false_result → P.t
- P.prompt → M2.input_value
- M2.text_output → Out.input_value

## n14 — 35 Читать Excel
- `X` — CustomComponent (Читать Excel)
- `LM` — ext:openai:OpenAIModelComponent@official (Модель для блока)
- `BR` — BatchRunComponent (Модель по строкам)
- `PA` — ParserComponent (В текст)
- `Out` — ChatOutput (Ответ)
- X.tablica → BR.df
- LM.model_output → BR.model
- BR.batch_results → PA.input_data
- PA.parsed_text → Out.input_value

## n15 — 36 Читать Word с таблицами
- `W` — CustomComponent (Читать Word с таблицами)
- `P` — Prompt Template (Промпт: проверить комплект)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `Out` — ChatOutput (Ответ)
- W.tekst → P.zayavka
- P.prompt → M.input_value
- M.text_output → Out.input_value

## n10 — 31 Расчёт кодом
- `In` — ChatInput (Письмо)
- `P` — Prompt Template (Промпт: JSON)
- `M` — ext:openai:OpenAIModelComponent@official (Модель: извлечь)
- `C` — CustomComponent (Расчёт кодом)
- `P2` — Prompt Template (Промпт: вывод)
- `M2` — ext:openai:OpenAIModelComponent@official (Модель: текст)
- `Out` — ChatOutput (Ответ)
- In.message → P.t
- P.prompt → M.input_value
- M.text_output → C.dannye
- C.rezultat → P2.rez
- P2.prompt → M2.input_value
- M2.text_output → Out.input_value

## n19 — 40 Выжимка и сводка
- `In` — ChatInput (Таблица CSV)
- `TC` — TypeConverterComponent (В таблицу)
- `LM` — ext:openai:OpenAIModelComponent@official (Модель для блока)
- `BR` — BatchRunComponent (Выжимка по каждой строке)
- `PA` — ParserComponent (В текст)
- `P` — Prompt Template (Промпт: сводка)
- `M` — ext:openai:OpenAIModelComponent@official (Модель: сводка)
- `Out` — ChatOutput (Сводка)
- In.message → TC.input_data
- TC.dataframe_output → BR.df
- LM.model_output → BR.model
- BR.batch_results → PA.input_data
- PA.parsed_text → P.vyzhimki
- P.prompt → M.input_value
- M.text_output → Out.input_value

## n5 — 26 Страница и текущая дата
- `In` — ChatInput (Вопрос)
- `U` — URLComponent (Страница)
- `D` — CurrentDate (Сегодня)
- `P` — Prompt Template (Промпт)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `Out` — ChatOutput (Ответ)
- U.raw_results → P.stranica
- D.current_date → P.data
- In.message → P.v
- P.prompt → M.input_value
- M.text_output → Out.input_value

## n6 — 27 Файл на выходе
- `In` — ChatInput (Обращения)
- `P` — Prompt Template (Промпт: таблица)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `F` — CustomComponent (Создать файл)
- `Out` — ChatOutput (Ссылка)
- In.message → P.t
- P.prompt → M.input_value
- M.text_output → F.tekst
- F.ssylka → Out.input_value

## n7 — 28 Сверка двух редакций
- `A` — TextInput (Редакция 1)
- `B` — TextInput (Редакция 2)
- `D` — CustomComponent (Сверка двух текстов)
- `P` — Prompt Template (Промпт: что изменилось)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `Out` — ChatOutput (Отчёт)
- A.text → D.pervyi
- B.text → D.vtoroi
- D.otlichiya → P.otl
- P.prompt → M.input_value
- M.text_output → Out.input_value

## n1 — 23 Сравнение моделей
- `In` — ChatInput (Обращение)
- `P` — Prompt Template (Промпт)
- `Ma` — ext:openai:OpenAIModelComponent@official (DeepSeek)
- `Mb` — ext:openai:OpenAIModelComponent@official (Qwen)
- `Mc` — ext:openai:OpenAIModelComponent@official (Alice)
- `Pc` — Prompt Template (Сводка)
- `Out` — ChatOutput (Сравнение)
- In.message → P.t
- P.prompt → Ma.input_value
- P.prompt → Mb.input_value
- P.prompt → Mc.input_value
- Ma.text_output → Pc.a
- Mb.text_output → Pc.b
- Mc.text_output → Pc.c
- Pc.prompt → Out.input_value

## n4 — 25 Проверка чувствительных данных
- `In` — ChatInput (Текст)
- `G` — GuardrailValidatorV2 (Проверка данных)
- `Op` — ChatOutput (Можно отправлять в модель)
- `Of` — ChatOutput (Остановлено)
- In.message → G.input_text
- G.pass_result → Op.input_value
- G.failed_result → Of.input_value

## n8 — 29 Действие в другой системе
- `In` — ChatInput (Обращение)
- `P` — Prompt Template (Промпт: тема)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `S` — CustomComponent (Отправить в систему)
- `Out` — ChatOutput (Ответ системы)
- In.message → P.t
- P.prompt → M.input_value
- M.text_output → S.tekst
- S.otvet → Out.input_value

## n12 — 33 Запуск от другой системы
- `WH` — Webhook (Вход от другой системы)
- `PA` — ParserComponent (Поля из запроса)
- `P` — Prompt Template (Промпт: тема)
- `M` — ext:openai:OpenAIModelComponent@official (Модель)
- `Out` — ChatOutput (Результат)
- WH.output_data → PA.input_data
- PA.parsed_text → P.t
- P.prompt → M.input_value
- M.text_output → Out.input_value
name: 03 Агент + SQL
description: Агент по правилам формирует SQL, база возвращает таблицу

nodes:
  Vhod: ChatInput
  Pravila: Prompt Template
  Model: ext:openai:OpenAIModelComponent@official
  G: Agent
  DB: SQLComponent
  Otvet: ChatOutput

edges:
  Vhod.message -> G.input_value
  Pravila.prompt -> G.system_prompt
  Model.model_output -> G.model
  G.response -> DB.query
  DB.run_sql_query -> Otvet.input_value

config:
  Pravila.template: |
    Ты — помощник по данным. Пользователь задаёт вопрос.
    Верни ТОЛЬКО SQL-запрос для PostgreSQL: без пояснений, без markdown-блоков,
    без точки с запятой в конце.
    Если вопрос не про данные — верни SELECT 'не могу помочь' AS message.
  Model.openai_api_base: <адрес модели из профиля стенда>
  Model.model_name: <имя модели из профиля стенда>
  Model.temperature: 0.1
  Model.max_tokens: 400
